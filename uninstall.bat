@echo off
rem LoL Chat Detox kaldirma
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Yonetici yetkisi isteniyor...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
schtasks /delete /f /tn "LoLChatDetox" >nul 2>&1
taskkill /f /im LoLDetoxWatcher.exe >nul 2>&1
taskkill /f /im LoLDetox.exe >nul 2>&1
taskkill /f /im LoLOverlay.exe >nul 2>&1
echo LoL Chat Detox kaldirildi. (API anahtari ve log dosyalari duruyor.)
pause
