@echo off
REM ════════════════════════════════════════════════════════════════
REM   DEPLOY TO ANDROID - Automated Script
REM ════════════════════════════════════════════════════════════════

echo.
echo ════════════════════════════════════════════════════════════════
echo   CHORD IMPORTER - ANDROID DEPLOYMENT
echo ════════════════════════════════════════════════════════════════
echo.
echo This will build and deploy the app to your Android phone!
echo.
echo REQUIREMENTS:
echo   1. Phone connected via USB
echo   2. USB Debugging enabled on phone
echo   3. WSL (Windows Subsystem for Linux) installed
echo.
echo ════════════════════════════════════════════════════════════════
echo.

REM Check if WSL is available
where wsl >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] WSL not found!
    echo.
    echo To install WSL:
    echo   1. Open PowerShell as Administrator
    echo   2. Run: wsl --install
    echo   3. Restart your computer
    echo   4. Run this script again
    echo.
    pause
    exit /b 1
)

echo [OK] WSL found!
echo.
echo Checking buildozer in WSL...
wsl which buildozer >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [SETUP NEEDED] Buildozer not installed in WSL
    echo.
    echo Installing buildozer... This will take 5-10 minutes.
    echo.
    wsl bash -c "sudo apt update && sudo apt install -y python3-pip git zip unzip openjdk-17-jdk autoconf automake libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev && pip3 install --user buildozer cython && echo 'export PATH=\$PATH:~/.local/bin' >> ~/.bashrc"
    echo.
    echo [OK] Setup complete!
    echo.
)

echo [OK] Buildozer ready!
echo.
echo ════════════════════════════════════════════════════════════════
echo   BUILDING APK
echo ════════════════════════════════════════════════════════════════
echo.
echo This will take 15-30 minutes on first build (or 2-5 min on subsequent builds)
echo.
echo Starting build...
echo.

REM Navigate to project directory in WSL and build
wsl bash -c "cd /mnt/f/projetos/chordImporter/android-kivy && export PATH=\$PATH:~/.local/bin && buildozer android debug deploy run"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo   SUCCESS!
    echo ════════════════════════════════════════════════════════════════
    echo.
    echo The app should now be running on your phone!
    echo.
    echo APK location: bin\chordimporter-0.1.0-arm64-v8a_armeabi-v7a-debug.apk
    echo.
) else (
    echo.
    echo ════════════════════════════════════════════════════════════════
    echo   BUILD FAILED
    echo ════════════════════════════════════════════════════════════════
    echo.
    echo Common fixes:
    echo   1. Make sure phone is connected and USB debugging is enabled
    echo   2. Try: buildozer android clean
    echo   3. Check BUILD_AND_DEPLOY.txt for detailed troubleshooting
    echo.
)

echo.
pause

