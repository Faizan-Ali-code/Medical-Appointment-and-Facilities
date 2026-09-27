@echo off
REM One-time setup: create virtual environment, install packages, create database.
cd /d "%~dp0"
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements-dev.txt
if not exist .env copy .env.example .env
venv\Scripts\python init_db.py
echo Loading demo hospitals, doctors and facilities...
venv\Scripts\flask --app run seed-demo
echo.
echo Setup complete. Start the app with run.bat
