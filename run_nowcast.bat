@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. Install the repository environment first.
  exit /b 1
)
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1
if exist "results\operations\current_production.json" (
  ".venv\Scripts\python.exe" -m scripts.production.update %*
) else (
  ".venv\Scripts\python.exe" "scripts\operations\run_update.py" %*
)
exit /b %errorlevel%
