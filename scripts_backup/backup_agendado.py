"""
⏰ Script para Backup Agendado
Configure este script para rodar automaticamente (cronjob, Task Scheduler, etc).
"""

import sys
from pathlib import Path
import schedule
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backup_service import criar_backup


def job():
    """Tarefa de backup agendado."""
    print(f"\n⏰ Iniciando backup agendado...")
    try:
        criar_backup(upload_to_drive=True, cleanup=True)
    except Exception as e:
        print(f"❌ Erro no backup agendado: {e}")


def main():
    """Configura e executa agendamento de backups."""
    
    # Configuração do agendamento
    # Opções: 
    # - schedule.every().hour.do(job)
    # - schedule.every().day.at("03:00").do(job)
    # - schedule.every().monday.do(job)
    # - schedule.every(6).hours.do(job)
    
    # Backup diário às 3h da manhã
    schedule.every().day.at("03:00").do(job)
    
    print("⏰ Serviço de Backup Agendado iniciado")
    print("   Backup diário às 03:00")
    print("   Pressione Ctrl+C para parar\n")
    
    # Executa um backup imediato
    print("🚀 Executando backup inicial...")
    job()
    
    # Loop de agendamento
    while True:
        schedule.run_pending()
        time.sleep(60)  # Checa a cada minuto


if __name__ == '__main__':
    main()
