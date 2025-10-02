"""
ChordImporter - Android/Kivy Version
Beautiful Mobile Guitar Tuner with HPS Algorithm
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line
from kivy.graphics.instructions import InstructionGroup
from kivy.animation import Animation
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
import webbrowser

import sys
import os
import math
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


class BeautifulButton(Button):
    """Custom button with beautiful styling"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.update_canvas, pos=self.update_canvas)
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Background gradient effect
            Color(0.2, 0.6, 1, 1)  # Blue
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12)]
            )
            # Highlight effect
            Color(1, 1, 1, 0.3)
            RoundedRectangle(
                pos=(self.pos[0], self.pos[1] + self.size[1] * 0.7),
                size=(self.size[0], self.size[1] * 0.3),
                radius=[dp(12)]
            )


class BeautifulCard(Widget):
    """Beautiful card widget with shadows and rounded corners"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.update_canvas, pos=self.update_canvas)
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Shadow effect
            Color(0, 0, 0, 0.1)
            RoundedRectangle(
                pos=(self.pos[0] + dp(2), self.pos[1] - dp(2)),
                size=self.size,
                radius=[dp(16)]
            )
            # Main card
            Color(1, 1, 1, 1)
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(16)]
            )


class FrequencyMeter(Widget):
    """Beautiful frequency meter with animated needle"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.needle_angle = 0
        self.target_angle = 0
        self.bind(size=self.update_canvas, pos=self.update_canvas)
        self.update_canvas()
    
    def set_frequency(self, freq):
        """Set frequency and animate needle"""
        if freq < 50:
            self.target_angle = -90  # Left side
        elif freq > 1000:
            self.target_angle = 90   # Right side
        else:
            # Map frequency to angle (-90 to 90 degrees)
            self.target_angle = (freq - 50) / (1000 - 50) * 180 - 90
        
        # Animate needle
        anim = Animation(needle_angle=self.target_angle, duration=0.3, transition='out_cubic')
        anim.start(self)
    
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
            
            # Scale marks
            Color(0.3, 0.3, 0.3, 1)
            for i in range(0, 181, 30):
                angle = math.radians(i - 90)
                x1 = center_x + math.cos(angle) * (radius - dp(10))
                y1 = center_y + math.sin(angle) * (radius - dp(10))
                x2 = center_x + math.cos(angle) * (radius - dp(20))
                y2 = center_y + math.sin(angle) * (radius - dp(20))
                Line(points=[x1, y1, x2, y2], width=dp(2))
            
            # Needle
            Color(1, 0.2, 0.2, 1)
            angle = math.radians(self.needle_angle)
            needle_x = center_x + math.cos(angle) * (radius - dp(15))
            needle_y = center_y + math.sin(angle) * (radius - dp(15))
            Line(points=[center_x, center_y, needle_x, needle_y], width=dp(4))
            
            # Center dot
            Color(0.2, 0.2, 0.2, 1)
            Ellipse(pos=(center_x - dp(3), center_y - dp(3)), size=(dp(6), dp(6)))


class BeautifulLabel(Label):
    """Beautiful label with custom styling"""
    
    def __init__(self, **kwargs):
        # Set default beautiful styling
        defaults = {
            'color': (0.2, 0.2, 0.2, 1),
            'font_size': sp(16),
            'halign': 'center',
            'valign': 'middle'
        }
        defaults.update(kwargs)
        super().__init__(**defaults)


class GradientBackground(Widget):
    """Beautiful gradient background widget"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.update_canvas, pos=self.update_canvas)
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Create gradient effect with multiple rectangles
            Color(0.95, 0.95, 0.98, 1)  # Light gray
            Rectangle(pos=self.pos, size=self.size)
            
            # Add subtle gradient overlay
            Color(0.9, 0.9, 0.95, 0.3)
            Rectangle(pos=(self.pos[0], self.pos[1] + self.size[1] * 0.7), 
                     size=(self.size[0], self.size[1] * 0.3))


class AnimatedButton(BeautifulButton):
    """Button with beautiful animations"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(on_press=self.animate_press)
    
    def animate_press(self, instance):
        """Animate button press"""
        # Scale animation
        anim = Animation(scale=0.95, duration=0.1) + Animation(scale=1.0, duration=0.1)
        anim.start(self)
        
        # Color pulse animation
        original_color = self.color
        pulse_anim = Animation(color=(1, 1, 1, 0.8), duration=0.1) + Animation(color=original_color, duration=0.1)
        pulse_anim.start(self)


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
        """Build the beautiful tuner UI - Mobile Optimized"""
        # Main container with gradient background
        main_container = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Header with icon and title
        header_card = BeautifulCard(size_hint_y=0.12)
        header_layout = BoxLayout(orientation='horizontal', padding=dp(15))
        
        # Guitar icon
        icon_label = BeautifulLabel(
            text='🎸',
            font_size=sp(32),
            size_hint_x=0.2
        )
        header_layout.add_widget(icon_label)
        
        # Title
        title_label = BeautifulLabel(
            text='Guitar Tuner',
            font_size=sp(24),
            bold=True,
            color=(0.2, 0.6, 1, 1),
            size_hint_x=0.8
        )
        header_layout.add_widget(title_label)
        
        header_card.add_widget(header_layout)
        main_container.add_widget(header_card)
        
        # Frequency meter card
        meter_card = BeautifulCard(size_hint_y=0.25)
        meter_layout = BoxLayout(orientation='vertical', padding=dp(20))
        
        # Frequency meter
        self.freq_meter = FrequencyMeter(size_hint_y=0.7)
        meter_layout.add_widget(self.freq_meter)
        
        # Frequency display
        self.freq_label = BeautifulLabel(
            text='0.00 Hz',
            font_size=sp(20),
            color=(0.2, 0.2, 0.2, 1),
            size_hint_y=0.3
        )
        meter_layout.add_widget(self.freq_label)
        
        meter_card.add_widget(meter_layout)
        main_container.add_widget(meter_card)
        
        # Note display card
        note_card = BeautifulCard(size_hint_y=0.2)
        note_layout = BoxLayout(orientation='vertical', padding=dp(20))
        
        self.note_label = BeautifulLabel(
            text='--',
            font_size=sp(48),
            bold=True,
            color=(0.2, 0.8, 0.2, 1),
            size_hint_y=0.6
        )
        note_layout.add_widget(self.note_label)
        
        self.cents_label = BeautifulLabel(
            text='±0.0 cents',
            font_size=sp(16),
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=0.4
        )
        note_layout.add_widget(self.cents_label)
        
        note_card.add_widget(note_layout)
        main_container.add_widget(note_card)
        
        # Status card
        status_card = BeautifulCard(size_hint_y=0.08)
        status_layout = BoxLayout(orientation='horizontal', padding=dp(15))
        
        self.status_label = BeautifulLabel(
            text=self.status_text,
            font_size=sp(14),
            color=(0.6, 0.6, 0.6, 1),
            size_hint_x=0.8
        )
        status_layout.add_widget(self.status_label)
        
        # Recording indicator
        self.recording_indicator = BeautifulLabel(
            text='●',
            font_size=sp(20),
            color=(1, 0.2, 0.2, 0),
            size_hint_x=0.2
        )
        status_layout.add_widget(self.recording_indicator)
        
        status_card.add_widget(status_layout)
        main_container.add_widget(status_card)
        
        # Control buttons - Beautiful design
        btn_layout = BoxLayout(size_hint_y=0.2, spacing=dp(15))
        
        # Start/Stop button
        self.start_btn = BeautifulButton(
            text='🎵 START',
            font_size=sp(18),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(0.4, 1)
        )
        self.start_btn.bind(on_press=self.toggle_recording)
        btn_layout.add_widget(self.start_btn)
        
        # Search button
        search_btn = BeautifulButton(
            text='🔍 SEARCH',
            font_size=sp(18),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(0.3, 1)
        )
        search_btn.bind(on_press=self.go_to_search)
        btn_layout.add_widget(search_btn)
        
        # Library button
        library_btn = BeautifulButton(
            text='📚 LIBRARY',
            font_size=sp(18),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(0.3, 1)
        )
        library_btn.bind(on_press=self.go_to_library)
        btn_layout.add_widget(library_btn)
        
        main_container.add_widget(btn_layout)
        
        self.add_widget(main_container)
        
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
            self.start_btn.text = '⏹ STOP'
            self.status_text = "Listening... Play a note"
            
            # Animate recording indicator
            self.recording_indicator.color = (1, 0.2, 0.2, 1)
            anim = Animation(color=(1, 0.2, 0.2, 0.3), duration=0.5) + Animation(color=(1, 0.2, 0.2, 1), duration=0.5)
            anim.repeat = True
            anim.start(self.recording_indicator)
            
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
        self.start_btn.text = '🎵 START'
        self.status_text = "Stopped"
        
        # Stop recording indicator animation
        self.recording_indicator.color = (1, 0.2, 0.2, 0)
        Animation.cancel_all(self.recording_indicator)
        
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
                
                # Update frequency meter
                self.freq_meter.set_frequency(freq)
                
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
        """Build the beautiful search UI - Mobile Optimized"""
        main_container = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Header card
        header_card = BeautifulCard(size_hint_y=0.1)
        header_layout = BoxLayout(orientation='horizontal', padding=dp(15))
        
        # Search icon
        icon_label = BeautifulLabel(
            text='🔍',
            font_size=sp(28),
            size_hint_x=0.2
        )
        header_layout.add_widget(icon_label)
        
        # Title
        title_label = BeautifulLabel(
            text='Chord Search',
            font_size=sp(22),
            bold=True,
            color=(0.2, 0.6, 1, 1),
            size_hint_x=0.8
        )
        header_layout.add_widget(title_label)
        
        header_card.add_widget(header_layout)
        main_container.add_widget(header_card)
        
        # Search input card
        search_card = BeautifulCard(size_hint_y=0.12)
        search_layout = BoxLayout(orientation='horizontal', padding=dp(15), spacing=dp(10))
        
        self.search_input = TextInput(
            hint_text='Artist, song, or chords...',
            font_size=sp(16),
            multiline=False,
            size_hint_x=0.7,
            padding=[dp(15), dp(15)],
            background_color=(0.98, 0.98, 0.98, 1),
            foreground_color=(0.2, 0.2, 0.2, 1)
        )
        self.search_input.bind(on_text_validate=self.perform_search)
        search_layout.add_widget(self.search_input)
        
        search_btn = BeautifulButton(
            text='🔍',
            font_size=sp(20),
            size_hint_x=0.3,
            color=(1, 1, 1, 1)
        )
        search_btn.bind(on_press=self.perform_search)
        search_layout.add_widget(search_btn)
        
        search_card.add_widget(search_layout)
        main_container.add_widget(search_card)
        
        # Results area - Beautiful scrolling
        scroll = ScrollView(
            size_hint=(1, 0.68), 
            scroll_type=['bars', 'content'], 
            bar_width=dp(8),
            bar_color=(0.2, 0.6, 1, 0.8)
        )
        self.results_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(12),
            size_hint_y=None,
            padding=[dp(10), dp(10)]
        )
        self.results_layout.bind(minimum_height=self.results_layout.setter('height'))
        scroll.add_widget(self.results_layout)
        main_container.add_widget(scroll)
        
        # Back button - Beautiful design
        back_btn = BeautifulButton(
            text='← BACK',
            font_size=sp(16),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=0.1
        )
        back_btn.bind(on_press=self.go_back)
        main_container.add_widget(back_btn)
        
        self.add_widget(main_container)
    
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
            
            # Display results - Beautiful cards
            for result in results[:20]:
                # Create beautiful result card
                result_card = BeautifulCard(size_hint_y=None, height=dp(100))
                result_layout = BoxLayout(orientation='horizontal', padding=dp(15), spacing=dp(10))
                
                # Song info section
                info_layout = BoxLayout(orientation='vertical', size_hint_x=0.5, spacing=dp(5))
                
                # Song title
                title_label = BeautifulLabel(
                    text=result.title,
                    font_size=sp(16),
                    bold=True,
                    color=(0.2, 0.2, 0.2, 1),
                    halign='left',
                    text_size=(None, None)
                )
                title_label.bind(size=title_label.setter('text_size'))
                info_layout.add_widget(title_label)
                
                # URL preview
                url_label = BeautifulLabel(
                    text=result.url[:60] + "..." if len(result.url) > 60 else result.url,
                    font_size=sp(12),
                    color=(0.5, 0.5, 0.5, 1),
                    halign='left',
                    text_size=(None, None)
                )
                url_label.bind(size=url_label.setter('text_size'))
                info_layout.add_widget(url_label)
                
                result_layout.add_widget(info_layout)
                
                # Action buttons
                btn_layout = BoxLayout(orientation='horizontal', size_hint_x=0.5, spacing=dp(8))
                
                # Save button
                save_btn = BeautifulButton(
                    text='💾\nSAVE',
                    font_size=sp(14),
                    bold=True,
                    color=(1, 1, 1, 1),
                    size_hint_x=0.5
                )
                save_btn.result_data = result
                save_btn.bind(on_press=self.save_to_library)
                btn_layout.add_widget(save_btn)
                
                # Open button
                open_btn = BeautifulButton(
                    text='🌐\nOPEN',
                    font_size=sp(14),
                    bold=True,
                    color=(1, 1, 1, 1),
                    size_hint_x=0.5
                )
                open_btn.url = result.url
                open_btn.bind(on_press=self.open_result)
                btn_layout.add_widget(open_btn)
                
                result_layout.add_widget(btn_layout)
                result_card.add_widget(result_layout)
                self.results_layout.add_widget(result_card)
                
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
        """Save search result to library - Extract chord content from website"""
        try:
            from chord_importer.models.database import get_database
            from chord_importer.services.flexible_extractor import extract_with_flexible_config
            db = get_database()

            result = instance.result_data
            url = result.url

            # Show extracting status
            instance.text = '⏳\nEXTRACTING'
            instance.background_color = (0.8, 0.6, 0.2, 1)

            # Extract chord content from the website
            title, artist, content = extract_with_flexible_config(url)

            # If extraction failed, use fallback data
            if not content or not content.strip():
                print(f"Failed to extract content from {url}, using fallback")
                # Parse title and artist from search result
                title_parts = result.title.split(' - ')
                if len(title_parts) >= 2:
                    artist = title_parts[0].strip()
                    title = ' - '.join(title_parts[1:]).strip()
                else:
                    title = result.title
                    artist = "Unknown"
                content = f"Content extraction failed. Original URL: {url}"

            # Save to database with extracted content
            db.save_song(
                title=title,
                artist=artist,
                url=url,
                source='search',
                content=content  # Save the extracted chord content
            )

            # Visual feedback
            instance.text = '✓\nSAVED'
            instance.background_color = (0.2, 0.8, 0.2, 1)
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
        """Build the beautiful library UI - Mobile Optimized"""
        main_container = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Header card
        header_card = BeautifulCard(size_hint_y=0.1)
        header_layout = BoxLayout(orientation='horizontal', padding=dp(15))
        
        # Library icon
        icon_label = BeautifulLabel(
            text='📚',
            font_size=sp(28),
            size_hint_x=0.2
        )
        header_layout.add_widget(icon_label)
        
        # Title
        title_label = BeautifulLabel(
            text='My Library',
            font_size=sp(22),
            bold=True,
            color=(0.2, 0.6, 1, 1),
            size_hint_x=0.6
        )
        header_layout.add_widget(title_label)
        
        # Refresh button
        refresh_btn = BeautifulButton(
            text='↻',
            font_size=sp(20),
            size_hint_x=0.2,
            color=(1, 1, 1, 1)
        )
        refresh_btn.bind(on_press=self.load_songs)
        header_layout.add_widget(refresh_btn)
        
        header_card.add_widget(header_layout)
        main_container.add_widget(header_card)
        
        # Songs list - Beautiful scrolling
        scroll = ScrollView(
            size_hint=(1, 0.8), 
            scroll_type=['bars', 'content'], 
            bar_width=dp(8),
            bar_color=(0.2, 0.6, 1, 0.8)
        )
        self.songs_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(12),
            size_hint_y=None,
            padding=[dp(10), dp(10)]
        )
        self.songs_layout.bind(minimum_height=self.songs_layout.setter('height'))
        scroll.add_widget(self.songs_layout)
        main_container.add_widget(scroll)
        
        # Back button - Beautiful design
        back_btn = BeautifulButton(
            text='← BACK',
            font_size=sp(16),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=0.1
        )
        back_btn.bind(on_press=self.go_back)
        main_container.add_widget(back_btn)
        
        self.add_widget(main_container)
    
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
            
            # Display each song - Beautiful cards
            for song in songs:
                # Create beautiful song card
                song_card = BeautifulCard(size_hint_y=None, height=dp(120))
                song_layout = BoxLayout(orientation='horizontal', padding=dp(15), spacing=dp(10))
                
                # Song info section
                info_layout = BoxLayout(orientation='vertical', size_hint_x=0.6, spacing=dp(5))
                
                # Song title
                title_label = BeautifulLabel(
                    text=song.get('title', 'Unknown'),
                    font_size=sp(16),
                    bold=True,
                    color=(0.2, 0.2, 0.2, 1),
                    halign='left',
                    text_size=(None, None)
                )
                title_label.bind(size=title_label.setter('text_size'))
                info_layout.add_widget(title_label)
                
                # Artist
                artist_label = BeautifulLabel(
                    text=song.get('artist', ''),
                    font_size=sp(14),
                    color=(0.5, 0.5, 0.5, 1),
                    halign='left',
                    text_size=(None, None)
                )
                artist_label.bind(size=artist_label.setter('text_size'))
                info_layout.add_widget(artist_label)
                
                # Content preview
                content = song.get('content', '') or ''
                content_preview = content[:80] + "..." if len(content) > 80 else content
                content_label = BeautifulLabel(
                    text=content_preview,
                    font_size=sp(12),
                    color=(0.6, 0.6, 0.6, 1),
                    halign='left',
                    text_size=(None, None)
                )
                content_label.bind(size=content_label.setter('text_size'))
                info_layout.add_widget(content_label)
                
                song_layout.add_widget(info_layout)
                
                # Action buttons
                btn_layout = BoxLayout(orientation='horizontal', size_hint_x=0.4, spacing=dp(8))
                
                # View button
                view_btn = BeautifulButton(
                    text='🎵\nVIEW',
                    font_size=sp(12),
                    bold=True,
                    color=(1, 1, 1, 1),
                    size_hint_x=0.5
                )
                view_btn.song_data = song
                view_btn.bind(on_press=self.view_song)
                btn_layout.add_widget(view_btn)
                
                # Delete button
                del_btn = BeautifulButton(
                    text='🗑\nDEL',
                    font_size=sp(12),
                    bold=True,
                    color=(1, 1, 1, 1),
                    size_hint_x=0.5
                )
                del_btn.song_id = song.get('id')
                del_btn.bind(on_press=self.delete_song)
                btn_layout.add_widget(del_btn)
                
                song_layout.add_widget(btn_layout)
                song_card.add_widget(song_layout)
                self.songs_layout.add_widget(song_card)
                
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
        """View song details - Show chord content"""
        song = instance.song_data
        content = song.get('content', '')
        url = song.get('url', '')
        
        if content and content.strip() and not content.startswith("Content extraction failed"):
            # Show chord content in a popup
            self.show_chord_content(song.get('title', 'Unknown'), content)
        elif url:
            # Fallback to opening URL if no content
            open_url(url)
        else:
            print("No content or URL available")
    
    def show_chord_content(self, title, content):
        """Show chord content in a popup window"""
        from kivy.uix.popup import Popup
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.label import Label
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        
        # Create content layout
        content_layout = BoxLayout(orientation='vertical', spacing=dp(10))
        
        # Title
        title_label = Label(
            text=f"🎵 {title}",
            font_size='20sp',
            size_hint_y=None,
            height=dp(50),
            color=(0.9, 0.9, 0.9, 1),
            bold=True
        )
        content_layout.add_widget(title_label)
        
        # Scrollable content
        scroll = ScrollView(
            size_hint=(1, 1),
            scroll_type=['bars'],
            bar_width=dp(10)
        )
        
        content_text = Label(
            text=content,
            font_size='14sp',
            text_size=(None, None),
            halign='left',
            valign='top',
            color=(0.8, 0.8, 0.8, 1),
            markup=True
        )
        content_text.bind(size=content_text.setter('text_size'))
        scroll.add_widget(content_text)
        content_layout.add_widget(scroll)
        
        # Close button
        close_btn = Button(
            text='CLOSE',
            size_hint_y=None,
            height=dp(50),
            font_size='18sp',
            background_color=(0.2, 0.6, 1, 1),
            background_normal='',
            bold=True
        )
        content_layout.add_widget(close_btn)
        
        # Create popup
        popup = Popup(
            title='',
            content=content_layout,
            size_hint=(0.9, 0.8),
            auto_dismiss=False
        )
        
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    
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
        """Build the beautiful app with mobile optimizations"""
        # Set beautiful gradient background
        Window.clearcolor = (0.95, 0.95, 0.98, 1)  # Light gray background
        
        # Create screen manager with smooth transitions
        sm = ScreenManager(transition=SlideTransition(direction='left', duration=0.4))
        sm.add_widget(TunerScreen(name='tuner'))
        sm.add_widget(SearchScreen(name='search'))
        sm.add_widget(LibraryScreen(name='library'))
        
        return sm


if __name__ == '__main__':
    ChordImporterApp().run()

