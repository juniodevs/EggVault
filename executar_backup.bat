@echo off
REM Script para executar backup manual do EggVault
cd /d "%~dp0"
python backup_manual.py
pause
