@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run these in this folder first:
    echo   uv venv --python 3.13 .venv
    echo   uv pip install --python .venv\Scripts\python.exe -r requirements.txt
    pause
    exit /b 1
)

if not exist "config.ini" (
    echo [INFO] config.ini not found, copying from config_template.ini ...
    copy /y "config_template.ini" "config.ini" >nul
    notepad "config.ini"
)

rem no arguments: run with config.ini; with arguments: pass them through
if "%~1"=="" (
    ".venv\Scripts\python.exe" main.py -c config.ini
) else (
    ".venv\Scripts\python.exe" main.py %*
)

echo.
echo ================================================
echo done, exit code = %ERRORLEVEL%
echo ================================================
pause