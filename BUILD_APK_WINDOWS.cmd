@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo THD Student Discipline - Android APK build
where flutter >nul 2>&1
if errorlevel 1 (
 echo KHONG TIM THAY FLUTTER. CAN CAI FLUTTER VA ANDROID SDK.
 echo Hoac chay workflow GitHub Actions trong repository RIENG TU.
 pause
 exit /b 1
)
where py >nul 2>&1
if errorlevel 1 (
 echo KHONG TIM THAY PYTHON LAUNCHER "py". CAN CAI PYTHON.
 pause
 exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_apk.ps1"
if errorlevel 1 (
 echo BUILD THAT BAI. Hay chup man hinh loi va gui de duoc huong dan.
 pause
 exit /b 1
)
echo FILE THU NGHIEM: mobile\build\app\outputs\flutter-apk\app-debug.apk
pause
