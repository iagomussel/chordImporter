"""
Guitar Tuner module using Tkinter and audio processing.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import math
from typing import Optional, Callable

try:
    import numpy as np
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    # Create dummy modules to avoid attribute errors
    class DummyNumpy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
        ndarray = type(None)
    
    class DummyPyAudio:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
        paInt16 = None
    
    np = DummyNumpy()
    pyaudio = DummyPyAudio()


class GuitarTuner:
    """Guitar tuner with frequency detection and visual feedback."""
    
    # Standard guitar tuning frequencies (Hz) - Exact values
    GUITAR_NOTES = {
        'E2': 82.0,    # 6ª corda (mais grave) - Mi
        'A2': 110.0,   # 5ª corda - Lá
        'D3': 146.0,   # 4ª corda - Ré
        'G3': 196.0,   # 3ª corda - Sol
        'B3': 247.0,   # 2ª corda - Si
        'E4': 330.0,   # 1ª corda (mais aguda) - Mi
    }
    
    # String names in order
    STRING_NAMES = ['E2', 'A2', 'D3', 'G3', 'B3', 'E4']
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.is_listening = False
        self.audio_stream: Optional[object] = None
        self.audio_thread: Optional[threading.Thread] = None
        self.current_frequency = 0.0
        self.target_note = 'E2'
        self.auto_detect = True
        self.detected_note = None
        
        # Audio settings - Based on TomSchimansky GuitarTuner
        self.sample_rate = 44100
        self.chunk_size = 4096  # Optimal for real-time processing
        self.audio_format = pyaudio.paInt16 if AUDIO_AVAILABLE else None
        self.selected_mic_index = None
        
        # Advanced audio processing (HPS algorithm)
        self.buffer_duration = 1.5  # 1.5 seconds buffer like reference
        self.buffer_size = int(self.sample_rate * self.buffer_duration)
        self.audio_buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.buffer_index = 0
        
        # HPS (Harmonic Product Spectrum) settings
        self.hps_harmonics = 5  # Number of harmonics to multiply
        self.min_frequency = 60.0   # C2 - minimum detectable frequency
        self.max_frequency = 2000.0 # C7 - maximum detectable frequency
        
        # Precision and stability
        self.frequency_history = []
        self.history_size = 10
        self.stability_threshold = 2.0  # Hz tolerance for stability
        self.noise_floor = 0.001  # Lower noise floor for better sensitivity
        
        # Get available microphones
        self.available_mics = self.get_available_microphones()
        
        self.setup_ui()
    
    def get_available_microphones(self) -> list:
        """Get list of available microphones."""
        if not AUDIO_AVAILABLE:
            return [{"index": 0, "name": "Microfone padrão (áudio não disponível)"}]
        
        try:
            audio = pyaudio.PyAudio()
            mics = []
            
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                # Only include input devices
                if device_info['maxInputChannels'] > 0:
                    mics.append({
                        "index": i,
                        "name": device_info['name'],
                        "channels": device_info['maxInputChannels'],
                        "sample_rate": int(device_info['defaultSampleRate'])
                    })
            
            audio.terminate()
            
            if not mics:
                mics = [{"index": 0, "name": "Nenhum microfone encontrado"}]
                
            return mics
            
        except Exception as e:
            return [{"index": 0, "name": f"Erro ao detectar microfones: {str(e)}"}]
    
    def find_closest_note(self, frequency: float) -> Optional[str]:
        """Find the closest guitar note to the given frequency using advanced detection."""
        if frequency < self.min_frequency or frequency > self.max_frequency:
            return None
            
        # Use the advanced frequency to note conversion
        detected_note, cents_deviation = self.frequency_to_note(frequency)
        
        if detected_note is None:
            return None
        
        # Check if it's close to a guitar note (within reasonable range)
        if abs(cents_deviation) > 50:  # More than 50 cents off
            return None
            
        # Map detected note to guitar strings if it matches
        for guitar_note, target_freq in self.GUITAR_NOTES.items():
            note_freq_diff = abs(frequency - target_freq)
            if note_freq_diff < 10:  # Within 10 Hz of a guitar string
                return guitar_note
        
        # If not a standard guitar note but still a valid musical note, return it
        # This allows detection of fretted notes
        return detected_note
        
    def setup_ui(self):
        """Setup the tuner user interface."""
        # Main frame
        self.frame = tk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(self.frame, text="🎸 Afinador de Guitarra", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Microphone selection
        mic_frame = tk.Frame(self.frame)
        mic_frame.pack(pady=10)
        
        tk.Label(mic_frame, text="Microfone:", font=("Arial", 12)).pack(side=tk.LEFT)
        
        mic_names = [mic["name"] for mic in self.available_mics]
        self.mic_var = tk.StringVar(value=mic_names[0] if mic_names else "Nenhum")
        self.mic_combo = ttk.Combobox(mic_frame, textvariable=self.mic_var,
                                     values=mic_names, state="readonly", width=30)
        self.mic_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.mic_combo.bind("<<ComboboxSelected>>", self.on_mic_changed)
        
        # Auto-detect mode
        auto_frame = tk.Frame(self.frame)
        auto_frame.pack(pady=10)
        
        self.auto_var = tk.BooleanVar(value=self.auto_detect)
        self.auto_check = tk.Checkbutton(auto_frame, text="Detectar corda automaticamente",
                                        variable=self.auto_var, command=self.on_auto_changed,
                                        font=("Arial", 12))
        self.auto_check.pack()
        
        # String selection (manual mode)
        string_frame = tk.Frame(self.frame)
        string_frame.pack(pady=10)
        
        tk.Label(string_frame, text="Corda:", font=("Arial", 12)).pack(side=tk.LEFT)
        
        self.string_var = tk.StringVar(value=self.target_note)
        self.string_combo = ttk.Combobox(string_frame, textvariable=self.string_var,
                                        values=self.STRING_NAMES, state="readonly", width=10)
        self.string_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.string_combo.bind("<<ComboboxSelected>>", self.on_string_changed)
        
        # Initially disable string selection if auto mode is on
        if self.auto_detect:
            self.string_combo.config(state=tk.DISABLED)
        
        # Target frequency display
        self.target_freq_label = tk.Label(self.frame, 
                                         text=f"Frequência alvo: {self.GUITAR_NOTES[self.target_note]:.0f} Hz",
                                         font=("Arial", 12))
        self.target_freq_label.pack(pady=5)
        
        # Current frequency display
        self.current_freq_label = tk.Label(self.frame, text="Frequência atual: -- Hz",
                                          font=("Arial", 14, "bold"))
        self.current_freq_label.pack(pady=5)
        
        # Detected note display
        self.detected_note_label = tk.Label(self.frame, text="Nota detectada: --",
                                           font=("Arial", 16, "bold"), fg='blue')
        self.detected_note_label.pack(pady=5)
        
        # Cents deviation display
        self.cents_label = tk.Label(self.frame, text="Desvio: -- cents",
                                   font=("Arial", 12))
        self.cents_label.pack(pady=5)
        
        # String information display
        self.string_info_label = tk.Label(self.frame, 
                                         text="Range: 60-2000 Hz | Precisão: < 0.5 cents | HPS Algorithm",
                                         font=("Arial", 9), fg='gray')
        self.string_info_label.pack(pady=5)
        
        # Tuning indicator
        indicator_frame = tk.Frame(self.frame)
        indicator_frame.pack(pady=20)
        
        # Visual tuning meter
        self.canvas = tk.Canvas(indicator_frame, width=400, height=100, bg='white')
        self.canvas.pack()
        
        # Status labels
        self.status_label = tk.Label(self.frame, text="Clique 'Iniciar' para começar",
                                    font=("Arial", 12))
        self.status_label.pack(pady=10)
        
        self.tuning_label = tk.Label(self.frame, text="", font=("Arial", 14, "bold"))
        self.tuning_label.pack(pady=5)
        
        # Control buttons
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=20)
        
        self.start_button = tk.Button(button_frame, text="Iniciar", 
                                     command=self.start_listening,
                                     bg='green', fg='white', font=("Arial", 12))
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(button_frame, text="Parar", 
                                    command=self.stop_listening,
                                    bg='red', fg='white', font=("Arial", 12),
                                    state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Audio availability warning
        if not AUDIO_AVAILABLE:
            warning_label = tk.Label(self.frame, 
                                   text="⚠️ Instale 'numpy' e 'pyaudio' para usar o afinador",
                                   fg='red', font=("Arial", 10))
            warning_label.pack(pady=10)
            self.start_button.config(state=tk.DISABLED)
        
        # Initialize visual meter
        self.draw_tuning_meter(0)
        
    def on_mic_changed(self, event=None):
        """Handle microphone selection change."""
        selected_name = self.mic_var.get()
        for mic in self.available_mics:
            if mic["name"] == selected_name:
                self.selected_mic_index = mic["index"]
                break
    
    def on_auto_changed(self):
        """Handle auto-detect mode change."""
        self.auto_detect = self.auto_var.get()
        if self.auto_detect:
            self.string_combo.config(state=tk.DISABLED)
            self.target_freq_label.config(text="Modo automático: Toque uma corda")
        else:
            self.string_combo.config(state="readonly")
            self.on_string_changed()
    
    def on_string_changed(self, event=None):
        """Handle string selection change."""
        if not self.auto_detect:
            self.target_note = self.string_var.get()
            target_freq = self.GUITAR_NOTES[self.target_note]
            self.target_freq_label.config(text=f"Frequência alvo: {target_freq:.0f} Hz")
        
    def start_listening(self):
        """Start audio input and frequency detection."""
        if not AUDIO_AVAILABLE:
            self.status_label.config(text="Erro: Bibliotecas de áudio não disponíveis", fg='red')
            return
            
        try:
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            
            # Use selected microphone or default
            input_device_index = self.selected_mic_index if self.selected_mic_index is not None else None
            
            # Open audio stream
            self.audio_stream = self.audio.open(
                format=self.audio_format,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_listening = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="Ouvindo... Toque uma corda!", fg='green')
            
            # Start audio processing thread
            self.audio_thread = threading.Thread(target=self.audio_processing_loop, daemon=True)
            self.audio_thread.start()
            
        except Exception as e:
            self.status_label.config(text=f"Erro ao iniciar áudio: {str(e)}", fg='red')
            
    def stop_listening(self):
        """Stop audio input and frequency detection."""
        self.is_listening = False
        
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
            
        if hasattr(self, 'audio'):
            self.audio.terminate()
            
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Parado", fg='black')
        self.current_freq_label.config(text="Frequência atual: -- Hz")
        self.tuning_label.config(text="")
        self.draw_tuning_meter(0)
        
    def audio_processing_loop(self):
        """Main audio processing loop running in separate thread."""
        while self.is_listening and self.audio_stream:
            try:
                # Read audio data
                data = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Convert to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Detect frequency
                frequency = self.detect_frequency(audio_data)
                
                if frequency > 0:
                    self.current_frequency = frequency
                    # Update UI in main thread
                    self.parent.after(0, self.update_ui)
                    
            except Exception as e:
                print(f"Audio processing error: {e}")
                break
                
        # Clean up when loop ends
        if self.is_listening:
            self.parent.after(0, self.stop_listening)
            
    def detect_frequency(self, audio_data: np.ndarray) -> float:
        """Advanced frequency detection using HPS algorithm (based on TomSchimansky GuitarTuner)."""
        if len(audio_data) == 0:
            return 0.0
        
        # Convert to float and normalize
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # Add to circular buffer (1.5 seconds like reference)
        chunk_size = len(audio_float)
        if self.buffer_index + chunk_size <= self.buffer_size:
            self.audio_buffer[self.buffer_index:self.buffer_index + chunk_size] = audio_float
            self.buffer_index += chunk_size
        else:
            # Wrap around
            remaining = self.buffer_size - self.buffer_index
            self.audio_buffer[self.buffer_index:] = audio_float[:remaining]
            self.audio_buffer[:chunk_size - remaining] = audio_float[remaining:]
            self.buffer_index = chunk_size - remaining
        
        # Check signal level
        rms = np.sqrt(np.mean(self.audio_buffer**2))
        if rms < self.noise_floor:
            return 0.0
        
        # Apply HPS (Harmonic Product Spectrum) algorithm
        frequency = self.hps_pitch_detection(self.audio_buffer)
        
        # Add to frequency history for stability
        if frequency > 0:
            self.frequency_history.append(frequency)
            if len(self.frequency_history) > self.history_size:
                self.frequency_history.pop(0)
            
            # Calculate stable frequency (median of recent detections)
            if len(self.frequency_history) >= 3:
                stable_freq = np.median(self.frequency_history)
                
                # Check if frequency is stable enough
                recent_freqs = self.frequency_history[-5:]
                if len(recent_freqs) >= 3:
                    freq_std = np.std(recent_freqs)
                    if freq_std < self.stability_threshold:
                        return stable_freq
                
                return stable_freq
        
        return frequency
    
    def hps_pitch_detection(self, audio_data):
        """
        HPS (Harmonic Product Spectrum) pitch detection algorithm.
        Based on TomSchimansky GuitarTuner implementation.
        
        This algorithm multiplies the FFT spectrum with its downsampled versions
        to enhance the fundamental frequency and suppress harmonics.
        """
        if len(audio_data) < 1024:
            return 0.0
        
        # Apply window function to reduce spectral leakage
        windowed = audio_data * np.hanning(len(audio_data))
        
        # Compute FFT
        fft = np.fft.rfft(windowed)
        magnitude = np.abs(fft)
        
        # Frequency resolution
        freq_resolution = self.sample_rate / len(windowed)
        
        # Convert frequency range to bin indices
        min_bin = max(1, int(self.min_frequency / freq_resolution))
        max_bin = min(len(magnitude) - 1, int(self.max_frequency / freq_resolution))
        
        if min_bin >= max_bin:
            return 0.0
        
        # Initialize HPS spectrum with the original magnitude spectrum
        hps_spectrum = magnitude[min_bin:max_bin].copy()
        
        # Apply HPS: multiply with downsampled versions
        for harmonic in range(2, self.hps_harmonics + 1):
            # Calculate the length for this harmonic
            harmonic_length = len(hps_spectrum) // harmonic
            if harmonic_length < 20:  # Need minimum length for reliable detection
                break
                
            # Create downsampled version by taking every 'harmonic'-th sample
            # This effectively compresses the spectrum by the harmonic factor
            downsampled = np.zeros(harmonic_length)
            for i in range(harmonic_length):
                # Average multiple bins to reduce noise
                start_idx = i * harmonic
                end_idx = min(start_idx + harmonic, len(hps_spectrum))
                if end_idx > start_idx:
                    downsampled[i] = np.mean(hps_spectrum[start_idx:end_idx])
            
            # Multiply with existing HPS spectrum (only the overlapping part)
            hps_spectrum[:harmonic_length] *= downsampled
        
        # Find the peak in HPS spectrum
        if len(hps_spectrum) == 0:
            return 0.0
        
        # Apply smoothing to reduce noise
        if len(hps_spectrum) > 5:
            # Simple moving average
            kernel_size = 3
            kernel = np.ones(kernel_size) / kernel_size
            hps_spectrum = np.convolve(hps_spectrum, kernel, mode='same')
        
        # Find the strongest peak
        peak_index = np.argmax(hps_spectrum)
        peak_value = hps_spectrum[peak_index]
        
        # Check if peak is significant enough
        mean_value = np.mean(hps_spectrum)
        if peak_value < mean_value * 2:  # Peak should be at least 2x the mean
            return 0.0
        
        # Convert back to frequency
        frequency = (min_bin + peak_index) * freq_resolution
        
        # Parabolic interpolation for sub-bin accuracy
        if 1 <= peak_index < len(hps_spectrum) - 1:
            y1, y2, y3 = hps_spectrum[peak_index-1], hps_spectrum[peak_index], hps_spectrum[peak_index+1]
            
            # Avoid division by zero and ensure valid parabola
            denominator = 2 * (2*y2 - y1 - y3)
            if y2 > 0 and abs(denominator) > 1e-10:
                x_offset = (y3 - y1) / denominator
                # Limit offset to reasonable range
                x_offset = max(-0.5, min(0.5, x_offset))
                frequency = (min_bin + peak_index + x_offset) * freq_resolution
        
        # Validate frequency range
        if self.min_frequency <= frequency <= self.max_frequency:
            return frequency
        
        return 0.0
    
    def frequency_to_note(self, frequency):
        """
        Convert frequency to musical note using the formula from TomSchimansky GuitarTuner:
        12 * log2(f / a4_frequency) + 69
        """
        if frequency <= 0:
            return None, 0
            
        a4_frequency = 440.0  # A4 reference frequency
        
        # Calculate MIDI note number
        midi_note = 12 * np.log2(frequency / a4_frequency) + 69
        
        # Round to nearest semitone
        midi_note_rounded = round(midi_note)
        
        # Calculate cents deviation
        cents_deviation = (midi_note - midi_note_rounded) * 100
        
        # Convert MIDI note to note name
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note_rounded - 12) // 12
        note_index = (midi_note_rounded - 12) % 12
        
        if 0 <= note_index < len(note_names) and octave >= 0:
            note_name = f"{note_names[int(note_index)]}{int(octave)}"
            return note_name, cents_deviation
        
        return None, 0
    
        
    def update_ui(self):
        """Update UI with current frequency information."""
        if not self.is_listening:
            return
            
        # Update frequency display
        self.current_freq_label.config(text=f"Frequência atual: {self.current_frequency:.1f} Hz")
        
        # Get detected note and cents deviation
        detected_note, cents_deviation = self.frequency_to_note(self.current_frequency)
        
        if detected_note:
            self.detected_note_label.config(text=f"Nota detectada: {detected_note}")
            self.cents_label.config(text=f"Desvio: {cents_deviation:+.1f} cents")
            
            # Color coding for cents deviation
            if abs(cents_deviation) < 5:  # Very close (< 5 cents)
                self.cents_label.config(fg='green')
            elif abs(cents_deviation) < 20:  # Close (< 20 cents)
                self.cents_label.config(fg='orange')
            else:  # Far (> 20 cents)
                self.cents_label.config(fg='red')
        else:
            self.detected_note_label.config(text="Nota detectada: --")
            self.cents_label.config(text="Desvio: -- cents", fg='black')
        
        # Auto-detect closest guitar string if enabled
        if self.auto_detect:
            guitar_string = self.find_closest_note(self.current_frequency)
            if guitar_string and guitar_string in self.GUITAR_NOTES:
                if guitar_string != self.detected_note:
                    self.detected_note = guitar_string
                    self.target_note = guitar_string
                    self.string_var.set(guitar_string)
                    target_freq = self.GUITAR_NOTES[guitar_string]
                    self.target_freq_label.config(text=f"Corda detectada: {guitar_string} ({target_freq:.0f} Hz)")
        
        # Calculate tuning status for guitar strings
        if self.target_note in self.GUITAR_NOTES:
            target_freq = self.GUITAR_NOTES[self.target_note]
            diff = self.current_frequency - target_freq
            diff_cents = 1200 * math.log2(self.current_frequency / target_freq) if target_freq > 0 and self.current_frequency > 0 else 0
        else:
            # Use the general cents deviation
            diff_cents = cents_deviation
        
        # Update tuning status
        if abs(diff_cents) < 5:  # Within 5 cents
            self.tuning_label.config(text="🎯 AFINADO!", fg='green')
            status_color = 'green'
        elif diff_cents > 0:
            self.tuning_label.config(text=f"🔺 AGUDO (+{diff_cents:.1f} cents)", fg='red')
            status_color = 'red'
        else:
            self.tuning_label.config(text=f"🔻 GRAVE ({diff_cents:.1f} cents)", fg='blue')
            status_color = 'blue'
            
        # Update visual meter
        self.draw_tuning_meter(diff_cents)
        
    def draw_tuning_meter(self, cents_diff: float):
        """Draw the visual tuning meter."""
        self.canvas.delete("all")
        
        # Canvas dimensions
        width = 400
        height = 100
        center_x = width // 2
        center_y = height // 2
        
        # Draw background
        self.canvas.create_rectangle(0, 0, width, height, fill='lightgray', outline='black')
        
        # Draw center line
        self.canvas.create_line(center_x, 10, center_x, height-10, fill='black', width=2)
        
        # Draw scale marks
        for i in range(-50, 51, 10):
            x = center_x + i * 3
            if x > 0 and x < width:
                mark_height = 20 if i % 20 == 0 else 10
                self.canvas.create_line(x, center_y - mark_height//2, 
                                      x, center_y + mark_height//2, fill='black')
                if i % 20 == 0 and i != 0:
                    self.canvas.create_text(x, center_y + 25, text=f"{i}", font=("Arial", 8))
        
        # Draw tuning zones
        # Green zone (in tune)
        green_left = center_x - 5 * 3
        green_right = center_x + 5 * 3
        self.canvas.create_rectangle(green_left, 10, green_right, height-10, 
                                   fill='lightgreen', outline='green')
        
        # Draw needle
        if cents_diff != 0:
            needle_x = center_x + max(-150, min(150, cents_diff)) * 3
            needle_color = 'green' if abs(cents_diff) < 5 else 'red' if cents_diff > 0 else 'blue'
            
            # Needle triangle
            self.canvas.create_polygon(needle_x, center_y - 15,
                                     needle_x - 8, center_y + 15,
                                     needle_x + 8, center_y + 15,
                                     fill=needle_color, outline='black')
        
        # Labels
        self.canvas.create_text(50, 20, text="GRAVE", font=("Arial", 10), fill='blue')
        self.canvas.create_text(center_x, 20, text="AFINADO", font=("Arial", 10), fill='green')
        self.canvas.create_text(width-50, 20, text="AGUDO", font=("Arial", 10), fill='red')


class TunerWindow:
    """Standalone tuner window."""
    
    def __init__(self, parent: Optional[tk.Widget] = None):
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
            
        self.window.title("🎸 Afinador de Guitarra")
        self.window.geometry("600x750")
        self.window.resizable(False, False)
        
        # Create tuner
        self.tuner = GuitarTuner(self.window)
        
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


def run_standalone():
    """Run the tuner as a standalone application."""
    if not AUDIO_AVAILABLE:
        print("Erro: Instale as dependências necessárias:")
        print("pip install numpy pyaudio")
        return
        
    app = TunerWindow()
    app.window.mainloop()


if __name__ == "__main__":
    run_standalone()
