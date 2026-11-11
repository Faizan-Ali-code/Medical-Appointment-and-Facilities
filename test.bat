@echo off
REM Run the full test suite with coverage on a temporary database (real data is not touched).
REM HTML coverage report: htmlcov\index.html
cd /d "%~dp0"
venv\Scripts\python -m pytest --cov --cov-report=term --cov-report=html %*
