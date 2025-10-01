"""
Advanced Melody Analyzer - Ferramenta avançada para análise melódica com separação vocal.
Implementa separação de stems, detecção melódica precisa e visualização piano roll.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import queue
import os
import tempfile
import subprocess
from typing import Optional, List, Tuple, Dict, Any
import math

# Required advanced audio processing libraries - NO FALLBACKS
import numpy as np
import sounddevice as sd
import librosa
import soundfile as sf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.patches import Rectangle

# Import audio player for real playback
from .audio_player import AudioPlayer, AudioPlayerWidget

# Verify critical dependencies are available
if not hasattr(np, 'zeros'):
    raise ImportError("numpy not properly installed")
if not hasattr(sd, 'InputStream'):
    raise ImportError("sounddevice not properly installed")
if not hasattr(librosa, 'load'):
    raise ImportError("librosa not properly installed")


class VocalSeparator:
    """Handles vocal separation using various methods."""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def separate_vocals_librosa(self, audio_file: str, progress_callback=None) -> Tuple[str, str]:
        """Separate vocals using librosa's harmonic-percussive separation."""
        
        try:
            if progress_callback:
                progress_callback(10, "Loading audio file...")
            
            # Load audio
            y, sr = librosa.load(audio_file, sr=44100)
            
            if progress_callback:
                progress_callback(30, "Performing harmonic-percussive separation...")
            
            # Use librosa's harmonic-percussive separation
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            
            if progress_callback:
                progress_callback(60, "Isolating vocals using spectral subtraction...")
            
            # Simple vocal isolation using center channel extraction
            # This is a basic approach - not as advanced as Demucs but works without external dependencies
            S_full, phase = librosa.magphase(librosa.stft(y))
            S_filter = librosa.decompose.nn_filter(S_full,
                                                 aggregate=np.median,
                                                 metric='cosine',
                                                 width=int(librosa.frames_to_time(S_full.shape[1], sr=sr)))
            S_filter = np.minimum(S_full, S_filter)
            
            margin_i, margin_v = 2, 10
            power = 2
            
            mask_i = librosa.util.softmask(S_filter,
                                         margin_i * (S_full - S_filter),
                                         power=power)
            
            mask_v = librosa.util.softmask(S_full - S_filter,
                                         margin_v * S_filter,
                                         power=power)
            
            # Apply masks
            S_foreground = mask_v * S_full
            S_background = mask_i * S_full
            
            if progress_callback:
                progress_callback(80, "Saving separated tracks...")
            
            # Convert back to audio
            vocals = librosa.istft(S_foreground * phase, hop_length=512)
            accompaniment = librosa.istft(S_background * phase, hop_length=512)
            
            # Save as WAV files
            vocals_path = os.path.join(self.temp_dir, "vocals.wav")
            accompaniment_path = os.path.join(self.temp_dir, "accompaniment.wav")
            
            sf.write(vocals_path, vocals, sr)
            sf.write(accompaniment_path, accompaniment, sr)
            
            if progress_callback:
                progress_callback(100, "Vocal separation complete!")
            
            return vocals_path, accompaniment_path
            
        except Exception as e:
            raise RuntimeError(f"Error in librosa vocal separation: {str(e)}")
    
    def separate_vocals_librosa(self, audio_file: str, progress_callback=None) -> Tuple[str, str]:
        """Separate vocals using librosa (simpler method)."""
        try:
            if progress_callback:
                progress_callback(10, "Loading audio file...")
            
            # Load audio
            y, sr = librosa.load(audio_file, sr=None)
            
            if progress_callback:
                progress_callback(30, "Converting to stereo...")
            
            # Ensure stereo
            if len(y.shape) == 1:
                # Mono to stereo (duplicate channel)
                y_stereo = np.array([y, y])
            else:
                y_stereo = y.T
            
            if progress_callback:
                progress_callback(50, "Separating vocals...")
            
            # Simple vocal separation (center channel extraction)
            # Vocals are typically in the center, so subtract L-R
            vocals = (y_stereo[0] + y_stereo[1]) / 2  # Center channel
            accompaniment = (y_stereo[0] - y_stereo[1]) / 2  # Side channels
            
            if progress_callback:
                progress_callback(80, "Saving separated tracks...")
            
            # Save separated tracks
            vocals_path = os.path.join(self.temp_dir, "vocals_librosa.wav")
            accompaniment_path = os.path.join(self.temp_dir, "accompaniment_librosa.wav")
            
            sf.write(vocals_path, vocals, sr)
            sf.write(accompaniment_path, accompaniment, sr)
            
            if progress_callback:
                progress_callback(100, "Separation complete!")
            
            return vocals_path, accompaniment_path
            
        except Exception as e:
            raise RuntimeError(f"Error in librosa separation: {str(e)}")
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass


class MelodyExtractor:
    """Advanced melody extraction using specialized algorithms."""
    
    def __init__(self):
        self.sample_rate = 44100
        
    def extract_melody_essentia(self, audio_file: str, progress_callback=None) -> Tuple[np.ndarray, np.ndarray]:
        """Extract melody using Essentia's PredominantPitchMelodia."""
        
        try:
            if progress_callback:
                progress_callback(10, "Loading audio with Essentia...")
            
            # Load audio
            loader = es.MonoLoader(filename=audio_file, sampleRate=self.sample_rate)
            audio = loader()
            
            if progress_callback:
                progress_callback(30, "Extracting predominant pitch...")
            
            # Extract predominant pitch melody
            pitch_extractor = es.PredominantPitchMelodia(
                frameSize=2048,
                hopSize=128,
                sampleRate=self.sample_rate
            )
            
            pitch_values, pitch_confidence = pitch_extractor(audio)
            
            if progress_callback:
                progress_callback(70, "Processing melody data...")
            
            # Create time array
            hop_size = 128
            times = np.arange(len(pitch_values)) * hop_size / self.sample_rate
            
            # Filter out low confidence pitches
            confidence_threshold = 0.5
            pitch_values[pitch_confidence < confidence_threshold] = 0
            
            if progress_callback:
                progress_callback(100, "Melody extraction complete!")
            
            return times, pitch_values
            
        except Exception as e:
            raise RuntimeError(f"Error in Essentia melody extraction: {str(e)}")
    
    def extract_melody_librosa(self, audio_file: str, progress_callback=None) -> Tuple[np.ndarray, np.ndarray]:
        """Extract melody using librosa's pitch tracking."""
        try:
            if progress_callback:
                progress_callback(10, "Loading audio...")
            
            # Load audio
            y, sr = librosa.load(audio_file, sr=self.sample_rate)
            
            if progress_callback:
                progress_callback(30, "Extracting pitch...")
            
            # Extract pitch using piptrack
            pitches, magnitudes = librosa.piptrack(
                y=y, 
                sr=sr,
                hop_length=512,
                fmin=80,
                fmax=2000
            )
            
            if progress_callback:
                progress_callback(70, "Processing pitch data...")
            
            # Extract the most prominent pitch at each time frame
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                pitch_values.append(pitch if pitch > 0 else 0)
            
            # Create time array
            times = np.arange(len(pitch_values)) * 512 / sr
            
            if progress_callback:
                progress_callback(100, "Melody extraction complete!")
            
            return times, np.array(pitch_values)
            
        except Exception as e:
            raise RuntimeError(f"Error in librosa melody extraction: {str(e)}")


class AdvancedMelodyAnalyzer:
    """
    Advanced melody analyzer with vocal separation and precise melody detection.
    """
    
    def __init__(self, parent: tk.Widget):
        """Initialize the advanced melody analyzer."""
        self.parent = parent
        
        # Components
        self.vocal_separator = VocalSeparator()
        self.melody_extractor = MelodyExtractor()
        
        # Audio processing parameters
        self.sample_rate = 44100
        self.hop_length = 512
        self.buffer_size = 4096
        
        # Real-time audio parameters
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.current_pitch = 0.0
        self.pitch_buffer = []
        self.buffer_max_size = 10
        
        # File analysis data
        self.original_file_path = None
        self.vocals_file_path = None
        self.accompaniment_file_path = None
        self.melody_times = []
        self.melody_pitches = []
        self.file_duration = 0.0
        
        # Audio player for real playback
        self.audio_player = None
        if AUDIO_AVAILABLE:
            self.audio_player = AudioPlayer()
        
        # Real-time singing data
        self.realtime_times = []
        self.realtime_pitches = []
        self.start_time = None
        
        # Musical note definitions
        self.setup_musical_notes()
        
        # Visualization parameters
        self.time_window = 30.0  # seconds to show
        self.piano_roll_height = 88  # Piano keys (A0 to C8)
        
        # Colors for piano roll
        self.colors = {
            'melody_line': '#2E86AB',        # Blue for extracted melody
            'realtime_pitch': '#E74C3C',     # Red for real-time singing
            'background': '#FFFFFF',         # White background
            'piano_white': '#FFFFFF',        # White piano keys
            'piano_black': '#2C3E50',        # Black piano keys
            'grid_lines': '#BDC3C7',         # Light gray for grid
            'playback_line': '#F39C12'       # Orange for playback position
        }
        
        self.setup_ui()
        
    def setup_musical_notes(self):
        """Setup musical note frequencies and MIDI mappings."""
        # MIDI note 21 = A0, MIDI note 108 = C8
        self.midi_to_freq = {}
        self.freq_to_midi = {}
        
        # A4 = 440 Hz = MIDI note 69
        A4_freq = 440.0
        A4_midi = 69
        
        for midi_note in range(21, 109):  # A0 to C8
            freq = A4_freq * (2 ** ((midi_note - A4_midi) / 12))
            self.midi_to_freq[midi_note] = freq
            self.freq_to_midi[freq] = midi_note
        
        # Note names
        self.note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
    def setup_ui(self):
        """Setup the advanced user interface."""
        # Main frame
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Advanced Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File controls
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(file_frame, text="Load Audio File", 
                  command=self.load_audio_file).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(file_frame, text="Separate Vocals", 
                  command=self.separate_vocals, state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(file_frame, text="Extract Melody", 
                  command=self.extract_melody, state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        
        self.file_label = ttk.Label(file_frame, text="No file loaded")
        self.file_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Separation method selection
        method_frame = ttk.Frame(control_frame)
        method_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(method_frame, text="Separation Method:").pack(side=tk.LEFT)
        
        self.separation_method = tk.StringVar(value="librosa")
        method_combo = ttk.Combobox(method_frame, textvariable=self.separation_method, 
                                   values=["librosa", "demucs"], state="readonly", width=10)
        method_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(method_frame, text="Melody Algorithm:").pack(side=tk.LEFT)
        
        self.melody_method = tk.StringVar(value="librosa")
        melody_combo = ttk.Combobox(method_frame, textvariable=self.melody_method,
                                   values=["librosa", "essentia"], state="readonly", width=10)
        melody_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(control_frame, text="Ready")
        self.progress_label.pack()
        
        # Audio player widget for real playback
        if self.audio_player:
            player_frame = ttk.LabelFrame(control_frame, text="Audio Playback", padding=5)
            player_frame.pack(fill=tk.X, pady=5)
            
            self.audio_player_widget = AudioPlayerWidget(player_frame)
            self.audio_player_widget.pack(fill=tk.X)
        else:
            # Fallback message
            fallback_frame = ttk.LabelFrame(control_frame, text="Audio Playback", padding=5)
            fallback_frame.pack(fill=tk.X, pady=5)
            
            fallback_label = ttk.Label(fallback_frame, 
                                     text="⚠️ Audio playback not available - missing dependencies",
                                     foreground="red")
            fallback_label.pack()
        
        # Real-time controls
        realtime_frame = ttk.Frame(control_frame)
        realtime_frame.pack(fill=tk.X, pady=5)
        
        self.listen_button = ttk.Button(realtime_frame, text="🎤 Start Recording", 
                                       command=self.toggle_listening)
        self.listen_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(realtime_frame, text="Clear Recording", 
                  command=self.clear_recording).pack(side=tk.LEFT, padx=(0, 5))
        
        self.pitch_label = ttk.Label(realtime_frame, text="Pitch: -- Hz")
        self.pitch_label.pack(side=tk.LEFT, padx=(10, 0))
        
        self.accuracy_label = ttk.Label(realtime_frame, text="Accuracy: --%")
        self.accuracy_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Visualization frame
        viz_frame = ttk.LabelFrame(main_frame, text="Piano Roll Visualization", padding=5)
        viz_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create piano roll visualization
        self.setup_piano_roll_visualization(viz_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Load an audio file to begin")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Store button references for state management
        self.separate_button = file_frame.winfo_children()[1]
        self.extract_button = file_frame.winfo_children()[2]
        
    def setup_piano_roll_visualization(self, parent_frame):
        """Setup the piano roll style visualization."""
        # Create figure and axis
        self.fig = Figure(figsize=(14, 10), dpi=100, facecolor=self.colors['background'])
        self.ax = self.fig.add_subplot(111)
        
        # Setup piano roll
        self.setup_piano_roll()
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize plot elements
        self.melody_line, = self.ax.plot([], [], color=self.colors['melody_line'], 
                                        linewidth=2, label='Extracted Melody', alpha=0.8)
        self.realtime_scatter = self.ax.scatter([], [], color=self.colors['realtime_pitch'], 
                                               s=50, label='Real-time Singing', alpha=0.8, zorder=5)
        
        # Note: Playback position tracking removed - handled by audio player widget
        
        self.ax.legend(loc='upper right')
        
    def setup_piano_roll(self):
        """Setup the piano roll background."""
        # Clear the axis
        self.ax.clear()
        
        # Set up the plot dimensions
        self.ax.set_xlim(0, self.time_window)
        self.ax.set_ylim(21, 109)  # MIDI notes A0 to C8
        
        # Draw piano key background
        for midi_note in range(21, 109):
            note_name = self.note_names[midi_note % 12]
            
            # Black keys (sharps/flats)
            if '#' in note_name or note_name in ['C#', 'D#', 'F#', 'G#', 'A#']:
                color = self.colors['piano_black']
                alpha = 0.1
            else:
                color = self.colors['piano_white']
                alpha = 0.05
            
            # Draw horizontal line for each note
            self.ax.axhline(y=midi_note, color=color, alpha=alpha, linewidth=0.5)
        
        # Draw octave separators (C notes)
        for midi_note in range(24, 109, 12):  # C notes
            self.ax.axhline(y=midi_note, color=self.colors['grid_lines'], 
                           linewidth=1, alpha=0.3)
        
        # Add note labels on the left (every octave)
        note_labels = []
        note_positions = []
        for midi_note in range(24, 109, 12):  # C notes
            octave = (midi_note - 12) // 12
            note_labels.append(f'C{octave}')
            note_positions.append(midi_note)
        
        self.ax.set_yticks(note_positions)
        self.ax.set_yticklabels(note_labels)
        
        # Labels and title
        self.ax.set_xlabel('Time (seconds)', fontsize=12)
        self.ax.set_ylabel('Musical Notes (MIDI)', fontsize=12)
        self.ax.set_title('Advanced Melody Analysis - Piano Roll View', fontsize=14, fontweight='bold')
        
        # Grid
        self.ax.grid(True, alpha=0.2)
        
    def frequency_to_midi(self, frequency: float) -> float:
        """Convert frequency to MIDI note number."""
        if frequency <= 0:
            return 0
        
        # A4 = 440 Hz = MIDI note 69
        A4_freq = 440.0
        A4_midi = 69
        
        midi_note = A4_midi + 12 * math.log2(frequency / A4_freq)
        return max(21, min(108, midi_note))  # Clamp to piano range
    
    def load_audio_file(self):
        """Load an audio file for analysis."""
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.m4a *.ogg *.aac"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("FLAC files", "*.flac"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # Store file path
            self.original_file_path = file_path
            filename = os.path.basename(file_path)
            
            # Get file duration
            y, sr = librosa.load(file_path, sr=None)
            self.file_duration = len(y) / sr
            
            # Update UI
            self.file_label.config(text=f"File: {filename}")
            self.separate_button.config(state=tk.NORMAL)
            self.position_scale.config(to=self.file_duration)
            
            self.status_var.set(f"File loaded: {filename} ({self.file_duration:.1f}s)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file:\n{str(e)}")
            self.status_var.set("Error loading file")
    
    def separate_vocals(self):
        """Separate vocals from the loaded audio file."""
        if not self.original_file_path:
            messagebox.showerror("Error", "No audio file loaded!")
            return
        
        # Run separation in separate thread
        thread = threading.Thread(target=self._separate_vocals_thread, daemon=True)
        thread.start()
    
    def _separate_vocals_thread(self):
        """Separate vocals in background thread."""
        try:
            method = self.separation_method.get()
            
            def progress_callback(percent, message):
                self.parent.after(0, lambda: self._update_progress(percent, message))
            
            if method == "demucs":
                vocals_path, accompaniment_path = self.vocal_separator.separate_vocals_demucs(
                    self.original_file_path, progress_callback
                )
            else:
                vocals_path, accompaniment_path = self.vocal_separator.separate_vocals_librosa(
                    self.original_file_path, progress_callback
                )
            
            # Store paths
            self.vocals_file_path = vocals_path
            self.accompaniment_file_path = accompaniment_path
            
            # Update UI in main thread
            self.parent.after(0, self._separation_complete)
            
        except Exception as e:
            self.parent.after(0, lambda: self._separation_error(str(e)))
    
    def _update_progress(self, percent, message):
        """Update progress bar and label."""
        self.progress_var.set(percent)
        self.progress_label.config(text=message)
        self.parent.update_idletasks()
    
    def _separation_complete(self):
        """Handle separation completion."""
        self.progress_var.set(0)
        self.progress_label.config(text="Vocal separation complete!")
        self.extract_button.config(state=tk.NORMAL)
        self.status_var.set("Vocals separated successfully - Ready for melody extraction")
    
    def _separation_error(self, error_msg):
        """Handle separation error."""
        self.progress_var.set(0)
        self.progress_label.config(text="Separation failed")
        messagebox.showerror("Error", f"Vocal separation failed:\n{error_msg}")
        self.status_var.set("Vocal separation failed")
    
    def extract_melody(self):
        """Extract melody from separated vocals."""
        if not self.vocals_file_path:
            messagebox.showerror("Error", "No separated vocals available!")
            return
        
        # Run extraction in separate thread
        thread = threading.Thread(target=self._extract_melody_thread, daemon=True)
        thread.start()
    
    def _extract_melody_thread(self):
        """Extract melody in background thread."""
        try:
            method = self.melody_method.get()
            
            def progress_callback(percent, message):
                self.parent.after(0, lambda: self._update_progress(percent, message))
            
            if method == "essentia":
                times, pitches = self.melody_extractor.extract_melody_essentia(
                    self.vocals_file_path, progress_callback
                )
            else:
                times, pitches = self.melody_extractor.extract_melody_librosa(
                    self.vocals_file_path, progress_callback
                )
            
            # Store melody data
            self.melody_times = times
            self.melody_pitches = pitches
            
            # Update UI in main thread
            self.parent.after(0, self._extraction_complete)
            
        except Exception as e:
            self.parent.after(0, lambda: self._extraction_error(str(e)))
    
    def _extraction_complete(self):
        """Handle melody extraction completion."""
        self.progress_var.set(0)
        self.progress_label.config(text="Melody extraction complete!")
        
        # Load vocals file into audio player for real playback
        if hasattr(self, 'audio_player_widget') and self.vocals_file_path:
            self.audio_player_widget.load_file(self.vocals_file_path)
        
        # Update visualization
        self.update_melody_visualization()
        
        self.status_var.set("Melody extracted successfully - Ready for playback and recording")
    
    def _extraction_error(self, error_msg):
        """Handle extraction error."""
        self.progress_var.set(0)
        self.progress_label.config(text="Extraction failed")
        messagebox.showerror("Error", f"Melody extraction failed:\n{error_msg}")
        self.status_var.set("Melody extraction failed")
    
    def update_melody_visualization(self):
        """Update the piano roll with extracted melody."""
        if not self.melody_times.size or not self.melody_pitches.size:
            return
        
        # Convert pitches to MIDI notes
        midi_notes = []
        valid_times = []
        
        for i, (time_val, pitch) in enumerate(zip(self.melody_times, self.melody_pitches)):
            if pitch > 0:  # Valid pitch
                midi_note = self.frequency_to_midi(pitch)
                if 21 <= midi_note <= 108:  # Valid piano range
                    midi_notes.append(midi_note)
                    valid_times.append(time_val)
        
        # Update the plot
        if valid_times and midi_notes:
            self.melody_line.set_data(valid_times, midi_notes)
            
            # Adjust time window if needed
            if max(valid_times) > self.time_window:
                self.ax.set_xlim(0, max(valid_times) + 5)
            
            self.canvas.draw()
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_listening()
        if hasattr(self, 'audio_player_widget'):
            self.audio_player_widget.cleanup()
        self.vocal_separator.cleanup()
    
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
            self.listen_button.config(text="🔴 Stop Recording")
            
            # Reset real-time data
            self.realtime_times = []
            self.realtime_pitches = []
            self.start_time = time.time()
            
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
            
            self.status_var.set("Recording real-time audio...")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error starting audio capture:\n{str(e)}")
            self.is_listening = False
            self.listen_button.config(text="🎤 Start Recording")
    
    def stop_listening(self):
        """Stop real-time audio capture."""
        self.is_listening = False
        
        try:
            if hasattr(self, 'listen_button') and self.listen_button.winfo_exists():
                self.listen_button.config(text="🎤 Start Recording")
            
            if hasattr(self, 'audio_stream'):
                self.audio_stream.stop()
                self.audio_stream.close()
            
            self.status_var.set("Recording stopped")
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Error stopping audio capture: {e}")
    
    def clear_recording(self):
        """Clear recorded real-time data."""
        self.realtime_times = []
        self.realtime_pitches = []
        
        # Clear visualization
        if hasattr(self, 'realtime_scatter'):
            self.realtime_scatter.set_offsets(np.empty((0, 2)))
            self.canvas.draw()
        
        self.status_var.set("Recording data cleared")
    
    def audio_callback(self, indata, frames, time, status):
        """Audio callback for real-time processing."""
        if status:
            print(f"Audio callback status: {status}")
        
        self.audio_queue.put(indata.copy())
    
    def process_realtime_audio(self):
        """Process real-time audio data."""
        while self.is_listening:
            try:
                audio_data = self.audio_queue.get(timeout=0.1)
                
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                # Detect pitch
                pitch = self.detect_pitch_autocorr(audio_data)
                
                if pitch > 0:
                    self.pitch_buffer.append(pitch)
                    if len(self.pitch_buffer) > self.buffer_max_size:
                        self.pitch_buffer.pop(0)
                    
                    if len(self.pitch_buffer) >= 3:
                        stable_pitch = np.median(self.pitch_buffer)
                        self.current_pitch = stable_pitch
                        
                        # Store real-time data
                        current_time = time.time() - self.start_time
                        self.realtime_times.append(current_time)
                        self.realtime_pitches.append(stable_pitch)
                        
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
        
        windowed = audio_data.flatten() * np.hanning(len(audio_data))
        autocorr = np.correlate(windowed, windowed, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        min_period = int(self.sample_rate / 2000)
        max_period = int(self.sample_rate / 80)
        
        if max_period >= len(autocorr):
            return 0.0
        
        search_range = autocorr[min_period:max_period]
        if len(search_range) == 0:
            return 0.0
        
        peak_index = np.argmax(search_range) + min_period
        
        if autocorr[peak_index] < 0.3 * autocorr[0]:
            return 0.0
        
        frequency = self.sample_rate / peak_index
        return frequency if 80 <= frequency <= 2000 else 0.0
    
    def update_realtime_ui(self):
        """Update UI with real-time pitch data."""
        try:
            if not hasattr(self, 'pitch_label') or not self.pitch_label.winfo_exists():
                return
            
            # Update pitch label
            self.pitch_label.config(text=f"Pitch: {self.current_pitch:.1f} Hz")
            
            # Calculate accuracy if melody is available
            if self.melody_times.size > 0 and self.realtime_times:
                accuracy = self.calculate_accuracy()
                self.accuracy_label.config(text=f"Accuracy: {accuracy:.1f}%")
            
            # Update visualization
            if self.realtime_times and self.realtime_pitches:
                # Convert to MIDI notes
                midi_notes = [self.frequency_to_midi(p) for p in self.realtime_pitches]
                valid_data = [(t, m) for t, m in zip(self.realtime_times, midi_notes) 
                             if 21 <= m <= 108]
                
                if valid_data:
                    times, notes = zip(*valid_data)
                    self.realtime_scatter.set_offsets(list(zip(times, notes)))
                    
                    # Adjust time window if needed
                    if max(times) > self.time_window:
                        self.ax.set_xlim(max(times) - self.time_window, max(times) + 5)
                    
                    self.canvas.draw_idle()
                    
        except tk.TclError:
            self.is_listening = False
        except Exception as e:
            print(f"Error updating real-time UI: {e}")
    
    def calculate_accuracy(self) -> float:
        """Calculate singing accuracy compared to extracted melody."""
        if not self.realtime_times or not self.melody_times.size:
            return 0.0
        
        try:
            # Find overlapping time range
            rt_start, rt_end = min(self.realtime_times), max(self.realtime_times)
            melody_start, melody_end = self.melody_times[0], self.melody_times[-1]
            
            overlap_start = max(rt_start, melody_start)
            overlap_end = min(rt_end, melody_end)
            
            if overlap_start >= overlap_end:
                return 0.0
            
            # Sample both signals at regular intervals
            sample_times = np.linspace(overlap_start, overlap_end, 100)
            
            # Interpolate melody pitches
            melody_interp = np.interp(sample_times, self.melody_times, self.melody_pitches)
            
            # Interpolate real-time pitches
            rt_interp = np.interp(sample_times, self.realtime_times, self.realtime_pitches)
            
            # Calculate accuracy (based on frequency difference)
            valid_indices = (melody_interp > 0) & (rt_interp > 0)
            if not np.any(valid_indices):
                return 0.0
            
            melody_valid = melody_interp[valid_indices]
            rt_valid = rt_interp[valid_indices]
            
            # Calculate percentage of notes within acceptable range (±50 cents)
            cent_differences = 1200 * np.log2(rt_valid / melody_valid)
            accurate_notes = np.abs(cent_differences) <= 50  # Within 50 cents
            
            accuracy = np.mean(accurate_notes) * 100
            return accuracy
            
        except Exception as e:
            print(f"Error calculating accuracy: {e}")
            return 0.0
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_listening()
        self.stop_playback()
        self.vocal_separator.cleanup()


def show_advanced_melody_analyzer(parent: tk.Widget):
    """Show the advanced melody analyzer window."""
    # Create new window
    window = tk.Toplevel(parent)
    window.title("Advanced Melody Analyzer")
    window.geometry("1400x900")
    window.minsize(1000, 700)
    
    # Create analyzer
    analyzer = AdvancedMelodyAnalyzer(window)
    
    # Handle window closing
    def on_closing():
        analyzer.cleanup()
        window.destroy()
    
    window.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window
    window.transient(parent)
    window.grab_set()
    
    return window
