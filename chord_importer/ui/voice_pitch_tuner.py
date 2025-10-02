"""
Voice Pitch Tuner - Real-time voice pitch detection and tuning assistance.
Designed for vocal training and pitch accuracy improvement.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import queue
from typing import Optional, List, Tuple, Dict, Any
import math
from enum import Enum
from dataclasses import dataclass

# Required audio processing libraries - NO FALLBACKS
import numpy as np
import sounddevice as sd

try:
    from ..utils import AudioHelpers, UIHelpers, ErrorHandler
    from ..models.audio import AudioConfig, AudioAnalysisResult
except ImportError:
    from chord_importer.utils import AudioHelpers, UIHelpers, ErrorHandler
    from chord_importer.models.audio import AudioConfig, AudioAnalysisResult

# Verify critical dependencies are available
if not hasattr(np, 'zeros'):
    raise ImportError("numpy not properly installed")
if not hasattr(sd, 'InputStream'):
    raise ImportError("sounddevice not properly installed")


class TuningMode(Enum):
    """Different tuning modes for the voice pitch tuner."""
    CHROMATIC = "chromatic"  # All 12 semitones
    MAJOR_SCALE = "major_scale"  # Major scale notes only
    MINOR_SCALE = "minor_scale"  # Minor scale notes only
    PENTATONIC = "pentatonic"  # Pentatonic scale
    CUSTOM = "custom"  # User-defined notes


@dataclass
class VoiceRange:
    """Defines a vocal range with min/max frequencies."""
    name: str
    min_freq: float
    max_freq: float
    color: str


class VoicePitchTuner:
    """
    Real-time voice pitch tuner for vocal training and pitch accuracy.
    Features visual feedback, target note selection, and pitch history.
    """
    
    def __init__(self, parent: tk.Widget):
        """Initialize the voice pitch tuner."""
        self.parent = parent
        self.setup_window()
        
        # Audio configuration optimized for voice
        self.audio_config = AudioConfig(
            sample_rate=44100,
            channels=1,
            chunk_size=4096,  # Larger chunk for better frequency resolution
            min_frequency=80.0,
            max_frequency=2000.0,
            threshold=0.005,  # Lower threshold for voice detection
            reference_frequency=440.0,
            cents_tolerance=15.0
        )
        
        # Voice-specific parameters
        self.voice_threshold = 0.02  # Minimum amplitude for voice detection
        self.noise_gate = 0.01  # Noise gate threshold
        self.smoothing_factor = 0.3  # Pitch smoothing (0-1, higher = more smoothing)
        self.min_voice_freq = 80.0  # Minimum human voice frequency
        self.max_voice_freq = 1100.0  # Maximum human voice frequency
        self.stability_threshold = 5.0  # Cents - how stable pitch needs to be
        
        # Pitch tracking
        self.previous_frequency = 0.0
        self.stable_pitch_count = 0
        self.required_stability = 3  # Number of stable readings required
        
        # Auto voice range detection
        self.auto_range_enabled = True
        self.min_detected_freq = float('inf')
        self.max_detected_freq = 0.0
        self.range_analysis_samples = 50  # Minimum samples before auto-detection
        self.last_range_update = 0
        self.range_update_interval = 5.0  # Update range every 5 seconds
        
        # Audio processing
        self.audio_stream = None
        self.is_recording = False
        self.audio_queue = queue.Queue()
        
        # Pitch detection
        self.current_frequency = 0.0
        self.current_note = "N/A"
        self.current_octave = 0
        self.current_cents = 0.0
        self.confidence = 0.0
        
        # Target settings
        self.target_note = "A"
        self.target_octave = 4
        self.target_frequency = 440.0
        self.tuning_mode = TuningMode.CHROMATIC
        
        # Voice ranges
        self.voice_ranges = {
            "Soprano": VoiceRange("Soprano", 261.63, 1046.50, "#FF69B4"),  # C4-C6
            "Alto": VoiceRange("Alto", 174.61, 698.46, "#9370DB"),         # F3-F5
            "Tenor": VoiceRange("Tenor", 130.81, 523.25, "#4169E1"),       # C3-C5
            "Bass": VoiceRange("Bass", 87.31, 349.23, "#228B22"),          # F2-F4
            "Full Range": VoiceRange("Full Range", 80.0, 2000.0, "#808080")
        }
        self.selected_voice_range = "Full Range"
        
        # Pitch history for visualization
        self.pitch_history = []
        self.max_history_length = 100
        
        # Musical scales
        self.scales = {
            TuningMode.CHROMATIC: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            TuningMode.MAJOR_SCALE: [0, 2, 4, 5, 7, 9, 11],
            TuningMode.MINOR_SCALE: [0, 2, 3, 5, 7, 8, 10],
            TuningMode.PENTATONIC: [0, 2, 4, 7, 9]
        }
        
        self.setup_ui()
        self.setup_audio()
        
    def setup_window(self):
        """Setup the main window."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Voice Pitch Tuner - Enhanced")
        self.window.geometry("1200x800")
        self.window.minsize(900, 600)
        
        # Center the window
        UIHelpers.center_window(self.window, 1200, 800)
        
        # Configure window
        self.window.configure(bg="#f0f0f0")
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Handle window closing
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = tk.Frame(self.window, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Voice Pitch Tuner",
            font=("Arial", 18, "bold"),
            bg="#f0f0f0",
            fg="#2196F3"
        )
        title_label.pack(pady=(0, 20))
        
        # Control panel
        self.setup_control_panel(main_frame)
        
        # Pitch display
        self.setup_pitch_display(main_frame)
        
        # Visual tuner
        self.setup_visual_tuner(main_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#e0e0e0",
            font=("Arial", 9)
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
    def setup_control_panel(self, parent):
        """Setup the control panel."""
        control_frame = tk.LabelFrame(
            parent,
            text="Controls",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0",
            fg="#333333"
        )
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # First row - Recording and device controls
        row1 = tk.Frame(control_frame, bg="#f0f0f0")
        row1.pack(fill=tk.X, padx=10, pady=10)
        
        # Start/Stop button
        self.record_button = UIHelpers.create_styled_button(
            row1,
            text="Start Tuning",
            command=self.toggle_recording,
            bg_color="#4CAF50",
            hover_color="#45a049"
        )
        self.record_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Device selection
        tk.Label(row1, text="Microphone:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(
            row1,
            textvariable=self.device_var,
            state="readonly",
            width=25
        )
        self.device_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_changed)
        
        # Refresh devices button
        refresh_btn = UIHelpers.create_styled_button(
            row1,
            text="Refresh",
            command=self.refresh_devices,
            bg_color="#2196F3",
            hover_color="#1976D2"
        )
        refresh_btn.pack(side=tk.LEFT)
        
        # Second row - Tuning settings
        row2 = tk.Frame(control_frame, bg="#f0f0f0")
        row2.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Voice range selection with auto-detection
        tk.Label(row2, text="Voice Range:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 5))
        
        # Auto-detection checkbox
        self.auto_range_var = tk.BooleanVar(value=self.auto_range_enabled)
        auto_check = tk.Checkbutton(
            row2,
            text="Auto",
            variable=self.auto_range_var,
            command=self.on_auto_range_changed,
            bg="#f0f0f0"
        )
        auto_check.pack(side=tk.LEFT, padx=(0, 5))
        
        # Manual range selection
        self.voice_range_var = tk.StringVar(value=self.selected_voice_range)
        self.voice_range_combo = ttk.Combobox(
            row2,
            textvariable=self.voice_range_var,
            values=list(self.voice_ranges.keys()),
            state="readonly" if not self.auto_range_enabled else "disabled",
            width=15
        )
        self.voice_range_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.voice_range_combo.bind("<<ComboboxSelected>>", self.on_voice_range_changed)
        
        # Tuning mode selection
        tk.Label(row2, text="Scale:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        self.tuning_mode_var = tk.StringVar(value=self.tuning_mode.value)
        tuning_mode_combo = ttk.Combobox(
            row2,
            textvariable=self.tuning_mode_var,
            values=[mode.value.replace("_", " ").title() for mode in TuningMode],
            state="readonly",
            width=15
        )
        tuning_mode_combo.pack(side=tk.LEFT, padx=(0, 10))
        tuning_mode_combo.bind("<<ComboboxSelected>>", self.on_tuning_mode_changed)
        
        # Reference frequency
        tk.Label(row2, text="A4 Ref:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        self.ref_freq_var = tk.StringVar(value="440")
        ref_freq_entry = tk.Entry(row2, textvariable=self.ref_freq_var, width=8)
        ref_freq_entry.pack(side=tk.LEFT, padx=(0, 5))
        ref_freq_entry.bind("<Return>", self.on_reference_changed)
        tk.Label(row2, text="Hz", bg="#f0f0f0").pack(side=tk.LEFT)
        
        # Third row - Voice detection settings
        row3 = tk.Frame(control_frame, bg="#f0f0f0")
        row3.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Voice sensitivity
        tk.Label(row3, text="Voice Sensitivity:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 5))
        self.sensitivity_var = tk.DoubleVar(value=self.voice_threshold * 1000)
        sensitivity_scale = tk.Scale(
            row3,
            from_=5, to=50,
            orient=tk.HORIZONTAL,
            variable=self.sensitivity_var,
            command=self.on_sensitivity_changed,
            length=100
        )
        sensitivity_scale.pack(side=tk.LEFT, padx=(0, 10))
        
        # Smoothing
        tk.Label(row3, text="Smoothing:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        self.smoothing_var = tk.DoubleVar(value=self.smoothing_factor * 100)
        smoothing_scale = tk.Scale(
            row3,
            from_=0, to=80,
            orient=tk.HORIZONTAL,
            variable=self.smoothing_var,
            command=self.on_smoothing_changed,
            length=100
        )
        smoothing_scale.pack(side=tk.LEFT, padx=(0, 10))
        
        # Noise gate
        tk.Label(row3, text="Noise Gate:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(10, 5))
        self.noise_gate_var = tk.DoubleVar(value=self.noise_gate * 1000)
        noise_gate_scale = tk.Scale(
            row3,
            from_=1, to=30,
            orient=tk.HORIZONTAL,
            variable=self.noise_gate_var,
            command=self.on_noise_gate_changed,
            length=100
        )
        noise_gate_scale.pack(side=tk.LEFT)
        
    def setup_pitch_display(self, parent):
        """Setup the pitch display panel."""
        display_frame = tk.LabelFrame(
            parent,
            text="Current Pitch",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0",
            fg="#333333"
        )
        display_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Main pitch info
        pitch_info_frame = tk.Frame(display_frame, bg="#f0f0f0")
        pitch_info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Current note display
        self.note_var = tk.StringVar(value="N/A")
        note_label = tk.Label(
            pitch_info_frame,
            textvariable=self.note_var,
            font=("Arial", 36, "bold"),
            bg="#f0f0f0",
            fg="#2196F3"
        )
        note_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Frequency and cents info
        info_frame = tk.Frame(pitch_info_frame, bg="#f0f0f0")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frequency
        freq_frame = tk.Frame(info_frame, bg="#f0f0f0")
        freq_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(freq_frame, text="Frequency:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        self.freq_var = tk.StringVar(value="0.0 Hz")
        tk.Label(freq_frame, textvariable=self.freq_var, bg="#f0f0f0", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 0))
        
        # Cents offset
        cents_frame = tk.Frame(info_frame, bg="#f0f0f0")
        cents_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(cents_frame, text="Cents:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        self.cents_var = tk.StringVar(value="0 ¢")
        self.cents_label = tk.Label(cents_frame, textvariable=self.cents_var, bg="#f0f0f0", font=("Arial", 10, "bold"))
        self.cents_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Confidence
        conf_frame = tk.Frame(info_frame, bg="#f0f0f0")
        conf_frame.pack(fill=tk.X)
        tk.Label(conf_frame, text="Confidence:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        self.conf_var = tk.StringVar(value="0%")
        tk.Label(conf_frame, textvariable=self.conf_var, bg="#f0f0f0", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 0))
        
    def setup_visual_tuner(self, parent):
        """Setup the visual tuner display."""
        tuner_frame = tk.LabelFrame(
            parent,
            text="Visual Tuner - Real-time Voice Analysis",
            font=("Arial", 14, "bold"),
            bg="#f0f0f0",
            fg="#333333"
        )
        tuner_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Canvas for visual tuner - much larger
        self.tuner_canvas = tk.Canvas(
            tuner_frame,
            height=400,  # Increased from 200 to 400
            bg="#1a1a1a",  # Dark background for better contrast
            highlightthickness=2,
            highlightbackground="#4CAF50"
        )
        self.tuner_canvas.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Bind canvas resize
        self.tuner_canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Initialize tuner display
        self.update_visual_tuner()
        
    def setup_audio(self):
        """Setup audio input."""
        self.refresh_devices()
        
    def refresh_devices(self):
        """Refresh the list of available audio devices."""
        try:
            devices = AudioHelpers.get_audio_devices()
            device_names = [f"{dev['name']} ({dev['index']})" for dev in devices]
            
            self.device_combo['values'] = device_names
            
            # Select default device
            default_device = AudioHelpers.get_default_input_device()
            if default_device is not None:
                for i, dev in enumerate(devices):
                    if dev['index'] == default_device:
                        self.device_combo.current(i)
                        break
            elif device_names:
                self.device_combo.current(0)
                
            self.status_var.set(f"Found {len(devices)} audio devices")
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "refreshing audio devices")
            self.status_var.set("Error refreshing devices")
            
    def on_device_changed(self, event=None):
        """Handle device selection change."""
        if self.is_recording:
            self.stop_recording()
            
    def on_voice_range_changed(self, event=None):
        """Handle voice range selection change."""
        if not self.auto_range_enabled:
            self.selected_voice_range = self.voice_range_var.get()
            voice_range = self.voice_ranges[self.selected_voice_range]
            self.audio_config.min_frequency = voice_range.min_freq
            self.audio_config.max_frequency = voice_range.max_freq
            self.update_visual_tuner()
    
    def on_auto_range_changed(self):
        """Handle auto-detection toggle."""
        self.auto_range_enabled = self.auto_range_var.get()
        
        if self.auto_range_enabled:
            # Enable auto-detection
            self.voice_range_combo.configure(state="disabled")
            self.status_var.set("Auto voice range detection enabled")
            # Reset detection parameters
            self.min_detected_freq = float('inf')
            self.max_detected_freq = 0.0
        else:
            # Disable auto-detection
            self.voice_range_combo.configure(state="readonly")
            self.status_var.set("Manual voice range selection enabled")
            # Apply current manual selection
            self.on_voice_range_changed()
        
    def on_tuning_mode_changed(self, event=None):
        """Handle tuning mode change."""
        mode_name = self.tuning_mode_var.get().lower().replace(" ", "_")
        for mode in TuningMode:
            if mode.value == mode_name:
                self.tuning_mode = mode
                break
        self.update_visual_tuner()
        
    def on_reference_changed(self, event=None):
        """Handle reference frequency change."""
        try:
            ref_freq = float(self.ref_freq_var.get())
            if 400 <= ref_freq <= 480:  # Reasonable range for A4
                self.audio_config.reference_frequency = ref_freq
                self.status_var.set(f"Reference frequency set to {ref_freq} Hz")
            else:
                raise ValueError("Reference frequency must be between 400-480 Hz")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            self.ref_freq_var.set(str(self.audio_config.reference_frequency))
            
    def on_sensitivity_changed(self, value):
        """Handle voice sensitivity change."""
        self.voice_threshold = float(value) / 1000
        self.status_var.set(f"Voice sensitivity: {float(value):.1f}")
        
    def on_smoothing_changed(self, value):
        """Handle smoothing change."""
        self.smoothing_factor = float(value) / 100
        self.status_var.set(f"Smoothing: {float(value):.0f}%")
        
    def on_noise_gate_changed(self, value):
        """Handle noise gate change."""
        self.noise_gate = float(value) / 1000
        self.status_var.set(f"Noise gate: {float(value):.1f}")
            
    def toggle_recording(self):
        """Toggle recording on/off."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def start_recording(self):
        """Start audio recording and pitch detection."""
        try:
            # Get selected device
            device_text = self.device_var.get()
            if not device_text:
                messagebox.showerror("Error", "Please select an audio device")
                return
                
            device_index = int(device_text.split("(")[-1].split(")")[0])
            
            # Validate audio parameters
            is_valid, error_msg = AudioHelpers.validate_audio_parameters(
                self.audio_config.sample_rate,
                self.audio_config.channels,
                self.audio_config.chunk_size
            )
            
            if not is_valid:
                messagebox.showerror("Audio Error", error_msg)
                return
            
            # Start audio stream
            self.audio_stream = sd.InputStream(
                device=device_index,
                channels=self.audio_config.channels,
                samplerate=self.audio_config.sample_rate,
                blocksize=self.audio_config.chunk_size,
                callback=self.audio_callback
            )
            
            self.audio_stream.start()
            self.is_recording = True
            
            # Update UI
            self.record_button.configure(text="Stop Tuning", bg="#f44336")
            self.status_var.set("Recording... Sing or hum into the microphone")
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self.process_audio, daemon=True)
            self.processing_thread.start()
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "starting audio recording")
            self.status_var.set("Error starting recording")
            
    def stop_recording(self):
        """Stop audio recording."""
        try:
            self.is_recording = False
            
            if self.audio_stream:
                self.audio_stream.stop()
                self.audio_stream.close()
                self.audio_stream = None
            
            # Update UI
            self.record_button.configure(text="Start Tuning", bg="#4CAF50")
            self.status_var.set("Recording stopped")
            
            # Clear display
            self.note_var.set("N/A")
            self.freq_var.set("0.0 Hz")
            self.cents_var.set("0 ¢")
            self.conf_var.set("0%")
            self.cents_label.configure(fg="black")
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "stopping audio recording")
            
    def audio_callback(self, indata, frames, time, status):
        """Audio input callback."""
        if status:
            print(f"Audio status: {status}")
        
        if self.is_recording:
            # Convert to mono if stereo
            if indata.shape[1] > 1:
                audio_data = np.mean(indata, axis=1)
            else:
                audio_data = indata[:, 0]
            
            # Add to queue for processing
            self.audio_queue.put(audio_data.copy())
            
    def process_audio(self):
        """Process audio data in separate thread with enhanced voice detection."""
        while self.is_recording:
            try:
                # Get audio data from queue
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Enhanced voice detection and filtering
                if not self.is_voice_signal(audio_data):
                    continue
                
                # Apply noise gate
                audio_data = self.apply_noise_gate(audio_data)
                
                # Pre-process audio for better pitch detection
                processed_audio = self.preprocess_audio(audio_data)
                
                # Detect pitch with multiple methods for accuracy
                frequency = self.detect_voice_pitch(processed_audio)
                
                if frequency > 0 and self.min_voice_freq <= frequency <= self.max_voice_freq:
                    # Apply pitch smoothing
                    frequency = self.smooth_pitch(frequency)
                    
                    # Check pitch stability
                    if self.is_pitch_stable(frequency):
                        # Convert to musical note
                        note, octave, cents = AudioHelpers.note_from_frequency(frequency)
                        
                        # Calculate enhanced confidence
                        confidence = self.calculate_voice_confidence(audio_data, frequency)
                        
                        # Update display
                        self.update_pitch_display(frequency, note, octave, cents, confidence)
                        
                        # Add to history
                        self.add_to_history(frequency, note, octave, cents)
                        
                        # Update auto voice range detection
                        if self.auto_range_enabled:
                            self.update_voice_range_detection(frequency)
                    
            except queue.Empty:
                continue
            except Exception as e:
                ErrorHandler.log_error("Error processing audio", e)
                
    def is_voice_signal(self, audio_data):
        """Enhanced voice detection to filter out noise."""
        # Calculate RMS amplitude
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        # Check if amplitude is above voice threshold
        if rms < self.voice_threshold:
            return False
        
        # Calculate spectral centroid (brightness measure)
        fft = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), 1/self.audio_config.sample_rate)
        
        # Voice signals typically have spectral centroid in human voice range
        spectral_centroid = np.sum(freqs * fft) / np.sum(fft)
        
        # Check if spectral centroid is in voice range
        if not (100 <= spectral_centroid <= 3000):
            return False
        
        # Calculate spectral rolloff (90% of energy)
        cumsum_fft = np.cumsum(fft)
        rolloff_point = 0.9 * cumsum_fft[-1]
        rolloff_freq = freqs[np.where(cumsum_fft >= rolloff_point)[0][0]]
        
        # Voice signals have rolloff typically below 4000 Hz
        if rolloff_freq > 4000:
            return False
        
        # Calculate zero crossing rate
        zero_crossings = np.sum(np.diff(np.sign(audio_data)) != 0)
        zcr = zero_crossings / len(audio_data)
        
        # Voice signals have moderate zero crossing rate
        if not (0.01 <= zcr <= 0.3):
            return False
        
        return True
    
    def apply_noise_gate(self, audio_data):
        """Apply noise gate to reduce background noise."""
        # Calculate RMS in small windows
        window_size = 512
        gated_audio = audio_data.copy()
        
        for i in range(0, len(audio_data) - window_size, window_size // 2):
            window = audio_data[i:i + window_size]
            window_rms = np.sqrt(np.mean(window ** 2))
            
            # Apply gate
            if window_rms < self.noise_gate:
                gated_audio[i:i + window_size] *= 0.1  # Reduce but don't eliminate
        
        return gated_audio
    
    def preprocess_audio(self, audio_data):
        """Preprocess audio for better pitch detection."""
        # Apply window function
        windowed = AudioHelpers.apply_window(audio_data, "hanning")
        
        # High-pass filter to remove low-frequency noise
        # Simple high-pass: remove DC and very low frequencies
        fft = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(len(windowed), 1/self.audio_config.sample_rate)
        
        # Zero out frequencies below 60 Hz
        fft[freqs < 60] = 0
        
        # Convert back to time domain
        filtered = np.fft.irfft(fft, len(windowed))
        
        return filtered
    
    def detect_voice_pitch(self, audio_data):
        """Enhanced pitch detection optimized for voice."""
        # Try multiple methods and combine results
        methods = ["hps", "autocorr", "fft"]
        frequencies = []
        
        for method in methods:
            freq = AudioHelpers.calculate_frequency(
                audio_data,
                self.audio_config.sample_rate,
                method=method
            )
            if self.min_voice_freq <= freq <= self.max_voice_freq:
                frequencies.append(freq)
        
        if not frequencies:
            return 0.0
        
        # Use median frequency for robustness
        return np.median(frequencies)
    
    def smooth_pitch(self, frequency):
        """Apply pitch smoothing to reduce jitter."""
        if self.previous_frequency == 0:
            self.previous_frequency = frequency
            return frequency
        
        # Exponential smoothing
        smoothed = (self.smoothing_factor * self.previous_frequency + 
                   (1 - self.smoothing_factor) * frequency)
        
        self.previous_frequency = smoothed
        return smoothed
    
    def is_pitch_stable(self, frequency):
        """Check if pitch is stable enough to display."""
        if self.previous_frequency == 0:
            self.stable_pitch_count = 1
            return True
        
        # Calculate cents difference from previous reading
        cents_diff = 1200 * np.log2(frequency / self.previous_frequency)
        
        if abs(cents_diff) <= self.stability_threshold:
            self.stable_pitch_count += 1
        else:
            self.stable_pitch_count = 0
        
        return self.stable_pitch_count >= self.required_stability
    
    def calculate_voice_confidence(self, audio_data, frequency):
        """Calculate confidence score for voice detection."""
        # Base confidence on amplitude
        rms = np.sqrt(np.mean(audio_data ** 2))
        amplitude_confidence = min(rms / self.voice_threshold, 1.0) * 50
        
        # Add harmonic confidence
        harmonic_confidence = self.calculate_harmonic_confidence(audio_data, frequency)
        
        # Combine confidences
        total_confidence = min(amplitude_confidence + harmonic_confidence, 100)
        
        return total_confidence
    
    def calculate_harmonic_confidence(self, audio_data, fundamental_freq):
        """Calculate confidence based on harmonic structure."""
        fft = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), 1/self.audio_config.sample_rate)
        
        # Look for harmonics (2f, 3f, 4f)
        harmonic_strength = 0
        harmonics_found = 0
        
        for harmonic in [2, 3, 4]:
            target_freq = fundamental_freq * harmonic
            if target_freq > self.audio_config.sample_rate / 2:
                break
            
            # Find closest frequency bin
            freq_idx = np.argmin(np.abs(freqs - target_freq))
            
            # Check if there's significant energy at this harmonic
            if freq_idx < len(fft):
                harmonic_strength += fft[freq_idx]
                harmonics_found += 1
        
        if harmonics_found > 0:
            return min(harmonic_strength / harmonics_found * 10, 50)
        
        return 0
    
    def update_voice_range_detection(self, frequency):
        """Update automatic voice range detection based on sung frequencies."""
        current_time = time.time()
        
        # Update frequency bounds
        self.min_detected_freq = min(self.min_detected_freq, frequency)
        self.max_detected_freq = max(self.max_detected_freq, frequency)
        
        # Check if we have enough samples and enough time has passed
        if (len(self.pitch_history) >= self.range_analysis_samples and 
            current_time - self.last_range_update >= self.range_update_interval):
            
            self.analyze_and_update_voice_range()
            self.last_range_update = current_time
    
    def analyze_and_update_voice_range(self):
        """Analyze pitch history and update voice range automatically."""
        if len(self.pitch_history) < self.range_analysis_samples:
            return
        
        # Get recent pitch data for analysis
        recent_pitches = [entry['frequency'] for entry in self.pitch_history[-self.range_analysis_samples:]]
        
        if not recent_pitches:
            return
        
        # Calculate statistical measures
        min_freq = min(recent_pitches)
        max_freq = max(recent_pitches)
        freq_range = max_freq - min_freq
        
        # Add some padding to the detected range (10% on each side)
        padding = freq_range * 0.1
        adjusted_min = max(80.0, min_freq - padding)  # Don't go below human voice minimum
        adjusted_max = min(1200.0, max_freq + padding)  # Don't go above reasonable maximum
        
        # Determine the best matching voice type
        detected_range = self.classify_voice_type(adjusted_min, adjusted_max)
        
        # Update the range if it's different from current
        if detected_range != self.selected_voice_range:
            self.selected_voice_range = detected_range
            self.voice_range_var.set(detected_range)
            
            # Update audio config
            voice_range = self.voice_ranges[detected_range]
            self.audio_config.min_frequency = voice_range.min_freq
            self.audio_config.max_frequency = voice_range.max_freq
            
            # Update status
            self.status_var.set(f"Auto-detected voice range: {detected_range}")
            
            # Update visual display
            self.update_visual_tuner()
    
    def classify_voice_type(self, min_freq, max_freq):
        """Classify voice type based on frequency range."""
        # Define typical voice ranges with some overlap
        voice_classifications = {
            "Bass": (80, 350),      # F2 to F4
            "Tenor": (130, 520),    # C3 to C5  
            "Alto": (175, 700),     # F3 to F5
            "Soprano": (260, 1050), # C4 to C6
        }
        
        best_match = "Full Range"
        best_score = 0
        
        for voice_type, (type_min, type_max) in voice_classifications.items():
            # Calculate overlap between detected range and voice type range
            overlap_min = max(min_freq, type_min)
            overlap_max = min(max_freq, type_max)
            
            if overlap_max > overlap_min:
                overlap = overlap_max - overlap_min
                detected_range_size = max_freq - min_freq
                type_range_size = type_max - type_min
                
                # Score based on how well the ranges match
                # Higher score for better coverage of the detected range
                coverage_score = overlap / detected_range_size if detected_range_size > 0 else 0
                fit_score = overlap / type_range_size if type_range_size > 0 else 0
                
                # Combined score favoring good coverage
                total_score = (coverage_score * 0.7) + (fit_score * 0.3)
                
                if total_score > best_score:
                    best_score = total_score
                    best_match = voice_type
        
        # Only return a specific voice type if the match is strong enough
        if best_score > 0.6:  # 60% confidence threshold
            return best_match
        else:
            return "Full Range"
                
    def update_pitch_display(self, frequency, note, octave, cents, confidence):
        """Update the pitch display."""
        self.current_frequency = frequency
        self.current_note = note
        self.current_octave = octave
        self.current_cents = cents
        self.confidence = confidence
        
        # Update UI in main thread
        self.window.after(0, self._update_ui_display)
        
    def _update_ui_display(self):
        """Update UI display (called in main thread)."""
        # Update text displays
        self.note_var.set(f"{self.current_note}{self.current_octave}")
        self.freq_var.set(f"{self.current_frequency:.1f} Hz")
        self.cents_var.set(f"{self.current_cents:+.0f} ¢")
        self.conf_var.set(f"{self.confidence:.0f}%")
        
        # Color code cents display
        if abs(self.current_cents) <= self.audio_config.cents_tolerance:
            self.cents_label.configure(fg="#4CAF50")  # Green - in tune
        elif abs(self.current_cents) <= 25:
            self.cents_label.configure(fg="#FF9800")  # Orange - close
        else:
            self.cents_label.configure(fg="#f44336")  # Red - out of tune
            
        # Update visual tuner
        self.update_visual_tuner()
        
    def add_to_history(self, frequency, note, octave, cents):
        """Add pitch data to history."""
        self.pitch_history.append({
            'frequency': frequency,
            'note': note,
            'octave': octave,
            'cents': cents,
            'timestamp': time.time()
        })
        
        # Limit history size
        if len(self.pitch_history) > self.max_history_length:
            self.pitch_history.pop(0)
            
    def update_visual_tuner(self):
        """Update the visual tuner display."""
        self.tuner_canvas.delete("all")
        
        canvas_width = self.tuner_canvas.winfo_width()
        canvas_height = self.tuner_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
            
        # Draw tuner meter
        self.draw_tuner_meter(canvas_width, canvas_height)
        
        # Draw pitch history
        self.draw_pitch_history(canvas_width, canvas_height)
        
    def draw_tuner_meter(self, width, height):
        """Draw the enhanced tuner meter with better visuals."""
        history_height = height // 3
        meter_height = height - history_height - 60  # Space for pitch history
        meter_y = history_height + 40  # Start after pitch history
        
        # Draw gradient background
        self.draw_gradient_background(10, meter_y, width - 10, meter_y + meter_height)
        
        # Draw meter frame with rounded corners effect
        self.tuner_canvas.create_rectangle(
            10, meter_y, width - 10, meter_y + meter_height,
            fill="", outline="#00FF00", width=3
        )
        
        # Draw center line (perfect pitch) - more prominent
        center_x = width // 2
        self.tuner_canvas.create_line(
            center_x, meter_y - 5, center_x, meter_y + meter_height + 5,
            fill="#00FF00", width=6
        )
        
        # Draw tolerance zone (green zone)
        tolerance_pixels = (self.audio_config.cents_tolerance / 50) * (width - 20) // 2
        
        # Green zone rectangle (without alpha transparency)
        self.tuner_canvas.create_rectangle(
            center_x - tolerance_pixels, meter_y + 10,
            center_x + tolerance_pixels, meter_y + meter_height - 10,
            fill="#004400", outline="#00FF00", width=2
        )
        
        # Draw scale markings
        for i in range(-50, 51, 10):
            x_pos = center_x + (i / 50) * (width - 40) // 2
            if x_pos < 20 or x_pos > width - 20:
                continue
                
            # Major marks every 20 cents
            if i % 20 == 0:
                mark_height = 20
                mark_width = 3
                color = "#FFFFFF"
            else:
                mark_height = 10
                mark_width = 1
                color = "#CCCCCC"
            
            self.tuner_canvas.create_line(
                x_pos, meter_y + meter_height - mark_height,
                x_pos, meter_y + meter_height,
                fill=color, width=mark_width
            )
            
            # Add numbers for major marks
            if i % 20 == 0 and i != 0:
                self.tuner_canvas.create_text(
                    x_pos, meter_y + meter_height + 15,
                    text=f"{i:+d}",
                    font=("Arial", 10, "bold"),
                    fill="#FFFFFF"
                )
        
        # Draw current pitch indicator - enhanced
        if self.is_recording and self.current_frequency > 0:
            # Calculate position based on cents offset
            cents_ratio = max(-1, min(1, self.current_cents / 50))  # Clamp to ±50 cents
            indicator_x = center_x + (cents_ratio * (width - 40) // 2)
            
            # Choose color and size based on accuracy
            if abs(self.current_cents) <= self.audio_config.cents_tolerance:
                color = "#00FF00"  # Bright green
                size = 15
                glow_color = "#00FF0080"
            elif abs(self.current_cents) <= 25:
                color = "#FFAA00"  # Orange
                size = 12
                glow_color = "#FFAA0080"
            else:
                color = "#FF0000"  # Red
                size = 10
                glow_color = "#FF000080"
            
            # Draw glow effect (without alpha transparency)
            glow_colors = {
                "#00FF0080": "#004400",
                "#FFAA0080": "#442200", 
                "#FF000080": "#440000"
            }
            solid_glow_color = glow_colors.get(glow_color, "#333333")
            
            for i in range(3):
                self.tuner_canvas.create_oval(
                    indicator_x - size - i*3, meter_y + 15 - i*3,
                    indicator_x + size + i*3, meter_y + meter_height - 15 + i*3,
                    fill="", outline=solid_glow_color, width=1
                )
            
            # Draw main indicator
            self.tuner_canvas.create_oval(
                indicator_x - size, meter_y + 15,
                indicator_x + size, meter_y + meter_height - 15,
                fill=color, outline="#FFFFFF", width=3
            )
            
            # Draw needle pointing to current pitch
            needle_y = meter_y - 10
            self.tuner_canvas.create_polygon(
                indicator_x - 8, needle_y,
                indicator_x + 8, needle_y,
                indicator_x, meter_y,
                fill=color, outline="#FFFFFF", width=2
            )
            
        # Draw enhanced labels
        tuner_title = "VOICE PITCH TUNER"
        if self.is_recording:
            if self.current_frequency > 0:
                tuner_title += " - VOICE DETECTED"
                title_color = "#00FF00"
            else:
                tuner_title += " - LISTENING..."
                title_color = "#FFAA00"
        else:
            title_color = "#666666"
            
        self.tuner_canvas.create_text(
            center_x, meter_y - 30,
            text=tuner_title,
            font=("Arial", 16, "bold"),
            fill=title_color
        )
        
        # Draw flat and sharp indicators
        self.tuner_canvas.create_text(
            30, meter_y + meter_height // 2,
            text="♭ FLAT", font=("Arial", 14, "bold"),
            fill="#FF6666", anchor="w"
        )
        
        self.tuner_canvas.create_text(
            width - 30, meter_y + meter_height // 2,
            text="SHARP ♯", font=("Arial", 14, "bold"),
            fill="#FF6666", anchor="e"
        )
        
        # Draw cents display
        if self.is_recording and self.current_frequency > 0:
            cents_text = f"{self.current_cents:+.0f} cents"
            self.tuner_canvas.create_text(
                center_x, meter_y + meter_height + 40,
                text=cents_text,
                font=("Arial", 18, "bold"),
                fill="#FFFFFF"
            )
    
    def draw_gradient_background(self, x1, y1, x2, y2):
        """Draw a gradient background for the meter."""
        # Simple gradient effect using multiple rectangles
        steps = 20
        height_step = (y2 - y1) / steps
        
        for i in range(steps):
            # Color gradient from dark to lighter
            intensity = int(20 + (i / steps) * 30)
            color = f"#{intensity:02x}{intensity:02x}{intensity:02x}"
            
            rect_y1 = y1 + i * height_step
            rect_y2 = rect_y1 + height_step
            
            self.tuner_canvas.create_rectangle(
                x1, rect_y1, x2, rect_y2,
                fill=color, outline=""
            )
        
    def draw_pitch_history(self, width, height):
        """Draw pitch history graph."""
        history_height = height // 3  # Top third of canvas
        
        # Draw background for pitch history
        self.tuner_canvas.create_rectangle(
            10, 10, width - 10, 10 + history_height,
            fill="#222222", outline="#555555", width=2
        )
        
        # Draw title with auto-detection status
        title_text = "PITCH HISTORY"
        if self.auto_range_enabled and len(self.pitch_history) >= self.range_analysis_samples:
            title_text += f" - Auto: {self.selected_voice_range}"
        elif self.auto_range_enabled:
            samples_needed = self.range_analysis_samples - len(self.pitch_history)
            title_text += f" - Analyzing... ({samples_needed} more samples)"
        
        self.tuner_canvas.create_text(
            width // 2, 25,
            text=title_text,
            font=("Arial", 12, "bold"),
            fill="#FFFFFF" if not self.auto_range_enabled else "#00FFAA"
        )
        
        # Get voice range
        voice_range = self.voice_ranges[self.selected_voice_range]
        min_freq = voice_range.min_freq
        max_freq = voice_range.max_freq
        
        # Draw frequency reference lines and labels
        num_lines = 6
        for i in range(num_lines + 1):
            freq = min_freq + (max_freq - min_freq) * i / num_lines
            note, octave, _ = AudioHelpers.note_from_frequency(freq)
            
            y = 40 + (history_height - 60) * (1 - (freq - min_freq) / (max_freq - min_freq))
            
            # Draw reference line
            self.tuner_canvas.create_line(
                15, y, width - 80, y,
                fill="#444444", width=1, dash=(3, 3)
            )
            
            # Draw note label with background
            self.tuner_canvas.create_rectangle(
                width - 75, y - 8, width - 15, y + 8,
                fill="#333333", outline="#666666", width=1
            )
            self.tuner_canvas.create_text(
                width - 45, y,
                text=f"{note}{octave}",
                font=("Arial", 10, "bold"),
                fill="#FFFFFF"
            )
            
        # Draw pitch history if available
        if len(self.pitch_history) > 1:
            current_time = time.time()
            time_window = 15.0  # Show last 15 seconds
            
            # Filter valid entries
            valid_entries = []
            for entry in self.pitch_history:
                age = current_time - entry['timestamp']
                if age <= time_window and min_freq <= entry['frequency'] <= max_freq:
                    valid_entries.append((age, entry))
            
            if len(valid_entries) > 1:
                # Create line points
                points = []
                for age, entry in valid_entries:
                    x = width - 80 - (age / time_window) * (width - 100)
                    freq = entry['frequency']
                    y = 40 + (history_height - 60) * (1 - (freq - min_freq) / (max_freq - min_freq))
                    points.extend([x, y])
                
                # Draw the pitch line
                if len(points) >= 4:
                    # Background line for better visibility
                    self.tuner_canvas.create_line(
                        points,
                        fill="#000000",
                        width=5,
                        smooth=True
                    )
                    # Main pitch line
                    self.tuner_canvas.create_line(
                        points,
                        fill="#00FFFF",
                        width=3,
                        smooth=True
                    )
                    
                    # Draw current pitch indicator (most recent point)
                    if len(valid_entries) > 0:
                        latest_age, latest_entry = valid_entries[0]
                        latest_x = width - 80 - (latest_age / time_window) * (width - 100)
                        latest_freq = latest_entry['frequency']
                        latest_y = 40 + (history_height - 60) * (1 - (latest_freq - min_freq) / (max_freq - min_freq))
                        
                        # Pulsing current pitch indicator
                        self.tuner_canvas.create_oval(
                            latest_x - 6, latest_y - 6,
                            latest_x + 6, latest_y + 6,
                            fill="#FFFF00", outline="#FFFFFF", width=2
                        )
                        
                        # Show current note
                        current_note, current_octave, current_cents = AudioHelpers.note_from_frequency(latest_freq)
                        self.tuner_canvas.create_text(
                            latest_x, latest_y - 20,
                            text=f"{current_note}{current_octave}",
                            font=("Arial", 12, "bold"),
                            fill="#FFFF00"
                        )
        else:
            # Show message when no history
            self.tuner_canvas.create_text(
                width // 2, 10 + history_height // 2,
                text="Start singing to see pitch history",
                font=("Arial", 14),
                fill="#888888"
            )
                
    def on_canvas_resize(self, event=None):
        """Handle canvas resize."""
        self.window.after(100, self.update_visual_tuner)
        
    def on_closing(self):
        """Handle window closing."""
        self.stop_recording()
        self.window.destroy()


def show_voice_pitch_tuner(parent: tk.Widget):
    """Show the voice pitch tuner window."""
    try:
        tuner = VoicePitchTuner(parent)
        return tuner.window
    except Exception as e:
        ErrorHandler.handle_exception(e, "opening voice pitch tuner")
        return None
