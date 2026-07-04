@echo off
rem LoL Chat Detox kurulum — yonetici yetkisi ister, gorev zamanlayiciya kurar
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Yonetici yetkisi isteniyor...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
echo.
echo === LoL Chat Detox Kurulum ===
echo.

rem API anahtari kontrolu
set "CURKEY="
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v GEMINI_API_KEY 2^>nul ^| find "GEMINI_API_KEY"') do set "CURKEY=%%b"
if defined CURKEY (
    echo Gemini API anahtari zaten kayitli, atlaniyor.
) else (
    echo Gemini API anahtari gerekli: https://aistudio.google.com/apikey
    set /p KEY="Anahtari yapistirin: "
    setx GEMINI_API_KEY "%KEY%" >nul
    echo Anahtar kaydedildi.
)

rem eski python-tabanli startup kisayolu varsa temizle
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\LoL Detox Watcher.lnk" >nul 2>&1

rem acilista yonetici yetkisiyle calisan gorev
schtasks /create /f /tn "LoLChatDetox" /sc onlogon /rl highest /tr "\"%~dp0LoLDetoxWatcher.exe\"" >nul
if %errorlevel% neq 0 (
    echo HATA: Zamanlanmis gorev olusturulamadi!
    pause
    exit /b 1
)
echo Baslangic gorevi kuruldu (yonetici yetkili^).

rem hemen baslat
start "" "%~dp0LoLDetoxWatcher.exe"
echo.
echo Kurulum tamamlandi! Oyunu actiginizda otomatik devreye girer.
echo Kaldirmak icin: uninstall.bat
echo.
pause
