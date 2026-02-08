@echo off
REM Script para executar backup manual do EggVault
cd /d "%~dp0.."

REM Ativa ambiente virtual se existir
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python scripts_backup\backup_manual.py
pause
