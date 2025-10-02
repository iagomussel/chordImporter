# ChordImporter - Android Version (Kivy)

This is the Android port of ChordImporter using the Kivy framework.

## Features

- HPS Guitar Tuner with real-time frequency detection
- Visual tuning indicator with cents accuracy
- Note name display with octave
- Mobile-optimized UI
- Reuses existing desktop algorithms

## Development Setup

### Prerequisites

1. Python 3.9 or higher
2. Java JDK 11 or higher
3. Android SDK and NDK (buildozer will install these)
4. Linux or macOS (Windows via WSL)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Desktop Testing

You can test the app on desktop before building for Android:

```bash
python main.py
```

Note: Desktop testing requires `sounddevice` for audio input.

## Building for Android

### First Time Setup

```bash
# Initialize buildozer (creates buildozer.spec)
buildozer init

# Install Android SDK/NDK (first build takes 20-60 minutes)
buildozer -v android debug
```

### Subsequent Builds

```bash
# Build debug APK
buildozer android debug

# Build and deploy to connected device
buildozer android debug deploy run

# View logs
buildozer android logcat
```

### Release Build

```bash
# Build release APK
buildozer android release

# Sign for Play Store
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore my-release-key.keystore \
  bin/chordimporter-release-unsigned.apk alias_name

# Align APK
zipalign -v 4 bin/chordimporter-release-unsigned.apk bin/chordimporter-release.apk
```

## Project Structure

```
android-kivy/
├── main.py                # Entry point & main app logic
├── buildozer.spec        # Build configuration
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Audio System

The app uses different audio systems depending on platform:

- **Android**: `audiostream` with Android AudioRecord API
- **Desktop**: `sounddevice` for testing

The HPS (Harmonic Product Spectrum) algorithm is platform-independent and works on both.

## Permissions

The app requires these Android permissions:

- `RECORD_AUDIO` - For microphone access
- `INTERNET` - For chord search (future feature)
- `WRITE_EXTERNAL_STORAGE` - For saving recordings
- `READ_EXTERNAL_STORAGE` - For loading saved data

## Performance

- Sample Rate: 44100 Hz
- Buffer Size: 4096 samples
- Update Rate: 10 Hz (100ms intervals)
- Latency: < 150ms on modern devices

## Known Issues

- First build takes a long time (SDK/NDK download)
- Audio latency may vary by device
- Some budget devices may have lower accuracy

## Roadmap

- [ ] Add chord search functionality
- [ ] Implement database for saved songs
- [ ] Add multiple tuning presets
- [ ] Recording and playback
- [ ] Cloud sync with desktop version
- [ ] Dark/light theme toggle
- [ ] Instrument selection (guitar, bass, ukulele)

## Testing

### On Physical Device

1. Enable Developer Mode on your Android device
2. Enable USB Debugging
3. Connect device via USB
4. Run: `buildozer android debug deploy run`

### On Emulator

1. Create AVD in Android Studio
2. Start emulator
3. Run: `buildozer android debug deploy run`

## Debugging

View real-time logs:

```bash
buildozer android logcat
```

Filter for Python output:

```bash
adb logcat -s python
```

## Troubleshooting

### Build fails with Java errors
- Ensure Java 11 is installed: `java -version`
- Set JAVA_HOME: `export JAVA_HOME=/path/to/java11`

### Audio not working
- Check microphone permissions in Android settings
- Try restarting the app
- Check logcat for error messages

### APK won't install
- Uninstall previous version first
- Enable "Install from Unknown Sources"
- Check APK is properly signed

## Contributing

This is a proof-of-concept. Contributions welcome!

## License

Same as main ChordImporter project

## Links

- Desktop Version: `../chord_importer/`
- Full Documentation: `../ANDROID_VERSION_PLAN.md`

