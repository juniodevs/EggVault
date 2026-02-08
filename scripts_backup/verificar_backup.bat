@echo off
REM ========================================
REM Script para Verificar Sistema de Backup
REM ========================================

echo.
echo ============================================
echo   Verificacao do Sistema de Backup
echo ============================================
echo.

cd /d "%~dp0.."

REM Ativa ambiente virtual se existir
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Executa verificacao
python scripts_backup\verificar_backup.py %*

pause
