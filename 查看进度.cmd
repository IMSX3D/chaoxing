@echo off
setlocal
cd /d "%~dp0"

rem READ-ONLY: only reads course / chapter lists, never studies or submits
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run these in this folder first:
    echo   uv venv --python 3.13 .venv
    echo   uv pip install --python .venv\Scripts\python.exe -r requirements.txt
    pause
    exit /b 1
)

if not exist "config.ini" (
    echo [ERROR] config.ini not found. Copy config_template.ini and fill it in first.
    pause
    exit /b 1
)

rem no arguments: check all courses and write the Markdown report
rem with arguments: pass them through, e.g.  --course 266224008 --todo
if "%~1"=="" (
    ".venv\Scripts\python.exe" progress.py --md --todo
) else (
    ".venv\Scripts\python.exe" progress.py %*
)

echo.
echo ================================================
echo done, exit code = %ERRORLEVEL%
echo ================================================
pause