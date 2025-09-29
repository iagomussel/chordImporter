"""
Chord Identifier Module
Real-time and file-based chord recognition using audio analysis.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Tuple, Any, Callable
import threading
import time
import numpy as np
from dataclasses import dataclass
from enum import Enum
import queue
import json

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from .database import get_database
    from .settings import get_settings
except ImportError:
    from chord_importer.database import get_database
    from chord_importer.settings import get_settings


class AnalysisMode(Enum):
    """Analysis mode types."""
    REAL_TIME = "real_time"
    FILE_ANALYSIS = "file_analysis"
    BATCH_PROCESSING = "batch_processing"


@dataclass
class ChordDetection:
    """Result of chord detection."""
    timestamp: float
    chord_name: str
    confidence: float
    root_note: str
    chord_type: str
    bass_note: Optional[str] = None
    notes: Optional[List[str]] = None


@dataclass
class AudioAnalysisResult:
    """Complete audio analysis result."""
    file_path: Optional[str]
    duration: float
    sample_rate: int
    detected_chords: List[ChordDetection]
    key_signature: Optional[str] = None
    tempo: Optional[float] = None
    time_signature: Optional[str] = None


class ChordRecognitionEngine:
    """Core engine for chord recognition using audio analysis."""
    
    # Chromatic scale for chord mapping
    CHROMATIC_SCALE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Chord templates (simplified)
    CHORD_TEMPLATES = {
        'major': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
        'minor': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
        'diminished': [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
        'augmented': [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        'major7': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        'minor7': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
        'dominant7': [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        'suspended2': [1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        'suspended4': [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0]
    }
    
    def __init__(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.n_fft = 2048
        self.frame_size = 4096
        
    def analyze_audio_file(self, file_path: str, progress_callback: Optional[Callable] = None) -> AudioAnalysisResult:
        """Analyze an audio file for chord progressions."""
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("librosa library is required for audio analysis")
        
        try:
            # Load audio file
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            duration = len(y) / sr
            
            # Extract features
            chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=self.hop_length)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            # Detect chords
            detected_chords = self._detect_chords_from_chroma(chroma, sr)
            
            # Estimate key
            key_signature = self._estimate_key(chroma)
            
            # Update progress
            if progress_callback:
                progress_callback(100)
            
            return AudioAnalysisResult(
                file_path=file_path,
                duration=duration,
                sample_rate=sr,
                detected_chords=detected_chords,
                key_signature=key_signature,
                tempo=float(tempo),
                time_signature="4/4"  # Simplified
            )
            
        except Exception as e:
            raise RuntimeError(f"Error analyzing audio file: {str(e)}")
    
    def analyze_real_time_audio(self, audio_data: np.ndarray) -> Optional[ChordDetection]:
        """Analyze real-time audio data for chord detection."""
        if not LIBROSA_AVAILABLE:
            return None
        
        try:
            if len(audio_data) < self.frame_size:
                return None
            
            # Extract chroma features
            chroma = librosa.feature.chroma_stft(
                y=audio_data, 
                sr=self.sample_rate, 
                hop_length=self.hop_length
            )
            
            # Average chroma across time
            avg_chroma = np.mean(chroma, axis=1)
            
            # Detect chord
            chord_name, confidence = self._match_chord_template(avg_chroma)
            
            if confidence > 0.6:  # Confidence threshold
                return ChordDetection(
                    timestamp=time.time(),
                    chord_name=chord_name,
                    confidence=confidence,
                    root_note=chord_name[0] if chord_name else 'C',
                    chord_type=chord_name[1:] if len(chord_name) > 1 else 'major'
                )
            
            return None
            
        except Exception as e:
            print(f"Error in real-time analysis: {e}")
            return None
    
    def _detect_chords_from_chroma(self, chroma: np.ndarray, sr: int) -> List[ChordDetection]:
        """Detect chords from chromagram."""
        detected_chords = []
        
        # Analyze in segments
        segment_length = int(2 * sr / self.hop_length)  # 2-second segments
        
        for i in range(0, chroma.shape[1], segment_length):
            segment = chroma[:, i:i+segment_length]
            if segment.shape[1] == 0:
                continue
            
            # Average chroma for this segment
            avg_chroma = np.mean(segment, axis=1)
            
            # Match to chord template
            chord_name, confidence = self._match_chord_template(avg_chroma)
            
            if confidence > 0.5:  # Lower threshold for file analysis
                timestamp = i * self.hop_length / sr
                detected_chords.append(ChordDetection(
                    timestamp=timestamp,
                    chord_name=chord_name,
                    confidence=confidence,
                    root_note=chord_name[0] if chord_name else 'C',
                    chord_type=chord_name[1:] if len(chord_name) > 1 else 'major'
                ))
        
        return detected_chords
    
    def _match_chord_template(self, chroma: np.ndarray) -> Tuple[str, float]:
        """Match chroma vector to chord templates."""
        best_chord = "C"
        best_confidence = 0.0
        
        # Normalize chroma
        chroma_norm = chroma / (np.sum(chroma) + 1e-8)
        
        # Try all root notes and chord types
        for root_idx, root_note in enumerate(self.CHROMATIC_SCALE):
            for chord_type, template in self.CHORD_TEMPLATES.items():
                # Rotate template to match root note
                rotated_template = np.roll(template, root_idx)
                template_norm = np.array(rotated_template) / np.sum(rotated_template)
                
                # Calculate correlation
                correlation = np.corrcoef(chroma_norm, template_norm)[0, 1]
                
                if not np.isnan(correlation) and correlation > best_confidence:
                    best_confidence = correlation
                    chord_suffix = "" if chord_type == "major" else self._get_chord_suffix(chord_type)
                    best_chord = root_note + chord_suffix
        
        return best_chord, best_confidence
    
    def _get_chord_suffix(self, chord_type: str) -> str:
        """Get chord suffix for chord type."""
        suffix_map = {
            'minor': 'm',
            'diminished': 'dim',
            'augmented': 'aug',
            'major7': 'maj7',
            'minor7': 'm7',
            'dominant7': '7',
            'suspended2': 'sus2',
            'suspended4': 'sus4'
        }
        return suffix_map.get(chord_type, '')
    
    def _estimate_key(self, chroma: np.ndarray) -> str:
        """Estimate the key signature from chromagram."""
        # Average chroma across time
        avg_chroma = np.mean(chroma, axis=1)
        
        # Key profiles (Krumhansl-Schmuckler)
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        best_key = "C"
        best_correlation = -1
        
        # Test all keys
        for i, root_note in enumerate(self.CHROMATIC_SCALE):
            # Major key
            rotated_major = np.roll(major_profile, i)
            correlation = np.corrcoef(avg_chroma, rotated_major)[0, 1]
            if not np.isnan(correlation) and correlation > best_correlation:
                best_correlation = correlation
                best_key = root_note
            
            # Minor key
            rotated_minor = np.roll(minor_profile, i)
            correlation = np.corrcoef(avg_chroma, rotated_minor)[0, 1]
            if not np.isnan(correlation) and correlation > best_correlation:
                best_correlation = correlation
                best_key = root_note + "m"
        
        return best_key


class AudioInputManager:
    """Manages real-time audio input for chord recognition."""
    
    def __init__(self):
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.pyaudio_instance = None
        
        # Audio parameters
        self.sample_rate = 22050
        self.chunk_size = 1024
        self.channels = 1
        self.format = None
        
        if PYAUDIO_AVAILABLE:
            self.format = pyaudio.paFloat32
    
    def start_recording(self, callback: Callable[[np.ndarray], None]):
        """Start real-time audio recording."""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio is required for real-time recording")
        
        self.is_recording = True
        self.callback = callback
        
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            self.stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            
        except Exception as e:
            self.is_recording = False
            raise RuntimeError(f"Error starting audio recording: {str(e)}")
    
    def stop_recording(self):
        """Stop real-time audio recording."""
        self.is_recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for processing audio data."""
        if self.is_recording:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # Call the processing callback
            if hasattr(self, 'callback'):
                self.callback(audio_data)
        
        return (in_data, pyaudio.paContinue)


class ChordIdentifierWindow:
    """Main window for the Chord Identifier."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.db = get_database()
        self.settings = get_settings()
        
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("Chord Identifier - Musical Tools Suite")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)
        
        # Initialize components
        self.recognition_engine = ChordRecognitionEngine()
        self.audio_manager = AudioInputManager()
        
        # State variables
        self.is_recording = False
        self.current_analysis = None
        self.audio_buffer = []
        self.buffer_size = 4096
        
        self.setup_ui()
        self.center_window()
    
    def center_window(self):
        """Center the window on screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Setup the user interface."""
        # Create notebook for different modes
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_real_time_tab()
        self.create_file_analysis_tab()
        self.create_batch_processing_tab()
        self.create_results_tab()
    
    def create_real_time_tab(self):
        """Create the real-time chord recognition tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Real-Time Recognition")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control section
        control_frame = tk.LabelFrame(main_frame, text="Recording Controls", font=("Arial", 12, "bold"))
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Recording controls
        record_controls = tk.Frame(control_frame)
        record_controls.pack(fill=tk.X, padx=10, pady=10)
        
        self.record_btn = tk.Button(
            record_controls, 
            text="Start Recording", 
            command=self.toggle_recording,
            bg="#4CAF50", 
            fg="white", 
            font=("Arial", 12, "bold"),
            width=15
        )
        self.record_btn.pack(side=tk.LEFT)
        
        self.clear_btn = tk.Button(
            record_controls, 
            text="Clear Results", 
            command=self.clear_real_time_results,
            bg="#f44336", 
            fg="white", 
            font=("Arial", 10, "bold")
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status indicator
        self.status_indicator = tk.Label(
            record_controls, 
            text="●", 
            font=("Arial", 20), 
            fg="#666666"
        )
        self.status_indicator.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.status_label = tk.Label(
            record_controls, 
            text="Ready", 
            font=("Arial", 12)
        )
        self.status_label.pack(side=tk.RIGHT)
        
        # Settings
        settings_frame = tk.Frame(control_frame)
        settings_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(settings_frame, text="Sensitivity:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.sensitivity_var = tk.DoubleVar(value=0.6)
        sensitivity_scale = tk.Scale(
            settings_frame, 
            from_=0.3, 
            to=0.9, 
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.sensitivity_var,
            length=200
        )
        sensitivity_scale.pack(side=tk.LEFT, padx=(10, 0))
        
        # Current chord display
        current_frame = tk.LabelFrame(main_frame, text="Current Chord", font=("Arial", 12, "bold"))
        current_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.current_chord_label = tk.Label(
            current_frame, 
            text="No chord detected", 
            font=("Arial", 24, "bold"),
            fg="#333333"
        )
        self.current_chord_label.pack(pady=20)
        
        # Confidence meter
        confidence_frame = tk.Frame(current_frame)
        confidence_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(confidence_frame, text="Confidence:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.confidence_var = tk.DoubleVar()
        self.confidence_meter = ttk.Progressbar(
            confidence_frame, 
            variable=self.confidence_var, 
            maximum=1.0,
            length=300
        )
        self.confidence_meter.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        self.confidence_label = tk.Label(confidence_frame, text="0%", font=("Arial", 10))
        self.confidence_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Real-time results
        results_frame = tk.LabelFrame(main_frame, text="Detected Chords", font=("Arial", 12, "bold"))
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Results treeview
        columns = ("Time", "Chord", "Confidence", "Notes")
        self.realtime_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.realtime_tree.heading(col, text=col)
            self.realtime_tree.column(col, width=100)
        
        realtime_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.realtime_tree.yview)
        self.realtime_tree.configure(yscrollcommand=realtime_scroll.set)
        
        self.realtime_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        realtime_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Export button
        export_frame = tk.Frame(results_frame)
        export_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Button(
            export_frame, 
            text="Export Results", 
            command=self.export_realtime_results,
            bg="#2196F3", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.RIGHT)
    
    def create_file_analysis_tab(self):
        """Create the file analysis tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="File Analysis")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File selection
        file_frame = tk.LabelFrame(main_frame, text="Audio File Selection", font=("Arial", 12, "bold"))
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_controls = tk.Frame(file_frame)
        file_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(file_controls, text="File:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.file_path_var = tk.StringVar()
        file_entry = tk.Entry(file_controls, textvariable=self.file_path_var, font=("Arial", 10))
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        tk.Button(
            file_controls, 
            text="Browse", 
            command=self.browse_audio_file,
            bg="#2196F3", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Analysis controls
        analysis_controls = tk.Frame(file_frame)
        analysis_controls.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.analyze_btn = tk.Button(
            analysis_controls, 
            text="Analyze File", 
            command=self.analyze_audio_file,
            bg="#4CAF50", 
            fg="white", 
            font=("Arial", 12, "bold")
        )
        self.analyze_btn.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            analysis_controls, 
            variable=self.progress_var, 
            maximum=100,
            length=300
        )
        self.progress_bar.pack(side=tk.LEFT, padx=(20, 0), fill=tk.X, expand=True)
        
        # Analysis results
        analysis_frame = tk.LabelFrame(main_frame, text="Analysis Results", font=("Arial", 12, "bold"))
        analysis_frame.pack(fill=tk.BOTH, expand=True)
        
        # File info
        info_frame = tk.Frame(analysis_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.file_info_label = tk.Label(info_frame, text="No file analyzed", font=("Arial", 10))
        self.file_info_label.pack(anchor=tk.W)
        
        # Results treeview
        columns = ("Start Time", "End Time", "Chord", "Confidence")
        self.analysis_tree = ttk.Treeview(analysis_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.analysis_tree.heading(col, text=col)
            self.analysis_tree.column(col, width=120)
        
        analysis_scroll = ttk.Scrollbar(analysis_frame, orient=tk.VERTICAL, command=self.analysis_tree.yview)
        self.analysis_tree.configure(yscrollcommand=analysis_scroll.set)
        
        self.analysis_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        analysis_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))
        
        # Export controls
        export_controls = tk.Frame(analysis_frame)
        export_controls.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Button(
            export_controls, 
            text="Export to ChordPro", 
            command=self.export_to_chordpro,
            bg="#FF9800", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT)
        
        tk.Button(
            export_controls, 
            text="Save to Library", 
            command=self.save_analysis_to_library,
            bg="#4CAF50", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(
            export_controls, 
            text="Export JSON", 
            command=self.export_analysis_json,
            bg="#2196F3", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.RIGHT)
    
    def create_batch_processing_tab(self):
        """Create the batch processing tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Batch Processing")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File list
        files_frame = tk.LabelFrame(main_frame, text="Audio Files", font=("Arial", 12, "bold"))
        files_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # File controls
        file_controls = tk.Frame(files_frame)
        file_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            file_controls, 
            text="Add Files", 
            command=self.add_batch_files,
            bg="#4CAF50", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT)
        
        tk.Button(
            file_controls, 
            text="Remove Selected", 
            command=self.remove_batch_files,
            bg="#f44336", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(
            file_controls, 
            text="Clear All", 
            command=self.clear_batch_files,
            bg="#FF9800", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # File list
        self.batch_listbox = tk.Listbox(files_frame, height=8, font=("Arial", 10))
        batch_scroll = tk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.batch_listbox.yview)
        self.batch_listbox.configure(yscrollcommand=batch_scroll.set)
        
        self.batch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        batch_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))
        
        # Processing controls
        process_frame = tk.LabelFrame(main_frame, text="Batch Processing", font=("Arial", 12, "bold"))
        process_frame.pack(fill=tk.X)
        
        process_controls = tk.Frame(process_frame)
        process_controls.pack(fill=tk.X, padx=10, pady=10)
        
        self.batch_process_btn = tk.Button(
            process_controls, 
            text="Start Batch Processing", 
            command=self.start_batch_processing,
            bg="#4CAF50", 
            fg="white", 
            font=("Arial", 12, "bold")
        )
        self.batch_process_btn.pack(side=tk.LEFT)
        
        # Batch progress
        self.batch_progress_var = tk.DoubleVar()
        self.batch_progress_bar = ttk.Progressbar(
            process_controls, 
            variable=self.batch_progress_var, 
            maximum=100,
            length=300
        )
        self.batch_progress_bar.pack(side=tk.LEFT, padx=(20, 0), fill=tk.X, expand=True)
        
        self.batch_status_label = tk.Label(process_controls, text="Ready", font=("Arial", 10))
        self.batch_status_label.pack(side=tk.RIGHT, padx=(10, 0))
    
    def create_results_tab(self):
        """Create the results and history tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Results & History")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # History controls
        history_controls = tk.Frame(main_frame)
        history_controls.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(history_controls, text="Analysis History:", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        tk.Button(
            history_controls, 
            text="Refresh", 
            command=self.load_analysis_history,
            bg="#2196F3", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.RIGHT)
        
        tk.Button(
            history_controls, 
            text="Clear History", 
            command=self.clear_analysis_history,
            bg="#f44336", 
            fg="white", 
            font=("Arial", 10, "bold")
        ).pack(side=tk.RIGHT, padx=(0, 10))
        
        # History treeview
        columns = ("Date", "File", "Duration", "Chords Found", "Key", "Tempo")
        self.history_tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=120)
        
        history_scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to view details
        self.history_tree.bind("<Double-Button-1>", self.view_analysis_details)
        
        # Load initial history
        self.load_analysis_history()
    
    # Event handlers and methods
    
    def toggle_recording(self):
        """Toggle real-time recording."""
        if not self.is_recording:
            self.start_real_time_recording()
        else:
            self.stop_real_time_recording()
    
    def start_real_time_recording(self):
        """Start real-time chord recognition."""
        if not PYAUDIO_AVAILABLE:
            messagebox.showerror("Error", "PyAudio is required for real-time recording.")
            return
        
        try:
            self.is_recording = True
            self.audio_buffer = []
            
            # Update UI
            self.record_btn.config(text="Stop Recording", bg="#f44336")
            self.status_label.config(text="Recording...")
            self.status_indicator.config(fg="#ff0000")
            
            # Start audio input
            self.audio_manager.start_recording(self.process_audio_chunk)
            
            # Start processing timer
            self.process_timer()
            
        except Exception as e:
            self.is_recording = False
            self.record_btn.config(text="Start Recording", bg="#4CAF50")
            self.status_label.config(text="Error")
            self.status_indicator.config(fg="#666666")
            messagebox.showerror("Error", f"Error starting recording: {str(e)}")
    
    def stop_real_time_recording(self):
        """Stop real-time chord recognition."""
        self.is_recording = False
        
        # Stop audio input
        self.audio_manager.stop_recording()
        
        # Update UI
        self.record_btn.config(text="Start Recording", bg="#4CAF50")
        self.status_label.config(text="Ready")
        self.status_indicator.config(fg="#666666")
        self.current_chord_label.config(text="No chord detected")
        self.confidence_var.set(0)
        self.confidence_label.config(text="0%")
    
    def process_audio_chunk(self, audio_data: np.ndarray):
        """Process incoming audio chunk."""
        if self.is_recording:
            self.audio_buffer.extend(audio_data)
            
            # Keep buffer size manageable
            if len(self.audio_buffer) > self.buffer_size * 2:
                self.audio_buffer = self.audio_buffer[-self.buffer_size:]
    
    def process_timer(self):
        """Timer for processing audio buffer."""
        if not self.is_recording:
            return
        
        if len(self.audio_buffer) >= self.buffer_size:
            # Process audio buffer
            audio_array = np.array(self.audio_buffer[-self.buffer_size:])
            detection = self.recognition_engine.analyze_real_time_audio(audio_array)
            
            if detection and detection.confidence >= self.sensitivity_var.get():
                # Update current chord display
                self.current_chord_label.config(text=detection.chord_name)
                self.confidence_var.set(detection.confidence)
                self.confidence_label.config(text=f"{detection.confidence:.1%}")
                
                # Add to results
                timestamp = time.strftime("%H:%M:%S")
                self.realtime_tree.insert("", 0, values=(
                    timestamp,
                    detection.chord_name,
                    f"{detection.confidence:.1%}",
                    detection.notes or ""
                ))
        
        # Schedule next processing
        if self.is_recording:
            self.window.after(500, self.process_timer)  # Process every 500ms
    
    def clear_real_time_results(self):
        """Clear real-time results."""
        for item in self.realtime_tree.get_children():
            self.realtime_tree.delete(item)
        self.current_chord_label.config(text="No chord detected")
        self.confidence_var.set(0)
        self.confidence_label.config(text="0%")
    
    def browse_audio_file(self):
        """Browse for audio file."""
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.aac *.ogg"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.file_path_var.set(file_path)
    
    def analyze_audio_file(self):
        """Analyze the selected audio file."""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("Warning", "Please select an audio file.")
            return
        
        if not LIBROSA_AVAILABLE:
            messagebox.showerror("Error", "librosa library is required for file analysis.")
            return
        
        # Start analysis in thread
        self.analyze_btn.config(state=tk.DISABLED, text="Analyzing...")
        self.progress_var.set(0)
        
        def analyze_thread():
            try:
                def progress_callback(progress):
                    self.progress_var.set(progress)
                
                result = self.recognition_engine.analyze_audio_file(file_path, progress_callback)
                
                # Update UI in main thread
                self.window.after(0, lambda: self.display_analysis_result(result))
                
            except Exception as e:
                self.window.after(0, lambda: self.handle_analysis_error(str(e)))
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def display_analysis_result(self, result: AudioAnalysisResult):
        """Display analysis result in UI."""
        # Update file info
        info_text = f"File: {result.file_path}\n"
        info_text += f"Duration: {result.duration:.1f}s, "
        info_text += f"Sample Rate: {result.sample_rate}Hz\n"
        info_text += f"Key: {result.key_signature or 'Unknown'}, "
        info_text += f"Tempo: {result.tempo:.0f} BPM" if result.tempo else "Tempo: Unknown"
        
        self.file_info_label.config(text=info_text)
        
        # Clear previous results
        for item in self.analysis_tree.get_children():
            self.analysis_tree.delete(item)
        
        # Add chord detections
        for i, detection in enumerate(result.detected_chords):
            # Calculate end time (next detection or file end)
            if i < len(result.detected_chords) - 1:
                end_time = result.detected_chords[i + 1].timestamp
            else:
                end_time = result.duration
            
            self.analysis_tree.insert("", tk.END, values=(
                f"{detection.timestamp:.1f}s",
                f"{end_time:.1f}s",
                detection.chord_name,
                f"{detection.confidence:.1%}"
            ))
        
        # Store result for export
        self.current_analysis = result
        
        # Reset UI
        self.analyze_btn.config(state=tk.NORMAL, text="Analyze File")
        self.progress_var.set(100)
        
        # Save to history
        self.save_analysis_to_history(result)
    
    def handle_analysis_error(self, error_message: str):
        """Handle analysis error."""
        self.analyze_btn.config(state=tk.NORMAL, text="Analyze File")
        self.progress_var.set(0)
        messagebox.showerror("Analysis Error", f"Error analyzing file: {error_message}")
    
    def export_realtime_results(self):
        """Export real-time results."""
        if not self.realtime_tree.get_children():
            messagebox.showwarning("Warning", "No results to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Real-time Results",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                results = []
                for item in self.realtime_tree.get_children():
                    values = self.realtime_tree.item(item)['values']
                    results.append({
                        'time': values[0],
                        'chord': values[1],
                        'confidence': values[2],
                        'notes': values[3]
                    })
                
                if file_path.endswith('.json'):
                    with open(file_path, 'w') as f:
                        json.dump(results, f, indent=2)
                else:
                    with open(file_path, 'w') as f:
                        f.write("Real-time Chord Recognition Results\n")
                        f.write("=" * 40 + "\n\n")
                        for result in results:
                            f.write(f"{result['time']}: {result['chord']} ({result['confidence']})\n")
                
                messagebox.showinfo("Success", f"Results exported to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting results: {str(e)}")
    
    def export_to_chordpro(self):
        """Export analysis to ChordPro format."""
        if not self.current_analysis:
            messagebox.showwarning("Warning", "No analysis to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export to ChordPro",
            defaultextension=".cho",
            filetypes=[("ChordPro files", "*.cho"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("{title: Chord Analysis}\n")
                    f.write(f"{{subtitle: {self.current_analysis.file_path}}}\n")
                    if self.current_analysis.key_signature:
                        f.write(f"{{key: {self.current_analysis.key_signature}}}\n")
                    if self.current_analysis.tempo:
                        f.write(f"{{tempo: {self.current_analysis.tempo:.0f}}}\n")
                    f.write("\n")
                    
                    for detection in self.current_analysis.detected_chords:
                        f.write(f"[{detection.chord_name}] ")
                        if detection == self.current_analysis.detected_chords[-1] or \
                           (len([d for d in self.current_analysis.detected_chords if d.timestamp == detection.timestamp]) % 4 == 0):
                            f.write("\n")
                
                messagebox.showinfo("Success", f"ChordPro file exported to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting ChordPro: {str(e)}")
    
    def save_analysis_to_library(self):
        """Save analysis to song library."""
        if not self.current_analysis:
            messagebox.showwarning("Warning", "No analysis to save.")
            return
        
        try:
            # Create chord progression string
            chord_progression = " - ".join([d.chord_name for d in self.current_analysis.detected_chords])
            
            # Extract filename for title
            import os
            filename = os.path.basename(self.current_analysis.file_path)
            title = os.path.splitext(filename)[0]
            
            # Save to database
            song_id = self.db.save_song(
                title=title,
                artist="Unknown",
                source="Chord Identifier",
                key_signature=self.current_analysis.key_signature,
                tempo=int(self.current_analysis.tempo) if self.current_analysis.tempo else None,
                chord_progression=chord_progression,
                content=f"Analyzed from: {self.current_analysis.file_path}",
                tags=["Chord Analysis", "Audio Recognition"]
            )
            
            messagebox.showinfo("Success", f"Analysis saved to library with ID: {song_id}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving to library: {str(e)}")
    
    def export_analysis_json(self):
        """Export analysis as JSON."""
        if not self.current_analysis:
            messagebox.showwarning("Warning", "No analysis to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Analysis JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Convert analysis to dict
                analysis_dict = {
                    'file_path': self.current_analysis.file_path,
                    'duration': self.current_analysis.duration,
                    'sample_rate': self.current_analysis.sample_rate,
                    'key_signature': self.current_analysis.key_signature,
                    'tempo': self.current_analysis.tempo,
                    'time_signature': self.current_analysis.time_signature,
                    'detected_chords': [
                        {
                            'timestamp': d.timestamp,
                            'chord_name': d.chord_name,
                            'confidence': d.confidence,
                            'root_note': d.root_note,
                            'chord_type': d.chord_type,
                            'bass_note': d.bass_note,
                            'notes': d.notes
                        }
                        for d in self.current_analysis.detected_chords
                    ]
                }
                
                with open(file_path, 'w') as f:
                    json.dump(analysis_dict, f, indent=2)
                
                messagebox.showinfo("Success", f"Analysis exported to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting JSON: {str(e)}")
    
    def add_batch_files(self):
        """Add files to batch processing list."""
        file_paths = filedialog.askopenfilenames(
            title="Select Audio Files for Batch Processing",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.aac *.ogg"),
                ("All files", "*.*")
            ]
        )
        
        for file_path in file_paths:
            if file_path not in [self.batch_listbox.get(i) for i in range(self.batch_listbox.size())]:
                self.batch_listbox.insert(tk.END, file_path)
    
    def remove_batch_files(self):
        """Remove selected files from batch list."""
        selection = self.batch_listbox.curselection()
        for index in reversed(selection):
            self.batch_listbox.delete(index)
    
    def clear_batch_files(self):
        """Clear all files from batch list."""
        self.batch_listbox.delete(0, tk.END)
    
    def start_batch_processing(self):
        """Start batch processing of files."""
        if self.batch_listbox.size() == 0:
            messagebox.showwarning("Warning", "No files to process.")
            return
        
        if not LIBROSA_AVAILABLE:
            messagebox.showerror("Error", "librosa library is required for batch processing.")
            return
        
        # Get file list
        files = [self.batch_listbox.get(i) for i in range(self.batch_listbox.size())]
        
        # Start processing in thread
        self.batch_process_btn.config(state=tk.DISABLED, text="Processing...")
        self.batch_progress_var.set(0)
        
        def batch_thread():
            try:
                for i, file_path in enumerate(files):
                    self.batch_status_label.config(text=f"Processing {i+1}/{len(files)}")
                    
                    # Analyze file
                    result = self.recognition_engine.analyze_audio_file(file_path)
                    
                    # Save to history
                    self.window.after(0, lambda r=result: self.save_analysis_to_history(r))
                    
                    # Update progress
                    progress = ((i + 1) / len(files)) * 100
                    self.batch_progress_var.set(progress)
                
                # Finished
                self.window.after(0, self.batch_processing_finished)
                
            except Exception as e:
                self.window.after(0, lambda: self.handle_batch_error(str(e)))
        
        threading.Thread(target=batch_thread, daemon=True).start()
    
    def batch_processing_finished(self):
        """Handle batch processing completion."""
        self.batch_process_btn.config(state=tk.NORMAL, text="Start Batch Processing")
        self.batch_status_label.config(text="Completed")
        self.batch_progress_var.set(100)
        self.load_analysis_history()
        messagebox.showinfo("Success", "Batch processing completed!")
    
    def handle_batch_error(self, error_message: str):
        """Handle batch processing error."""
        self.batch_process_btn.config(state=tk.NORMAL, text="Start Batch Processing")
        self.batch_status_label.config(text="Error")
        messagebox.showerror("Batch Processing Error", f"Error during batch processing: {error_message}")
    
    def save_analysis_to_history(self, result: AudioAnalysisResult):
        """Save analysis result to history."""
        try:
            # This would save to a database table for analysis history
            # For now, we'll just refresh the history view
            pass
        except Exception as e:
            print(f"Error saving to history: {e}")
    
    def load_analysis_history(self):
        """Load analysis history."""
        # Clear current items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # This would load from database
        # For now, show placeholder
        self.history_tree.insert("", tk.END, values=(
            "2024-01-01 12:00",
            "example.wav",
            "180.0s",
            "24",
            "C major",
            "120 BPM"
        ))
    
    def clear_analysis_history(self):
        """Clear analysis history."""
        if messagebox.askyesno("Confirm", "Clear all analysis history?"):
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
    
    def view_analysis_details(self, event):
        """View details of selected analysis."""
        selection = self.history_tree.selection()
        if selection:
            messagebox.showinfo("Analysis Details", "Analysis details feature coming soon!")


def show_chord_identifier(parent=None):
    """Show the Chord Identifier window."""
    return ChordIdentifierWindow(parent)


if __name__ == "__main__":
    # Test the Chord Identifier window
    app = ChordIdentifierWindow()
    app.window.mainloop()
