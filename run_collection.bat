@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing pinned virtual environment .venv\Scripts\python.exe
  exit /b 4
)
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1
".venv\Scripts\python.exe" -B -X utf8 -m scripts.collection.run %*
exit /b %errorlevel%
