# Docker Android Build Guide

This guide explains how to build the ChordImporter Android APK using Docker and buildozer.

## Prerequisites

1. **Docker Desktop** installed and running
2. **At least 5GB free disk space**
3. **Stable internet connection** (buildozer downloads Android SDK)

## Quick Start

### Method 1: Simple Build (Recommended)

```bash
# Run the simple build script
build-simple.bat
```

This uses the official Kivy buildozer Docker image and handles everything automatically.

### Method 2: Custom Docker Build

```bash
# Build custom Docker image
docker build -t chordimporter-android .

# Run the build
docker run --rm -v "%cd%":/app -v "%USERPROFILE%\.buildozer":/root/.buildozer -v "%USERPROFILE%\.android":/root/.android chordimporter-android
```

## What Happens During Build

1. **Docker Image Download**: Downloads the official Kivy buildozer image (~2GB)
2. **Android SDK Setup**: Downloads and configures Android SDK (~3GB)
3. **Dependencies**: Installs all Python packages and Android tools
4. **APK Compilation**: Compiles the Python code to Android APK
5. **Output**: Creates APK file in `bin/` directory

## Build Output

After successful build, you'll find:
- `bin/chordimporter-0.1.0-arm64-v8a-debug.apk` (ARM64 devices)
- `bin/chordimporter-0.1.0-armeabi-v7a-debug.apk` (ARM32 devices)

## Installing on Android Device

1. **Enable Developer Options** on your Android device:
   - Go to Settings > About Phone
   - Tap "Build Number" 7 times
   - Go back to Settings > Developer Options
   - Enable "USB Debugging"

2. **Connect your device** via USB

3. **Install the APK**:
   ```bash
   adb install bin/chordimporter-0.1.0-arm64-v8a-debug.apk
   ```

## Troubleshooting

### Build Fails with "No space left on device"
- Free up disk space (need at least 5GB)
- Clear Docker cache: `docker system prune -a`

### Build Fails with "Network error"
- Check internet connection
- Try again (buildozer downloads large files)

### Build Fails with "Permission denied"
- Make sure Docker Desktop is running
- Try running as Administrator

### Build Takes Too Long
- First build takes 20-40 minutes
- Subsequent builds are much faster (5-10 minutes)
- Buildozer caches Android SDK and dependencies

## Build Configuration

The build configuration is in `buildozer.spec`:

- **App Name**: ChordImporter
- **Package**: com.musical.chordimporter
- **Version**: 0.1.0
- **Target API**: 31 (Android 12+)
- **Min API**: 21 (Android 5.0+)
- **Architectures**: ARM64, ARM32

## Advanced Usage

### Clean Build (Remove Cache)
```bash
docker run --rm -v "%cd%":/app -v "%USERPROFILE%\.buildozer":/root/.buildozer -v "%USERPROFILE%\.android":/root/.android kivy/buildozer:latest buildozer android clean
```

### Debug Build
```bash
docker run --rm -v "%cd%":/app -v "%USERPROFILE%\.buildozer":/root/.buildozer -v "%USERPROFILE%\.android":/root/.android kivy/buildozer:latest buildozer android debug
```

### Release Build
```bash
docker run --rm -v "%cd%":/app -v "%USERPROFILE%\.buildozer":/root/.buildozer -v "%USERPROFILE%\.android":/root/.android kivy/buildozer:latest buildozer android release
```

## File Structure

```
android-kivy/
├── main.py                 # Main application code
├── buildozer.spec          # Build configuration
├── Dockerfile              # Custom Docker image (optional)
├── docker-compose.yml      # Docker Compose configuration
├── build-simple.bat        # Simple build script
├── build-android.bat       # Custom build script
├── DOCKER_BUILD.md         # This guide
└── bin/                    # Output APK files (created after build)
```

## Notes

- The first build downloads ~5GB of Android SDK and tools
- Buildozer caches everything in `~/.buildozer` and `~/.android`
- Subsequent builds are much faster
- The official Kivy buildozer image is regularly updated
- All dependencies are handled automatically by buildozer
