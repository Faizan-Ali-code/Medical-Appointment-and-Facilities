@echo off
REM One-time setup: virtual environment, packages, settings file, database with sample data.
cd /d "%~dp0"
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
if not exist .env (
    copy .env.example .env >nul
    REM a random SECRET_KEY for this installation
    venv\Scripts\python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
)
venv\Scripts\flask --app run init-db
echo.
echo Setup complete. Start the app with run.bat
