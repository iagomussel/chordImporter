# Android Version - ChordImporter

## Current Architecture Analysis

### Core Features to Port
1. **HPS Guitar Tuner** - Real-time audio processing with frequency detection
2. **Chord Search** - CifraClub, file type, and chord sequence search
3. **Chord Identifier** - Audio-based chord recognition
4. **Music Visualizer** - Visual feedback for tuning and chords
5. **Database** - SQLite-based song/search storage
6. **Settings** - Configuration management

### Technical Challenges

#### Current Dependencies (Desktop-Only)
- `tkinter` - Not available on Android
- `pyaudio` - Desktop audio library
- `sounddevice` - Not Android-compatible
- `playwright` - Browser automation (desktop)
- Desktop file system expectations

#### Reusable Components
- `numpy`, `scipy` - Work on Android with proper setup
- `librosa` - Audio analysis (portable)
- `requests`, `beautifulsoup4` - HTTP/scraping (portable)
- SQLite database - Native on Android
- Core business logic - 100% reusable

---

## Android Implementation Options

### Option 1: Kivy Framework (RECOMMENDED for Quick Port)
**Use Python with Kivy to build native Android APK**

#### Pros
- Reuse 80-90% of existing Python code
- Keep audio processing algorithms (numpy, scipy, librosa)
- Active community and good documentation
- Can access Android APIs via pyjnius
- Cross-platform (iOS later)

#### Cons
- Larger APK size (~40-60 MB)
- Slightly slower than native
- Custom UI design needed (Kivy language)

#### Implementation Steps
1. Replace tkinter UI with Kivy UI
2. Replace pyaudio with Android audio via `audiostream`
3. Use Kivy's native widgets for mobile UX
4. Build APK with buildozer
5. Test audio latency and optimize

#### Required Changes
```python
# Before (Desktop)
import tkinter as tk
import pyaudio

# After (Android)
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from audiostream import get_input
```

#### Estimated Timeline
- UI Migration: 2-3 weeks
- Audio System: 1-2 weeks
- Testing & Optimization: 1-2 weeks
- **Total: 4-7 weeks**

---

### Option 2: React Native + Python Backend (BEST UX)
**Modern mobile UI with Python API backend**

#### Architecture
```
Android App (React Native)
    ↓ HTTP/REST API
Python Backend (Flask/FastAPI)
    ├─ Audio Processing
    ├─ Database
    └─ Search Logic
```

#### Pros
- Modern, native-like mobile UI
- Excellent performance
- Better App Store compliance
- Professional mobile UX patterns
- Can use existing Python code as API

#### Cons
- Requires backend hosting (or local server)
- Audio processing runs remotely (latency)
- More complex architecture
- Two codebases to maintain

#### Implementation Steps
1. Create REST API with Flask/FastAPI
2. Build React Native UI
3. Implement audio recording in JS
4. Send audio to Python backend for processing
5. Display results in mobile UI

#### Estimated Timeline
- API Development: 2-3 weeks
- Mobile UI: 3-4 weeks
- Integration: 1-2 weeks
- **Total: 6-9 weeks**

---

### Option 3: Native Android (Kotlin) (BEST PERFORMANCE)
**Full rewrite in Kotlin with native Android APIs**

#### Pros
- Best performance and battery life
- Smallest APK size
- Native audio APIs (low latency)
- Best integration with Android
- Play Store friendly

#### Cons
- Complete rewrite required
- Need Android development skills
- Port all algorithms to Kotlin
- Longer development time

#### Implementation Steps
1. Port HPS algorithm to Kotlin
2. Implement Android audio recording
3. Build Material Design UI
4. Port database logic
5. Integrate web scraping

#### Required Libraries
- Kotlin Coroutines
- Android AudioRecord API
- Room Database (SQLite)
- Retrofit (HTTP)
- MPAndroidChart (visualization)

#### Estimated Timeline
- Core Algorithm Port: 3-4 weeks
- UI Development: 3-4 weeks
- Audio System: 2-3 weeks
- Testing: 2-3 weeks
- **Total: 10-14 weeks**

---

### Option 4: Progressive Web App (PWA) (FASTEST)
**Web-based app that works on mobile browsers**

#### Pros
- Works on all platforms
- Quick development
- No app store approval
- Easy updates
- Reuse backend code

#### Cons
- Limited audio API access
- Requires internet connection
- Not a "real" app
- Performance limitations
- Limited offline features

#### Implementation Steps
1. Create Flask/FastAPI backend
2. Build responsive HTML5 UI
3. Use Web Audio API for tuner
4. Add PWA manifest
5. Deploy to web server

#### Estimated Timeline
- Backend API: 1-2 weeks
- Frontend: 2-3 weeks
- **Total: 3-5 weeks**

---

## Recommended Approach: Kivy Implementation

### Phase 1: Proof of Concept (1 week)
- Basic Kivy app structure
- Audio input test on Android
- HPS algorithm validation
- UI mockups

### Phase 2: Core Features (3-4 weeks)
- Guitar tuner with HPS
- Visual tuning indicator
- Microphone selection
- Basic search functionality

### Phase 3: Advanced Features (2-3 weeks)
- Chord identifier
- Database integration
- Settings screen
- Search with all sources

### Phase 4: Polish & Release (1-2 weeks)
- UI/UX refinements
- Performance optimization
- Icon and branding
- Play Store submission

---

## Technical Implementation Guide (Kivy)

### 1. Project Setup

#### Install Kivy and Build Tools
```bash
# Development
pip install kivy[base] kivy-garden
pip install buildozer  # For APK building
pip install pyjnius    # For Android APIs

# Create buildozer.spec
buildozer init
```

#### Configure buildozer.spec
```ini
[app]
title = ChordImporter
package.name = chordimporter
package.domain = com.yourdomain

# Permissions
android.permissions = RECORD_AUDIO,INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Requirements
requirements = python3,kivy,numpy,scipy,librosa,requests,beautifulsoup4,sqlite3

# Orientation
orientation = portrait

# Android API
android.api = 31
android.minapi = 21
android.ndk = 25b
```

### 2. Audio System (Android)

#### Replace pyaudio with audiostream
```python
from audiostream import get_input
from audiostream.sources.thread import ThreadSource
import numpy as np

class AndroidAudioInput:
    def __init__(self, sample_rate=44100, buffer_size=4096):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.mic = get_input(
            callback=self.audio_callback,
            source='default',
            buffersize=buffer_size,
            encoding=16,  # 16-bit
            channels=1,   # Mono
            rate=sample_rate
        )
    
    def audio_callback(self, buf):
        """Process incoming audio data"""
        # Convert bytes to numpy array
        audio_data = np.frombuffer(buf, dtype=np.int16)
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        # Process with HPS algorithm
        freq = self.detect_frequency_hps(audio_data)
        return freq
    
    def start(self):
        self.mic.start()
    
    def stop(self):
        self.mic.stop()
```

### 3. Kivy UI Structure

#### Main App
```python
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, StringProperty

class TunerScreen(Screen):
    frequency = NumericProperty(0.0)
    note_name = StringProperty("--")
    cents_off = NumericProperty(0.0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_input = None
        self.is_recording = False
    
    def start_tuning(self):
        if not self.is_recording:
            self.audio_input = AndroidAudioInput()
            self.audio_input.start()
            self.is_recording = True
            # Schedule updates
            Clock.schedule_interval(self.update_tuner, 0.1)
    
    def stop_tuning(self):
        if self.is_recording:
            self.audio_input.stop()
            self.is_recording = False
            Clock.unschedule(self.update_tuner)
    
    def update_tuner(self, dt):
        # Update UI with frequency data
        freq = self.audio_input.get_frequency()
        note, cents = self.freq_to_note(freq)
        self.frequency = freq
        self.note_name = note
        self.cents_off = cents

class SearchScreen(Screen):
    pass

class SettingsScreen(Screen):
    pass

class ChordImporterApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(TunerScreen(name='tuner'))
        sm.add_widget(SearchScreen(name='search'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm

if __name__ == '__main__':
    ChordImporterApp().run()
```

#### Kivy UI File (tuner.kv)
```yaml
<TunerScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(10)
        
        # Header
        Label:
            text: 'Guitar Tuner HPS'
            font_size: sp(32)
            size_hint_y: 0.1
        
        # Frequency Display
        Label:
            text: f'{root.frequency:.2f} Hz'
            font_size: sp(48)
            size_hint_y: 0.15
        
        # Note Display
        Label:
            text: root.note_name
            font_size: sp(96)
            bold: True
            size_hint_y: 0.25
        
        # Cents Indicator
        Widget:
            size_hint_y: 0.15
            canvas:
                Color:
                    rgba: 1, 0, 0, 1 if abs(root.cents_off) > 10 else 0.3
                Rectangle:
                    pos: self.center_x - dp(2), self.y
                    size: dp(4), self.height
                Color:
                    rgba: 0, 1, 0, 1
                Rectangle:
                    pos: self.center_x + root.cents_off * dp(5) - dp(5), self.center_y - dp(5)
                    size: dp(10), dp(10)
        
        # Cents Text
        Label:
            text: f'{root.cents_off:+.1f} cents'
            font_size: sp(24)
            size_hint_y: 0.1
        
        # Control Buttons
        BoxLayout:
            size_hint_y: 0.15
            spacing: dp(10)
            
            Button:
                text: 'Start' if not root.is_recording else 'Stop'
                on_press: root.start_tuning() if not root.is_recording else root.stop_tuning()
                background_color: 0.2, 0.8, 0.2, 1
            
            Button:
                text: 'Settings'
                on_press: app.root.current = 'settings'
```

### 4. Keep Existing Algorithms

**No changes needed to:**
- `chord_importer/services/core.py` - Core logic
- `chord_importer/services/serper.py` - Search
- `chord_importer/models/database.py` - Database
- `chord_importer/utils/chord_transposer.py` - Music theory

**Just import and use them:**
```python
from chord_importer.services.core import fetch_song
from chord_importer.services.serper import search_cifraclub
from chord_importer.models.database import get_database
```

### 5. Build APK

```bash
# First build (takes 20-60 minutes)
buildozer -v android debug

# Deploy to connected device
buildozer android deploy run

# Build release APK
buildozer android release

# Sign APK for Play Store
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore my-release-key.keystore bin/chordimporter-release-unsigned.apk alias_name
```

---

## File Structure (Android/Kivy Version)

```
ChordImporter-Android/
├── main.py                      # Kivy app entry point
├── buildozer.spec              # Build configuration
├── screens/
│   ├── tuner_screen.py         # Tuner UI
│   ├── search_screen.py        # Search UI
│   ├── identifier_screen.py    # Chord identifier UI
│   └── settings_screen.py      # Settings UI
├── android_audio/
│   ├── audio_input.py          # Android audio capture
│   ├── hps_detector.py         # HPS algorithm (reused)
│   └── audio_processor.py      # Audio processing
├── chord_importer/             # Existing backend (reused)
│   ├── services/
│   ├── models/
│   └── utils/
├── assets/
│   ├── icon.png                # App icon
│   ├── fonts/
│   └── sounds/
└── kv/                         # Kivy UI files
    ├── tuner.kv
    ├── search.kv
    └── main.kv
```

---

## Alternative: Hybrid Approach

### Keep Desktop & Create Companion Android App

**Desktop (Full Features)**
- Advanced HPS tuner with recording
- Complex chord searches
- Full database management
- Export/import capabilities

**Android (Mobile Essentials)**
- Basic HPS tuner
- Quick chord search
- View saved songs
- Sync with desktop via cloud

This approach allows:
- Focus on mobile-optimized features
- Smaller, faster Android app
- Desktop remains primary tool
- Gradual feature parity

---

## Next Steps

### Option A: Quick Start (Kivy)
1. Create basic Kivy app with tuner
2. Test on Android device
3. Validate audio performance
4. Iterate on UI/UX

### Option B: Native Quality (React Native)
1. Design mobile UI mockups
2. Create Python API
3. Build React Native prototype
4. Test end-to-end flow

### Option C: Professional Native (Kotlin)
1. Port HPS algorithm to Kotlin
2. Build proof-of-concept tuner
3. Validate performance
4. Plan full app architecture

---

## Questions to Consider

1. **Target Audience**: Professional musicians or casual users?
2. **Feature Priority**: Tuner first, or search first?
3. **Offline Support**: How important is offline functionality?
4. **Monetization**: Free, ads, or paid app?
5. **Timeline**: Quick port or polished release?
6. **Maintenance**: Who will maintain two codebases?

---

## Recommendation

**Start with Kivy for fastest path to Android** while reusing existing code. If the app gains traction, consider:
- Rewriting in React Native for better UX
- Or porting to native Kotlin for best performance

This allows validation of market fit before major investment.

