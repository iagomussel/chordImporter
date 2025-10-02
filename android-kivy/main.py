"""
ChordImporter - Android/Kivy Version
Proof of Concept - Guitar Tuner with HPS Algorithm
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.core.window import Window

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

# Import existing HPS algorithm and utilities
try:
    from chord_importer.utils.audio_helpers import AudioHelpers
except ImportError:
    print("Warning: Could not import AudioHelpers, using simplified version")
    AudioHelpers = None


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
            self.current_frequency = freqs[peak_idx]
        
        return self.current_frequency
    
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
        
        # Calculate cents offset
        cents = 100 * (note_num - note_idx)
        
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
        """Build the tuner UI"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Header
        header = Label(
            text='🎸 Guitar Tuner HPS',
            font_size='32sp',
            size_hint_y=0.1,
            color=(0.2, 0.6, 1, 1)
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
        
        # Control buttons
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        
        self.start_btn = Button(
            text='START',
            font_size='24sp',
            background_color=(0.2, 0.8, 0.2, 1),
            background_normal=''
        )
        self.start_btn.bind(on_press=self.toggle_recording)
        btn_layout.add_widget(self.start_btn)
        
        search_btn = Button(
            text='SEARCH',
            font_size='24sp',
            background_color=(0.2, 0.6, 1, 1),
            background_normal=''
        )
        search_btn.bind(on_press=self.go_to_search)
        btn_layout.add_widget(search_btn)
        
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
                self.frequency = freq
                self.note_name = note
                self.cents_off = cents
                
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


class SearchScreen(Screen):
    """Search screen for chord lookup"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        """Build the search UI"""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Header
        header = Label(
            text='🔍 Chord Search',
            font_size='32sp',
            size_hint_y=0.1,
            color=(0.2, 0.6, 1, 1)
        )
        layout.add_widget(header)
        
        # Info label
        info = Label(
            text='Search functionality coming soon!\nCurrent desktop features:\n- CifraClub search\n- Chord sequence search\n- File type filters',
            font_size='18sp',
            size_hint_y=0.4,
            color=(0.8, 0.8, 0.8, 1)
        )
        layout.add_widget(info)
        
        # Back button
        back_btn = Button(
            text='BACK TO TUNER',
            font_size='24sp',
            size_hint_y=0.15,
            background_color=(0.2, 0.6, 1, 1),
            background_normal=''
        )
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def go_back(self, instance):
        """Go back to tuner"""
        self.manager.current = 'tuner'


class ChordImporterApp(App):
    """Main Kivy application"""
    
    def build(self):
        """Build the app"""
        # Set window background color
        Window.clearcolor = (0.1, 0.1, 0.15, 1)
        
        # Create screen manager
        sm = ScreenManager()
        sm.add_widget(TunerScreen(name='tuner'))
        sm.add_widget(SearchScreen(name='search'))
        
        return sm


if __name__ == '__main__':
    ChordImporterApp().run()

