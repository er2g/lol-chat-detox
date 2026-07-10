@echo off
rem LoL Chat Detox — single EXE install (admin recommended)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
echo.
echo === LoL Chat Detox Install ===
echo.

if not exist "%~dp0LoLDetox.exe" (
    echo ERROR: LoLDetox.exe not found in this folder.
    echo Build it first or extract a release zip here.
    pause
    exit /b 1
)

rem Clean old multi-exe tasks / processes
schtasks /delete /f /tn "LoLChatDetox" >nul 2>&1
taskkill /f /im LoLDetoxWatcher.exe >nul 2>&1
taskkill /f /im LoLOverlay.exe >nul 2>&1
taskkill /f /im LoLDetoxSettings.exe >nul 2>&1
taskkill /f /im LoLDetox.exe >nul 2>&1

schtasks /create /f /tn "LoLChatDetox" /sc onlogon /rl highest /tr "\"%~dp0LoLDetox.exe\" --background" >nul
if %errorlevel% neq 0 (
    schtasks /create /f /tn "LoLChatDetox" /sc onlogon /rl limited /tr "\"%~dp0LoLDetox.exe\" --background" >nul
)
if %errorlevel% neq 0 (
    echo WARNING: Could not create startup task. You can enable it in the app.
) else (
    echo Startup task created.
)

start "" "%~dp0LoLDetox.exe"
echo.
echo Done. Configure language, mode, and API key in the app.
echo Uninstall: uninstall.bat
echo.
pause
