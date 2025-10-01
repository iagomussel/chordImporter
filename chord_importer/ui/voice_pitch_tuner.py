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
        
        # Audio configuration
        self.audio_config = AudioConfig(
            sample_rate=44100,
            channels=1,
            chunk_size=2048,
            min_frequency=80.0,
            max_frequency=2000.0,
            threshold=0.01,
            reference_frequency=440.0,
            cents_tolerance=10.0
        )
        
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
        self.window.title("Voice Pitch Tuner")
        self.window.geometry("800x600")
        self.window.minsize(600, 400)
        
        # Center the window
        UIHelpers.center_window(self.window, 800, 600)
        
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
        
        # Voice range selection
        tk.Label(row2, text="Voice Range:", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 5))
        self.voice_range_var = tk.StringVar(value=self.selected_voice_range)
        voice_range_combo = ttk.Combobox(
            row2,
            textvariable=self.voice_range_var,
            values=list(self.voice_ranges.keys()),
            state="readonly",
            width=15
        )
        voice_range_combo.pack(side=tk.LEFT, padx=(0, 10))
        voice_range_combo.bind("<<ComboboxSelected>>", self.on_voice_range_changed)
        
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
            text="Visual Tuner",
            font=("Arial", 12, "bold"),
            bg="#f0f0f0",
            fg="#333333"
        )
        tuner_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Canvas for visual tuner
        self.tuner_canvas = tk.Canvas(
            tuner_frame,
            height=200,
            bg="white",
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.tuner_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        self.selected_voice_range = self.voice_range_var.get()
        voice_range = self.voice_ranges[self.selected_voice_range]
        self.audio_config.min_frequency = voice_range.min_freq
        self.audio_config.max_frequency = voice_range.max_freq
        self.update_visual_tuner()
        
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
        """Process audio data in separate thread."""
        while self.is_recording:
            try:
                # Get audio data from queue
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Check for silence
                if AudioHelpers.detect_silence(audio_data, self.audio_config.threshold):
                    continue
                
                # Detect pitch
                frequency = AudioHelpers.calculate_frequency(
                    audio_data,
                    self.audio_config.sample_rate,
                    method="hps"
                )
                
                if frequency > 0:
                    # Convert to musical note
                    note, octave, cents = AudioHelpers.note_from_frequency(frequency)
                    
                    # Calculate confidence (simple amplitude-based)
                    amplitude = np.sqrt(np.mean(audio_data ** 2))
                    confidence = min(amplitude * 100, 100)
                    
                    # Update display
                    self.update_pitch_display(frequency, note, octave, cents, confidence)
                    
                    # Add to history
                    self.add_to_history(frequency, note, octave, cents)
                    
            except queue.Empty:
                continue
            except Exception as e:
                ErrorHandler.log_error("Error processing audio", e)
                
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
        """Draw the tuner meter."""
        meter_height = height // 3
        meter_y = height - meter_height - 10
        
        # Draw meter background
        self.tuner_canvas.create_rectangle(
            10, meter_y, width - 10, meter_y + meter_height,
            fill="#f0f0f0", outline="#cccccc", width=2
        )
        
        # Draw center line (perfect pitch)
        center_x = width // 2
        self.tuner_canvas.create_line(
            center_x, meter_y, center_x, meter_y + meter_height,
            fill="#4CAF50", width=3
        )
        
        # Draw tolerance lines
        tolerance_pixels = (self.audio_config.cents_tolerance / 100) * (width - 20) // 2
        
        # Left tolerance
        left_tolerance_x = center_x - tolerance_pixels
        self.tuner_canvas.create_line(
            left_tolerance_x, meter_y, left_tolerance_x, meter_y + meter_height,
            fill="#FF9800", width=2, dash=(5, 5)
        )
        
        # Right tolerance
        right_tolerance_x = center_x + tolerance_pixels
        self.tuner_canvas.create_line(
            right_tolerance_x, meter_y, right_tolerance_x, meter_y + meter_height,
            fill="#FF9800", width=2, dash=(5, 5)
        )
        
        # Draw current pitch indicator
        if self.is_recording and self.current_frequency > 0:
            # Calculate position based on cents offset
            cents_ratio = self.current_cents / 100  # -1 to 1
            indicator_x = center_x + (cents_ratio * (width - 20) // 2)
            
            # Clamp to canvas bounds
            indicator_x = max(15, min(width - 15, indicator_x))
            
            # Choose color based on accuracy
            if abs(self.current_cents) <= self.audio_config.cents_tolerance:
                color = "#4CAF50"  # Green
            elif abs(self.current_cents) <= 25:
                color = "#FF9800"  # Orange
            else:
                color = "#f44336"  # Red
                
            # Draw indicator
            self.tuner_canvas.create_oval(
                indicator_x - 8, meter_y + 5,
                indicator_x + 8, meter_y + meter_height - 5,
                fill=color, outline="white", width=2
            )
            
        # Draw labels
        self.tuner_canvas.create_text(
            center_x, meter_y - 10,
            text="Perfect Pitch",
            font=("Arial", 10, "bold"),
            fill="#4CAF50"
        )
        
        self.tuner_canvas.create_text(
            10, meter_y + meter_height // 2,
            text="♭", font=("Arial", 16, "bold"),
            fill="#f44336", anchor="w"
        )
        
        self.tuner_canvas.create_text(
            width - 10, meter_y + meter_height // 2,
            text="♯", font=("Arial", 16, "bold"),
            fill="#f44336", anchor="e"
        )
        
    def draw_pitch_history(self, width, height):
        """Draw pitch history graph."""
        if len(self.pitch_history) < 2:
            return
            
        history_height = height - (height // 3) - 30
        
        # Get voice range
        voice_range = self.voice_ranges[self.selected_voice_range]
        min_freq = voice_range.min_freq
        max_freq = voice_range.max_freq
        
        # Draw frequency lines
        num_lines = 8
        for i in range(num_lines + 1):
            freq = min_freq + (max_freq - min_freq) * i / num_lines
            note, octave, _ = AudioHelpers.note_from_frequency(freq)
            
            y = 10 + history_height * (1 - (freq - min_freq) / (max_freq - min_freq))
            
            self.tuner_canvas.create_line(
                10, y, width - 10, y,
                fill="#e0e0e0", width=1
            )
            
            self.tuner_canvas.create_text(
                width - 5, y,
                text=f"{note}{octave}",
                font=("Arial", 8),
                fill="#666666",
                anchor="e"
            )
            
        # Draw pitch history
        if len(self.pitch_history) > 1:
            points = []
            current_time = time.time()
            time_window = 10.0  # Show last 10 seconds
            
            for i, entry in enumerate(self.pitch_history):
                age = current_time - entry['timestamp']
                if age > time_window:
                    continue
                    
                x = 10 + (width - 20) * (1 - age / time_window)
                freq = entry['frequency']
                
                if min_freq <= freq <= max_freq:
                    y = 10 + history_height * (1 - (freq - min_freq) / (max_freq - min_freq))
                    points.extend([x, y])
                    
            # Draw line
            if len(points) >= 4:
                self.tuner_canvas.create_line(
                    points,
                    fill=voice_range.color,
                    width=2,
                    smooth=True
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
