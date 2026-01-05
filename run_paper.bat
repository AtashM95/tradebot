@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\activate (
  echo Sanal ortam bulunamadi. Lutfen once install_windows.bat calistirin.
  exit /b 1
)

call .venv\Scripts\activate
set APP_MODE=paper
echo Sunucu basliyor: http://127.0.0.1:5000
python -m src.app.main
