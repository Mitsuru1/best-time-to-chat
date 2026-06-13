@echo off
setlocal

cd /d "%~dp0"

echo Setting up Best Time to Chat...

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto error
) else (
    echo Virtual environment already exists.
)

echo Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

echo Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo Initializing database...
python -m flask --app app init-db
if errorlevel 1 goto error

echo.
echo Setup complete. Run run.bat to start the app at http://127.0.0.1:5050
exit /b 0

:error
echo.
echo Setup failed. Check the message above for details.
exit /b 1
