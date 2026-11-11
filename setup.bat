@echo off
REM One-time setup: create virtual environment, install packages, create database.
cd /d "%~dp0"
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
if not exist .env (
    copy .env.example .env >nul
    REM a random SECRET_KEY for this installation (signs the session cookies)
    venv\Scripts\python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
)
venv\Scripts\flask --app run init-db
echo Loading demo hospitals, doctors and facilities...
venv\Scripts\flask --app run seed-demo
echo.
echo Setup complete. Note the sample logins printed above, then start the app with run.bat
