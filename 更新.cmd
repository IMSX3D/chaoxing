@echo off
setlocal
cd /d "%~dp0"

echo ================ git pull ================
git pull --ff-only
if errorlevel 1 (
    echo.
    echo [FAILED] pull failed. Common causes:
    echo   1. cannot reach github -- check hosts for "127.0.0.1 github.com"
    echo      (SteamTools leaves it behind when killed; reopen it or delete that line)
    echo   2. local edits to upstream files -- run git stash or check git status
    echo   3. upstream rewrote history -- git fetch --all then git reset --hard origin/main
    pause
    exit /b 1
)

echo.
echo ================ last 5 commits ================
git log --oneline -5

echo.
choice /c YN /m "Check and update python dependencies"
if errorlevel 2 goto done

echo.
echo ================ update dependencies ================
set "UV_CACHE_DIR=%~dp0.uv-cache"
uv pip install --python ".venv\Scripts\python.exe" -r requirements.txt --find-links "%~dp0vendor" --default-index https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 echo [WARN] dependency update failed, you can rerun the command above later

:done
echo.
pause