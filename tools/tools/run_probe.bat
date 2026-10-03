@echo off
cd /d "%~dp0"
set /p IP=Device IP address (e.g. 192.168.25.120): 
set /p USR=Username [admin]: 
if "%USR%"=="" set USR=admin
set /p PWD=Password (blank if none): 
echo.
python probe.py %IP% --user %USR% --password "%PWD%" || py probe.py %IP% --user %USR% --password "%PWD%"
echo.
pause
