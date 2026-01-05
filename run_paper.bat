@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not exist .venv\Scripts\activate (
  echo Sanal ortam bulunamadi. Lutfen once install_windows.bat calistirin.
  exit /b 1
)

call .venv\Scripts\activate
set APP_MODE=paper
if not exist .env (
  echo .env bulunamadi. install_windows.bat calistirin veya .env.example dosyasini kopyalayin.
  exit /b 1
)
set ALPACA_PAPER_API_KEY_VALUE=
set ALPACA_PAPER_SECRET_KEY_VALUE=
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "ALPACA_PAPER_API_KEY=" .env`) do set ALPACA_PAPER_API_KEY_VALUE=%%B
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "ALPACA_PAPER_SECRET_KEY=" .env`) do set ALPACA_PAPER_SECRET_KEY_VALUE=%%B
if "!ALPACA_PAPER_API_KEY_VALUE!"=="" (
  echo Alpaca paper API key bulunamadi. Mock mod aciliyor.
  set TRADEBOT_MOCK_MODE=1
)
if "!ALPACA_PAPER_SECRET_KEY_VALUE!"=="" (
  echo Alpaca paper secret key bulunamadi. Mock mod aciliyor.
  set TRADEBOT_MOCK_MODE=1
)
echo Sunucu basliyor: http://127.0.0.1:5000
python -m src.app.main
