"""
🔄 Script para Executar Backup Manual
Execute este script para fazer backup imediato do banco de dados.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backup_service import criar_backup


def main():
    """Executa backup manual."""
    print("🔒 EggVault - Backup do Banco de Dados\n")
    
    try:
        sucesso = criar_backup(upload_to_drive=True, cleanup=True)
        
        if sucesso:
            print("\n✅ Backup concluído com sucesso!")
            sys.exit(0)
        else:
            print("\n❌ Erro ao realizar backup!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        print("\nVerifique se configurou as credenciais no .env:")
        print("  - GOOGLE_DRIVE_CLIENT_ID")
        print("  - GOOGLE_DRIVE_CLIENT_SECRET")
        print("  - GOOGLE_DRIVE_REFRESH_TOKEN")
        sys.exit(1)


if __name__ == '__main__':
    main()
