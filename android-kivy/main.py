"""
ChordImporter - Android/Kivy Version
Simple and Working Mobile Guitar Tuner
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line
from kivy.animation import Animation
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
import webbrowser
import sys
import os
import math
import threading
import time
import numpy as np

# Add parent directory to path to import existing modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Try to import Android audio (will fall back to desktop for testing)
try:
    from audiostream import get_input
    ANDROID_AUDIO = True
except ImportError:
    ANDROID_AUDIO = False
    print("Android audio not available - using desktop fallback")

# Android browser support
try:
    from jnius import autoclass
    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    ANDROID_BROWSER = True
except:
    ANDROID_BROWSER = False

# Import existing HPS algorithm and utilities
try:
    from chord_importer.models.audio import HPSDetector, AudioInput
    from chord_importer.models.database import Database
    from chord_importer.services.serper import search_cifraclub
except ImportError as e:
    print(f"Import error: {e}")
    # Create mock classes for development
    class HPSDetector:
        def __init__(self):
            pass
        def detect_frequency(self, audio_data):
            return 440.0

class AudioInput:
        def __init__(self):
            pass
        def start_recording(self):
            pass
        def stop_recording(self):
            pass
        def get_audio_data(self):
            return []
    
    class Database:
        def __init__(self):
            self.songs = []
        def get_all_songs(self):
            return self.songs
        def save_song(self, title, artist, content, url):
            self.songs.append({
                'title': title,
                'artist': artist,
                'content': content,
                'url': url
            })
    
    def search_cifraclub(query):
        """Real search function using serper service"""
        try:
            # Import the real serper service
            from chord_importer.services.serper import search_cifraclub as real_search
            return real_search(query)
        except Exception as e:
            raise RuntimeError(
                f"Search failed: {e}\n\n"
                "Please check:\n"
                "1. Serper API key is configured in settings\n"
                "2. Network connectivity is available\n"
                "3. API key is valid and has credits"
            )


def open_url(url):
    """Open URL using Android Intent - no fallbacks"""
    if not ANDROID_BROWSER:
        raise RuntimeError("URL opening requires Android browser. This app must run on Android device.")
    
    try:
        intent = Intent(Intent.ACTION_VIEW)
        intent.setData(Uri.parse(url))
        PythonActivity.mActivity.startActivity(intent)
    except Exception as e:
        raise RuntimeError(f"Failed to open URL on Android: {e}")


class SimpleButton(Button):
    """Simple button with basic styling"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0.2, 0.6, 1, 1)
        self.color = (1, 1, 1, 1)
        self.font_size = sp(16)
        self.size_hint_y = None
        self.height = dp(50)


class SimpleLabel(Label):
    """Simple label with basic styling"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = (0.2, 0.2, 0.2, 1)
        self.font_size = sp(16)
        self.text_size = (None, None)
        self.halign = 'center'
        self.valign = 'middle'


class FrequencyMeter(Widget):
    """Simple frequency meter"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.needle_angle = 0
        self.bind(size=self.update_canvas, pos=self.update_canvas)
        self.update_canvas()
    
    def set_frequency(self, freq):
        """Set frequency and update needle"""
        if freq < 50:
            self.needle_angle = -90
        elif freq > 1000:
            self.needle_angle = 90
        else:
            self.needle_angle = (freq - 50) / (1000 - 50) * 180 - 90
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.clear()
        if not self.size[0] or not self.size[1]:
            return
            
        center_x = self.pos[0] + self.size[0] / 2
        center_y = self.pos[1] + self.size[1] / 2
        radius = min(self.size) * 0.4
        
        with self.canvas:
            # Background circle
            Color(0.95, 0.95, 0.95, 1)
            Ellipse(pos=(center_x - radius, center_y - radius), size=(radius * 2, radius * 2))
            
            # Needle
            Color(1, 0.2, 0.2, 1)
            angle = math.radians(self.needle_angle)
            needle_x = center_x + math.cos(angle) * (radius - dp(15))
            needle_y = center_y + math.sin(angle) * (radius - dp(15))
            Line(points=[center_x, center_y, needle_x, needle_y], width=dp(4))
            
            # Center dot
            Color(0.2, 0.2, 0.2, 1)
            Ellipse(pos=(center_x - dp(3), center_y - dp(3)), size=(dp(6), dp(6)))


class TunerScreen(Screen):
    """Main tuner screen"""
    frequency = NumericProperty(0.0)
    note_name = StringProperty("--")
    cents_off = NumericProperty(0.0)
    is_recording = BooleanProperty(False)
    status_text = StringProperty("Tap START to begin tuning")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_input = None
        self.hps_detector = HPSDetector()
        self.audio_buffer = []
        self.buffer_size = 4096
        self.build_ui()
    
    def build_ui(self):
        """Build the tuner UI"""
        # Main container
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        
        # Title
        title = SimpleLabel(
            text='🎸 Guitar Tuner',
            font_size=sp(24),
            size_hint_y=None,
            height=dp(60)
        )
        main_layout.add_widget(title)
        
        # Frequency meter
        self.freq_meter = FrequencyMeter(
            size_hint_y=0.4
        )
        main_layout.add_widget(self.freq_meter)
        
        # Frequency display
        freq_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60))
        
        self.freq_label = SimpleLabel(
            text='440.0 Hz',
            font_size=sp(20)
        )
        freq_layout.add_widget(self.freq_label)
        
        self.note_label = SimpleLabel(
            text='A',
            font_size=sp(20)
        )
        freq_layout.add_widget(self.note_label)
        
        main_layout.add_widget(freq_layout)
        
        # Status
        self.status_label = SimpleLabel(
            text=self.status_text,
            font_size=sp(16),
            size_hint_y=None,
            height=dp(40)
        )
        main_layout.add_widget(self.status_label)
        
        # Control buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        
        self.start_button = SimpleButton(
            text='START',
            on_press=self.start_tuning
        )
        button_layout.add_widget(self.start_button)
        
        self.stop_button = SimpleButton(
            text='STOP',
            on_press=self.stop_tuning
        )
        button_layout.add_widget(self.stop_button)
        
        main_layout.add_widget(button_layout)
        
        # Navigation
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        search_btn = SimpleButton(
            text='SEARCH',
            on_press=self.go_to_search
        )
        nav_layout.add_widget(search_btn)
        
        library_btn = SimpleButton(
            text='LIBRARY',
            on_press=self.go_to_library
        )
        nav_layout.add_widget(library_btn)
        
        main_layout.add_widget(nav_layout)
        
        self.add_widget(main_layout)
    
    def start_tuning(self, instance):
        """Start tuning"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.start_button.text = 'RECORDING...'
        self.status_label.text = 'Listening for audio...'
        
        # Start audio recording
        try:
            if ANDROID_AUDIO:
                self.audio_input = get_input(callback=self.audio_callback, channels=1, rate=44100, buffersize=1024)
            self.audio_input.start()
            else:
                # No fallback - real audio required
                self.is_recording = False
                self.start_button.text = 'START'
                self.status_label.text = "ERROR: Real audio input required on Android device"
                raise RuntimeError("Real microphone access required. This app must run on Android with microphone permissions.")
        except Exception as e:
            print(f"Audio error: {e}")
            self.status_label.text = f"Audio error: {e}"
            self.is_recording = False
            self.start_button.text = 'START'
    
    def stop_tuning(self, instance):
        """Stop tuning"""
        self.is_recording = False
        self.start_button.text = 'START'
        self.status_label.text = 'Tuning stopped'
        
        try:
        if self.audio_input:
            self.audio_input.stop()
                self.audio_input = None
            else:
                Clock.unschedule(self.simulate_audio)
        except Exception as e:
            print(f"Stop error: {e}")
    
    def audio_callback(self, buf):
        """Audio callback for Android"""
        if not self.is_recording:
            return
        
        # Convert buffer to numpy array
        audio_data = np.frombuffer(buf, dtype=np.float32)
        self.process_audio(audio_data)
    
    def simulate_audio(self, dt):
        """Audio simulation not available - real audio required"""
        if not self.is_recording:
            return
        
        # No fallback - real audio required
        self.stop_tuning(None)
        self.status_label.text = "ERROR: Real audio input required"
        raise RuntimeError("Audio simulation disabled. Real microphone access required for tuning.")
    
    def process_audio(self, audio_data):
        """Process audio data"""
        if not self.is_recording:
            return
        
        try:
            # Detect frequency
            freq = self.hps_detector.detect_frequency(audio_data)
            self.update_display(freq)
        except Exception as e:
            print(f"Processing error: {e}")
    
    def update_display(self, freq):
        """Update frequency display"""
        self.frequency = freq
        self.freq_label.text = f'{freq:.1f} Hz'
        
        # Update meter
        self.freq_meter.set_frequency(freq)
        
        # Determine note
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        note_index = int(12 * math.log2(freq / 440.0)) % 12
        self.note_name = notes[note_index]
        self.note_label.text = self.note_name
        
        # Calculate cents off
        target_freq = 440.0 * (2 ** (note_index / 12))
        cents = 1200 * math.log2(freq / target_freq)
        self.cents_off = cents
        
        # Update status
                if abs(cents) < 5:
            self.status_label.text = 'In tune!'
            self.note_label.color = (0, 1, 0, 1)  # Green
                elif abs(cents) < 20:
            self.status_label.text = f'Close! {cents:+.0f} cents'
            self.note_label.color = (1, 0.5, 0, 1)  # Orange
                else:
            self.status_label.text = f'Off by {cents:+.0f} cents'
            self.note_label.color = (1, 0, 0, 1)  # Red
    
    def go_to_search(self, instance):
        """Go to search screen"""
        self.manager.current = 'search'
    
    def go_to_library(self, instance):
        """Go to library screen"""
        self.manager.current = 'library'


class SearchScreen(Screen):
    """Search screen for finding songs"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results = []
        self.build_ui()
    
    def build_ui(self):
        """Build the search UI"""
        # Main container
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        
        # Title
        title = SimpleLabel(
            text='🔍 Search Songs',
            font_size=sp(24),
            size_hint_y=None,
            height=dp(60)
        )
        main_layout.add_widget(title)
        
        # Search input
        search_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        self.search_input = TextInput(
            hint_text='Enter song name or artist...',
            multiline=False,
            size_hint_x=0.7
        )
        search_layout.add_widget(self.search_input)
        
        search_btn = SimpleButton(
            text='SEARCH',
            on_press=self.search_songs,
            size_hint_x=0.3
        )
        search_layout.add_widget(search_btn)
        
        main_layout.add_widget(search_layout)
        
        # Results scroll
        self.results_scroll = ScrollView()
        self.results_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        self.results_layout.bind(minimum_height=self.results_layout.setter('height'))
        self.results_scroll.add_widget(self.results_layout)
        main_layout.add_widget(self.results_scroll)
        
        # Navigation
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        tuner_btn = SimpleButton(
            text='TUNER',
            on_press=self.go_to_tuner
        )
        nav_layout.add_widget(tuner_btn)
        
        library_btn = SimpleButton(
            text='LIBRARY',
            on_press=self.go_to_library
        )
        nav_layout.add_widget(library_btn)
        
        settings_btn = SimpleButton(
            text='SETTINGS',
            on_press=self.go_to_settings
        )
        nav_layout.add_widget(settings_btn)
        
        main_layout.add_widget(nav_layout)
        
        self.add_widget(main_layout)
    
    def search_songs(self, instance):
        """Search for songs"""
        query = self.search_input.text.strip()
        if not query:
            return
        
        # Clear previous results
        self.results_layout.clear_widgets()
        
        # Show searching message
        searching = SimpleLabel(
            text='Searching...',
            font_size=sp(16),
            size_hint_y=None,
            height=dp(40)
        )
        self.results_layout.add_widget(searching)
        
        # Perform search
        try:
            results = search_cifraclub(query)
            self.results = results
            
            self.results_layout.clear_widgets()
            
            if not results:
                no_results = SimpleLabel(
                    text='No results found',
                    font_size=sp(16),
                    size_hint_y=None,
                    height=dp(40)
                )
                self.results_layout.add_widget(no_results)
            else:
                for result in results[:10]:  # Limit to 10 results
                    self.add_result(result)
                    
        except Exception as e:
            self.results_layout.clear_widgets()
            error = SimpleLabel(
                text=f'Search error: {e}',
                font_size=sp(16),
                    size_hint_y=None,
                height=dp(40)
            )
            self.results_layout.add_widget(error)
    
    def add_result(self, result):
        """Add a search result"""
        result_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100), spacing=dp(5))
        
        # Title
        title = SimpleLabel(
            text=result.get('title', 'Unknown'),
            font_size=sp(16),
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        result_layout.add_widget(title)
        
        # URL
        url = SimpleLabel(
            text=result.get('url', ''),
            font_size=sp(12),
            size_hint_y=None,
            height=dp(20),
            halign='left'
        )
        result_layout.add_widget(url)
        
        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(5))
        
        save_btn = SimpleButton(
            text='SAVE',
            on_press=lambda x: self.save_song(result),
            size_hint_x=0.5
        )
        button_layout.add_widget(save_btn)
        
        open_btn = SimpleButton(
            text='OPEN',
            on_press=lambda x: self.open_song(result),
            size_hint_x=0.5
        )
        button_layout.add_widget(open_btn)
        
        result_layout.add_widget(button_layout)
        self.results_layout.add_widget(result_layout)
    
    def save_song(self, result):
        """Save song to library"""
        try:
            # Get database instance
            db = Database()
            db.save_song(
                result.get('title', 'Unknown'),
                result.get('artist', 'Unknown'),
                result.get('content', ''),
                result.get('url', '')
            )
            
            # Show success message
            success = SimpleLabel(
                text='Song saved to library!',
                font_size=sp(14),
                size_hint_y=None,
                height=dp(30)
            )
            self.results_layout.add_widget(success)

        except Exception as e:
            print(f"Save error: {e}")
    
    def open_song(self, result):
        """Open song in browser"""
        url = result.get('url', '')
        if url:
            open_url(url)
    
    def go_to_tuner(self, instance):
        """Go to tuner screen"""
        self.manager.current = 'tuner'

    def go_to_library(self, instance):
        """Go to library screen"""
        self.manager.current = 'library'

    def go_to_settings(self, instance):
        """Go to settings screen"""
        self.manager.current = 'settings'
    
    
class SettingsScreen(Screen):
    """Settings screen for API configuration"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        """Build the settings UI"""
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Title
        title = SimpleLabel(
            text='Settings',
            size_hint_y=None,
            height=40,
            font_size=24,
            bold=True
        )
        main_layout.add_widget(title)
        
        # API Configuration Card
        api_card = SimpleCard()
        api_layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        api_title = SimpleLabel(
            text='API Configuration',
            size_hint_y=None,
            height=30,
            font_size=18,
            bold=True
        )
        api_layout.add_widget(api_title)
        
        # Serper API Key
        serper_label = SimpleLabel(
            text='Serper API Key:',
            size_hint_y=None,
            height=25,
            font_size=14
        )
        api_layout.add_widget(serper_label)
        
        self.api_key_input = TextInput(
            hint_text='Enter your Serper API key',
            size_hint_y=None,
            height=40,
            multiline=False,
            password=True
        )
        api_layout.add_widget(self.api_key_input)
        
        # API Key Info
        info_label = SimpleLabel(
            text='Get your free API key at: https://serper.dev',
            size_hint_y=None,
            height=25,
            font_size=12,
            color=(0.6, 0.6, 0.6, 1)
        )
        api_layout.add_widget(info_label)
        
        # Save Button
        save_button = SimpleButton(
            text='Save API Key',
            size_hint_y=None,
            height=40
        )
        save_button.bind(on_press=self.save_api_key)
        api_layout.add_widget(save_button)
        
        api_card.add_widget(api_layout)
        main_layout.add_widget(api_card)
        
        # Status Card
        status_card = SimpleCard()
        status_layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        status_title = SimpleLabel(
            text='Status',
            size_hint_y=None,
            height=30,
            font_size=18,
            bold=True
        )
        status_layout.add_widget(status_title)
        
        self.status_label = SimpleLabel(
            text='API key not configured',
                    size_hint_y=None,
            height=25,
            font_size=14
        )
        status_layout.add_widget(self.status_label)
        
        # Test Button
        test_button = SimpleButton(
            text='Test API Key',
                    size_hint_y=None,
            height=40
        )
        test_button.bind(on_press=self.test_api_key)
        status_layout.add_widget(test_button)
        
        status_card.add_widget(status_layout)
        main_layout.add_widget(status_card)
        
        # Back Button
        back_button = SimpleButton(
            text='Back to Search',
            size_hint_y=None,
            height=50
        )
        back_button.bind(on_press=self.go_to_search)
        main_layout.add_widget(back_button)
        
        self.add_widget(main_layout)
        self.load_api_key()
    
    def go_to_search(self, instance):
        """Go to search screen"""
        self.manager.current = 'search'
    
    def load_api_key(self):
        """Load API key from settings"""
        try:
            # Try to load from the original settings system
            from chord_importer.models.settings import get_settings
            settings = get_settings()
            api_key = settings.get_serper_api_key()
            if api_key:
                self.api_key_input.text = api_key
                self.status_label.text = 'API key loaded from settings'
                self.status_label.color = (0, 0.8, 0, 1)  # Green
            else:
                self.status_label.text = 'No API key configured'
                self.status_label.color = (0.8, 0, 0, 1)  # Red
        except Exception as e:
            self.status_label.text = f'Error loading settings: {e}'
            self.status_label.color = (0.8, 0, 0, 1)  # Red
    
    def save_api_key(self, instance):
        """Save API key to settings"""
        api_key = self.api_key_input.text.strip()
        if not api_key:
            self.status_label.text = 'Please enter an API key'
            self.status_label.color = (0.8, 0, 0, 1)  # Red
            return
        
        try:
            # Save to the original settings system
            from chord_importer.models.settings import get_settings
            settings = get_settings()
            settings.set_serper_api_key(api_key)
            settings.save_settings()
            
            self.status_label.text = 'API key saved successfully!'
            self.status_label.color = (0, 0.8, 0, 1)  # Green
        except Exception as e:
            self.status_label.text = f'Error saving API key: {e}'
            self.status_label.color = (0.8, 0, 0, 1)  # Red
    
    def test_api_key(self, instance):
        """Test the API key"""
        api_key = self.api_key_input.text.strip()
        if not api_key:
            self.status_label.text = 'Please enter an API key first'
            self.status_label.color = (0.8, 0, 0, 1)  # Red
            return
        
        try:
            # Test with a simple search
            import requests
            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
            payload = {"q": "test", "gl": "br", "hl": "pt-br", "num": 1}
            response = requests.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.status_label.text = 'API key is working!'
                self.status_label.color = (0, 0.8, 0, 1)  # Green
            else:
                self.status_label.text = f'API error: {response.status_code}'
                self.status_label.color = (0.8, 0, 0, 1)  # Red
        except Exception as e:
            self.status_label.text = f'Test failed: {e}'
            self.status_label.color = (0.8, 0, 0, 1)  # Red


class LibraryScreen(Screen):
    """Library screen for saved songs"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.songs = []
        self.database = Database()
        self.build_ui()
        self.load_songs()
    
    def build_ui(self):
        """Build the library UI"""
        # Main container
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        
        # Title
        title = SimpleLabel(
            text='📚 My Library',
            font_size=sp(24),
            size_hint_y=None,
            height=dp(60)
        )
        main_layout.add_widget(title)
        
        # Songs scroll
        self.songs_scroll = ScrollView()
        self.songs_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        self.songs_layout.bind(minimum_height=self.songs_layout.setter('height'))
        self.songs_scroll.add_widget(self.songs_layout)
        main_layout.add_widget(self.songs_scroll)
        
        # Navigation
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        tuner_btn = SimpleButton(
            text='TUNER',
            on_press=self.go_to_tuner
        )
        nav_layout.add_widget(tuner_btn)
        
        search_btn = SimpleButton(
            text='SEARCH',
            on_press=self.go_to_search
        )
        nav_layout.add_widget(search_btn)
        
        main_layout.add_widget(nav_layout)
        
        self.add_widget(main_layout)
    
    def load_songs(self):
        """Load saved songs from database"""
        try:
            songs = self.database.get_all_songs()
            self.songs = songs
            self.update_song_display()
        except Exception as e:
            print(f"Library Error: {e}")
    
    def update_song_display(self):
        """Update the song display"""
        self.songs_layout.clear_widgets()
        
        if not self.songs:
            no_songs = SimpleLabel(
                text='No songs saved yet',
                font_size=sp(16),
                size_hint_y=None,
                height=dp(40)
            )
            self.songs_layout.add_widget(no_songs)
        else:
            for song in self.songs:
                self.add_song_display(song)
    
    def add_song_display(self, song):
        """Add a song to the display"""
        song_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120), spacing=dp(5))
        
        # Title
        title = SimpleLabel(
            text=song.get('title', 'Unknown'),
            font_size=sp(16),
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        song_layout.add_widget(title)
        
        # Artist
        artist = SimpleLabel(
            text=song.get('artist', 'Unknown'),
            font_size=sp(14),
            size_hint_y=None,
            height=dp(25),
            halign='left'
        )
        song_layout.add_widget(artist)
        
        # Content preview
        content = song.get('content', '') or ''
        content_preview = content[:80] + "..." if len(content) > 80 else content
        content_label = SimpleLabel(
            text=content_preview,
            font_size=sp(12),
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        song_layout.add_widget(content_label)
        
        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(5))
        
        view_btn = SimpleButton(
            text='VIEW',
            on_press=lambda x: self.view_song(song),
            size_hint_x=0.5
        )
        button_layout.add_widget(view_btn)
        
        delete_btn = SimpleButton(
            text='DELETE',
            on_press=lambda x: self.delete_song(song),
            size_hint_x=0.5
        )
        button_layout.add_widget(delete_btn)
        
        song_layout.add_widget(button_layout)
        self.songs_layout.add_widget(song_layout)
    
    def view_song(self, song):
        """View song in browser"""
        url = song.get('url', '')
        if url:
            open_url(url)
    
    def delete_song(self, song):
        """Delete song from library"""
        try:
            # Remove from database
            if song in self.songs:
                self.songs.remove(song)
                self.update_song_display()
        except Exception as e:
            print(f"Delete error: {e}")
    
    def go_to_tuner(self, instance):
        """Go to tuner screen"""
        self.manager.current = 'tuner'
    
    def go_to_search(self, instance):
        """Go to search screen"""
        self.manager.current = 'search'


class ChordImporterApp(App):
    """Main Kivy application"""
    
    def build(self):
        """Build the app"""
        # Set window color
        Window.clearcolor = (0.95, 0.95, 0.98, 1)
        
        # Create screen manager
        sm = ScreenManager(transition=SlideTransition(direction='left', duration=0.3))
        sm.add_widget(TunerScreen(name='tuner'))
        sm.add_widget(SearchScreen(name='search'))
        sm.add_widget(LibraryScreen(name='library'))
        sm.add_widget(SettingsScreen(name='settings'))
        
        return sm


if __name__ == '__main__':
    ChordImporterApp().run()