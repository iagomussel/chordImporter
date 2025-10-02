# Windows Quick Start - Test on Android Device

## You're on Windows! Here are your best options:

---

## Option 1: Easiest - Use Cloud Build (No setup!)

### Use Replit, Google Colab, or GitHub Actions

1. **Upload your code to GitHub:**
   ```bash
   cd F:\projetos\chordImporter
   git add android-kivy/
   git commit -m "Android version"
   git push
   ```

2. **Go to https://replit.com or https://colab.research.google.com**

3. **Create new Python environment and run:**
   ```bash
   git clone YOUR_REPO_URL
   cd chordImporter/android-kivy
   apt-get update
   apt-get install -y openjdk-11-jdk
   pip install buildozer cython
   buildozer android debug
   ```

4. **Download the APK from:**
   - `bin/chordimporter-*-debug.apk`

5. **Transfer to your phone:**
   - Email it to yourself
   - Or use Google Drive
   - Or USB transfer

6. **Install on phone:**
   - Open the APK file
   - Tap "Install"
   - Allow "Install from Unknown Sources" if asked

**Time: 15-20 minutes**

---

## Option 2: WSL2 (Windows Subsystem for Linux)

Build locally on your Windows machine using Linux subsystem.

### Setup WSL2 (One-time, 10 minutes)

1. **Open PowerShell as Administrator and run:**
   ```powershell
   wsl --install
   ```

2. **Restart your computer**

3. **Open Ubuntu from Start Menu**

4. **Create username and password**

### Build APK in WSL2

1. **Navigate to your project:**
   ```bash
   cd /mnt/f/projetos/chordImporter/android-kivy
   ```

2. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip openjdk-11-jdk
   pip3 install buildozer cython
   ```

3. **Build APK:**
   ```bash
   buildozer android debug
   ```
   APK will be in: `bin/chordimporter-*-debug.apk`

4. **Transfer to phone:**
   - APK is in Windows at: `F:\projetos\chordImporter\android-kivy\bin\`
   - Email it, USB transfer, or use adb

**Time: First build 30-60 min, subsequent 2-5 min**

---

## Option 3: Simplest for Testing - APK Transfer

If you have access to a Linux/Mac machine (or friend!):

1. **Build on Linux/Mac:**
   ```bash
   cd android-kivy
   buildozer android debug
   ```

2. **Transfer APK to Windows:**
   - Copy `bin/chordimporter-*-debug.apk` to USB drive
   - Or use cloud storage

3. **Install on Android:**
   - Connect phone to Windows PC
   - Copy APK to phone storage
   - Open file manager on phone
   - Tap APK to install

---

## Recommended: Use WSL2 (Best for Long-term Development)

### Why WSL2?
- ✅ Build locally on your Windows machine
- ✅ Fast rebuilds (2-5 minutes after first build)
- ✅ No cloud dependency
- ✅ Full control
- ✅ Can use adb to deploy directly

### Quick WSL2 Setup

```powershell
# In PowerShell (as Admin):
wsl --install

# After restart, in Ubuntu:
cd /mnt/f/projetos/chordImporter/android-kivy
sudo apt update
sudo apt install -y python3-pip openjdk-11-jdk git zip unzip
pip3 install buildozer cython

# Build!
buildozer android debug
```

### Deploy to Device via WSL2

```bash
# Connect phone via USB, enable USB debugging

# In WSL2:
sudo apt install adb
adb devices  # Should show your device

# Build and deploy:
buildozer android debug deploy run
```

---

## After You Have the APK

### Install on Android Device

1. **Method 1 - Direct Install:**
   - Transfer APK to phone (email, USB, cloud)
   - Open file manager on phone
   - Tap the APK file
   - Tap "Install"
   - If blocked: Settings > Security > Allow from this source

2. **Method 2 - ADB Install:**
   - Download platform-tools: https://developer.android.com/studio/releases/platform-tools
   - Extract to folder (e.g., `C:\platform-tools`)
   - Enable USB debugging on phone
   - Connect phone via USB
   - In PowerShell:
     ```powershell
     cd C:\platform-tools
     .\adb.exe devices  # Should show your device
     .\adb.exe install F:\projetos\chordImporter\android-kivy\bin\chordimporter-*-debug.apk
     ```

### Grant Permissions

When app launches:
1. Tap "Allow" when asked for microphone permission
2. If you miss it: Settings > Apps > ChordImporter > Permissions > Enable Microphone

### Test the Tuner

1. Open the app
2. Tap "START"
3. Play a guitar note or sing
4. Watch frequency and note name update
5. Green = in tune, Yellow = close, Orange = adjust more

---

## Troubleshooting

### WSL2 won't install
- Ensure Windows 10 version 2004+ or Windows 11
- Enable virtualization in BIOS
- Run: `wsl --update`

### Buildozer fails in WSL2
```bash
# Install missing dependencies:
sudo apt install -y build-essential libffi-dev libssl-dev python3-dev
sudo apt install -y libltdl-dev
```

### Phone not detected by adb
1. Enable USB debugging on phone
2. Change USB mode to "File Transfer" or "PTP"
3. Authorize computer on phone screen
4. Try: `adb kill-server && adb start-server`

### APK won't install on phone
- Check Android version (need 5.0+)
- Enable "Install from Unknown Sources"
- Uninstall any previous version first

---

## Quick Reference

### WSL2 Build Command
```bash
cd /mnt/f/projetos/chordImporter/android-kivy
buildozer android debug
```

### Find APK in Windows
```
F:\projetos\chordImporter\android-kivy\bin\chordimporter-*-debug.apk
```

### Install via ADB (Windows)
```powershell
cd C:\platform-tools
.\adb.exe install path\to\chordimporter.apk
```

---

## My Recommendation for You

Since you're on Windows:

**Short-term (Testing):**
1. ✅ Already testing on desktop (running now!)
2. Use cloud build or WSL2 for first APK
3. Install APK on your phone
4. Test and iterate on desktop
5. Rebuild occasionally for phone testing

**Long-term (Development):**
1. Set up WSL2 (one-time 10 min setup)
2. Build in WSL2 (fast rebuilds)
3. Deploy via adb
4. Develop/test cycle: Desktop → WSL2 build → Phone test

---

## Current Status

✅ Desktop version is running on your Windows machine right now!
- Test the tuner
- Make changes to `main.py`
- See results immediately

When you're ready for Android:
1. Choose WSL2 or cloud build
2. Build APK (30-60 min first time)
3. Install on phone
4. Test!

---

**The desktop version you're running NOW is the same code that runs on Android! 🎉**

