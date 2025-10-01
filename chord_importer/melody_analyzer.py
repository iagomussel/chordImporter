"""
Melody Analyzer - Ferramenta para análise melódica com visualização gráfica tipo partitura.
Permite análise de arquivos de áudio e comparação em tempo real com microfone.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import queue
from typing import Optional, List, Tuple, Dict
import os
import math

# Required audio processing libraries - NO FALLBACKS
import numpy as np
import sounddevice as sd
import librosa
import soundfile as sf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches

# Import audio player for real playback
from .audio_player import AudioPlayer, AudioPlayerWidget

# Verify critical dependencies are available
if not hasattr(np, 'zeros'):
    raise ImportError("numpy not properly installed")
if not hasattr(sd, 'InputStream'):
    raise ImportError("sounddevice not properly installed")
if not hasattr(librosa, 'load'):
    raise ImportError("librosa not properly installed")


class MelodyAnalyzer:
    """
    Analisador de melodia com visualização gráfica tipo partitura.
    Suporta análise de arquivos de áudio e comparação em tempo real.
    """
    
    def __init__(self, parent: tk.Widget):
        """Initialize the melody analyzer."""
        self.parent = parent
        
        # Audio processing parameters
        self.sample_rate = 44100
        self.hop_length = 512
        self.frame_length = 2048
        self.buffer_size = 4096
        
        # Real-time audio parameters
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.current_pitch = 0.0
        self.pitch_buffer = []
        self.buffer_max_size = 10
        
        # File analysis data
        self.audio_file_path = None
        self.file_pitches = []
        self.file_times = []
        self.file_duration = 0.0
        
        # Audio player for real playback
        self.audio_player = AudioPlayer()
        
        # Musical note definitions (C3 to G6 - 5 octaves)
        self.setup_musical_notes()
        
        # Visualization parameters
        self.staff_lines = 5  # Traditional staff lines
        self.time_window = 10.0  # seconds to show
        self.current_time = 0.0
        
        # Colors
        self.colors = {
            'file_melody': '#2E86AB',      # Blue for file melody
            'realtime_pitch': '#A23B72',   # Pink for real-time pitch
            'staff_lines': '#666666',      # Gray for staff lines
            'background': '#FFFFFF',       # White background
            'note_names': '#333333'        # Dark gray for note names
        }
        
        self.setup_ui()
        
    def setup_musical_notes(self):
        """Setup musical note frequencies and positions."""
        # Note names in chromatic order
        self.note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Generate notes from C3 to G6 (5 octaves as requested)
        self.notes_info = {}
        self.note_positions = {}
        
        # A4 = 440 Hz reference
        A4_freq = 440.0
        A4_midi = 69  # MIDI note number for A4
        
        position = 0
        for octave in range(3, 7):  # C3 to G6
            for i, note_name in enumerate(self.note_names):
                if octave == 6 and i > 7:  # Stop at G6
                    break
                    
                # Calculate MIDI note number
                midi_note = (octave + 1) * 12 + i
                
                # Calculate frequency using equal temperament
                frequency = A4_freq * (2 ** ((midi_note - A4_midi) / 12))
                
                note_full_name = f"{note_name}{octave}"
                self.notes_info[note_full_name] = {
                    'frequency': frequency,
                    'midi': midi_note,
                    'position': position
                }
                self.note_positions[position] = note_full_name
                position += 1
        
        # Create frequency to position mapping for quick lookup
        self.freq_to_position = {}
        for note, info in self.notes_info.items():
            self.freq_to_position[info['frequency']] = info['position']
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Controles", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File controls
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(file_frame, text="Carregar Arquivo de Áudio", 
                  command=self.load_audio_file).pack(side=tk.LEFT, padx=(0, 5))
        
        self.file_label = ttk.Label(file_frame, text="Nenhum arquivo carregado")
        self.file_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Audio player widget
        player_frame = ttk.LabelFrame(control_frame, text="Audio Playback", padding=5)
        player_frame.pack(fill=tk.X, pady=5)
        
        self.audio_player_widget = AudioPlayerWidget(player_frame)
        self.audio_player_widget.pack(fill=tk.X)
        
        # Real-time controls
        realtime_frame = ttk.Frame(control_frame)
        realtime_frame.pack(fill=tk.X, pady=5)
        
        self.listen_button = ttk.Button(realtime_frame, text="🎤 Iniciar Captura", 
                                       command=self.toggle_listening)
        self.listen_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pitch_label = ttk.Label(realtime_frame, text="Pitch: -- Hz")
        self.pitch_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Visualization frame
        viz_frame = ttk.LabelFrame(main_frame, text="Visualização Melódica", padding=5)
        viz_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure
        self.setup_visualization(viz_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Pronto")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
    def setup_visualization(self, parent_frame):
        """Setup the matplotlib visualization."""
        # Create figure and axis
        self.fig = Figure(figsize=(12, 8), dpi=100, facecolor=self.colors['background'])
        self.ax = self.fig.add_subplot(111)
        
        # Setup staff-like visualization
        self.setup_staff_visualization()
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize plot lines
        self.file_melody_line, = self.ax.plot([], [], color=self.colors['file_melody'], 
                                             linewidth=2, label='Melodia do Arquivo', alpha=0.8)
        self.realtime_pitch_line, = self.ax.plot([], [], color=self.colors['realtime_pitch'], 
                                                 linewidth=3, label='Pitch em Tempo Real', 
                                                 marker='o', markersize=8)
        
        # Note: Playback position tracking removed - handled by audio player widget
        
        self.ax.legend(loc='upper right')
        
    def setup_staff_visualization(self):
        """Setup the staff-like visualization with note lines."""
        # Clear the axis
        self.ax.clear()
        
        # Set up the plot
        self.ax.set_xlim(0, self.time_window)
        self.ax.set_ylim(-5, len(self.note_positions) + 5)
        
        # Draw staff lines (every octave)
        octave_positions = []
        for pos, note_name in self.note_positions.items():
            if note_name.endswith('C'):  # C notes mark octave boundaries
                octave_positions.append(pos)
        
        # Draw main staff lines
        for pos in octave_positions:
            self.ax.axhline(y=pos, color=self.colors['staff_lines'], 
                           linestyle='-', linewidth=1, alpha=0.6)
        
        # Draw lighter lines for other notes
        for pos in range(len(self.note_positions)):
            if pos not in octave_positions:
                self.ax.axhline(y=pos, color=self.colors['staff_lines'], 
                               linestyle='-', linewidth=0.5, alpha=0.3)
        
        # Add note labels on the left
        note_labels = []
        note_positions_list = []
        for pos in range(0, len(self.note_positions), 12):  # Every octave
            if pos in self.note_positions:
                note_labels.append(self.note_positions[pos])
                note_positions_list.append(pos)
        
        self.ax.set_yticks(note_positions_list)
        self.ax.set_yticklabels(note_labels)
        
        # Labels and title
        self.ax.set_xlabel('Tempo (segundos)', fontsize=12)
        self.ax.set_ylabel('Notas Musicais', fontsize=12)
        self.ax.set_title('Análise Melódica - Arquivo vs Tempo Real', fontsize=14, fontweight='bold')
        
        # Grid
        self.ax.grid(True, alpha=0.3)
        
    def frequency_to_position(self, frequency: float) -> float:
        """Convert frequency to staff position."""
        if frequency <= 0:
            return -1
        
        # Find closest note using equal temperament
        # A4 = 440 Hz, MIDI note 69
        A4_freq = 440.0
        A4_midi = 69
        
        # Calculate MIDI note number
        midi_note = A4_midi + 12 * math.log2(frequency / A4_freq)
        
        # Find closest integer MIDI note
        closest_midi = round(midi_note)
        
        # Convert MIDI to our position system
        # Our positions start from C3 (MIDI 48)
        if closest_midi < 48:  # Below C3
            return -1
        if closest_midi > 91:  # Above G6
            return len(self.note_positions)
        
        position = closest_midi - 48
        return position
    
    def load_audio_file(self):
        """Load and analyze an audio file."""
        
        file_path = filedialog.askopenfilename(
            title="Selecionar Arquivo de Áudio",
            filetypes=[
                ("Arquivos de Áudio", "*.wav *.mp3 *.flac *.m4a *.ogg"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("FLAC files", "*.flac"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        self.status_var.set("Carregando arquivo...")
        self.parent.update()
        
        try:
            # Load audio file
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            self.file_duration = len(y) / sr
            
            # Extract pitch using librosa
            self.status_var.set("Analisando melodia...")
            self.parent.update()
            
            # Use librosa's pitch tracking
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr, 
                                                  hop_length=self.hop_length,
                                                  fmin=80, fmax=2000)
            
            # Extract the most prominent pitch at each time frame
            self.file_pitches = []
            self.file_times = []
            
            for t in range(pitches.shape[1]):
                # Find the pitch with highest magnitude
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                
                if pitch > 0:  # Valid pitch detected
                    self.file_pitches.append(pitch)
                else:
                    self.file_pitches.append(0)  # No pitch detected
                
                # Calculate time
                time_sec = t * self.hop_length / sr
                self.file_times.append(time_sec)
            
            # Update UI
            self.audio_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"Arquivo: {filename}")
            
            # Load into audio player for real playback
            if hasattr(self, 'audio_player_widget'):
                self.audio_player_widget.load_file(file_path)
            
            # Update visualization
            self.update_file_melody_visualization()
            
            self.status_var.set(f"Arquivo carregado: {filename} ({self.file_duration:.1f}s)")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivo:\n{str(e)}")
            self.status_var.set("Erro ao carregar arquivo")
    
    def update_file_melody_visualization(self):
        """Update the visualization with file melody data."""
        if not self.file_times or not self.file_pitches:
            return
        
        # Convert pitches to staff positions
        positions = []
        times = []
        
        for i, (time_val, pitch) in enumerate(zip(self.file_times, self.file_pitches)):
            if pitch > 0:  # Valid pitch
                position = self.frequency_to_position(pitch)
                if 0 <= position < len(self.note_positions):
                    positions.append(position)
                    times.append(time_val)
        
        # Update the plot
        if times and positions:
            self.file_melody_line.set_data(times, positions)
            
            # Adjust time window if needed
            if max(times) > self.time_window:
                self.ax.set_xlim(0, max(times) + 2)
            
            self.canvas.draw()
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_listening()
        if hasattr(self, 'audio_player_widget'):
            self.audio_player_widget.cleanup()
    
    def toggle_listening(self):
        """Toggle real-time audio listening."""
        
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()
    
    def start_listening(self):
        """Start real-time audio capture."""
        try:
            self.is_listening = True
            self.listen_button.config(text="🔴 Parar Captura")
            
            # Start audio stream
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=self.audio_callback,
                blocksize=self.buffer_size
            )
            self.audio_stream.start()
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self.process_realtime_audio, daemon=True)
            self.processing_thread.start()
            
            self.status_var.set("Capturando áudio em tempo real...")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar captura de áudio:\n{str(e)}")
            self.is_listening = False
            self.listen_button.config(text="🎤 Iniciar Captura")
    
    def stop_listening(self):
        """Stop real-time audio capture."""
        self.is_listening = False
        
        try:
            if hasattr(self, 'listen_button') and self.listen_button.winfo_exists():
                self.listen_button.config(text="🎤 Iniciar Captura")
            
            if hasattr(self, 'audio_stream'):
                self.audio_stream.stop()
                self.audio_stream.close()
            
            if hasattr(self, 'status_var'):
                self.status_var.set("Captura de áudio parada")
        except tk.TclError:
            # Widget was destroyed, ignore
            pass
        except Exception as e:
            print(f"Error stopping audio capture: {e}")
    
    def audio_callback(self, indata, frames, time, status):
        """Audio callback for real-time processing."""
        if status:
            print(f"Audio callback status: {status}")
        
        # Put audio data in queue for processing
        self.audio_queue.put(indata.copy())
    
    def process_realtime_audio(self):
        """Process real-time audio data."""
        while self.is_listening:
            try:
                # Get audio data from queue
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Convert to mono if needed
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                # Detect pitch using autocorrelation
                pitch = self.detect_pitch_autocorr(audio_data)
                
                if pitch > 0:
                    # Add to buffer for stability
                    self.pitch_buffer.append(pitch)
                    if len(self.pitch_buffer) > self.buffer_max_size:
                        self.pitch_buffer.pop(0)
                    
                    # Use median for stability
                    if len(self.pitch_buffer) >= 3:
                        stable_pitch = np.median(self.pitch_buffer)
                        self.current_pitch = stable_pitch
                        
                        # Update UI in main thread
                        self.parent.after(0, self.update_realtime_ui)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Real-time audio processing error: {e}")
                continue
    
    def detect_pitch_autocorr(self, audio_data: np.ndarray) -> float:
        """Detect pitch using autocorrelation method."""
        if len(audio_data) == 0:
            return 0.0
        
        # Apply window to reduce spectral leakage
        windowed = audio_data.flatten() * np.hanning(len(audio_data))
        
        # Autocorrelation
        autocorr = np.correlate(windowed, windowed, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find the first peak after the zero lag
        min_period = int(self.sample_rate / 2000)  # Max 2000 Hz
        max_period = int(self.sample_rate / 80)    # Min 80 Hz
        
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
        
        return frequency if 80 <= frequency <= 2000 else 0.0
    
    def update_realtime_ui(self):
        """Update UI with real-time pitch data."""
        try:
            # Check if widgets still exist
            if not hasattr(self, 'pitch_label') or not self.pitch_label.winfo_exists():
                return
            
            # Update pitch label
            self.pitch_label.config(text=f"Pitch: {self.current_pitch:.1f} Hz")
            
            # Update visualization
            if self.current_pitch > 0 and hasattr(self, 'canvas'):
                position = self.frequency_to_position(self.current_pitch)
                if 0 <= position < len(self.note_positions):
                    # Get current time for x-axis
                    current_time = time.time()
                    if not hasattr(self, 'start_time'):
                        self.start_time = current_time
                    
                    relative_time = current_time - self.start_time
                    
                    # Update real-time pitch line
                    self.realtime_pitch_line.set_data([relative_time], [position])
                    
                    # Adjust time window if needed
                    if relative_time > self.time_window:
                        self.ax.set_xlim(relative_time - self.time_window, relative_time + 2)
                    
                    self.canvas.draw_idle()
        except tk.TclError:
            # Widget was destroyed, stop processing
            self.is_listening = False
        except Exception as e:
            print(f"Error updating real-time UI: {e}")


def show_melody_analyzer(parent: tk.Widget):
    """Show the melody analyzer window."""
    
    # Create new window
    window = tk.Toplevel(parent)
    window.title("Analisador de Melodia")
    window.geometry("1200x800")
    window.minsize(800, 600)
    
    # Create analyzer
    analyzer = MelodyAnalyzer(window)
    
    # Center window
    window.transient(parent)
    window.grab_set()
    
    return window
