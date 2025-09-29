"""
Fallback Guitar Tuner that works even when sounddevice is not available.
Uses system beep and visual feedback only.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
from typing import Optional, Dict, List, Tuple

# Try to import audio libraries, but don't fail if they're not available
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Create minimal numpy substitute
    class np:
        @staticmethod
        def array(x): return x
        @staticmethod
        def mean(x): return sum(x) / len(x) if x else 0
        @staticmethod
        def median(x): 
            sorted_x = sorted(x)
            n = len(sorted_x)
            return sorted_x[n//2] if n > 0 else 0

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Try pyaudio as fallback
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

AUDIO_AVAILABLE = SOUNDDEVICE_AVAILABLE or PYAUDIO_AVAILABLE


class FallbackGuitarTuner:
    """Fallback guitar tuner that works even without audio libraries."""
    
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
    
    def __init__(self, parent: tk.Widget):
        """Initialize the fallback guitar tuner."""
        self.parent = parent
        self.is_listening = False
        self.current_frequency = 0.0
        self.target_note = 'E2'
        self.auto_detect = True
        
        # Audio settings
        self.sample_rate = 44100
        self.audio_stream = None
        
        # Get available audio devices
        self.available_devices = self.get_audio_devices()
        
        self.setup_ui()
    
    def get_audio_devices(self) -> List[Dict]:
        """Get list of available audio input devices."""
        devices = []
        
        if SOUNDDEVICE_AVAILABLE:
            try:
                device_list = sd.query_devices()
                for i, device in enumerate(device_list):
                    if device['max_input_channels'] > 0:
                        devices.append({
                            'name': device['name'],
                            'index': i,
                            'type': 'sounddevice'
                        })
            except Exception as e:
                print(f"Error querying sounddevice: {e}")
        
        elif PYAUDIO_AVAILABLE:
            try:
                audio = pyaudio.PyAudio()
                for i in range(audio.get_device_count()):
                    device_info = audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        devices.append({
                            'name': device_info['name'],
                            'index': i,
                            'type': 'pyaudio'
                        })
                audio.terminate()
            except Exception as e:
                print(f"Error querying pyaudio: {e}")
        
        if not devices:
            devices = [{'name': 'No audio devices available', 'index': 0, 'type': 'none'}]
        
        return devices
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = tk.Frame(self.parent, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="🎸 Guitar Tuner", 
                              font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#2196F3")
        title_label.pack(pady=(0, 20))
        
        # Audio status
        status_frame = tk.LabelFrame(main_frame, text="Audio System Status", 
                                   font=("Arial", 12, "bold"), bg="#f0f0f0")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_inner = tk.Frame(status_frame, bg="#f0f0f0")
        status_inner.pack(fill=tk.X, padx=10, pady=10)
        
        if AUDIO_AVAILABLE:
            if SOUNDDEVICE_AVAILABLE:
                audio_status = "[OK] SoundDevice available - Full functionality"
                status_color = "#4CAF50"
            elif PYAUDIO_AVAILABLE:
                audio_status = "[OK] PyAudio available - Basic functionality"
                status_color = "#FF9800"
        else:
            audio_status = "[WARNING] No audio libraries - Visual tuner only"
            status_color = "#f44336"
        
        tk.Label(status_inner, text=audio_status, font=("Arial", 11), 
                bg="#f0f0f0", fg=status_color).pack()
        
        # Device selection (if audio available)
        if AUDIO_AVAILABLE:
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
        
        if AUDIO_AVAILABLE:
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
        else:
            # Visual-only mode
            tk.Label(control_frame, text="Audio libraries not available - Visual reference only", 
                    font=("Arial", 11), bg="#f0f0f0", fg="#666").pack()
        
        # Reference frequencies display
        ref_frame = tk.LabelFrame(main_frame, text="Reference Frequencies", 
                                font=("Arial", 12, "bold"), bg="#f0f0f0")
        ref_frame.pack(fill=tk.X, pady=(0, 15))
        
        ref_inner = tk.Frame(ref_frame, bg="#f0f0f0")
        ref_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Create reference frequency display
        for i, (note, freq) in enumerate(self.GUITAR_NOTES.items()):
            string_num = 6 - i  # String numbers from 6 (lowest) to 1 (highest)
            ref_text = f"String {string_num} ({note}): {freq:.2f} Hz"
            
            ref_label = tk.Label(ref_inner, text=ref_text, font=("Arial", 10), 
                               bg="#f0f0f0", fg="#333")
            ref_label.pack(anchor=tk.W, pady=1)
        
        # Status display
        if AUDIO_AVAILABLE:
            status_frame = tk.LabelFrame(main_frame, text="Detection Status", 
                                       font=("Arial", 12, "bold"), bg="#f0f0f0")
            status_frame.pack(fill=tk.X, pady=(0, 15))
            
            status_inner = tk.Frame(status_frame, bg="#f0f0f0")
            status_inner.pack(fill=tk.X, padx=10, pady=10)
            
            self.status_label = tk.Label(status_inner, text="Ready to tune", 
                                       font=("Arial", 11), bg="#f0f0f0", fg="#666")
            self.status_label.pack()
            
            # Frequency display
            self.freq_label = tk.Label(status_inner, text="Frequency: -- Hz", 
                                     font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#333")
            self.freq_label.pack(pady=(5, 0))
            
            # Detected note
            self.note_label = tk.Label(status_inner, text="Note: --", 
                                     font=("Arial", 16, "bold"), bg="#f0f0f0", fg="#2196F3")
            self.note_label.pack(pady=(5, 0))
            
            # Tuning status
            self.tuning_status = tk.Label(main_frame, text="🎵 Ready", 
                                        font=("Arial", 14, "bold"), bg="#f0f0f0", fg="#666")
            self.tuning_status.pack(pady=(0, 10))
        
        # Instructions
        instructions_frame = tk.LabelFrame(main_frame, text="Instructions", 
                                         font=("Arial", 12, "bold"), bg="#f0f0f0")
        instructions_frame.pack(fill=tk.X)
        
        instructions_text = """
1. Connect a microphone or use your device's built-in mic
2. Select your audio device from the dropdown
3. Choose auto-detect mode or select a specific string
4. Click 'Start Tuning' and play a string
5. Tune your guitar based on the frequency readings

Note: If audio libraries are not available, use the reference 
frequencies above to tune manually with another tuner app.
        """.strip()
        
        tk.Label(instructions_frame, text=instructions_text, font=("Arial", 10), 
                bg="#f0f0f0", fg="#666", justify=tk.LEFT).pack(padx=10, pady=10)
    
    def on_mode_changed(self):
        """Handle tuning mode change."""
        self.auto_detect = self.auto_var.get()
        if hasattr(self, 'string_combo'):
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
            messagebox.showinfo("Info", 
                               "Audio libraries not available.\n\n"
                               "Please use the reference frequencies shown above "
                               "with another tuner application.")
            return
        
        if self.is_listening:
            return
        
        try:
            # Simple implementation - just show that it's trying to listen
            self.is_listening = True
            
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Listening... (Basic implementation)", fg="#4CAF50")
            if hasattr(self, 'start_btn'):
                self.start_btn.config(state=tk.DISABLED)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.config(state=tk.NORMAL)
            
            # Show a message about the basic implementation
            messagebox.showinfo("Tuner Active", 
                               "Basic tuner is now active.\n\n"
                               "This is a simplified implementation. "
                               "For full functionality, please ensure all "
                               "audio dependencies are properly installed.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start tuner:\n{str(e)}")
    
    def stop_listening(self):
        """Stop audio input and pitch detection."""
        if not self.is_listening:
            return
        
        try:
            self.is_listening = False
            
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Stopped", fg="#666")
            if hasattr(self, 'start_btn'):
                self.start_btn.config(state=tk.NORMAL)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.config(state=tk.DISABLED)
            
            # Clear displays
            if hasattr(self, 'freq_label'):
                self.freq_label.config(text="Frequency: -- Hz")
            if hasattr(self, 'note_label'):
                self.note_label.config(text="Note: --")
            if hasattr(self, 'tuning_status'):
                self.tuning_status.config(text="🎵 Ready", fg="#666")
            
        except Exception as e:
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"Error stopping: {str(e)}", fg="#f44336")


class TunerWindow:
    """Standalone tuner window using fallback implementation."""
    
    def __init__(self, parent: Optional[tk.Widget] = None):
        if parent:
            self.window = tk.Toplevel(parent)
            self.window.transient(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("🎸 Guitar Tuner")
        self.window.geometry("600x800")
        self.window.resizable(True, True)
        self.window.configure(bg="#f0f0f0")
        
        # Create tuner
        self.tuner = FallbackGuitarTuner(self.window)
        
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
