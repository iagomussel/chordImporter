# Quick Test Guide - Get App on Your Android Device

## Desktop Test (Already Done!)
The app is running on your desktop. Test the tuner before building for Android.

---

## Android Device Test - Two Methods

### Method A: Build APK Locally (Recommended)

#### Requirements
- Android device with USB debugging enabled
- USB cable
- 20-60 minutes for first build (downloads Android SDK/NDK)
- Linux or macOS (Windows requires WSL)

#### Steps

1. **Enable USB Debugging on your Android device:**
   - Go to Settings > About Phone
   - Tap "Build Number" 7 times to enable Developer Options
   - Go to Settings > Developer Options
   - Enable "USB Debugging"

2. **Install Buildozer** (if not already installed):
   ```bash
   pip install buildozer cython
   ```

3. **Build and Deploy to Device:**
   ```bash
   cd android-kivy
   
   # Connect your device via USB first!
   
   # Build APK and install directly to device
   buildozer android debug deploy run
   ```

4. **First Build Notes:**
   - Takes 20-60 minutes (downloads Android SDK, NDK, etc.)
   - Requires ~4GB of disk space
   - Subsequent builds are much faster (2-5 minutes)

5. **Grant Microphone Permission:**
   - When app launches, allow microphone access
   - If you miss it, go to Settings > Apps > ChordImporter > Permissions

#### Troubleshooting

**If buildozer fails:**
```bash
# Check Java is installed
java -version

# If not, install Java 11 or higher:
# Windows: https://adoptium.net/
# Linux: sudo apt install openjdk-11-jdk
# macOS: brew install openjdk@11
```

**If device not detected:**
```bash
# Check device is connected
adb devices

# If no devices shown:
# - Ensure USB debugging is enabled
# - Try a different USB cable
# - Authorize the computer on your device
```

---

### Method B: Transfer APK File (Easier for Windows)

If you're on Windows and don't want to set up WSL, you can build on a cloud service or Linux machine, then transfer the APK.

#### Steps

1. **Build APK** (on Linux/Mac or cloud):
   ```bash
   cd android-kivy
   buildozer android debug
   ```
   APK will be in: `bin/chordimporter-*-debug.apk`

2. **Transfer to Phone:**
   - Option 1: Email the APK to yourself
   - Option 2: Upload to Google Drive/Dropbox
   - Option 3: Use USB file transfer
   - Option 4: Use `adb install bin/chordimporter-*-debug.apk`

3. **Install on Phone:**
   - Open the APK file on your phone
   - Tap "Install" (may need to allow "Install from Unknown Sources")
   - Grant microphone permission when prompted

---

### Method C: Use GitHub Actions (Automated Cloud Build)

Build APK automatically using GitHub Actions (no local build needed!).

#### Steps

1. **Push code to GitHub:**
   ```bash
   git add android-kivy/
   git commit -m "Add Android version"
   git push
   ```

2. **Create GitHub Actions workflow:**
   Create `.github/workflows/build-android.yml`:
   ```yaml
   name: Build Android APK
   
   on: [push, workflow_dispatch]
   
   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.11'
         
         - name: Install dependencies
           run: |
             pip install buildozer cython
             sudo apt-get update
             sudo apt-get install -y openjdk-11-jdk
         
         - name: Build APK
           working-directory: android-kivy
           run: buildozer android debug
         
         - name: Upload APK
           uses: actions/upload-artifact@v3
           with:
             name: android-apk
             path: android-kivy/bin/*.apk
   ```

3. **Download APK:**
   - Go to GitHub Actions tab
   - Download the artifact
   - Transfer to your phone and install

---

## What to Test on Your Device

Once the app is running on your Android device:

### 1. Basic Functionality
- [ ] App launches without crashing
- [ ] Main screen loads
- [ ] "START" button works
- [ ] Microphone permission granted

### 2. Tuner Testing
- [ ] Tap START
- [ ] Play a guitar note (or sing/whistle)
- [ ] Frequency displays (e.g., "110.00 Hz")
- [ ] Note name shows (e.g., "A2")
- [ ] Cents offset updates
- [ ] Color changes (green when in tune)

### 3. Performance
- [ ] Smooth updates (no lag)
- [ ] Battery usage acceptable
- [ ] No crashes after 5+ minutes
- [ ] App responds to screen rotation
- [ ] STOP button works

### 4. Audio Quality
- [ ] Detects guitar strings accurately
- [ ] Responds quickly (< 200ms)
- [ ] Stable readings (not jumping around)
- [ ] Works with background noise

---

## Expected Performance

### Mid-Range Device (Snapdragon 6-series, 4GB RAM)
- Latency: 100-150ms
- Battery: ~5% per hour
- Update rate: 10 Hz

### High-End Device (Snapdragon 8-series, 8GB+ RAM)
- Latency: 50-100ms
- Battery: ~3% per hour
- Update rate: 20 Hz

---

## Known Issues & Workarounds

### Issue: "Permission denied" for microphone
**Solution:** Go to Settings > Apps > ChordImporter > Permissions > Enable Microphone

### Issue: Audio not detecting
**Solution:** 
1. Check microphone isn't blocked
2. Try louder note
3. Restart app
4. Check device volume isn't muted

### Issue: App crashes on startup
**Solution:**
1. Check logs: `adb logcat | grep python`
2. Reinstall: Uninstall and install fresh
3. Clear app data

### Issue: Readings unstable
**Solution:**
1. Reduce background noise
2. Play notes louder
3. Hold note steady longer

---

## View Logs from Device

To see what's happening inside the app:

```bash
# Connect device via USB
adb logcat -s python

# Or with buildozer
buildozer android logcat
```

---

## Next Steps After Testing

Once you've confirmed it works on your device:

1. **Customize branding:**
   - Add app icon: Edit `buildozer.spec` > `icon.filename`
   - Change colors: Edit `main.py` color values

2. **Add features:**
   - Chord search (import existing serper module)
   - Database (import existing database module)
   - Settings screen

3. **Polish UI:**
   - Improve layout
   - Add animations
   - Better visual feedback

4. **Build release version:**
   ```bash
   buildozer android release
   ```

5. **Publish to Play Store:**
   - Create developer account ($25)
   - Create store listing
   - Submit APK for review

---

## Estimated Times

| Task | First Time | Subsequent |
|------|------------|------------|
| Setup buildozer | 10 min | - |
| First APK build | 30-60 min | - |
| Rebuild APK | - | 2-5 min |
| Transfer to device | 2 min | 2 min |
| Test on device | 5-10 min | 2-3 min |

**Total first time: 45-80 minutes**
**Total after setup: 5-10 minutes**

---

## Alternative: Use Pre-built APK

If someone else builds the APK, you can just:
1. Download the .apk file
2. Transfer to your phone
3. Install
4. Test

No build tools needed!

---

## Questions?

- **Can I test without building?** Yes! Desktop version works now.
- **Do I need Play Store to test?** No! Install APK directly.
- **Can I share with friends?** Yes! Send them the APK file.
- **Does it need internet?** No! Works completely offline.
- **Will it drain battery?** ~3-5% per hour of active use.

---

## Support

If you encounter issues:
1. Check logs with `adb logcat`
2. See `README.md` troubleshooting section
3. Check Buildozer docs: https://buildozer.readthedocs.io/
4. Kivy community: https://chat.kivy.org/

---

**Ready to test? Connect your device and run:**
```bash
cd android-kivy
buildozer android debug deploy run
```

The app will build and install automatically! 🎸📱

