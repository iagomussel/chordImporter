"""
Karaoke Analyzer - Complete karaoke application with vocal isolation, melody detection,
and real-time pitch comparison. Follows the step-by-step process outlined.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import queue
import subprocess
import tempfile
import shutil
from typing import Optional, List, Tuple, Dict, Any
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
import aubio
import pyaudio

# Import our audio player
from .audio_player import AudioPlayer, AudioPlayerWidget

# Verify critical dependencies are available
if not hasattr(sd, 'InputStream'):
    raise ImportError("sounddevice not properly installed")

if not hasattr(aubio, 'pitch'):
    raise ImportError("aubio not properly installed")


class VocalIsolator:
    """Handles vocal isolation using Spleeter."""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def isolate_vocals_spleeter(self, input_file: str, progress_callback=None) -> Tuple[str, str]:
        """
        Isolate vocals using Spleeter (2stems model).
        
        Args:
            input_file: Path to input audio file
            progress_callback: Callback for progress updates
            
        Returns:
            Tuple of (vocals_path, accompaniment_path)
        """
        try:
            if progress_callback:
                progress_callback(10, "Initializing Spleeter...")
            
            # Prepare Spleeter command
            output_dir = os.path.join(self.temp_dir, "spleeter_output")
            os.makedirs(output_dir, exist_ok=True)
            
            command = [
                "spleeter", "separate",
                "-i", input_file,
                "-p", "spleeter:2stems-16kHz",
                "-o", output_dir
            ]
            
            if progress_callback:
                progress_callback(30, "Running Spleeter separation...")
            
            # Run Spleeter
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            if progress_callback:
                progress_callback(80, "Processing separated tracks...")
            
            # Find the separated files
            song_name = os.path.splitext(os.path.basename(input_file))[0]
            vocals_path = os.path.join(output_dir, song_name, "vocals.wav")
            accompaniment_path = os.path.join(output_dir, song_name, "accompaniment.wav")
            
            if not os.path.exists(vocals_path) or not os.path.exists(accompaniment_path):
                raise FileNotFoundError("Spleeter output files not found")
            
            if progress_callback:
                progress_callback(100, "Vocal separation complete!")
            
            return vocals_path, accompaniment_path
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Spleeter failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Error in vocal isolation: {str(e)}")
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass


class MelodyDetector:
    """Handles melody detection using librosa.pyin."""
    
    def __init__(self):
        self.sample_rate = 44100
        
    def detect_melody_pyin(self, vocal_file: str, progress_callback=None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Detect melody using librosa.pyin algorithm.
        
        Args:
            vocal_file: Path to vocal track file
            progress_callback: Callback for progress updates
            
        Returns:
            Tuple of (notes, times, frequencies)
        """
        try:
            if progress_callback:
                progress_callback(10, "Loading vocal track...")
            
            # Load the vocal track
            y, sr = librosa.load(vocal_file, sr=self.sample_rate)
            
            if progress_callback:
                progress_callback(30, "Detecting fundamental frequency...")
            
            # Use librosa.pyin for pitch detection
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y, 
                sr=sr,
                fmin=librosa.note_to_hz('C2'),  # ~65 Hz
                fmax=librosa.note_to_hz('C7'),  # ~2093 Hz
                frame_length=2048,
                hop_length=512
            )
            
            if progress_callback:
                progress_callback(70, "Converting frequencies to notes...")
            
            # Convert frequencies to notes
            notes = librosa.hz_to_note(f0, cents=False)
            
            # Get time array
            times = librosa.times_like(f0, sr=sr, hop_length=512)
            
            # Filter out unvoiced segments
            voiced_f0 = np.where(voiced_flag, f0, np.nan)
            voiced_notes = np.where(voiced_flag, notes, None)
            
            if progress_callback:
                progress_callback(100, "Melody detection complete!")
            
            return voiced_notes, times, voiced_f0
            
        except Exception as e:
            raise RuntimeError(f"Error in melody detection: {str(e)}")


class RealtimePitchTracker:
    """Handles real-time pitch tracking using aubio."""
    
    def __init__(self):
        self.chunk_size = 1024
        self.sample_rate = 44100
        self.is_tracking = False
        self.pitch_queue = queue.Queue()
        
        # Aubio pitch detection setup
        self.tolerance = 0.8
        self.win_s = 4096
        self.hop_s = self.chunk_size
        
        self.pitch_detector = aubio.pitch("default", self.win_s, self.hop_s, self.sample_rate)
        self.pitch_detector.set_unit("Hz")
        self.pitch_detector.set_tolerance(self.tolerance)
        
        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
    def start_tracking(self, callback):
        """Start real-time pitch tracking."""
        if self.is_tracking:
            return
        
        self.is_tracking = True
        self.callback = callback
        
        try:
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self._process_pitch, daemon=True)
            self.processing_thread.start()
            
        except Exception as e:
            self.is_tracking = False
            raise RuntimeError(f"Error starting pitch tracking: {str(e)}")
    
    def stop_tracking(self):
        """Stop real-time pitch tracking."""
        self.is_tracking = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for real-time processing."""
        if status:
            print(f"Audio callback status: {status}")
        
        if self.is_tracking:
            # Convert audio data
            signal = np.frombuffer(in_data, dtype=np.float32)
            
            # Detect pitch
            pitch_hz = self.pitch_detector(signal)[0]
            
            # Put in queue for processing
            self.pitch_queue.put((time.time(), pitch_hz))
        
        return (None, pyaudio.paContinue)
    
    def _process_pitch(self):
        """Process pitch data in separate thread."""
        while self.is_tracking:
            try:
                timestamp, pitch_hz = self.pitch_queue.get(timeout=0.1)
                
                if pitch_hz > 0:  # Valid pitch detected
                    self.callback(timestamp, pitch_hz)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Pitch processing error: {e}")
                continue
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_tracking()
        if self.audio:
            self.audio.terminate()


class KaraokeAnalyzer:
    """
    Complete karaoke analyzer with vocal isolation, melody detection,
    and real-time pitch comparison.
    """
    
    def __init__(self, parent: tk.Widget):
        """Initialize the karaoke analyzer."""
        self.parent = parent
        
        # Components
        self.vocal_isolator = VocalIsolator()
        self.melody_detector = MelodyDetector()
        self.pitch_tracker = RealtimePitchTracker()
        
        # File data
        self.original_file = None
        self.vocals_file = None
        self.accompaniment_file = None
        
        # Melody data
        self.target_notes = None
        self.target_times = None
        self.target_frequencies = None
        
        # Real-time data
        self.user_pitches = []
        self.user_times = []
        self.start_time = None
        
        # Visualization parameters
        self.time_window = 30.0  # seconds
        self.note_range = (librosa.note_to_midi('C2'), librosa.note_to_midi('C7'))
        
        # Colors
        self.colors = {
            'target_melody': '#2E86AB',      # Blue for target melody
            'user_pitch': '#E74C3C',        # Red for user singing
            'background': '#FFFFFF',        # White background
            'grid': '#BDC3C7',              # Light gray for grid
            'accuracy_good': '#27AE60',     # Green for good accuracy
            'accuracy_bad': '#E74C3C'       # Red for poor accuracy
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the karaoke analyzer interface."""
        # Main frame
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Karaoke Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File controls
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(file_frame, text="Load Song", 
                  command=self.load_song).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(file_frame, text="Isolate Vocals", 
                  command=self.isolate_vocals, state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(file_frame, text="Detect Melody", 
                  command=self.detect_melody, state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        
        self.file_label = ttk.Label(file_frame, text="No song loaded")
        self.file_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(control_frame, text="Ready")
        self.progress_label.pack()
        
        # Audio playback
        player_frame = ttk.LabelFrame(control_frame, text="Audio Playback", padding=5)
        player_frame.pack(fill=tk.X, pady=5)
        
        self.audio_player_widget = AudioPlayerWidget(player_frame)
        self.audio_player_widget.pack(fill=tk.X)
        
        # Karaoke controls
        karaoke_frame = ttk.Frame(control_frame)
        karaoke_frame.pack(fill=tk.X, pady=5)
        
        self.start_karaoke_button = ttk.Button(karaoke_frame, text="🎤 Start Karaoke", 
                                              command=self.start_karaoke, state=tk.DISABLED)
        self.start_karaoke_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_karaoke_button = ttk.Button(karaoke_frame, text="⏹ Stop Karaoke", 
                                             command=self.stop_karaoke, state=tk.DISABLED)
        self.stop_karaoke_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(karaoke_frame, text="Clear Recording", 
                  command=self.clear_recording).pack(side=tk.LEFT, padx=(0, 5))
        
        # Accuracy display
        self.accuracy_label = ttk.Label(karaoke_frame, text="Accuracy: --%", 
                                       font=("Arial", 12, "bold"))
        self.accuracy_label.pack(side=tk.LEFT, padx=(20, 0))
        
        self.pitch_label = ttk.Label(karaoke_frame, text="Current Pitch: -- Hz")
        self.pitch_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Visualization frame
        viz_frame = ttk.LabelFrame(main_frame, text="Karaoke Visualization", padding=5)
        viz_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create matplotlib visualization
        self.setup_visualization(viz_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Load a song to begin karaoke")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Store button references
        self.isolate_button = file_frame.winfo_children()[1]
        self.detect_button = file_frame.winfo_children()[2]
        
    def setup_visualization(self, parent_frame):
        """Setup the karaoke visualization."""
        # Create figure and axis
        self.fig = Figure(figsize=(14, 8), dpi=100, facecolor=self.colors['background'])
        self.ax = self.fig.add_subplot(111)
        
        # Setup the plot
        self.setup_karaoke_plot()
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize plot elements
        self.target_line, = self.ax.plot([], [], color=self.colors['target_melody'], 
                                        linewidth=3, label='Target Melody', alpha=0.8)
        self.user_scatter = self.ax.scatter([], [], color=self.colors['user_pitch'], 
                                           s=60, label='Your Singing', alpha=0.8, zorder=5)
        
        self.ax.legend(loc='upper right')
        
    def setup_karaoke_plot(self):
        """Setup the karaoke plot background."""
        # Clear the axis
        self.ax.clear()
        
        # Set up the plot dimensions
        self.ax.set_xlim(0, self.time_window)
        self.ax.set_ylim(self.note_range[0], self.note_range[1])
        
        # Draw note grid lines
        for midi_note in range(self.note_range[0], self.note_range[1] + 1, 12):  # Every octave
            self.ax.axhline(y=midi_note, color=self.colors['grid'], 
                           linewidth=1, alpha=0.3)
        
        # Add note labels
        note_labels = []
        note_positions = []
        for midi_note in range(self.note_range[0], self.note_range[1] + 1, 12):
            note_name = librosa.midi_to_note(midi_note)
            note_labels.append(note_name)
            note_positions.append(midi_note)
        
        self.ax.set_yticks(note_positions)
        self.ax.set_yticklabels(note_labels)
        
        # Labels and title
        self.ax.set_xlabel('Time (seconds)', fontsize=12)
        self.ax.set_ylabel('Musical Notes', fontsize=12)
        self.ax.set_title('Karaoke - Sing Along with the Melody!', fontsize=14, fontweight='bold')
        
        # Grid
        self.ax.grid(True, alpha=0.2)
        
    def load_song(self):
        """Load a song file for karaoke."""
        file_path = filedialog.askopenfilename(
            title="Select Song File",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.m4a *.ogg"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            self.original_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"Song: {filename}")
            
            # Enable next step
            self.isolate_button.config(state=tk.NORMAL)
            
            self.status_var.set(f"Song loaded: {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading song:\n{str(e)}")
            self.status_var.set("Error loading song")
    
    def isolate_vocals(self):
        """Isolate vocals using Spleeter."""
        if not self.original_file:
            messagebox.showerror("Error", "No song loaded!")
            return
        
        # Run isolation in separate thread
        thread = threading.Thread(target=self._isolate_vocals_thread, daemon=True)
        thread.start()
    
    def _isolate_vocals_thread(self):
        """Isolate vocals in background thread."""
        try:
            def progress_callback(percent, message):
                self.parent.after(0, lambda: self._update_progress(percent, message))
            
            vocals_path, accompaniment_path = self.vocal_isolator.isolate_vocals_spleeter(
                self.original_file, progress_callback
            )
            
            self.vocals_file = vocals_path
            self.accompaniment_file = accompaniment_path
            
            # Update UI in main thread
            self.parent.after(0, self._isolation_complete)
            
        except Exception as e:
            self.parent.after(0, lambda: self._isolation_error(str(e)))
    
    def _isolation_complete(self):
        """Handle vocal isolation completion."""
        self.progress_var.set(0)
        self.progress_label.config(text="Vocal isolation complete!")
        self.detect_button.config(state=tk.NORMAL)
        self.status_var.set("Vocals isolated - Ready for melody detection")
    
    def _isolation_error(self, error_msg):
        """Handle isolation error."""
        self.progress_var.set(0)
        self.progress_label.config(text="Isolation failed")
        messagebox.showerror("Error", f"Vocal isolation failed:\n{error_msg}")
        self.status_var.set("Vocal isolation failed")
    
    def detect_melody(self):
        """Detect melody from isolated vocals."""
        if not self.vocals_file:
            messagebox.showerror("Error", "No isolated vocals available!")
            return
        
        # Run detection in separate thread
        thread = threading.Thread(target=self._detect_melody_thread, daemon=True)
        thread.start()
    
    def _detect_melody_thread(self):
        """Detect melody in background thread."""
        try:
            def progress_callback(percent, message):
                self.parent.after(0, lambda: self._update_progress(percent, message))
            
            notes, times, frequencies = self.melody_detector.detect_melody_pyin(
                self.vocals_file, progress_callback
            )
            
            self.target_notes = notes
            self.target_times = times
            self.target_frequencies = frequencies
            
            # Update UI in main thread
            self.parent.after(0, self._detection_complete)
            
        except Exception as e:
            self.parent.after(0, lambda: self._detection_error(str(e)))
    
    def _detection_complete(self):
        """Handle melody detection completion."""
        self.progress_var.set(0)
        self.progress_label.config(text="Melody detection complete!")
        
        # Load accompaniment for playback
        if self.accompaniment_file:
            self.audio_player_widget.load_file(self.accompaniment_file)
        
        # Enable karaoke
        self.start_karaoke_button.config(state=tk.NORMAL)
        
        # Update visualization
        self.update_target_melody_visualization()
        
        self.status_var.set("Melody detected - Ready for karaoke!")
    
    def _detection_error(self, error_msg):
        """Handle detection error."""
        self.progress_var.set(0)
        self.progress_label.config(text="Detection failed")
        messagebox.showerror("Error", f"Melody detection failed:\n{error_msg}")
        self.status_var.set("Melody detection failed")
    
    def update_target_melody_visualization(self):
        """Update visualization with target melody."""
        if self.target_notes is None or self.target_times is None:
            return
        
        # Convert notes to MIDI numbers for plotting
        midi_notes = []
        valid_times = []
        
        for i, (note, time_val) in enumerate(zip(self.target_notes, self.target_times)):
            if note is not None:
                try:
                    midi_note = librosa.note_to_midi(note)
                    if self.note_range[0] <= midi_note <= self.note_range[1]:
                        midi_notes.append(midi_note)
                        valid_times.append(time_val)
                except:
                    continue
        
        # Update the plot
        if valid_times and midi_notes:
            self.target_line.set_data(valid_times, midi_notes)
            
            # Adjust time window if needed
            if max(valid_times) > self.time_window:
                self.ax.set_xlim(0, max(valid_times) + 5)
            
            self.canvas.draw()
    
    def start_karaoke(self):
        """Start karaoke mode with real-time pitch tracking."""
        if not self.target_notes is not None:
            messagebox.showerror("Error", "No melody detected!")
            return
        
        try:
            # Clear previous recording
            self.user_pitches = []
            self.user_times = []
            self.start_time = time.time()
            
            # Start pitch tracking
            self.pitch_tracker.start_tracking(self._on_pitch_detected)
            
            # Update UI
            self.start_karaoke_button.config(state=tk.DISABLED)
            self.stop_karaoke_button.config(state=tk.NORMAL)
            
            self.status_var.set("🎤 Karaoke active - Start singing!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error starting karaoke:\n{str(e)}")
    
    def stop_karaoke(self):
        """Stop karaoke mode."""
        self.pitch_tracker.stop_tracking()
        
        # Update UI
        self.start_karaoke_button.config(state=tk.NORMAL)
        self.stop_karaoke_button.config(state=tk.DISABLED)
        
        self.status_var.set("Karaoke stopped")
    
    def clear_recording(self):
        """Clear recorded user data."""
        self.user_pitches = []
        self.user_times = []
        
        # Clear visualization
        if hasattr(self, 'user_scatter'):
            self.user_scatter.set_offsets(np.empty((0, 2)))
            self.canvas.draw()
        
        self.accuracy_label.config(text="Accuracy: --%")
        self.pitch_label.config(text="Current Pitch: -- Hz")
        
        self.status_var.set("Recording cleared")
    
    def _on_pitch_detected(self, timestamp, pitch_hz):
        """Handle detected pitch from real-time tracking."""
        if pitch_hz > 0:
            # Calculate relative time
            relative_time = timestamp - self.start_time
            
            # Store user data
            self.user_pitches.append(pitch_hz)
            self.user_times.append(relative_time)
            
            # Update UI in main thread
            self.parent.after(0, lambda: self._update_karaoke_ui(pitch_hz, relative_time))
    
    def _update_karaoke_ui(self, pitch_hz, relative_time):
        """Update karaoke UI with real-time data."""
        try:
            # Update pitch display
            self.pitch_label.config(text=f"Current Pitch: {pitch_hz:.1f} Hz")
            
            # Calculate accuracy
            if len(self.user_pitches) > 0:
                accuracy = self._calculate_accuracy()
                self.accuracy_label.config(text=f"Accuracy: {accuracy:.1f}%")
                
                # Color code accuracy
                if accuracy >= 80:
                    self.accuracy_label.config(foreground=self.colors['accuracy_good'])
                else:
                    self.accuracy_label.config(foreground=self.colors['accuracy_bad'])
            
            # Update visualization
            if self.user_times and self.user_pitches:
                # Convert pitches to MIDI notes
                midi_notes = []
                valid_times = []
                
                for time_val, pitch in zip(self.user_times, self.user_pitches):
                    try:
                        midi_note = librosa.hz_to_midi(pitch)
                        if self.note_range[0] <= midi_note <= self.note_range[1]:
                            midi_notes.append(midi_note)
                            valid_times.append(time_val)
                    except:
                        continue
                
                if valid_times and midi_notes:
                    self.user_scatter.set_offsets(list(zip(valid_times, midi_notes)))
                    
                    # Adjust time window if needed
                    if max(valid_times) > self.time_window:
                        self.ax.set_xlim(max(valid_times) - self.time_window, max(valid_times) + 2)
                    
                    self.canvas.draw_idle()
                    
        except Exception as e:
            print(f"Error updating karaoke UI: {e}")
    
    def _calculate_accuracy(self) -> float:
        """Calculate singing accuracy compared to target melody."""
        if not self.user_times or not self.target_times.size:
            return 0.0
        
        try:
            # Find overlapping time range
            user_start, user_end = min(self.user_times), max(self.user_times)
            target_start, target_end = self.target_times[0], self.target_times[-1]
            
            overlap_start = max(user_start, target_start)
            overlap_end = min(user_end, target_end)
            
            if overlap_start >= overlap_end:
                return 0.0
            
            # Sample both signals at regular intervals
            sample_times = np.linspace(overlap_start, overlap_end, 50)
            
            # Interpolate target frequencies
            target_freqs = np.interp(sample_times, self.target_times, 
                                   np.nan_to_num(self.target_frequencies, nan=0))
            
            # Interpolate user frequencies
            user_freqs = np.interp(sample_times, self.user_times, self.user_pitches)
            
            # Calculate accuracy (based on frequency difference)
            valid_indices = (target_freqs > 0) & (user_freqs > 0)
            if not np.any(valid_indices):
                return 0.0
            
            target_valid = target_freqs[valid_indices]
            user_valid = user_freqs[valid_indices]
            
            # Calculate percentage of notes within acceptable range (±100 cents)
            cent_differences = 1200 * np.log2(user_valid / target_valid)
            accurate_notes = np.abs(cent_differences) <= 100  # Within 100 cents
            
            accuracy = np.mean(accurate_notes) * 100
            return accuracy
            
        except Exception as e:
            print(f"Error calculating accuracy: {e}")
            return 0.0
    
    def _update_progress(self, percent, message):
        """Update progress bar and label."""
        self.progress_var.set(percent)
        self.progress_label.config(text=message)
        self.parent.update_idletasks()
    
    def cleanup(self):
        """Clean up resources."""
        self.pitch_tracker.cleanup()
        self.vocal_isolator.cleanup()
        if hasattr(self, 'audio_player_widget'):
            self.audio_player_widget.cleanup()


def show_karaoke_analyzer(parent: tk.Widget):
    """Show the karaoke analyzer window."""
    # Create new window
    window = tk.Toplevel(parent)
    window.title("🎤 Karaoke Analyzer")
    window.geometry("1400x900")
    window.minsize(1000, 700)
    
    # Create analyzer
    analyzer = KaraokeAnalyzer(window)
    
    # Handle window closing
    def on_closing():
        analyzer.cleanup()
        window.destroy()
    
    window.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window
    window.transient(parent)
    window.grab_set()
    
    return window
