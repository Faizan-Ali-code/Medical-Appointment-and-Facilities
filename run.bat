@echo off
REM Start the app using the project's virtual environment.
cd /d "%~dp0"
if not exist venv (
    echo Virtual environment not found. Run setup.bat first.
    exit /b 1
)
echo Open http://127.0.0.1:5000 in your browser
venv\Scripts\python run.py
