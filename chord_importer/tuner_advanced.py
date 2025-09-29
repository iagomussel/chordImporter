"""
Advanced Guitar Tuner with HPS Algorithm, Audio Recording, and Auto-Tuning.
Based on chciken.com implementation: https://www.chciken.com/digital/signal/processing/2020/05/13/guitar-tuner.html
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import math
import copy
import os
from typing import Optional, List, Tuple
import wave

# Try to import audio libraries with graceful fallback
try:
    import numpy as np
    import pyaudio
    import scipy.io.wavfile
    import scipy.fftpack
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    # Create dummy numpy for fallback
    class np:
        @staticmethod
        def zeros(size, dtype=None): return [0] * size
        @staticmethod
        def hanning(size): return [1] * size
        @staticmethod
        def array(x): return x
        @staticmethod
        def abs(x): return [abs(i) for i in x] if isinstance(x, list) else abs(x)
        @staticmethod
        def argmax(x): return x.index(max(x)) if x else 0
        @staticmethod
        def log2(x): return math.log2(x) if x > 0 else 0
        @staticmethod
        def round(x): return round(x)
        @staticmethod
        def interp(x, xp, fp): return fp[0] if fp else 0
        @staticmethod
        def arange(start, stop, step=1): return list(range(int(start), int(stop), int(step)))
        @staticmethod
        def ceil(x): return math.ceil(x)
        @staticmethod
        def multiply(a, b): return [x*y for x, y in zip(a, b)]
        @staticmethod
        def concatenate(arrays): 
            result = []
            for arr in arrays:
                result.extend(arr)
            return result
        float64 = float
        int16 = int
        
        class linalg:
            @staticmethod
            def norm(x, ord=2):
                return math.sqrt(sum(i*i for i in x))

class AdvancedGuitarTuner:
    """
    Advanced Guitar Tuner implementing HPS (Harmonic Product Spectrum) algorithm
    from chciken.com with audio recording and auto-tuning capabilities.
    """
    
    def __init__(self, parent: tk.Widget):
        """Initialize the advanced guitar tuner."""
        self.parent = parent
        self.is_listening = False
        self.is_recording = False
        self.current_frequency = 0.0
        self.target_note = 'E2'
        self.auto_detect = True
        self.detected_note = None
        
        # Make numpy available as instance attribute
        self.np = np
        
        # HPS Algorithm Parameters (from chciken.com)
        self.SAMPLE_FREQ = 44100  # Sampling frequency
        self.WINDOW_SIZE = 4096   # Window size for FFT
        self.WINDOW_STEP = 1024   # Step size for sliding window
        self.NUM_HPS = 5          # Number of harmonics for HPS
        self.POWER_THRESH = 1e-6  # Power threshold for signal detection
        self.WHITE_NOISE_THRESH = 0.2  # White noise threshold
        
        # Concert pitch and note definitions (from chciken.com)
        self.CONCERT_PITCH = 440  # A4 = 440 Hz
        self.ALL_NOTES = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
        
        # Standard guitar tuning frequencies (exact values from chciken.com)
        self.GUITAR_NOTES = {
            'E2': 82.41,   # 6ª corda (mais grave) - Mi
            'A2': 110.00,  # 5ª corda - Lá  
            'D3': 146.83,  # 4ª corda - Ré
            'G3': 196.00,  # 3ª corda - Sol
            'B3': 246.94,  # 2ª corda - Si
            'E4': 329.63,  # 1ª corda (mais aguda) - Mi
        }
        
        # String names in order
        self.STRING_NAMES = ['E2', 'A2', 'D3', 'G3', 'B3', 'E4']
        
        # Octave bands for noise reduction (from chciken.com)
        self.OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]
        
        # Audio processing variables
        self.audio_stream = None
        self.audio_data = None
        self.window_samples = None
        self.note_buffer = []
        self.recording_data = []
        
        # Auto-tuning variables
        self.auto_tune_enabled = False
        self.target_pitch_correction = 0.0
        
        # Get available microphones
        self.available_mics = self.get_available_microphones()
        
        self.setup_ui()
    
    def get_available_microphones(self) -> List[dict]:
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
    
    def find_closest_note(self, pitch: float) -> Tuple[str, float]:
        """
        Find closest note using chciken.com algorithm.
        
        Args:
            pitch: Frequency in Hz
            
        Returns:
            Tuple of (note_name, closest_pitch)
        """
        if pitch <= 0:
            return None, 0
            
        # Calculate semitone index from A4 (chciken.com formula)
        i = int(np.round(np.log2(pitch / self.CONCERT_PITCH) * 12))
        
        # Get note name
        closest_note = self.ALL_NOTES[i % 12] + str(4 + (i + 9) // 12)
        
        # Calculate exact pitch of closest note
        closest_pitch = self.CONCERT_PITCH * (2 ** (i / 12))
        
        return closest_note, closest_pitch
    
    def hps_pitch_detection(self, audio_data: np.array) -> float:
        """
        HPS (Harmonic Product Spectrum) pitch detection algorithm.
        Implementation based on chciken.com article.
        
        Args:
            audio_data: Audio samples as numpy array
            
        Returns:
            Detected frequency in Hz
        """
        if len(audio_data) < self.WINDOW_SIZE:
            return 0.0
        
        # Calculate signal power (chciken.com implementation)
        signal_power = (np.linalg.norm(audio_data, ord=2)**2) / len(audio_data)
        if signal_power < self.POWER_THRESH:
            return 0.0
        
        # Apply Hann window to reduce spectral leakage (chciken.com)
        hann_window = np.hanning(len(audio_data))
        hann_samples = audio_data * hann_window
        
        # Compute magnitude spectrum using FFT
        magnitude_spec = np.abs(scipy.fftpack.fft(hann_samples)[:len(hann_samples)//2])
        
        # Frequency resolution
        delta_freq = self.SAMPLE_FREQ / len(audio_data)
        
        # Suppress mains hum - set everything below 62 Hz to zero (chciken.com)
        for i in range(int(62 / delta_freq)):
            if i < len(magnitude_spec):
                magnitude_spec[i] = 0
        
        # Noise reduction using octave bands (chciken.com implementation)
        for j in range(len(self.OCTAVE_BANDS) - 1):
            ind_start = int(self.OCTAVE_BANDS[j] / delta_freq)
            ind_end = int(self.OCTAVE_BANDS[j + 1] / delta_freq)
            ind_end = min(ind_end, len(magnitude_spec))
            
            if ind_start < ind_end:
                # Calculate average energy per frequency
                band_energy = magnitude_spec[ind_start:ind_end]
                if len(band_energy) > 0:
                    avg_energy_per_freq = (np.linalg.norm(band_energy, ord=2)**2) / len(band_energy)
                    avg_energy_per_freq = avg_energy_per_freq**0.5
                    
                    # Suppress frequencies below threshold
                    for i in range(ind_start, ind_end):
                        if magnitude_spec[i] <= self.WHITE_NOISE_THRESH * avg_energy_per_freq:
                            magnitude_spec[i] = 0
        
        # Interpolate spectrum for HPS (chciken.com)
        mag_spec_ipol = np.interp(
            np.arange(0, len(magnitude_spec), 1/self.NUM_HPS),
            np.arange(0, len(magnitude_spec)),
            magnitude_spec
        )
        
        # Normalize interpolated spectrum
        if np.linalg.norm(mag_spec_ipol, ord=2) > 0:
            mag_spec_ipol = mag_spec_ipol / np.linalg.norm(mag_spec_ipol, ord=2)
        
        # Calculate HPS (chciken.com implementation)
        hps_spec = copy.deepcopy(mag_spec_ipol)
        
        for i in range(self.NUM_HPS):
            # Calculate downsampled spectrum length
            downsample_length = int(np.ceil(len(mag_spec_ipol) / (i + 1)))
            if downsample_length <= 0:
                break
                
            # Multiply with downsampled spectrum
            downsampled = mag_spec_ipol[::i+1][:downsample_length]
            
            if len(downsampled) > 0 and len(hps_spec) >= len(downsampled):
                tmp_hps_spec = np.multiply(hps_spec[:len(downsampled)], downsampled)
                if np.any(tmp_hps_spec):
                    hps_spec = tmp_hps_spec
                else:
                    break
        
        # Find peak frequency
        if len(hps_spec) == 0 or not np.any(hps_spec):
            return 0.0
            
        max_ind = np.argmax(hps_spec)
        max_freq = max_ind * (self.SAMPLE_FREQ / len(audio_data)) / self.NUM_HPS
        
        return max_freq
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Audio callback function for real-time processing."""
        if not AUDIO_AVAILABLE:
            return (None, pyaudio.paContinue)
        
        if status:
            print(f"Audio callback status: {status}")
        
        try:
            # Convert audio data to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # Initialize window samples if needed
            if self.window_samples is None:
                self.window_samples = np.zeros(self.WINDOW_SIZE)
            
            # Update sliding window
            if len(audio_data) > 0:
                # Append new samples and remove old ones
                self.window_samples = np.concatenate((self.window_samples, audio_data))
                self.window_samples = self.window_samples[len(audio_data):]
                
                # Detect pitch using HPS
                detected_freq = self.hps_pitch_detection(self.window_samples)
                
                if detected_freq > 0:
                    self.current_frequency = detected_freq
                    
                    # Find closest note
                    closest_note, closest_pitch = self.find_closest_note(detected_freq)
                    
                    # Update note buffer for stability (chciken.com majority vote)
                    if len(self.note_buffer) >= 2:
                        self.note_buffer.pop()
                    self.note_buffer.insert(0, closest_note)
                    
                    # Update UI in main thread
                    self.parent.after(0, self.update_ui_callback)
                
                # Record audio if recording is enabled
                if self.is_recording and len(audio_data) > 0:
                    self.recording_data.extend(audio_data)
        
        except Exception as e:
            print(f"Audio callback error: {e}")
        
        return (None, pyaudio.paContinue)
    
    def update_ui_callback(self):
        """Update UI from main thread."""
        if hasattr(self, 'update_ui'):
            self.update_ui()
    
    def setup_ui(self):
        """Setup the advanced tuner user interface."""
        # Main frame
        self.frame = tk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(self.frame, text="🎸 Afinador Avançado com HPS", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Microphone selection
        mic_frame = tk.Frame(self.frame)
        mic_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(mic_frame, text="Microfone:", font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.mic_var = tk.StringVar()
        mic_names = [mic['name'] for mic in self.available_mics]
        self.mic_combo = ttk.Combobox(mic_frame, textvariable=self.mic_var, 
                                     values=mic_names, state="readonly")
        self.mic_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        if mic_names:
            self.mic_combo.current(0)
        self.mic_combo.bind('<<ComboboxSelected>>', self.on_mic_changed)
        
        # Auto-detect and string selection
        controls_frame = tk.Frame(self.frame)
        controls_frame.pack(fill=tk.X, pady=10)
        
        self.auto_var = tk.BooleanVar(value=True)
        self.auto_checkbox = tk.Checkbutton(controls_frame, text="Detectar corda automaticamente", 
                                           variable=self.auto_var, command=self.on_auto_changed)
        self.auto_checkbox.pack(side=tk.LEFT)
        
        tk.Label(controls_frame, text="Corda:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        
        self.string_var = tk.StringVar(value=self.target_note)
        self.string_combo = ttk.Combobox(controls_frame, textvariable=self.string_var,
                                        values=self.STRING_NAMES, state="readonly", width=8)
        self.string_combo.pack(side=tk.LEFT)
        self.string_combo.bind('<<ComboboxSelected>>', self.on_string_changed)
        
        # Initially disable string selection if auto mode is on
        if self.auto_detect:
            self.string_combo.config(state=tk.DISABLED)
        
        # Target frequency display
        self.target_freq_label = tk.Label(self.frame, 
                                         text=f"Frequência alvo: {self.GUITAR_NOTES[self.target_note]:.2f} Hz",
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
        
        # Algorithm info
        self.algorithm_info_label = tk.Label(self.frame, 
                                           text="Algoritmo HPS (Harmonic Product Spectrum) - chciken.com",
                                           font=("Arial", 9), fg='gray')
        self.algorithm_info_label.pack(pady=5)
        
        # Tuning indicator (visual meter)
        indicator_frame = tk.Frame(self.frame)
        indicator_frame.pack(pady=20)
        
        self.canvas = tk.Canvas(indicator_frame, width=400, height=100, bg='white')
        self.canvas.pack()
        
        # Draw tuning meter
        self.draw_tuning_meter()
        
        # Status and tuning label
        self.tuning_label = tk.Label(self.frame, text="🎵 Toque uma corda", 
                                    font=("Arial", 14, "bold"), fg='blue')
        self.tuning_label.pack(pady=10)
        
        # Control buttons
        button_frame = tk.Frame(self.frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.start_button = tk.Button(button_frame, text="▶️ Iniciar", 
                                     command=self.start_listening, font=("Arial", 12))
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(button_frame, text="⏹️ Parar", 
                                    command=self.stop_listening, font=("Arial", 12))
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Recording controls
        self.record_button = tk.Button(button_frame, text="🔴 Gravar", 
                                      command=self.start_recording, font=("Arial", 12))
        self.record_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_record_button = tk.Button(button_frame, text="⏹️ Parar Gravação", 
                                           command=self.stop_recording, font=("Arial", 12))
        self.stop_record_button.pack(side=tk.LEFT, padx=5)
        
        # Auto-tuning controls
        self.autotune_var = tk.BooleanVar()
        self.autotune_checkbox = tk.Checkbutton(button_frame, text="Auto-Tuning", 
                                               variable=self.autotune_var, 
                                               command=self.toggle_autotune)
        self.autotune_checkbox.pack(side=tk.LEFT, padx=20)
        
        # Status label
        self.status_label = tk.Label(self.frame, text="Pronto para usar", 
                                    font=("Arial", 10), fg='green')
        self.status_label.pack(pady=10)
    
    def draw_tuning_meter(self):
        """Draw the visual tuning meter."""
        self.canvas.delete("all")
        
        # Draw meter background
        self.canvas.create_rectangle(50, 30, 350, 70, fill='lightgray', outline='black')
        
        # Draw center line (perfect tuning)
        center_x = 200
        self.canvas.create_line(center_x, 20, center_x, 80, fill='black', width=2)
        
        # Draw scale marks
        for i in range(-4, 5):
            x = center_x + i * 30
            self.canvas.create_line(x, 65, x, 75, fill='black')
            if i != 0:
                self.canvas.create_text(x, 85, text=f"{i*25}", font=("Arial", 8))
        
        # Labels
        self.canvas.create_text(25, 50, text="GRAVE", font=("Arial", 8), angle=90)
        self.canvas.create_text(375, 50, text="AGUDO", font=("Arial", 8), angle=90)
        self.canvas.create_text(200, 10, text="AFINADO", font=("Arial", 10, "bold"))
    
    def update_tuning_meter(self, cents_deviation: float):
        """Update the visual tuning meter."""
        # Clear previous needle
        self.canvas.delete("needle")
        
        # Calculate needle position
        center_x = 200
        max_deviation = 100  # cents
        needle_x = center_x + (cents_deviation / max_deviation) * 120
        needle_x = max(60, min(340, needle_x))  # Clamp to meter bounds
        
        # Choose color based on deviation
        if abs(cents_deviation) < 5:
            color = 'green'
        elif abs(cents_deviation) < 20:
            color = 'orange'
        else:
            color = 'red'
        
        # Draw needle
        self.canvas.create_line(needle_x, 30, needle_x, 70, fill=color, width=4, tags="needle")
        self.canvas.create_oval(needle_x-5, 45, needle_x+5, 55, fill=color, tags="needle")
    
    def on_mic_changed(self, event=None):
        """Handle microphone selection change."""
        if self.is_listening:
            self.stop_listening()
            self.parent.after(100, self.start_listening)  # Restart with new mic
    
    def on_auto_changed(self):
        """Handle auto-detect checkbox change."""
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
            self.target_freq_label.config(text=f"Frequência alvo: {target_freq:.2f} Hz")
    
    def start_listening(self):
        """Start audio input and frequency detection."""
        if not AUDIO_AVAILABLE:
            self.status_label.config(text="Erro: Bibliotecas de áudio não disponíveis", fg='red')
            messagebox.showerror("Erro", "Bibliotecas de áudio (numpy, pyaudio) não estão instaladas!")
            return
        
        if self.is_listening:
            return
        
        try:
            # Get selected microphone
            selected_mic_name = self.mic_var.get()
            selected_mic_index = 0
            
            for mic in self.available_mics:
                if mic['name'] == selected_mic_name:
                    selected_mic_index = mic['index']
                    break
            
            # Initialize audio stream
            audio = pyaudio.PyAudio()
            
            self.audio_stream = audio.open(
                format=pyaudio.paFloat32,  # Changed from paFloat64 to paFloat32 for compatibility
                channels=1,
                rate=self.SAMPLE_FREQ,
                input=True,
                input_device_index=selected_mic_index,
                frames_per_buffer=self.WINDOW_STEP,
                stream_callback=self.audio_callback
            )
            
            # Initialize processing variables
            self.window_samples = np.zeros(self.WINDOW_SIZE)
            self.note_buffer = []
            
            self.audio_stream.start_stream()
            self.is_listening = True
            
            self.status_label.config(text="Ouvindo... Toque uma corda!", fg='green')
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
        except Exception as e:
            self.status_label.config(text=f"Erro ao iniciar áudio: {str(e)}", fg='red')
            messagebox.showerror("Erro", f"Erro ao iniciar captura de áudio:\n{str(e)}")
    
    def stop_listening(self):
        """Stop audio input and frequency detection."""
        if not self.is_listening:
            return
        
        try:
            self.is_listening = False
            
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            
            self.status_label.config(text="Parado", fg='orange')
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Clear displays
            self.current_freq_label.config(text="Frequência atual: -- Hz")
            self.detected_note_label.config(text="Nota detectada: --")
            self.cents_label.config(text="Desvio: -- cents")
            self.tuning_label.config(text="🎵 Parado", fg='gray')
            
            # Clear meter
            self.canvas.delete("needle")
            
        except Exception as e:
            self.status_label.config(text=f"Erro ao parar: {str(e)}", fg='red')
    
    def start_recording(self):
        """Start audio recording."""
        if not self.is_listening:
            messagebox.showwarning("Aviso", "Inicie o afinador antes de gravar!")
            return
        
        self.is_recording = True
        self.recording_data = []
        
        self.record_button.config(state=tk.DISABLED)
        self.stop_record_button.config(state=tk.NORMAL)
        self.status_label.config(text="Gravando áudio...", fg='red')
    
    def stop_recording(self):
        """Stop audio recording and save to file."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if len(self.recording_data) == 0:
            messagebox.showwarning("Aviso", "Nenhum áudio foi gravado!")
            return
        
        # Ask user where to save
        filename = filedialog.asksaveasfilename(
            title="Salvar gravação",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Convert to numpy array and save
                audio_array = np.array(self.recording_data, dtype=np.float32)
                
                # Normalize to 16-bit range
                audio_normalized = np.int16(audio_array * 32767)
                
                # Save using scipy
                scipy.io.wavfile.write(filename, self.SAMPLE_FREQ, audio_normalized)
                
                messagebox.showinfo("Sucesso", f"Áudio salvo em:\n{filename}")
                self.status_label.config(text=f"Gravação salva: {os.path.basename(filename)}", fg='green')
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar áudio:\n{str(e)}")
                self.status_label.config(text="Erro ao salvar gravação", fg='red')
        
        self.record_button.config(state=tk.NORMAL)
        self.stop_record_button.config(state=tk.DISABLED)
    
    def toggle_autotune(self):
        """Toggle auto-tuning functionality."""
        self.auto_tune_enabled = self.autotune_var.get()
        
        if self.auto_tune_enabled:
            self.status_label.config(text="Auto-tuning ativado", fg='blue')
        else:
            self.status_label.config(text="Auto-tuning desativado", fg='gray')
    
    def apply_autotune(self, frequency: float, target_frequency: float) -> float:
        """
        Apply auto-tuning correction to frequency.
        Simple pitch correction algorithm.
        """
        if not self.auto_tune_enabled:
            return frequency
        
        # Calculate cents deviation
        if target_frequency > 0 and frequency > 0:
            cents_deviation = 1200 * np.log2(frequency / target_frequency)
            
            # Apply correction (simple snap-to-pitch)
            correction_strength = 0.8  # 80% correction
            corrected_cents = cents_deviation * (1 - correction_strength)
            
            # Convert back to frequency
            corrected_frequency = target_frequency * (2 ** (corrected_cents / 1200))
            
            return corrected_frequency
        
        return frequency
    
    def update_ui(self):
        """Update UI with current frequency information."""
        if not self.is_listening:
            return
        
        # Update frequency display
        self.current_freq_label.config(text=f"Frequência atual: {self.current_frequency:.1f} Hz")
        
        # Get detected note and cents deviation
        if self.current_frequency > 0:
            detected_note, closest_pitch = self.find_closest_note(self.current_frequency)
            
            if detected_note:
                self.detected_note_label.config(text=f"Nota detectada: {detected_note}")
                
                # Calculate cents deviation
                cents_deviation = 1200 * np.log2(self.current_frequency / closest_pitch) if closest_pitch > 0 else 0
                
                self.cents_label.config(text=f"Desvio: {cents_deviation:+.1f} cents")
                
                # Color coding for cents deviation
                if abs(cents_deviation) < 5:  # Very close (< 5 cents)
                    self.cents_label.config(fg='green')
                    self.tuning_label.config(text="🎯 AFINADO!", fg='green')
                elif abs(cents_deviation) < 20:  # Close (< 20 cents)
                    self.cents_label.config(fg='orange')
                    direction = "agudo" if cents_deviation > 0 else "grave"
                    self.tuning_label.config(text=f"📈 Muito {direction}", fg='orange')
                else:  # Far (> 20 cents)
                    self.cents_label.config(fg='red')
                    direction = "AGUDO" if cents_deviation > 0 else "GRAVE"
                    self.tuning_label.config(text=f"📊 {direction}!", fg='red')
                
                # Update visual meter
                self.update_tuning_meter(cents_deviation)
                
                # Auto-detect closest guitar string if enabled
                if self.auto_detect:
                    # Find closest guitar string
                    closest_guitar_note = None
                    min_distance = float('inf')
                    
                    for note, freq in self.GUITAR_NOTES.items():
                        distance = abs(self.current_frequency - freq)
                        if distance < min_distance:
                            min_distance = distance
                            closest_guitar_note = note
                    
                    # Update target if close enough (within 50 Hz)
                    if closest_guitar_note and min_distance < 50:
                        if closest_guitar_note != self.detected_note:
                            self.detected_note = closest_guitar_note
                            self.target_note = closest_guitar_note
                            self.string_var.set(closest_guitar_note)
                            target_freq = self.GUITAR_NOTES[closest_guitar_note]
                            self.target_freq_label.config(text=f"Corda detectada: {closest_guitar_note} ({target_freq:.2f} Hz)")
                
                # Apply auto-tuning if enabled
                if self.auto_tune_enabled and self.target_note in self.GUITAR_NOTES:
                    target_freq = self.GUITAR_NOTES[self.target_note]
                    corrected_freq = self.apply_autotune(self.current_frequency, target_freq)
                    if corrected_freq != self.current_frequency:
                        self.status_label.config(text=f"Auto-tune: {corrected_freq:.1f} Hz", fg='blue')
            
            else:
                self.detected_note_label.config(text="Nota detectada: --")
                self.cents_label.config(text="Desvio: -- cents", fg='black')
                self.tuning_label.config(text="🎵 Toque uma corda", fg='blue')
        else:
            self.detected_note_label.config(text="Nota detectada: --")
            self.cents_label.config(text="Desvio: -- cents", fg='black')
            self.tuning_label.config(text="🎵 Toque uma corda", fg='blue')

class TunerWindow:
    """Advanced Tuner window wrapper."""
    
    def __init__(self, parent=None):
        """Initialize tuner window."""
        self.parent = parent
        
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
            
        self.window.title("🎸 Afinador Avançado HPS")
        self.window.geometry("650x800")
        self.window.resizable(False, False)
        
        # Create tuner
        self.tuner = AdvancedGuitarTuner(self.window)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """Handle window close event."""
        if hasattr(self.tuner, 'stop_listening'):
            self.tuner.stop_listening()
        if hasattr(self.tuner, 'stop_recording'):
            self.tuner.stop_recording()
        self.window.destroy()

# For backward compatibility
def show_tuner_window(parent=None):
    """Show the advanced tuner window."""
    return TunerWindow(parent)
