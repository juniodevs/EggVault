"""
📊 Status Rápido do Sistema de Backup
Mostra um resumo visual do status do backup.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Adiciona diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


def get_status_emoji(condition):
    """Retorna emoji baseado na condição."""
    return "✅" if condition else "❌"


def print_status():
    """Imprime status rápido."""
    backup_dir = Path(__file__).parent.parent / 'backups'
    
    print("\n" + "═" * 60)
    print("📊 STATUS DO SISTEMA DE BACKUP".center(60))
    print("═" * 60 + "\n")
    
    # Diretório
    dir_exists = backup_dir.exists()
    print(f"{get_status_emoji(dir_exists)} Diretório: {backup_dir}")
    
    if not dir_exists:
        print("\n❌ Sistema de backup não configurado!\n")
        return
    
    # Backups
    all_backups = sorted(
        list(backup_dir.glob('EggVault_postgres_backup_*.sql')) + 
        list(backup_dir.glob('EggVault_sqlite_backup_*.db')),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    backup_count = len(all_backups)
    print(f"{get_status_emoji(backup_count > 0)} Total de backups: {backup_count}")
    
    if backup_count > 0:
        latest = all_backups[0]
        modified = datetime.fromtimestamp(latest.stat().st_mtime)
        age = datetime.now() - modified
        size_mb = latest.stat().st_size / (1024 * 1024)
        
        is_recent = age < timedelta(days=1)
        
        print(f"\n📦 Último backup:")
        print(f"   Nome: {latest.name}")
        print(f"   {get_status_emoji(is_recent)} Idade: {format_age(age)}")
        print(f"   Tamanho: {size_mb:.2f} MB")
        print(f"   Data: {modified.strftime('%d/%m/%Y %H:%M')}")
    
    # Banco
    database_url = os.environ.get('DATABASE_URL', '').strip()
    use_postgres = bool(database_url and database_url.startswith('postgresql'))
    sqlite_path = Path(os.environ.get('OVOS_DB_PATH', 'ovos.db'))
    
    db_type = "PostgreSQL" if use_postgres else ("SQLite" if sqlite_path.exists() else "Nenhum")
    print(f"\n💾 Banco de dados: {db_type}")
    
    # Google Drive
    has_gdrive = bool(
        os.environ.get('GOOGLE_DRIVE_CLIENT_ID') and
        os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET') and
        os.environ.get('GOOGLE_DRIVE_REFRESH_TOKEN')
    )
    print(f"{get_status_emoji(has_gdrive)} Google Drive: {'Configurado' if has_gdrive else 'Não configurado'}")
    
    # Status geral
    print("\n" + "─" * 60)
    if backup_count > 0 and is_recent:
        print("✅ Sistema funcionando normalmente".center(60))
    elif backup_count > 0:
        print("⚠️  Backup desatualizado - considere executar um novo".center(60))
    else:
        print("❌ Nenhum backup encontrado - execute backup agora!".center(60))
    print("─" * 60)
    
    # Comandos úteis
    print("\n💡 Comandos úteis:")
    print("   python scripts_backup/verificar_backup.py        - Verificação completa")
    print("   python scripts_backup/backup_manual.py           - Executar backup")
    print("   python scripts_backup/verificar_backup.py --test - Testar backup")
    
    print("\n" + "═" * 60 + "\n")


def format_age(age: timedelta) -> str:
    """Formata idade."""
    if age.days > 0:
        return f"{age.days} dia(s) atrás"
    elif age.seconds >= 3600:
        hours = age.seconds // 3600
        return f"{hours} hora(s) atrás"
    elif age.seconds >= 60:
        minutes = age.seconds // 60
        return f"{minutes} minuto(s) atrás"
    else:
        return f"{age.seconds} segundo(s) atrás"


if __name__ == '__main__':
    print_status()
