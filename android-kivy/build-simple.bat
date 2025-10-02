@echo off
echo Building ChordImporter Android APK with Docker (Simple Method)...
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

echo Docker is running. Starting build process...
echo.

REM Create buildozer cache directories
if not exist "%USERPROFILE%\.buildozer" mkdir "%USERPROFILE%\.buildozer"
if not exist "%USERPROFILE%\.android" mkdir "%USERPROFILE%\.android"

echo Building custom Docker image with buildozer...
docker build -t chordimporter-android .

if %errorlevel% neq 0 (
    echo ERROR: Docker build failed.
    pause
    exit /b 1
)

echo Docker image built successfully.
echo.

echo Starting Android APK build...
echo This may take 10-30 minutes on first run...
echo.

REM Run the build using the custom Docker image
docker run --rm ^
    -v "%cd%":/app ^
    -v "%USERPROFILE%\.buildozer":/root/.buildozer ^
    -v "%USERPROFILE%\.android":/root/.android ^
    chordimporter-android

if %errorlevel% neq 0 (
    echo ERROR: Android build failed.
    echo.
    echo Common solutions:
    echo 1. Make sure you have enough disk space (at least 5GB free)
    echo 2. Check your internet connection (buildozer downloads Android SDK)
    echo 3. Try running: docker pull kivy/buildozer:latest
    echo.
    pause
    exit /b 1
)

echo.
echo SUCCESS: Android APK built successfully!
echo.
echo APK files should be in the 'bin' directory:
dir bin\*.apk
echo.
echo To install on your Android device:
echo 1. Enable "Developer Options" and "USB Debugging" on your phone
echo 2. Connect your phone via USB
echo 3. Run: adb install bin\chordimporter-0.1.0-arm64-v8a-debug.apk
echo.
pause
