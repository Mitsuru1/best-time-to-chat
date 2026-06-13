@echo off
REM Initializes this project as a git repository, commits all tracked project files,
REM and creates a new private GitHub repository named best-time-to-chat.
REM Manual step: GitHub CLI may open a browser and ask you to complete login.
REM If Git or gh is not recognized, run install-tools.bat first, then close and reopen your terminal.

setlocal
cd /d "%~dp0"

set "REPO_NAME=best-time-to-chat"
set "COMMIT_MESSAGE=Initial Best Time to Chat app"

echo This will create a private GitHub repo named %REPO_NAME% and push this folder to it.
echo Complete any GitHub login browser prompt if one appears.
echo.
pause

echo Logging in to GitHub CLI...
gh auth login
if errorlevel 1 goto error

echo.
echo Initializing git repository...
git init
if errorlevel 1 goto error

echo.
echo Setting main branch...
git branch -M main
if errorlevel 1 goto error

echo.
echo Staging files...
git add .
if errorlevel 1 goto error

echo.
echo Creating commit...
git commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 goto error

echo.
echo Creating private GitHub repository and pushing...
gh repo create %REPO_NAME% --private --source=. --remote=origin --push
if errorlevel 1 goto error

echo.
echo Push complete.
pause
exit /b 0

:error
echo.
echo Something failed. Read the output above for details.
echo Common fixes: install Git/GitHub CLI, close and reopen the terminal, complete gh auth login, or configure git user.name and user.email.
pause
exit /b 1
