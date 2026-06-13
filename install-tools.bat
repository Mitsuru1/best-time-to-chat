@echo off
REM Installs Git and GitHub CLI with winget.
REM Manual step: close and reopen your terminal after this finishes so PATH updates.
REM If installation fails, right-click this file and choose "Run as administrator".

echo Installing Git...
winget install --id Git.Git -e
if errorlevel 1 goto error

echo.
echo Installing GitHub CLI...
winget install --id GitHub.cli -e
if errorlevel 1 goto error

echo.
echo Install complete.
echo Close and reopen your terminal, then run push-to-github.bat.
pause
exit /b 0

:error
echo.
echo Installation failed.
echo Try running this file as administrator, then close and reopen your terminal.
pause
exit /b 1
