@echo off
echo Building ChordImporter Android APK with Docker...
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

REM Build the Docker image
echo Building Docker image...
docker build -t chordimporter-android .

if %errorlevel% neq 0 (
    echo ERROR: Docker build failed.
    pause
    exit /b 1
)

echo Docker image built successfully.
echo.

REM Run the build
echo Starting Android APK build...
docker run --rm -v "%cd%":/app -v "%USERPROFILE%\.buildozer":/root/.buildozer -v "%USERPROFILE%\.android":/root/.android chordimporter-android

if %errorlevel% neq 0 (
    echo ERROR: Android build failed.
    pause
    exit /b 1
)

echo.
echo SUCCESS: Android APK built successfully!
echo APK location: bin/chordimporter-0.1.0-arm64-v8a-debug.apk
echo.
pause
