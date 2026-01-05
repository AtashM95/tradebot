@echo off
setlocal
cd /d "%~dp0"

py -3.10 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.10 bulunamadi. Lutfen Python 3.10 kurun.
  exit /b 1
)

if not exist .venv (
  py -3.10 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
  echo .env olusturuldu. Lutfen API anahtarlarini girin.
)

python -m compileall src
echo Kurulum tamamlandi.
