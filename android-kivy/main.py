"""
ChordImporter - Android/Kivy Version
Proof of Concept - Guitar Tuner with HPS Algorithm
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
import webbrowser

import sys
import os
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
    from chord_importer.utils.audio_helpers import AudioHelpers
except ImportError:
    print("Warning: Could not import AudioHelpers, using simplified version")
    AudioHelpers = None


def open_url(url):
    """Open URL in browser - works on Android and Desktop"""
    if ANDROID_BROWSER:
        try:
            # Use Android's native Intent system
            intent = Intent()
            intent.setAction(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(url))
            currentActivity = PythonActivity.mActivity
            currentActivity.startActivity(intent)
            return True
        except Exception as e:
            print(f"Android browser open failed: {e}")
            return False
    else:
        # Use standard webbrowser for desktop
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"Browser open failed: {e}")
            return False


class AudioInput:
    """Unified audio input for Android and Desktop"""
    
    def __init__(self, sample_rate=44100, buffer_size=4096):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.callback = None
        self.audio_buffer = []
        self.is_active = False
        
        if ANDROID_AUDIO:
            self._setup_android()
        else:
            self._setup_desktop()
    
    def _setup_android(self):
        """Setup Android audio using audiostream"""
        self.mic = get_input(
            callback=self._audio_callback_android,
            source='default',
            buffersize=self.buffer_size,
            encoding=16,
            channels=1,
            rate=self.sample_rate
        )
    
    def _setup_desktop(self):
        """Setup desktop audio using sounddevice or pyaudio"""
        try:
            import sounddevice as sd
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                channels=1,
                callback=self._audio_callback_desktop
            )
        except ImportError:
            print("Warning: sounddevice not available")
            self.stream = None
    
    def _audio_callback_android(self, buf):
        """Process audio data from Android"""
        if self.callback:
            audio_data = np.frombuffer(buf, dtype=np.int16)
            audio_data = audio_data.astype(np.float32) / 32768.0
            self.callback(audio_data)
    
    def _audio_callback_desktop(self, indata, frames, time, status):
        """Process audio data from desktop"""
        if self.callback:
            audio_data = indata[:, 0] if len(indata.shape) > 1 else indata
            self.callback(audio_data)
    
    def start(self):
        """Start audio capture"""
        self.is_active = True
        if ANDROID_AUDIO:
            self.mic.start()
        elif self.stream:
            self.stream.start()
    
    def stop(self):
        """Stop audio capture"""
        self.is_active = False
        if ANDROID_AUDIO:
            self.mic.stop()
        elif self.stream:
            self.stream.stop()


class HPSDetector:
    """Harmonic Product Spectrum frequency detector"""
    
    def __init__(self, sample_rate=44100, buffer_size=4096):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.current_frequency = 0.0
    
    def detect_frequency(self, audio_data):
        """Detect frequency using HPS algorithm"""
        if len(audio_data) < self.buffer_size:
            return 0.0
        
        # Apply Hann window
        windowed = audio_data * np.hanning(len(audio_data))
        
        # Compute FFT
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), 1.0 / self.sample_rate)
        
        # Apply HPS (multiply downsampled spectra)
        hps = spectrum.copy()
        for h in range(2, 6):  # Use 5 harmonics
            decimated = spectrum[::h]
            hps[:len(decimated)] *= decimated
        
        # Find peak in HPS
        min_freq_idx = int(50 * len(hps) / (self.sample_rate / 2))  # 50 Hz min
        max_freq_idx = int(1000 * len(hps) / (self.sample_rate / 2))  # 1000 Hz max
        
        if max_freq_idx > len(hps):
            max_freq_idx = len(hps) - 1
        
        peak_idx = np.argmax(hps[min_freq_idx:max_freq_idx]) + min_freq_idx
        
        if peak_idx < len(freqs):
            self.current_frequency = float(freqs[peak_idx])
        
        return float(self.current_frequency)
    
    @staticmethod
    def freq_to_note(frequency):
        """Convert frequency to note name and cents offset"""
        if frequency < 20:
            return "--", 0.0
        
        # Standard note names
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Calculate note number (A4 = 440Hz is note 69)
        note_num = 12 * np.log2(frequency / 440.0) + 69
        note_idx = int(round(note_num))
        
        # Calculate cents offset (convert to Python float)
        cents = float(100 * (note_num - note_idx))
        
        # Get note name with octave
        note_name = note_names[note_idx % 12]
        octave = (note_idx // 12) - 1
        
        return f"{note_name}{octave}", cents


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
        
        # Build UI
        self.build_ui()
    
    def build_ui(self):
        """Build the tuner UI - Mobile Optimized"""
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        
        # Header with larger touch-friendly size
        header = Label(
            text='🎸 Guitar Tuner',
            font_size='36sp',
            size_hint_y=0.08,
            color=(0.2, 0.6, 1, 1),
            bold=True
        )
        layout.add_widget(header)
        
        # Frequency display
        self.freq_label = Label(
            text='0.00 Hz',
            font_size='36sp',
            size_hint_y=0.12,
            color=(1, 1, 1, 1)
        )
        layout.add_widget(self.freq_label)
        
        # Note display
        self.note_label = Label(
            text='--',
            font_size='96sp',
            size_hint_y=0.25,
            bold=True,
            color=(0.2, 1, 0.2, 1)
        )
        layout.add_widget(self.note_label)
        
        # Cents display
        self.cents_label = Label(
            text='±0.0 cents',
            font_size='28sp',
            size_hint_y=0.1,
            color=(1, 1, 1, 1)
        )
        layout.add_widget(self.cents_label)
        
        # Status
        self.status_label = Label(
            text=self.status_text,
            font_size='16sp',
            size_hint_y=0.08,
            color=(0.7, 0.7, 0.7, 1)
        )
        layout.add_widget(self.status_label)
        
        # Spacer
        layout.add_widget(Label(size_hint_y=0.15))
        
        # Control buttons - Larger for touch
        btn_layout = BoxLayout(size_hint_y=0.18, spacing=dp(10))
        
        self.start_btn = Button(
            text='START',
            font_size='24sp',
            background_color=(0.2, 0.8, 0.2, 1),
            background_normal='',
            size_hint=(1, 1)
        )
        self.start_btn.bind(on_press=self.toggle_recording)
        btn_layout.add_widget(self.start_btn)
        
        search_btn = Button(
            text='SEARCH',
            font_size='24sp',
            background_color=(0.2, 0.6, 1, 1),
            background_normal='',
            size_hint=(1, 1)
        )
        search_btn.bind(on_press=self.go_to_search)
        btn_layout.add_widget(search_btn)
        
        library_btn = Button(
            text='LIBRARY',
            font_size='24sp',
            background_color=(0.8, 0.4, 0.8, 1),
            background_normal='',
            size_hint=(1, 1)
        )
        library_btn.bind(on_press=self.go_to_library)
        btn_layout.add_widget(library_btn)
        
        layout.add_widget(btn_layout)
        
        self.add_widget(layout)
        
        # Bind properties to update labels
        self.bind(frequency=self.update_freq_label)
        self.bind(note_name=self.update_note_label)
        self.bind(cents_off=self.update_cents_label)
        self.bind(status_text=self.update_status_label)
    
    def toggle_recording(self, instance):
        """Toggle recording on/off"""
        if not self.is_recording:
            self.start_tuning()
        else:
            self.stop_tuning()
    
    def start_tuning(self):
        """Start the tuner"""
        try:
            if not self.audio_input:
                self.audio_input = AudioInput()
                self.audio_input.callback = self.process_audio
            
            self.audio_input.start()
            self.is_recording = True
            self.start_btn.text = 'STOP'
            self.start_btn.background_color = (0.8, 0.2, 0.2, 1)
            self.status_text = "Listening... Play a note"
            
            # Schedule UI updates
            Clock.schedule_interval(self.update_display, 0.1)
            
        except Exception as e:
            self.status_text = f"Error: {str(e)}"
            print(f"Error starting tuner: {e}")
    
    def stop_tuning(self):
        """Stop the tuner"""
        if self.audio_input:
            self.audio_input.stop()
        
        self.is_recording = False
        self.start_btn.text = 'START'
        self.start_btn.background_color = (0.2, 0.8, 0.2, 1)
        self.status_text = "Stopped"
        
        Clock.unschedule(self.update_display)
    
    def process_audio(self, audio_data):
        """Process incoming audio data"""
        self.audio_buffer.extend(audio_data)
        
        # Keep buffer at reasonable size
        if len(self.audio_buffer) > self.buffer_size * 2:
            self.audio_buffer = self.audio_buffer[-self.buffer_size:]
    
    def update_display(self, dt):
        """Update the display with current frequency/note"""
        if len(self.audio_buffer) >= self.buffer_size:
            # Get frequency from HPS
            audio_chunk = np.array(self.audio_buffer[-self.buffer_size:])
            freq = self.hps_detector.detect_frequency(audio_chunk)
            
            if freq > 50:  # Valid frequency
                note, cents = HPSDetector.freq_to_note(freq)
                # Convert numpy types to Python native types for Kivy
                self.frequency = float(freq)
                self.note_name = str(note)
                self.cents_off = float(cents)
                
                # Update status based on tuning accuracy
                if abs(cents) < 5:
                    self.status_text = "🎯 Perfect tune!"
                    self.note_label.color = (0.2, 1, 0.2, 1)  # Green
                elif abs(cents) < 20:
                    self.status_text = "Close... Keep adjusting"
                    self.note_label.color = (1, 1, 0.2, 1)  # Yellow
                else:
                    self.status_text = "Tune needed"
                    self.note_label.color = (1, 0.4, 0.2, 1)  # Orange
    
    def update_freq_label(self, instance, value):
        self.freq_label.text = f'{value:.2f} Hz'
    
    def update_note_label(self, instance, value):
        self.note_label.text = value
    
    def update_cents_label(self, instance, value):
        if abs(value) < 0.1:
            self.cents_label.text = 'Perfect!'
        else:
            self.cents_label.text = f'{value:+.1f} cents'
    
    def update_status_label(self, instance, value):
        self.status_label.text = value
    
    def go_to_search(self, instance):
        """Navigate to search screen"""
        self.stop_tuning()
        self.manager.current = 'search'
    
    def go_to_library(self, instance):
        """Navigate to library screen"""
        self.stop_tuning()
        self.manager.current = 'library'


class SearchScreen(Screen):
    """Search screen for chord lookup"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_results = []
        self.build_ui()
    
    def build_ui(self):
        """Build the search UI - Mobile Optimized"""
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        
        # Header
        header = Label(
            text='🔍 Chord Search',
            font_size='32sp',
            size_hint_y=0.08,
            color=(0.2, 0.6, 1, 1),
            bold=True
        )
        layout.add_widget(header)
        
        # Search input box - Larger for mobile
        search_box = BoxLayout(size_hint_y=0.12, spacing=dp(10))
        
        self.search_input = TextInput(
            hint_text='Artist, song, or chords...',
            font_size='20sp',
            multiline=False,
            size_hint_x=0.65,
            padding=[dp(10), dp(10)]
        )
        self.search_input.bind(on_text_validate=self.perform_search)
        search_box.add_widget(self.search_input)
        
        search_btn = Button(
            text='GO',
            font_size='24sp',
            size_hint_x=0.35,
            background_color=(0.2, 0.8, 0.2, 1),
            background_normal='',
            bold=True
        )
        search_btn.bind(on_press=self.perform_search)
        search_box.add_widget(search_btn)
        
        layout.add_widget(search_box)
        
        # Results area - Better scrolling
        scroll = ScrollView(size_hint=(1, 0.70), scroll_type=['bars', 'content'], bar_width=dp(10))
        self.results_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(8),
            size_hint_y=None,
            padding=[dp(5), 0]
        )
        self.results_layout.bind(minimum_height=self.results_layout.setter('height'))
        scroll.add_widget(self.results_layout)
        layout.add_widget(scroll)
        
        # Back button - Larger touch target
        back_btn = Button(
            text='← BACK',
            font_size='24sp',
            size_hint_y=0.10,
            background_color=(0.5, 0.5, 0.5, 1),
            background_normal='',
            bold=True
        )
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def perform_search(self, instance):
        """Search using existing backend"""
        query = self.search_input.text.strip()
        if not query:
            return
        
        # Clear previous results
        self.results_layout.clear_widgets()
        
        # Add searching indicator
        searching = Label(
            text=f'Searching: {query}...',
            font_size='16sp',
            size_hint_y=None,
            height=40
        )
        self.results_layout.add_widget(searching)
        
        # Import and use existing search function
        try:
            from chord_importer.services.serper import search_cifraclub
            results = search_cifraclub(query)
            
            self.results_layout.clear_widgets()
            
            if not results:
                no_results = Label(
                    text='No results found',
                    font_size='16sp',
                    size_hint_y=None,
                    height=40
                )
                self.results_layout.add_widget(no_results)
                return
            
            # Display results - With Open and Save buttons
            for result in results[:20]:
                # Container for each result
                result_box = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=dp(90),
                    spacing=dp(8)
                )
                
                # Song info button (opens browser)
                info_btn = Button(
                    text=f"{result.title}\n{result.url[:50]}...",
                    font_size='16sp',
                    size_hint_x=0.5,
                    background_color=(0.2, 0.2, 0.3, 1),
                    background_normal='',
                    halign='left',
                    valign='middle',
                    padding=[dp(12), dp(8)]
                )
                info_btn.url = result.url
                info_btn.bind(on_press=self.open_result)
                result_box.add_widget(info_btn)
                
                # Save to library button
                save_btn = Button(
                    text='💾\nSAVE',
                    font_size='18sp',
                    size_hint_x=0.25,
                    background_color=(0.2, 0.8, 0.2, 1),
                    background_normal='',
                    bold=True
                )
                save_btn.result_data = result
                save_btn.bind(on_press=self.save_to_library)
                result_box.add_widget(save_btn)
                
                # Open browser button
                open_btn = Button(
                    text='🌐\nOPEN',
                    font_size='18sp',
                    size_hint_x=0.25,
                    background_color=(0.2, 0.6, 1, 1),
                    background_normal='',
                    bold=True
                )
                open_btn.url = result.url
                open_btn.bind(on_press=self.open_result)
                result_box.add_widget(open_btn)
                
                self.results_layout.add_widget(result_box)
                
        except Exception as e:
            self.results_layout.clear_widgets()
            error_label = Label(
                text=f'Error: {str(e)}',
                font_size='14sp',
                size_hint_y=None,
                height=60,
                color=(1, 0.3, 0.3, 1)
            )
            self.results_layout.add_widget(error_label)
    
    def save_to_library(self, instance):
        """Save search result to library"""
        try:
            from chord_importer.models.database import get_database
            db = get_database()
            
            result = instance.result_data
            
            # Parse title and artist
            title_parts = result.title.split(' - ')
            if len(title_parts) >= 2:
                artist = title_parts[0].strip()
                title = ' - '.join(title_parts[1:]).strip()
            else:
                title = result.title
                artist = "Unknown"
            
            # Save to database
            db.save_song(
                title=title,
                artist=artist,
                url=result.url,
                source='search'
            )
            
            # Visual feedback
            instance.text = '✓\nSAVED'
            instance.background_color = (0.3, 0.3, 0.3, 1)
            instance.disabled = True
            
        except Exception as e:
            print(f"Error saving to library: {e}")
            import traceback
            traceback.print_exc()
            instance.text = '✗\nERROR'
            instance.background_color = (0.8, 0.2, 0.2, 1)
    
    def open_result(self, instance):
        """Open result in browser"""
        open_url(instance.url)
    
    def go_back(self, instance):
        """Go back to tuner"""
        self.manager.current = 'tuner'


class LibraryScreen(Screen):
    """Saved songs library"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = None
        self.build_ui()
    
    def on_enter(self):
        """Called when screen is displayed"""
        self.load_songs()
    
    def build_ui(self):
        """Build the library UI - Mobile Optimized"""
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        
        # Header - Better mobile layout
        header_box = BoxLayout(size_hint_y=0.10, spacing=dp(10))
        
        header = Label(
            text='📚 My Library',
            font_size='32sp',
            size_hint_x=0.7,
            color=(0.2, 0.6, 1, 1),
            bold=True
        )
        header_box.add_widget(header)
        
        refresh_btn = Button(
            text='↻',
            font_size='32sp',
            size_hint_x=0.3,
            background_color=(0.3, 0.6, 0.9, 1),
            background_normal='',
            bold=True
        )
        refresh_btn.bind(on_press=self.load_songs)
        header_box.add_widget(refresh_btn)
        
        layout.add_widget(header_box)
        
        # Songs list - Better scrolling
        scroll = ScrollView(size_hint=(1, 0.80), scroll_type=['bars', 'content'], bar_width=dp(10))
        self.songs_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(8),
            size_hint_y=None,
            padding=[dp(5), 0]
        )
        self.songs_layout.bind(minimum_height=self.songs_layout.setter('height'))
        scroll.add_widget(self.songs_layout)
        layout.add_widget(scroll)
        
        # Back button - Larger touch target
        back_btn = Button(
            text='← BACK',
            font_size='24sp',
            size_hint_y=0.10,
            background_color=(0.5, 0.5, 0.5, 1),
            background_normal='',
            bold=True
        )
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def load_songs(self, instance=None):
        """Load songs from database"""
        self.songs_layout.clear_widgets()
        
        try:
            from chord_importer.models.database import get_database
            self.db = get_database()
            
            songs = self.db.get_songs()
            
            if not songs:
                no_songs = Label(
                    text='No saved songs yet\nSearch and save from Search tab',
                    font_size='16sp',
                    size_hint_y=None,
                    height=80,
                    color=(0.7, 0.7, 0.7, 1)
                )
                self.songs_layout.add_widget(no_songs)
                return
            
            # Display each song - Better layout with action buttons
            for song in songs:
                song_box = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=dp(100),
                    spacing=dp(8)
                )
                
                # Song info label (not clickable)
                song_info = Label(
                    text=f"{song.get('title', 'Unknown')}\n{song.get('artist', '')}",
                    font_size='18sp',
                    size_hint_x=0.5,
                    color=(0.9, 0.9, 0.9, 1),
                    halign='left',
                    valign='middle',
                    text_size=(None, None)
                )
                song_info.bind(size=song_info.setter('text_size'))
                song_box.add_widget(song_info)
                
                # Open button - Opens in browser
                open_btn = Button(
                    text='🌐\nOPEN',
                    font_size='18sp',
                    size_hint_x=0.25,
                    background_color=(0.2, 0.6, 1, 1),
                    background_normal='',
                    bold=True
                )
                open_btn.song_data = song
                open_btn.bind(on_press=self.view_song)
                song_box.add_widget(open_btn)
                
                # Delete button - Larger for easier tapping
                del_btn = Button(
                    text='🗑\nDEL',
                    font_size='18sp',
                    size_hint_x=0.25,
                    background_color=(0.8, 0.2, 0.2, 1),
                    background_normal='',
                    bold=True
                )
                del_btn.song_id = song.get('id')
                del_btn.bind(on_press=self.delete_song)
                song_box.add_widget(del_btn)
                
                self.songs_layout.add_widget(song_box)
                
        except Exception as e:
            print(f"Library Error: {e}")
            import traceback
            traceback.print_exc()
            
            error_label = Label(
                text=f'Library Error:\n{str(e)}\n\nMake sure database is accessible',
                font_size='14sp',
                size_hint_y=None,
                height=100,
                color=(1, 0.3, 0.3, 1)
            )
            self.songs_layout.add_widget(error_label)
    
    def view_song(self, instance):
        """View song details"""
        song = instance.song_data
        url = song.get('url', '')
        if url:
            open_url(url)
    
    def delete_song(self, instance):
        """Delete a song"""
        if self.db:
            self.db.delete_song(instance.song_id)
            self.load_songs()
    
    def go_back(self, instance):
        """Go back to tuner"""
        self.manager.current = 'tuner'


class ChordImporterApp(App):
    """Main Kivy application - Mobile Optimized"""
    
    def build(self):
        """Build the app with mobile optimizations"""
        # Set window background color
        Window.clearcolor = (0.1, 0.1, 0.15, 1)
        
        # Create screen manager with smooth transitions
        sm = ScreenManager(transition=SlideTransition(direction='left', duration=0.3))
        sm.add_widget(TunerScreen(name='tuner'))
        sm.add_widget(SearchScreen(name='search'))
        sm.add_widget(LibraryScreen(name='library'))
        
        return sm


if __name__ == '__main__':
    ChordImporterApp().run()

