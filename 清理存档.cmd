@echo off
setlocal
cd /d "%~dp0"

rem Delete archived progress reports older than 7 days.
rem Never touches the latest report and never changes progress.py behaviour.
if not exist "clean_reports.ps1" (
    echo [ERROR] clean_reports.ps1 not found next to this file.
    pause
    exit /b 1
)

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0clean_reports.ps1" %*

echo.
echo ================================================
echo done, exit code = %ERRORLEVEL%
echo ================================================
pause
