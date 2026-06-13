@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Run setup.bat first.
    exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

echo Starting Best Time to Chat at http://127.0.0.1:5050
python -m flask --app app run --port 5050
