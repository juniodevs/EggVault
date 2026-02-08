"""
🔍 Script de Verificação do Sistema de Backup
Verifica se o sistema de backup está configurado e funcionando corretamente.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


class BackupVerifier:
    """Verifica o funcionamento do sistema de backup."""
    
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent / 'backups'
        self.database_url = os.environ.get('DATABASE_URL', '').strip()
        self.use_postgres = bool(self.database_url and self.database_url.startswith('postgresql'))
        self.sqlite_path = Path(os.environ.get(
            'OVOS_DB_PATH',
            Path(__file__).parent.parent / 'ovos.db'
        ))
        
        self.issues = []
        self.warnings = []
        self.success = []
        
    def print_header(self):
        """Imprime cabeçalho."""
        print("=" * 70)
        print("🔍 VERIFICAÇÃO DO SISTEMA DE BACKUP".center(70))
        print("=" * 70)
        print()
    
    def print_section(self, title):
        """Imprime seção."""
        print(f"\n{'─' * 70}")
        print(f"▶ {title}")
        print('─' * 70)
    
    def check_backup_directory(self):
        """Verifica se o diretório de backup existe."""
        self.print_section("1. Diretório de Backup")
        
        if self.backup_dir.exists():
            print(f"✅ Diretório de backup existe: {self.backup_dir}")
            self.success.append("Diretório de backup configurado")
            return True
        else:
            print(f"❌ Diretório de backup não existe: {self.backup_dir}")
            self.issues.append("Diretório de backup não encontrado")
            return False
    
    def check_existing_backups(self):
        """Verifica backups existentes."""
        self.print_section("2. Backups Existentes")
        
        if not self.backup_dir.exists():
            print("⚠️  Diretório de backup não existe")
            return False
        
        # Busca backups PostgreSQL e SQLite
        postgres_backups = sorted(
            self.backup_dir.glob('EggVault_postgres_backup_*.sql'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        sqlite_backups = sorted(
            self.backup_dir.glob('EggVault_sqlite_backup_*.db'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        all_backups = postgres_backups + sqlite_backups
        
        if not all_backups:
            print("❌ Nenhum backup encontrado")
            self.issues.append("Nenhum backup no diretório")
            return False
        
        print(f"✅ Encontrados {len(all_backups)} backup(s):")
        
        # Mostra últimos 5 backups
        for backup in all_backups[:5]:
            size_mb = backup.stat().st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(backup.stat().st_mtime)
            age = datetime.now() - modified
            
            print(f"   📦 {backup.name}")
            print(f"      Tamanho: {size_mb:.2f} MB")
            print(f"      Data: {modified.strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"      Idade: {self.format_age(age)}")
            
            # Verifica se o backup é válido
            if size_mb < 0.001:
                print(f"      ⚠️  AVISO: Backup muito pequeno (pode estar vazio)")
                self.warnings.append(f"Backup {backup.name} muito pequeno")
        
        # Verifica idade do último backup
        latest_backup = all_backups[0]
        modified = datetime.fromtimestamp(latest_backup.stat().st_mtime)
        age = datetime.now() - modified
        
        if age > timedelta(days=7):
            print(f"\n⚠️  AVISO: Último backup tem mais de 7 dias")
            self.warnings.append("Último backup está desatualizado")
        elif age > timedelta(days=1):
            print(f"\n⚠️  AVISO: Último backup tem mais de 1 dia")
            self.warnings.append("Último backup não é recente")
        else:
            print(f"\n✅ Último backup é recente")
            self.success.append("Backups estão atualizados")
        
        return True
    
    def check_database_connection(self):
        """Verifica conexão com banco de dados."""
        self.print_section("3. Conexão com Banco de Dados")
        
        # PostgreSQL
        if self.use_postgres:
            print("🐘 Verificando PostgreSQL...")
            try:
                import psycopg2
                from urllib.parse import urlparse
                
                parsed = urlparse(self.database_url)
                conn = psycopg2.connect(
                    host=parsed.hostname,
                    port=parsed.port or 5432,
                    user=parsed.username,
                    password=parsed.password,
                    database=parsed.path.lstrip('/')
                )
                conn.close()
                print("✅ Conexão com PostgreSQL OK")
                self.success.append("PostgreSQL acessível")
                
                # Verifica pg_dump
                import subprocess
                try:
                    result = subprocess.run(
                        ['pg_dump', '--version'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"✅ pg_dump disponível: {result.stdout.strip()}")
                        self.success.append("pg_dump instalado")
                    else:
                        print("❌ pg_dump não está funcionando")
                        self.issues.append("pg_dump não funcional")
                except FileNotFoundError:
                    print("❌ pg_dump não encontrado no PATH")
                    self.issues.append("pg_dump não instalado")
                
                return True
                
            except ImportError:
                print("❌ Biblioteca psycopg2 não instalada")
                self.issues.append("psycopg2 não instalado")
                return False
            except Exception as e:
                print(f"❌ Erro ao conectar PostgreSQL: {e}")
                self.issues.append(f"Erro PostgreSQL: {e}")
                return False
        
        # SQLite
        elif self.sqlite_path.exists():
            print("📁 Verificando SQLite...")
            try:
                import sqlite3
                conn = sqlite3.connect(str(self.sqlite_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                count = cursor.fetchone()[0]
                conn.close()
                
                print(f"✅ Banco SQLite OK ({count} tabelas)")
                self.success.append("SQLite acessível")
                return True
                
            except Exception as e:
                print(f"❌ Erro ao conectar SQLite: {e}")
                self.issues.append(f"Erro SQLite: {e}")
                return False
        
        else:
            print("❌ Nenhum banco de dados configurado")
            self.issues.append("Banco de dados não configurado")
            return False
    
    def check_google_drive_config(self):
        """Verifica configuração do Google Drive."""
        self.print_section("4. Configuração Google Drive")
        
        client_id = os.environ.get('GOOGLE_DRIVE_CLIENT_ID', '').strip()
        client_secret = os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET', '').strip()
        refresh_token = os.environ.get('GOOGLE_DRIVE_REFRESH_TOKEN', '').strip()
        folder_id = os.environ.get('GDRIVE_BACKUP_FOLDER_ID', '').strip()
        
        has_config = bool(client_id and client_secret and refresh_token)
        
        print(f"{'✅' if client_id else '❌'} GOOGLE_DRIVE_CLIENT_ID: {'Configurado' if client_id else 'Não configurado'}")
        print(f"{'✅' if client_secret else '❌'} GOOGLE_DRIVE_CLIENT_SECRET: {'Configurado' if client_secret else 'Não configurado'}")
        print(f"{'✅' if refresh_token else '❌'} GOOGLE_DRIVE_REFRESH_TOKEN: {'Configurado' if refresh_token else 'Não configurado'}")
        print(f"{'✅' if folder_id else '⚠️ '} GDRIVE_BACKUP_FOLDER_ID: {'Configurado' if folder_id else 'Não configurado (opcional)'}")
        
        if not has_config:
            print("\n❌ Google Drive não está configurado")
            self.issues.append("Google Drive não configurado")
            print("\n💡 Para configurar o Google Drive:")
            print("   1. Configure CLIENT_ID e CLIENT_SECRET no .env")
            print("   2. Execute: python -c \"from services.backup_service import obter_refresh_token; obter_refresh_token()\"")
            return False
        
        # Tenta autenticar
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            
            if creds.expired or not creds.valid:
                creds.refresh(Request())
            
            service = build('drive', 'v3', credentials=creds)
            
            # Testa listando arquivos
            results = service.files().list(
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            print("\n✅ Autenticação Google Drive OK")
            self.success.append("Google Drive configurado e funcional")
            return True
            
        except ImportError as e:
            print(f"\n❌ Bibliotecas do Google não instaladas: {e}")
            self.issues.append("Bibliotecas Google não instaladas")
            print("\n💡 Instale com: pip install google-auth google-auth-oauthlib google-api-python-client")
            return False
        except Exception as e:
            print(f"\n❌ Erro ao autenticar Google Drive: {e}")
            self.issues.append(f"Erro autenticação Google: {e}")
            return False
    
    def test_backup(self):
        """Testa criação de backup."""
        self.print_section("5. Teste de Backup")
        
        print("🧪 Executando backup de teste...")
        print("   (sem upload para Google Drive e sem limpeza)")
        print()
        
        try:
            from services.backup_service import criar_backup
            
            # Executa backup sem upload e sem cleanup
            success = criar_backup(upload_to_drive=False, cleanup=False)
            
            if success:
                print("\n✅ Teste de backup executado com sucesso!")
                self.success.append("Backup de teste funcionou")
                return True
            else:
                print("\n❌ Teste de backup falhou")
                self.issues.append("Backup de teste falhou")
                return False
                
        except Exception as e:
            print(f"\n❌ Erro no teste de backup: {e}")
            self.issues.append(f"Erro no teste: {e}")
            return False
    
    def print_summary(self):
        """Imprime resumo final."""
        print("\n" + "=" * 70)
        print("📊 RESUMO DA VERIFICAÇÃO".center(70))
        print("=" * 70)
        
        if self.success:
            print(f"\n✅ SUCESSOS ({len(self.success)}):")
            for item in self.success:
                print(f"   • {item}")
        
        if self.warnings:
            print(f"\n⚠️  AVISOS ({len(self.warnings)}):")
            for item in self.warnings:
                print(f"   • {item}")
        
        if self.issues:
            print(f"\n❌ PROBLEMAS ({len(self.issues)}):")
            for item in self.issues:
                print(f"   • {item}")
        
        print("\n" + "=" * 70)
        
        if not self.issues:
            print("✅ SISTEMA DE BACKUP ESTÁ FUNCIONANDO!".center(70))
            print("=" * 70)
            return True
        else:
            print("❌ SISTEMA DE BACKUP TEM PROBLEMAS".center(70))
            print("=" * 70)
            return False
    
    @staticmethod
    def format_age(age: timedelta) -> str:
        """Formata idade do backup."""
        if age.days > 0:
            return f"{age.days} dia(s)"
        elif age.seconds >= 3600:
            hours = age.seconds // 3600
            return f"{hours} hora(s)"
        elif age.seconds >= 60:
            minutes = age.seconds // 60
            return f"{minutes} minuto(s)"
        else:
            return f"{age.seconds} segundo(s)"
    
    def run(self, test_backup=False):
        """Executa todas as verificações."""
        self.print_header()
        
        self.check_backup_directory()
        self.check_existing_backups()
        self.check_database_connection()
        self.check_google_drive_config()
        
        if test_backup:
            self.test_backup()
        
        return self.print_summary()


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verifica se o sistema de backup está funcionando'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Executa um backup de teste (local, sem upload)'
    )
    parser.add_argument(
        '--full-test',
        action='store_true',
        help='Executa backup completo de teste (COM upload para Google Drive)'
    )
    
    args = parser.parse_args()
    
    verifier = BackupVerifier()
    success = verifier.run(test_backup=args.test or args.full_test)
    
    # Se solicitou teste completo, faz backup com upload
    if args.full_test and success:
        print("\n" + "=" * 70)
        print("🚀 EXECUTANDO BACKUP COMPLETO DE TESTE".center(70))
        print("=" * 70)
        print()
        
        try:
            from services.backup_service import criar_backup
            criar_backup(upload_to_drive=True, cleanup=True)
        except Exception as e:
            print(f"\n❌ Erro no backup completo: {e}")
            sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
