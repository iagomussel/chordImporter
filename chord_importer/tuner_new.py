"""
Modern Guitar Tuner using sounddevice and numpy for robust pitch detection.
This replaces the complex HPS implementation with a simpler, more reliable approach.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
import queue
from typing import Optional, Dict, List, Tuple

# Try to import required libraries
try:
    import numpy as np
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    # Create dummy modules
    class DummyNumpy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
        ndarray = type(None)
        float32 = float
        
    class DummySoundDevice:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    
    np = DummyNumpy()
    sd = DummySoundDevice()


class ModernGuitarTuner:
    """Modern guitar tuner with reliable pitch detection."""
    
    # Standard guitar tuning frequencies (Hz)
    GUITAR_NOTES = {
        'E2': 82.41,   # 6th string (lowest) - E
        'A2': 110.00,  # 5th string - A
        'D3': 146.83,  # 4th string - D
        'G3': 196.00,  # 3rd string - G
        'B3': 246.94,  # 2nd string - B
        'E4': 329.63,  # 1st string (highest) - E
    }
    
    # String names in order (low to high)
    STRING_NAMES = ['E2', 'A2', 'D3', 'G3', 'B3', 'E4']
    
    # All chromatic notes for detection
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    def __init__(self, parent: tk.Widget):
        """Initialize the modern guitar tuner."""
        self.parent = parent
        self.is_listening = False
        self.current_frequency = 0.0
        self.target_note = 'E2'
        self.auto_detect = True
        self.detected_note = None
        
        # Audio settings
        self.sample_rate = 44100
        self.block_size = 4096
        self.audio_queue = queue.Queue()
        self.audio_stream = None
        
        # Pitch detection settings
        self.min_frequency = 70.0   # Below lowest guitar note
        self.max_frequency = 400.0  # Above highest guitar note
        self.frequency_buffer = []
        self.buffer_size = 5  # Number of readings to average
        
        # Get available audio devices
        self.available_devices = self.get_audio_devices()
        
        self.setup_ui()
    
    def get_audio_devices(self) -> List[Dict]:
        """Get list of available audio input devices."""
        devices = []
        if not AUDIO_AVAILABLE:
            return [{'name': 'No audio devices available', 'index': 0}]
        
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device['max_input_channels'] > 0:  # Input device
                    devices.append({
                        'name': device['name'],
                        'index': i,
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate']
                    })
        except Exception as e:
            print(f"Error querying audio devices: {e}")
            devices = [{'name': 'Default', 'index': 0}]
        
        return devices if devices else [{'name': 'No devices found', 'index': 0}]
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = tk.Frame(self.parent, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="🎸 Modern Guitar Tuner", 
                              font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#2196F3")
        title_label.pack(pady=(0, 20))
        
        # Device selection
        device_frame = tk.LabelFrame(main_frame, text="Audio Device", 
                                   font=("Arial", 12, "bold"), bg="#f0f0f0")
        device_frame.pack(fill=tk.X, pady=(0, 15))
        
        device_inner = tk.Frame(device_frame, bg="#f0f0f0")
        device_inner.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(device_inner, text="Microphone:", font=("Arial", 10), 
                bg="#f0f0f0").pack(side=tk.LEFT)
        
        self.device_var = tk.StringVar()
        device_names = [dev['name'] for dev in self.available_devices]
        self.device_combo = ttk.Combobox(device_inner, textvariable=self.device_var,
                                       values=device_names, state="readonly", width=40)
        self.device_combo.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        if device_names:
            self.device_combo.set(device_names[0])
        
        # Tuning mode selection
        mode_frame = tk.LabelFrame(main_frame, text="Tuning Mode", 
                                 font=("Arial", 12, "bold"), bg="#f0f0f0")
        mode_frame.pack(fill=tk.X, pady=(0, 15))
        
        mode_inner = tk.Frame(mode_frame, bg="#f0f0f0")
        mode_inner.pack(fill=tk.X, padx=10, pady=10)
        
        self.auto_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(mode_inner, text="Auto-detect string", 
                                  variable=self.auto_var, command=self.on_mode_changed,
                                  font=("Arial", 10), bg="#f0f0f0")
        auto_check.pack(side=tk.LEFT)
        
        tk.Label(mode_inner, text="Target string:", font=("Arial", 10), 
                bg="#f0f0f0").pack(side=tk.LEFT, padx=(20, 5))
        
        self.string_var = tk.StringVar(value='E2')
        self.string_combo = ttk.Combobox(mode_inner, textvariable=self.string_var,
                                       values=self.STRING_NAMES, state="disabled", width=10)
        self.string_combo.pack(side=tk.LEFT)
        self.string_combo.bind("<<ComboboxSelected>>", self.on_string_changed)
        
        # Control buttons
        control_frame = tk.Frame(main_frame, bg="#f0f0f0")
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.start_btn = tk.Button(control_frame, text="🎤 Start Tuning", 
                                 command=self.start_listening,
                                 bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                                 relief=tk.FLAT, padx=20, pady=10, cursor="hand2")
        self.start_btn.pack(side=tk.LEFT)
        
        self.stop_btn = tk.Button(control_frame, text="⏹ Stop", 
                                command=self.stop_listening,
                                bg="#f44336", fg="white", font=("Arial", 12, "bold"),
                                relief=tk.FLAT, padx=20, pady=10, cursor="hand2",
                                state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status display
        status_frame = tk.LabelFrame(main_frame, text="Status", 
                                   font=("Arial", 12, "bold"), bg="#f0f0f0")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_inner = tk.Frame(status_frame, bg="#f0f0f0")
        status_inner.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = tk.Label(status_inner, text="Ready to tune", 
                                   font=("Arial", 11), bg="#f0f0f0", fg="#666")
        self.status_label.pack()
        
        # Frequency display
        freq_frame = tk.LabelFrame(main_frame, text="Detection", 
                                 font=("Arial", 12, "bold"), bg="#f0f0f0")
        freq_frame.pack(fill=tk.X, pady=(0, 15))
        
        freq_inner = tk.Frame(freq_frame, bg="#f0f0f0")
        freq_inner.pack(fill=tk.X, padx=10, pady=15)
        
        # Current frequency
        self.freq_label = tk.Label(freq_inner, text="Frequency: -- Hz", 
                                 font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#333")
        self.freq_label.pack()
        
        # Detected note
        self.note_label = tk.Label(freq_inner, text="Note: --", 
                                 font=("Arial", 16, "bold"), bg="#f0f0f0", fg="#2196F3")
        self.note_label.pack(pady=(5, 0))
        
        # Cents deviation
        self.cents_label = tk.Label(freq_inner, text="Deviation: -- cents", 
                                  font=("Arial", 12), bg="#f0f0f0", fg="#666")
        self.cents_label.pack(pady=(5, 0))
        
        # Tuning meter
        meter_frame = tk.LabelFrame(main_frame, text="Tuning Meter", 
                                  font=("Arial", 12, "bold"), bg="#f0f0f0")
        meter_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.canvas = tk.Canvas(meter_frame, width=400, height=80, bg="white", 
                              highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        
        self.draw_tuning_meter(0)  # Initialize meter
        
        # Tuning status
        self.tuning_status = tk.Label(main_frame, text="🎵 Ready", 
                                    font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#666")
        self.tuning_status.pack(pady=(0, 10))
    
    def draw_tuning_meter(self, cents_deviation: float):
        """Draw the tuning meter with needle position."""
        self.canvas.delete("all")
        
        width = 400
        height = 80
        center_x = width // 2
        center_y = height // 2
        
        # Draw scale
        scale_width = 300
        scale_height = 20
        scale_x = (width - scale_width) // 2
        scale_y = center_y - scale_height // 2
        
        # Background
        self.canvas.create_rectangle(scale_x, scale_y, scale_x + scale_width, 
                                   scale_y + scale_height, fill="#e0e0e0", outline="#ccc")
        
        # Center line (perfect tune)
        self.canvas.create_line(center_x, scale_y - 5, center_x, scale_y + scale_height + 5, 
                              fill="#4CAF50", width=2)
        
        # Scale marks
        for i in range(-50, 51, 10):
            x = center_x + (i * scale_width // 100)
            if i == 0:
                continue  # Skip center (already drawn)
            self.canvas.create_line(x, scale_y - 3, x, scale_y + scale_height + 3, 
                                  fill="#999", width=1)
            if i % 20 == 0:
                self.canvas.create_text(x, scale_y + scale_height + 15, text=str(i), 
                                      font=("Arial", 8), fill="#666")
        
        # Needle
        if cents_deviation != 0:
            # Clamp deviation to scale
            clamped_cents = max(-50, min(50, cents_deviation))
            needle_x = center_x + (clamped_cents * scale_width // 100)
            
            # Needle color based on accuracy
            if abs(clamped_cents) <= 5:
                needle_color = "#4CAF50"  # Green - in tune
            elif abs(clamped_cents) <= 15:
                needle_color = "#FF9800"  # Orange - close
            else:
                needle_color = "#f44336"  # Red - out of tune
            
            # Draw needle
            self.canvas.create_line(needle_x, scale_y - 10, needle_x, scale_y + scale_height + 10,
                                  fill=needle_color, width=3)
            self.canvas.create_oval(needle_x - 4, center_y - 4, needle_x + 4, center_y + 4,
                                  fill=needle_color, outline=needle_color)
        
        # Labels
        self.canvas.create_text(scale_x - 10, center_y, text="♭", font=("Arial", 16), 
                              fill="#f44336", anchor="e")
        self.canvas.create_text(scale_x + scale_width + 10, center_y, text="♯", 
                              font=("Arial", 16), fill="#f44336", anchor="w")
    
    def frequency_to_note_and_cents(self, frequency: float) -> Tuple[str, float]:
        """Convert frequency to note name and cents deviation."""
        if frequency <= 0:
            return "Unknown", 0
        
        # Calculate the note number (A4 = 440Hz is note 69)
        A4 = 440.0
        note_number = 12 * math.log2(frequency / A4) + 69
        
        # Get the closest note
        closest_note_number = round(note_number)
        note_index = closest_note_number % 12
        octave = closest_note_number // 12 - 1
        
        note_name = self.NOTE_NAMES[note_index]
        full_note_name = f"{note_name}{octave}"
        
        # Calculate cents deviation
        cents = (note_number - closest_note_number) * 100
        
        return full_note_name, cents
    
    def find_closest_guitar_string(self, frequency: float) -> Tuple[str, float]:
        """Find the closest guitar string to the detected frequency."""
        if frequency <= 0:
            return "Unknown", 0
        
        closest_string = None
        min_cents_diff = float('inf')
        
        for string_name, string_freq in self.GUITAR_NOTES.items():
            # Calculate cents difference
            cents_diff = 1200 * math.log2(frequency / string_freq)
            
            if abs(cents_diff) < abs(min_cents_diff):
                min_cents_diff = cents_diff
                closest_string = string_name
        
        return closest_string, min_cents_diff
    
    def detect_pitch(self, audio_data: np.ndarray) -> float:
        """Detect pitch using autocorrelation method."""
        if not AUDIO_AVAILABLE or len(audio_data) == 0:
            return 0.0
        
        # Apply window to reduce spectral leakage
        windowed = audio_data * np.hanning(len(audio_data))
        
        # Autocorrelation
        autocorr = np.correlate(windowed, windowed, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find the first peak after the zero lag
        min_period = int(self.sample_rate / self.max_frequency)
        max_period = int(self.sample_rate / self.min_frequency)
        
        if max_period >= len(autocorr):
            return 0.0
        
        # Find peak in the valid range
        search_range = autocorr[min_period:max_period]
        if len(search_range) == 0:
            return 0.0
        
        peak_index = np.argmax(search_range) + min_period
        
        # Check if peak is significant
        if autocorr[peak_index] < 0.3 * autocorr[0]:
            return 0.0
        
        # Convert to frequency
        frequency = self.sample_rate / peak_index
        
        return frequency if self.min_frequency <= frequency <= self.max_frequency else 0.0
    
    def audio_callback(self, indata, frames, time, status):
        """Audio callback for real-time processing."""
        if status:
            print(f"Audio callback status: {status}")
        
        # Put audio data in queue for processing
        self.audio_queue.put(indata.copy())
    
    def process_audio(self):
        """Process audio data in separate thread."""
        while self.is_listening:
            try:
                # Get audio data from queue (with timeout)
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Convert to mono if stereo
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                # Detect pitch
                frequency = self.detect_pitch(audio_data)
                
                if frequency > 0:
                    # Add to buffer for stability
                    self.frequency_buffer.append(frequency)
                    if len(self.frequency_buffer) > self.buffer_size:
                        self.frequency_buffer.pop(0)
                    
                    # Use median for stability
                    if len(self.frequency_buffer) >= 3:
                        stable_freq = np.median(self.frequency_buffer)
                        self.current_frequency = stable_freq
                        
                        # Update UI in main thread
                        self.parent.after(0, self.update_ui)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio processing error: {e}")
                continue
    
    def update_ui(self):
        """Update UI with current frequency detection."""
        if not self.is_listening or self.current_frequency <= 0:
            return
        
        frequency = self.current_frequency
        
        # Update frequency display
        self.freq_label.config(text=f"Frequency: {frequency:.1f} Hz")
        
        if self.auto_detect:
            # Auto-detect closest guitar string
            closest_string, cents_deviation = self.find_closest_guitar_string(frequency)
            self.note_label.config(text=f"String: {closest_string}")
            self.detected_note = closest_string
        else:
            # Manual mode - compare to selected string
            target_freq = self.GUITAR_NOTES[self.target_note]
            cents_deviation = 1200 * math.log2(frequency / target_freq)
            self.note_label.config(text=f"Target: {self.target_note}")
        
        # Update cents display
        self.cents_label.config(text=f"Deviation: {cents_deviation:+.1f} cents")
        
        # Update tuning meter
        self.draw_tuning_meter(cents_deviation)
        
        # Update tuning status
        if abs(cents_deviation) <= 5:
            self.tuning_status.config(text="🎯 IN TUNE!", fg="#4CAF50")
        elif abs(cents_deviation) <= 15:
            self.tuning_status.config(text="🎵 Close", fg="#FF9800")
        elif cents_deviation > 0:
            self.tuning_status.config(text="🔺 Too High", fg="#f44336")
        else:
            self.tuning_status.config(text="🔻 Too Low", fg="#f44336")
    
    def on_mode_changed(self):
        """Handle tuning mode change."""
        self.auto_detect = self.auto_var.get()
        if self.auto_detect:
            self.string_combo.config(state="disabled")
        else:
            self.string_combo.config(state="readonly")
            self.on_string_changed()
    
    def on_string_changed(self, event=None):
        """Handle string selection change."""
        if not self.auto_detect:
            self.target_note = self.string_var.get()
    
    def start_listening(self):
        """Start audio input and pitch detection."""
        if not AUDIO_AVAILABLE:
            messagebox.showerror("Error", 
                               "Audio libraries not available!\n\n"
                               "Please install: pip install sounddevice numpy")
            return
        
        if self.is_listening:
            return
        
        try:
            # Get selected device
            device_name = self.device_var.get()
            device_index = 0
            
            for device in self.available_devices:
                if device['name'] == device_name:
                    device_index = device['index']
                    break
            
            # Start audio stream
            self.audio_stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                callback=self.audio_callback,
                dtype=np.float32
            )
            
            self.audio_stream.start()
            self.is_listening = True
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self.process_audio, daemon=True)
            self.processing_thread.start()
            
            # Update UI
            self.status_label.config(text="Listening... Play a string!", fg="#4CAF50")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start audio:\n{str(e)}")
            self.status_label.config(text=f"Error: {str(e)}", fg="#f44336")
    
    def stop_listening(self):
        """Stop audio input and pitch detection."""
        if not self.is_listening:
            return
        
        try:
            self.is_listening = False
            
            if self.audio_stream:
                self.audio_stream.stop()
                self.audio_stream.close()
                self.audio_stream = None
            
            # Clear buffers
            self.frequency_buffer.clear()
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Update UI
            self.status_label.config(text="Stopped", fg="#666")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            # Clear displays
            self.freq_label.config(text="Frequency: -- Hz")
            self.note_label.config(text="Note: --")
            self.cents_label.config(text="Deviation: -- cents")
            self.tuning_status.config(text="🎵 Ready", fg="#666")
            
            # Clear meter
            self.draw_tuning_meter(0)
            
        except Exception as e:
            self.status_label.config(text=f"Error stopping: {str(e)}", fg="#f44336")


class TunerWindow:
    """Standalone tuner window."""
    
    def __init__(self, parent: Optional[tk.Widget] = None):
        if parent:
            self.window = tk.Toplevel(parent)
            self.window.transient(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("🎸 Modern Guitar Tuner")
        self.window.geometry("500x700")
        self.window.resizable(False, False)
        self.window.configure(bg="#f0f0f0")
        
        # Create tuner
        self.tuner = ModernGuitarTuner(self.window)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """Handle window close event."""
        if hasattr(self.tuner, 'stop_listening'):
            self.tuner.stop_listening()
        self.window.destroy()
    
    def show(self):
        """Show the tuner window."""
        self.window.lift()
        self.window.focus_force()


def show_tuner_window(parent=None):
    """Show the tuner window."""
    return TunerWindow(parent)


if __name__ == "__main__":
    # Test the tuner
    root = tk.Tk()
    root.withdraw()  # Hide root window
    tuner_window = TunerWindow()
    root.mainloop()
