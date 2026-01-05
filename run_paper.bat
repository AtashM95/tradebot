@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\activate (
  echo Sanal ortam bulunamadi. Lutfen once install_windows.bat calistirin.
  exit /b 1
)

call .venv\Scripts\activate
set APP_MODE=paper
if not exist .env (
  echo .env bulunamadi. install_windows.bat calistirin veya .env.example dosyasini kopyalayin.
  echo API anahtari yoksa mock mod aciliyor.
  set TRADEBOT_MOCK_MODE=1
)
echo Sunucu basliyor: http://127.0.0.1:5000
python -m src.app.main
