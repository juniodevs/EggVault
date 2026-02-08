import os
import subprocess
from datetime import datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class BackupService:
    """Gerencia backups do banco de dados para Google Drive."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        self.database_url = os.environ.get('DATABASE_URL', '').strip()
        self.use_postgres = bool(self.database_url and self.database_url.startswith('postgresql'))
        self.sqlite_path = os.environ.get(
            'OVOS_DB_PATH',
            Path(__file__).parent.parent / 'ovos.db'
        )
        
        self.client_id = os.environ.get('GOOGLE_DRIVE_CLIENT_ID', '').strip()
        self.client_secret = os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET', '').strip()
        self.refresh_token = os.environ.get('GOOGLE_DRIVE_REFRESH_TOKEN', '').strip()
        self.drive_folder_id = os.environ.get('GDRIVE_BACKUP_FOLDER_ID', '').strip()
    
    def authenticate(self):
        """Autentica com Google Drive API usando credenciais do .env."""
        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise ValueError(
                "Credenciais do Google Drive não configuradas no .env\n"
                "Configure: GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_REFRESH_TOKEN"
            )
        
        creds = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES
        )
        
        if creds.expired or not creds.valid:
            creds.refresh(Request())
        
        return build('drive', 'v3', credentials=creds)
    
    def backup_postgres(self):
        """Cria backup do PostgreSQL / usando pg_dump."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'postgres_backup_{timestamp}.sql'
        
        print(f"📦 Criando backup do PostgreSQL")
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.database_url)
            
            env = os.environ.copy()
            env['PGPASSWORD'] = parsed.password
            
            cmd = [
                'pg_dump',
                '-h', parsed.hostname,
                '-U', parsed.username,
                '-d', parsed.path.lstrip('/'),
                '-F', 'p',  # Plain text format
                '-f', str(backup_file)
            ]
            
            if parsed.port:
                cmd.extend(['-p', str(parsed.port)])
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Erro no pg_dump: {result.stderr}")
            
            print(f"✅ Backup PostgreSQL criado: {backup_file}")
            return backup_file
            
        except Exception as e:
            print(f"❌ Erro ao fazer backup PostgreSQL: {e}")
            print(f"   Certifique-se de que pg_dump está instalado e acessível.")
            raise
    
    def backup_sqlite(self):
        """Cria backup do SQLite copiando o arquivo."""
        import shutil
        
        if not Path(self.sqlite_path).exists():
            print(f"⚠️  Banco SQLite não encontrado: {self.sqlite_path}")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'sqlite_backup_{timestamp}.db'
        
        print(f"📦 Criando backup do SQLite...")
        
        try:
            shutil.copy2(self.sqlite_path, backup_file)
            print(f"✅ Backup SQLite criado: {backup_file}")
            return backup_file
        except Exception as e:
            print(f"❌ Erro ao fazer backup SQLite: {e}")
            raise
    
    def upload_to_drive(self, file_path):
        """Faz upload de um arquivo para o Google Drive."""
        try:
            service = self.authenticate()
            
            file_metadata = {
                'name': Path(file_path).name
            }
            
            # Se especificou uma pasta, adiciona o parent
            if self.drive_folder_id:
                file_metadata['parents'] = [self.drive_folder_id]
            
            media = MediaFileUpload(
                str(file_path),
                resumable=True
            )
            
            print(f"☁️  Enviando para Google Drive...")
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            print(f"✅ Upload concluído!")
            print(f"   ID: {file.get('id')}")
            print(f"   Link: {file.get('webViewLink')}")
            
            return file
            
        except Exception as e:
            print(f"❌ Erro ao fazer upload para Google Drive: {e}")
            raise
        
    def cleanup_old_backups(self, keep_last=5):
        """Remove backups locais antigos, mantendo apenas os últimos N."""
        backups = sorted(self.backup_dir.glob('*_backup_*'), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if len(backups) > keep_last:
            print(f"🧹 Limpando backups antigos (mantendo {keep_last})...")
            for backup in backups[keep_last:]:
                backup.unlink()
                print(f"   Removido: {backup.name}")
    
    def run_backup(self, upload_to_drive=True, cleanup=True):
        """Executa o processo completo de backup."""
        print("=" * 60)
        print("🔒 INICIANDO BACKUP DO BANCO DE DADOS")
        print("=" * 60)
        print()
        
        backup_files = []
        
        # Backup PostgreSQL
        if self.use_postgres:
            try:
                backup_file = self.backup_postgres()
                backup_files.append(backup_file)
            except Exception as e:
                print(f"⚠️  Falha no backup PostgreSQL: {e}")
        
        # Backup SQLite
        if Path(self.sqlite_path).exists():
            try:
                backup_file = self.backup_sqlite()
                if backup_file:
                    backup_files.append(backup_file)
            except Exception as e:
                print(f"⚠️  Falha no backup SQLite: {e}")
        
        if not backup_files:
            print("❌ Nenhum backup foi criado!")
            return False
        
        # Upload para Google Drive
        if upload_to_drive:
            print()
            for backup_file in backup_files:
                try:
                    self.upload_to_drive(backup_file)
                except Exception as e:
                    print(f"⚠️  Falha no upload de {backup_file.name}: {e}")
        
        # Limpeza de backups antigos
        if cleanup:
            print()
            self.cleanup_old_backups(keep_last=5)
        
        print()
        print("=" * 60)
        print("✅ BACKUP CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        
        return True


def criar_backup(upload_to_drive=True, cleanup=True):
    """Função de conveniência para criar backup."""
    service = BackupService()
    return service.run_backup(upload_to_drive=upload_to_drive, cleanup=cleanup)


def obter_refresh_token():
    """
    Helper para obter o refresh token do Google Drive.
    Execute: python -c "from services.backup_service import obter_refresh_token; obter_refresh_token()"
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    print("=" * 60)
    print("🔑 OBTER REFRESH TOKEN DO GOOGLE DRIVE")
    print("=" * 60)
    print()
    
    client_id = input("CLIENT_ID: ").strip()
    client_secret = input("CLIENT_SECRET: ").strip()
    
    if not client_id or not client_secret:
        print("❌ CLIENT_ID e CLIENT_SECRET são obrigatórios!")
        return
    
    import json
    import tempfile
    
    credentials = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(credentials, f)
        temp_file = f.name
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            temp_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        print()
        print("🌐 Abrindo navegador para autenticação...")
        print("   Faça login e autorize o aplicativo")
        print()
        
        creds = flow.run_local_server(port=0)
        
        print()
        print("✅ Autenticação bem-sucedida!")
        print()
        print("📝 Adicione ao seu arquivo .env:")
        print("=" * 60)
        print(f"GOOGLE_DRIVE_CLIENT_ID={client_id}")
        print(f"GOOGLE_DRIVE_CLIENT_SECRET={client_secret}")
        print(f"GOOGLE_DRIVE_REFRESH_TOKEN={creds.refresh_token}")
        print("=" * 60)
        print()
        
    finally:
        import os
        os.unlink(temp_file)


if __name__ == '__main__':
    criar_backup()
