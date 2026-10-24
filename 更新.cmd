@echo off
setlocal
cd /d "%~dp0"

echo ================ git pull (from fork: github/main) ================
git pull --ff-only github main
if errorlevel 1 (
    echo.
    echo [FAILED] pull failed. Common causes:
    echo   1. cannot reach ssh.github.com:443 -- check hosts / proxy, or run: ssh -T -p 443 git@ssh.github.com
    echo      (our remotes use SSH over 443, so plain github.com hijack does not matter)
    echo   2. local edits to upstream files -- run git stash or check git status
    echo   3. fork rewrote history -- git fetch github then git reset --hard github/main
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