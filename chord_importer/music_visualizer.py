"""
Music Visualizer Module
Real-time and static visualization of musical elements including waveforms, 
spectrograms, chord progressions, and music theory concepts.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Tuple, Any, Callable, TYPE_CHECKING
import threading
import time
import numpy as np
import math
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from matplotlib.figure import Figure

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    from matplotlib.animation import FuncAnimation
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    # Create a dummy Figure class for type hints when matplotlib is not available
    class Figure:
        pass

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from .database import get_database
    from .settings import get_settings
    from .song_utilities import MusicTheoryEngine
except ImportError:
    from chord_importer.database import get_database
    from chord_importer.settings import get_settings
    from chord_importer.song_utilities import MusicTheoryEngine


class VisualizationType(Enum):
    """Types of visualizations available."""
    CIRCLE_OF_FIFTHS = "circle_of_fifths"
    CHORD_PROGRESSION = "chord_progression"
    FRETBOARD = "fretboard"
    PIANO_KEYBOARD = "piano_keyboard"
    WAVEFORM = "waveform"
    SPECTROGRAM = "spectrogram"
    CHROMAGRAM = "chromagram"
    SCALE_DEGREES = "scale_degrees"


@dataclass
class VisualizationConfig:
    """Configuration for visualizations."""
    width: int = 800
    height: int = 600
    dpi: int = 100
    background_color: str = "#ffffff"
    primary_color: str = "#2196F3"
    secondary_color: str = "#FF9800"
    accent_color: str = "#4CAF50"
    text_color: str = "#333333"
    font_size: int = 12
    title_font_size: int = 16


class CircleOfFifthsVisualizer:
    """Visualizer for the Circle of Fifths."""
    
    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.keys = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'Ab', 'Eb', 'Bb', 'F']
        self.minor_keys = ['Am', 'Em', 'Bm', 'F#m', 'C#m', 'G#m', 'D#m', 'A#m', 'Fm', 'Cm', 'Gm', 'Dm']
    
    def create_visualization(self, fig: "Figure", highlighted_keys: List[str] = None) -> None:
        """Create circle of fifths visualization."""
        ax = fig.add_subplot(111)
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Draw outer circle (major keys)
        outer_radius = 1.2
        for i, key in enumerate(self.keys):
            angle = i * 2 * math.pi / 12 - math.pi / 2
            x = outer_radius * math.cos(angle)
            y = outer_radius * math.sin(angle)
            
            # Highlight if in highlighted keys
            color = self.config.accent_color if highlighted_keys and key in highlighted_keys else self.config.primary_color
            
            # Draw key circle
            circle = patches.Circle((x, y), 0.15, facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(circle)
            
            # Add key label
            ax.text(x, y, key, ha='center', va='center', fontsize=self.config.font_size, 
                   fontweight='bold', color='white')
        
        # Draw inner circle (minor keys)
        inner_radius = 0.8
        for i, key in enumerate(self.minor_keys):
            angle = i * 2 * math.pi / 12 - math.pi / 2
            x = inner_radius * math.cos(angle)
            y = inner_radius * math.sin(angle)
            
            # Highlight if in highlighted keys
            color = self.config.accent_color if highlighted_keys and key in highlighted_keys else self.config.secondary_color
            
            # Draw key circle
            circle = patches.Circle((x, y), 0.12, facecolor=color, edgecolor='black', linewidth=1)
            ax.add_patch(circle)
            
            # Add key label
            ax.text(x, y, key, ha='center', va='center', fontsize=self.config.font_size-2, 
                   fontweight='bold', color='white')
        
        # Add title
        ax.text(0, -1.4, 'Circle of Fifths', ha='center', va='center', 
               fontsize=self.config.title_font_size, fontweight='bold')
        
        # Add legend
        ax.text(1.3, 1.2, 'Major Keys', ha='left', va='center', fontsize=10, 
               bbox=dict(boxstyle="round,pad=0.3", facecolor=self.config.primary_color, alpha=0.7))
        ax.text(1.3, 1.0, 'Minor Keys', ha='left', va='center', fontsize=10,
               bbox=dict(boxstyle="round,pad=0.3", facecolor=self.config.secondary_color, alpha=0.7))


class ChordProgressionVisualizer:
    """Visualizer for chord progressions."""
    
    def __init__(self, config: VisualizationConfig):
        self.config = config
    
    def create_visualization(self, fig: "Figure", chords: List[str], key: str = None) -> None:
        """Create chord progression visualization optimized for live performance."""
        ax = fig.add_subplot(111)
        
        if not chords:
            ax.text(0.5, 0.5, 'No chord progression to display\nLoad a setlist or enter chords manually', 
                   ha='center', va='center', transform=ax.transAxes, 
                   fontsize=self.config.font_size + 4, color='#666666')
            return
        
        # Create large, clear chord boxes for stage visibility
        num_chords = len(chords)
        
        # Determine layout based on number of chords
        if num_chords <= 4:
            # Single row for 4 or fewer chords
            cols = num_chords
            rows = 1
        elif num_chords <= 8:
            # Two rows for 5-8 chords
            cols = 4
            rows = 2
        else:
            # Multiple rows for more chords
            cols = 4
            rows = (num_chords + 3) // 4
        
        box_width = 0.8 / cols
        box_height = 0.6 / rows
        
        for i, chord in enumerate(chords):
            row = i // cols
            col = i % cols
            
            x = 0.1 + col * (0.8 / cols)
            y = 0.7 - row * (0.6 / rows)
            
            # Parse chord for coloring
            chord_analysis = MusicTheoryEngine.parse_chord(chord)
            
            # Choose color based on chord quality - high contrast for stage
            if chord_analysis:
                if chord_analysis.quality.value == 'major':
                    color = '#2196F3'  # Bright blue for major
                elif chord_analysis.quality.value == 'minor':
                    color = '#FF5722'  # Orange-red for minor
                elif 'dominant' in chord_analysis.quality.value:
                    color = '#9C27B0'  # Purple for dominant
                else:
                    color = '#4CAF50'  # Green for other qualities
            else:
                color = '#607D8B'  # Blue-grey for unknown
            
            # Draw chord box with thick border for visibility
            rect = patches.Rectangle((x, y), box_width * 0.9, box_height * 0.8, 
                                   facecolor=color, edgecolor='black', linewidth=3)
            ax.add_patch(rect)
            
            # Add chord label - large font for stage visibility
            font_size = max(16, self.config.font_size + 8)
            ax.text(x + (box_width * 0.45), y + (box_height * 0.5), chord, 
                   ha='center', va='center', fontsize=font_size, 
                   fontweight='bold', color='white')
            
            # Add Roman numeral if key is provided - smaller but visible
            if key and chord_analysis:
                roman = self._get_roman_numeral(chord, key)
                ax.text(x + (box_width * 0.45), y + (box_height * 0.15), roman, 
                       ha='center', va='center', fontsize=font_size - 4, 
                       style='italic', color='white', alpha=0.8)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Add title with key information - large and clear
        title = f"Chord Progression"
        if key:
            title += f" - Key of {key}"
        ax.text(0.5, 0.95, title, ha='center', va='center', transform=ax.transAxes,
               fontsize=self.config.title_font_size + 4, fontweight='bold', color='#333333')
        
        # Add chord count info
        ax.text(0.5, 0.05, f"{num_chords} chords", ha='center', va='center', 
               transform=ax.transAxes, fontsize=self.config.font_size, 
               color='#666666', style='italic')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
    
    def _get_roman_numeral(self, chord: str, key: str) -> str:
        """Get roman numeral for chord in key (simplified)."""
        # This is a simplified implementation
        chord_root = chord[0] if chord else 'C'
        key_root = key[0] if key else 'C'
        
        try:
            key_index = MusicTheoryEngine.CHROMATIC_SCALE.index(key_root)
            chord_index = MusicTheoryEngine.CHROMATIC_SCALE.index(chord_root)
            interval = (chord_index - key_index) % 12
            
            roman_map = {
                0: 'I', 2: 'ii', 4: 'iii', 5: 'IV', 
                7: 'V', 9: 'vi', 11: 'vii°'
            }
            
            return roman_map.get(interval, '?')
        except ValueError:
            return '?'


class FretboardVisualizer:
    """Visualizer for guitar fretboard."""
    
    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.strings = ['E', 'A', 'D', 'G', 'B', 'E']  # Standard tuning
        self.frets = 12
    
    def create_visualization(self, fig: "Figure", chord: str = None, scale: str = None) -> None:
        """Create fretboard visualization."""
        ax = fig.add_subplot(111)
        
        # Draw fretboard
        fret_width = 0.8 / self.frets
        string_height = 0.6 / len(self.strings)
        
        # Draw frets
        for fret in range(self.frets + 1):
            x = 0.1 + fret * fret_width
            ax.plot([x, x], [0.1, 0.7], 'k-', linewidth=2 if fret == 0 else 1)
        
        # Draw strings
        for string in range(len(self.strings)):
            y = 0.1 + string * string_height
            ax.plot([0.1, 0.9], [y, y], 'k-', linewidth=1)
            
            # Add string labels
            ax.text(0.05, y, self.strings[string], ha='center', va='center',
                   fontsize=self.config.font_size, fontweight='bold')
        
        # Add fret markers
        fret_markers = [3, 5, 7, 9, 12]
        for fret in fret_markers:
            if fret <= self.frets:
                x = 0.1 + (fret - 0.5) * fret_width
                y = 0.4
                marker_size = 200 if fret == 12 else 100
                ax.scatter([x], [y], s=marker_size, c='lightgray', marker='o', alpha=0.5)
        
        # Highlight chord or scale notes
        if chord:
            self._highlight_chord(ax, chord, fret_width, string_height)
        elif scale:
            self._highlight_scale(ax, scale, fret_width, string_height)
        
        # Add title
        title = "Guitar Fretboard"
        if chord:
            title += f" - {chord} Chord"
        elif scale:
            title += f" - {scale} Scale"
        
        ax.text(0.5, 0.85, title, ha='center', va='center', transform=ax.transAxes,
               fontsize=self.config.title_font_size, fontweight='bold')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 0.8)
        ax.axis('off')
    
    def _highlight_chord(self, ax, chord: str, fret_width: float, string_height: float) -> None:
        """Highlight chord notes on fretboard."""
        # Simplified chord shapes (C major example)
        chord_shapes = {
            'C': [(0, 3), (1, 2), (2, 0), (3, 1), (4, 0), (5, 0)],  # String, Fret
            'G': [(0, 3), (1, 2), (2, 0), (3, 0), (4, 3), (5, 3)],
            'Am': [(0, 0), (1, 0), (2, 2), (3, 2), (4, 1), (5, 0)],
            'F': [(0, 1), (1, 1), (2, 3), (3, 3), (4, 2), (5, 1)],
        }
        
        shape = chord_shapes.get(chord, [])
        for string, fret in shape:
            if fret >= 0:  # -1 means don't play string
                x = 0.1 + (fret + 0.5) * fret_width if fret > 0 else 0.05
                y = 0.1 + string * string_height
                ax.scatter([x], [y], s=150, c=self.config.accent_color, marker='o', 
                          edgecolors='black', linewidth=2)
    
    def _highlight_scale(self, ax, scale: str, fret_width: float, string_height: float) -> None:
        """Highlight scale notes on fretboard."""
        # This would require more complex logic to map scale notes to fretboard positions
        pass


class PianoKeyboardVisualizer:
    """Visualizer for piano keyboard."""
    
    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.white_keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        self.black_keys = ['C#', 'D#', 'F#', 'G#', 'A#']
    
    def create_visualization(self, fig: "Figure", highlighted_notes: List[str] = None) -> None:
        """Create piano keyboard visualization."""
        ax = fig.add_subplot(111)
        
        # Draw white keys
        white_key_width = 0.8 / len(self.white_keys)
        for i, key in enumerate(self.white_keys):
            x = 0.1 + i * white_key_width
            
            # Determine color
            color = self.config.accent_color if highlighted_notes and key in highlighted_notes else 'white'
            
            # Draw key
            rect = patches.Rectangle((x, 0.2), white_key_width * 0.9, 0.4,
                                   facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(rect)
            
            # Add label
            ax.text(x + white_key_width * 0.45, 0.1, key, ha='center', va='center',
                   fontsize=self.config.font_size, fontweight='bold')
        
        # Draw black keys
        black_key_positions = [0.5, 1.5, 3.5, 4.5, 5.5]  # Relative to white keys
        for i, key in enumerate(self.black_keys):
            if i < len(black_key_positions):
                x = 0.1 + black_key_positions[i] * white_key_width
                
                # Determine color
                color = self.config.accent_color if highlighted_notes and key in highlighted_notes else 'black'
                
                # Draw key
                rect = patches.Rectangle((x, 0.35), white_key_width * 0.6, 0.25,
                                       facecolor=color, edgecolor='black', linewidth=2)
                ax.add_patch(rect)
                
                # Add label
                text_color = 'white' if color == 'black' else 'black'
                ax.text(x + white_key_width * 0.3, 0.47, key, ha='center', va='center',
                       fontsize=self.config.font_size - 2, fontweight='bold', color=text_color)
        
        # Add title
        ax.text(0.5, 0.8, 'Piano Keyboard', ha='center', va='center', transform=ax.transAxes,
               fontsize=self.config.title_font_size, fontweight='bold')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')


class AudioWaveformVisualizer:
    """Visualizer for audio waveforms and spectrograms."""
    
    def __init__(self, config: VisualizationConfig):
        self.config = config
    
    def create_waveform(self, fig: "Figure", audio_data: np.ndarray, sample_rate: int) -> None:
        """Create waveform visualization."""
        ax = fig.add_subplot(111)
        
        # Create time axis
        time = np.linspace(0, len(audio_data) / sample_rate, len(audio_data))
        
        # Plot waveform
        ax.plot(time, audio_data, color=self.config.primary_color, linewidth=0.5)
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Amplitude')
        ax.set_title('Audio Waveform')
        ax.grid(True, alpha=0.3)
    
    def create_spectrogram(self, fig: "Figure", audio_data: np.ndarray, sample_rate: int) -> None:
        """Create spectrogram visualization."""
        if not LIBROSA_AVAILABLE:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, 'librosa required for spectrogram', ha='center', va='center',
                   transform=ax.transAxes)
            return
        
        ax = fig.add_subplot(111)
        
        # Compute spectrogram
        D = librosa.amplitude_to_db(np.abs(librosa.stft(audio_data)), ref=np.max)
        
        # Display spectrogram
        img = librosa.display.specshow(D, y_axis='hz', x_axis='time', sr=sample_rate, ax=ax)
        ax.set_title('Spectrogram')
        fig.colorbar(img, ax=ax, format='%+2.0f dB')
    
    def create_chromagram(self, fig: "Figure", audio_data: np.ndarray, sample_rate: int) -> None:
        """Create chromagram visualization."""
        if not LIBROSA_AVAILABLE:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, 'librosa required for chromagram', ha='center', va='center',
                   transform=ax.transAxes)
            return
        
        ax = fig.add_subplot(111)
        
        # Compute chromagram
        chroma = librosa.feature.chroma_stft(y=audio_data, sr=sample_rate)
        
        # Display chromagram
        img = librosa.display.specshow(chroma, y_axis='chroma', x_axis='time', ax=ax)
        ax.set_title('Chromagram')
        fig.colorbar(img, ax=ax)


class MusicVisualizerWindow:
    """Main window for the Music Visualizer."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.db = get_database()
        self.settings = get_settings()
        
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("Music Visualizer - Musical Tools Suite")
        self.window.geometry("1200x800")
        self.window.resizable(True, True)
        
        # Initialize components
        self.config = VisualizationConfig()
        self.current_audio = None
        self.current_sample_rate = None
        
        # Create visualizers
        self.circle_visualizer = CircleOfFifthsVisualizer(self.config)
        self.progression_visualizer = ChordProgressionVisualizer(self.config)
        self.fretboard_visualizer = FretboardVisualizer(self.config)
        self.keyboard_visualizer = PianoKeyboardVisualizer(self.config)
        self.audio_visualizer = AudioWaveformVisualizer(self.config)
        
        # Live performance mode
        self.live_mode = False
        self.fullscreen_mode = False
        self.current_setlist = None
        self.current_song_index = 0
        
        self.setup_ui()
        self.center_window()
    
    def create_menu_bar(self):
        """Create menu bar with live performance options."""
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Fullscreen", command=self.toggle_fullscreen, accelerator="F11")
        view_menu.add_separator()
        view_menu.add_command(label="Live Performance Mode", command=self.toggle_live_mode)
        view_menu.add_separator()
        view_menu.add_command(label="Load Setlist", command=self.load_setlist)
        
        # Performance menu
        perf_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Performance", menu=perf_menu)
        perf_menu.add_command(label="Next Song", command=self.next_song, accelerator="Ctrl+Right")
        perf_menu.add_command(label="Previous Song", command=self.prev_song, accelerator="Ctrl+Left")
        perf_menu.add_separator()
        perf_menu.add_command(label="Transpose Up", command=lambda: self.transpose_current(1), accelerator="Ctrl+Up")
        perf_menu.add_command(label="Transpose Down", command=lambda: self.transpose_current(-1), accelerator="Ctrl+Down")
        
        # Bind keyboard shortcuts
        self.window.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.window.bind("<Control-Right>", lambda e: self.next_song())
        self.window.bind("<Control-Left>", lambda e: self.prev_song())
        self.window.bind("<Control-Up>", lambda e: self.transpose_current(1))
        self.window.bind("<Control-Down>", lambda e: self.transpose_current(-1))
        self.window.bind("<Escape>", lambda e: self.exit_fullscreen())
    
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
        # Create menu bar
        self.create_menu_bar()
        
        # Create main paned window
        main_paned = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # Right panel - Visualization
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)
        
        self.setup_controls(left_frame)
        self.setup_visualization_area(right_frame)
        
        # Initialize live performance components
        self.setup_live_performance_components()
    
    def setup_controls(self, parent):
        """Setup the control panel."""
        # Create notebook for different control tabs
        self.control_notebook = ttk.Notebook(parent)
        self.control_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Live Performance tab (priority)
        live_tab = ttk.Frame(self.control_notebook)
        self.control_notebook.add(live_tab, text="🎤 Live")
        self.create_live_performance_tab(live_tab)
        
        # Visualization tab
        viz_tab = ttk.Frame(self.control_notebook)
        self.control_notebook.add(viz_tab, text="📊 Visualizations")
        self.create_visualization_tab(viz_tab)
        
        # Audio tab
        audio_tab = ttk.Frame(self.control_notebook)
        self.control_notebook.add(audio_tab, text="🎵 Audio")
        self.create_audio_tab(audio_tab)
    
    def create_live_performance_tab(self, parent):
        """Create live performance controls tab."""
        # Performance mode toggle
        mode_frame = tk.LabelFrame(parent, text="Performance Mode", font=("Arial", 12, "bold"))
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.live_mode_btn = tk.Button(
            mode_frame,
            text="🎤 Enter Live Mode",
            command=self.toggle_live_mode,
            bg="#FF5722",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.live_mode_btn.pack(fill=tk.X, padx=10, pady=10)
        
        # Setlist controls
        setlist_frame = tk.LabelFrame(parent, text="Setlist", font=("Arial", 12, "bold"))
        setlist_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Load setlist button
        tk.Button(
            setlist_frame,
            text="📋 Load Setlist",
            command=self.load_setlist,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(fill=tk.X, padx=10, pady=5)
        
        # Current song info
        self.current_song_label = tk.Label(
            setlist_frame,
            text="No setlist loaded",
            font=("Arial", 10),
            fg="#666666",
            wraplength=200
        )
        self.current_song_label.pack(fill=tk.X, padx=10, pady=5)
        
        # Navigation controls
        nav_frame = tk.Frame(setlist_frame)
        nav_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(
            nav_frame,
            text="⬅️ Previous",
            command=self.prev_song,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        tk.Button(
            nav_frame,
            text="Next ➡️",
            command=self.next_song,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Transpose controls
        transpose_frame = tk.LabelFrame(parent, text="Quick Transpose", font=("Arial", 12, "bold"))
        transpose_frame.pack(fill=tk.X, padx=10, pady=10)
        
        transpose_controls = tk.Frame(transpose_frame)
        transpose_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            transpose_controls,
            text="🔽 -1",
            command=lambda: self.transpose_current(-1),
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.transpose_label = tk.Label(
            transpose_controls,
            text="Original",
            font=("Arial", 10, "bold"),
            fg="#333333"
        )
        self.transpose_label.pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            transpose_controls,
            text="🔼 +1",
            command=lambda: self.transpose_current(1),
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Fullscreen control
        fullscreen_frame = tk.LabelFrame(parent, text="Display", font=("Arial", 12, "bold"))
        fullscreen_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            fullscreen_frame,
            text="🖥️ Toggle Fullscreen (F11)",
            command=self.toggle_fullscreen,
            bg="#9C27B0",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(fill=tk.X, padx=10, pady=10)
    
    def create_visualization_tab(self, parent):
        """Create visualization controls tab."""
        # Visualization type selection
        viz_frame = tk.LabelFrame(parent, text="Visualization Type", font=("Arial", 12, "bold"))
        viz_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.viz_type = tk.StringVar(value="chord_progression")  # Default to chord progression for live use
        
        viz_options = [
            ("🎵 Chord Progression", "chord_progression"),
            ("🎸 Guitar Fretboard", "fretboard"),
            ("🎹 Piano Keyboard", "piano_keyboard"),
            ("⭕ Circle of Fifths", "circle_of_fifths"),
            ("📊 Audio Waveform", "waveform"),
            ("📈 Spectrogram", "spectrogram"),
            ("🌈 Chromagram", "chromagram")
        ]
        
        for text, value in viz_options:
            tk.Radiobutton(viz_frame, text=text, variable=self.viz_type, value=value,
                          command=self.on_visualization_type_changed, font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # Input controls
        input_frame = tk.LabelFrame(parent, text="Input", font=("Arial", 12, "bold"))
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Key selection
        key_frame = tk.Frame(input_frame)
        key_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(key_frame, text="Key:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.key_var = tk.StringVar(value="C")
        key_combo = ttk.Combobox(key_frame, textvariable=self.key_var,
                               values=MusicTheoryEngine.CHROMATIC_SCALE + [k + 'm' for k in MusicTheoryEngine.CHROMATIC_SCALE],
                               state="readonly", width=8)
        key_combo.pack(side=tk.LEFT, padx=(10, 0))
        key_combo.bind("<<ComboboxSelected>>", self.on_input_changed)
        
        # Chord input
        chord_frame = tk.Frame(input_frame)
        chord_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(chord_frame, text="Chord:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.chord_var = tk.StringVar()
        chord_entry = tk.Entry(chord_frame, textvariable=self.chord_var, font=("Arial", 10))
        chord_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        chord_entry.bind("<KeyRelease>", self.on_input_changed)
        
        # Chord progression input
        progression_frame = tk.Frame(input_frame)
        progression_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(progression_frame, text="Progression:", font=("Arial", 10)).pack(anchor=tk.W)
        self.progression_text = tk.Text(progression_frame, height=3, font=("Arial", 10))
        self.progression_text.pack(fill=tk.X, pady=(5, 0))
        self.progression_text.bind("<KeyRelease>", self.on_input_changed)
        
        # Audio file controls
        audio_frame = tk.LabelFrame(parent, text="Audio File", font=("Arial", 12, "bold"))
        audio_frame.pack(fill=tk.X, padx=10, pady=10)
        
        file_controls = tk.Frame(audio_frame)
        file_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(file_controls, text="Load Audio File", command=self.load_audio_file,
                 bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(fill=tk.X)
        
        self.audio_info_label = tk.Label(audio_frame, text="No audio file loaded", 
                                       font=("Arial", 9), wraplength=200)
        self.audio_info_label.pack(padx=10, pady=(0, 10))
        
        # Song library integration
        library_frame = tk.LabelFrame(parent, text="Song Library", font=("Arial", 12, "bold"))
        library_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(library_frame, text="Select Song:", font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.song_combo = ttk.Combobox(library_frame, state="readonly")
        self.song_combo.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.song_combo.bind("<<ComboboxSelected>>", self.on_song_selected)
        
        tk.Button(library_frame, text="Load Songs", command=self.load_songs,
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # Visualization controls
        viz_controls_frame = tk.LabelFrame(parent, text="Visualization Controls", font=("Arial", 12, "bold"))
        viz_controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(viz_controls_frame, text="Update Visualization", command=self.update_visualization,
                 bg="#FF9800", fg="white", font=("Arial", 12, "bold")).pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(viz_controls_frame, text="Export Image", command=self.export_visualization,
                 bg="#9C27B0", fg="white", font=("Arial", 10, "bold")).pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Load initial songs
        self.load_songs()
    
    def setup_visualization_area(self, parent):
        """Setup the visualization display area."""
        if not MATPLOTLIB_AVAILABLE:
            error_frame = tk.Frame(parent, bg="#ffebee")
            error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            tk.Label(error_frame, text="⚠️ Missing Dependency", 
                    font=("Arial", 16, "bold"), fg="#c62828", bg="#ffebee").pack(pady=(20, 10))
            tk.Label(error_frame, text="matplotlib library is required for visualizations",
                    font=("Arial", 12), fg="#d32f2f", bg="#ffebee").pack(pady=5)
            tk.Label(error_frame, text="Please install it with: pip install matplotlib",
                    font=("Arial", 10), fg="#666666", bg="#ffebee").pack(pady=5)
            return
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(10, 8), dpi=self.config.dpi)
        self.fig.patch.set_facecolor(self.config.background_color)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, parent)
        toolbar.update()
        
        # Initial visualization
        self.update_visualization()
    
    def on_visualization_type_changed(self):
        """Handle visualization type change."""
        self.update_visualization()
    
    def on_input_changed(self, event=None):
        """Handle input change."""
        # Auto-update visualization if enabled
        viz_type = self.viz_type.get()
        if viz_type in ["circle_of_fifths", "chord_progression", "fretboard", "piano_keyboard"]:
            self.update_visualization()
    
    def on_song_selected(self, event=None):
        """Handle song selection from library."""
        selection = self.song_combo.get()
        if not selection:
            return
        
        try:
            # Extract song title from selection
            title = selection.split(" - ")[0]
            songs = self.db.get_songs(search_term=title)
            
            if songs:
                song = songs[0]
                
                # Update inputs
                if song.get('key_signature'):
                    self.key_var.set(song['key_signature'])
                
                if song.get('chord_progression'):
                    self.progression_text.delete(1.0, tk.END)
                    self.progression_text.insert(1.0, song['chord_progression'])
                
                # Update visualization
                self.update_visualization()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading song: {str(e)}")
    
    def load_songs(self):
        """Load songs from database."""
        try:
            songs = self.db.get_songs()
            song_names = [f"{song['title']} - {song.get('artist', 'Unknown')}" for song in songs]
            self.song_combo['values'] = song_names
        except Exception as e:
            messagebox.showerror("Error", f"Error loading songs: {str(e)}")
    
    def load_audio_file(self):
        """Load audio file for visualization."""
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.aac *.ogg"),
                ("WAV files", "*.wav"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        if not LIBROSA_AVAILABLE:
            messagebox.showerror("Error", "librosa library is required for audio file loading.")
            return
        
        try:
            # Load audio file
            self.current_audio, self.current_sample_rate = librosa.load(file_path, sr=22050)
            
            # Update info label
            duration = len(self.current_audio) / self.current_sample_rate
            self.audio_info_label.config(
                text=f"Loaded: {file_path.split('/')[-1]}\nDuration: {duration:.1f}s\nSample Rate: {self.current_sample_rate}Hz"
            )
            
            # Update visualization if audio type is selected
            viz_type = self.viz_type.get()
            if viz_type in ["waveform", "spectrogram", "chromagram"]:
                self.update_visualization()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading audio file: {str(e)}")
    
    def update_visualization(self):
        """Update the current visualization."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        # Clear previous plot
        self.fig.clear()
        
        viz_type = self.viz_type.get()
        
        try:
            if viz_type == "circle_of_fifths":
                self.create_circle_of_fifths()
            elif viz_type == "chord_progression":
                self.create_chord_progression()
            elif viz_type == "fretboard":
                self.create_fretboard()
            elif viz_type == "piano_keyboard":
                self.create_piano_keyboard()
            elif viz_type == "waveform":
                self.create_waveform()
            elif viz_type == "spectrogram":
                self.create_spectrogram()
            elif viz_type == "chromagram":
                self.create_chromagram()
            
            # Refresh canvas
            self.canvas.draw()
            
        except Exception as e:
            # Show error in plot
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Error creating visualization:\n{str(e)}", 
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=12, color='red')
            ax.axis('off')
            self.canvas.draw()
    
    def create_circle_of_fifths(self):
        """Create circle of fifths visualization."""
        key = self.key_var.get()
        highlighted_keys = [key] if key else []
        
        # Add related keys
        if key:
            key_analysis = MusicTheoryEngine.get_key_signature(key)
            if hasattr(key_analysis, 'relative_key'):
                highlighted_keys.append(key_analysis.relative_key)
        
        self.circle_visualizer.create_visualization(self.fig, highlighted_keys)
    
    def create_chord_progression(self):
        """Create chord progression visualization."""
        progression_text = self.progression_text.get(1.0, tk.END).strip()
        if not progression_text:
            # Use default progression
            chords = ['C', 'Am', 'F', 'G']
        else:
            # Parse chord progression
            chords = [chord.strip() for chord in progression_text.replace('-', ' ').split() if chord.strip()]
        
        key = self.key_var.get() if self.key_var.get() else None
        self.progression_visualizer.create_visualization(self.fig, chords, key)
    
    def create_fretboard(self):
        """Create fretboard visualization."""
        chord = self.chord_var.get().strip() if self.chord_var.get().strip() else None
        self.fretboard_visualizer.create_visualization(self.fig, chord=chord)
    
    def create_piano_keyboard(self):
        """Create piano keyboard visualization."""
        chord = self.chord_var.get().strip()
        highlighted_notes = []
        
        if chord:
            # Parse chord and get notes (simplified)
            chord_analysis = MusicTheoryEngine.parse_chord(chord)
            if chord_analysis:
                highlighted_notes = [chord_analysis.root]
                # Add more chord tones based on quality
                if chord_analysis.quality.value == 'major':
                    highlighted_notes.extend([
                        MusicTheoryEngine.transpose_note(chord_analysis.root, 4),
                        MusicTheoryEngine.transpose_note(chord_analysis.root, 7)
                    ])
                elif chord_analysis.quality.value == 'minor':
                    highlighted_notes.extend([
                        MusicTheoryEngine.transpose_note(chord_analysis.root, 3),
                        MusicTheoryEngine.transpose_note(chord_analysis.root, 7)
                    ])
        
        self.keyboard_visualizer.create_visualization(self.fig, highlighted_notes)
    
    def create_waveform(self):
        """Create waveform visualization."""
        if self.current_audio is None:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, 'Load an audio file to view waveform', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        self.audio_visualizer.create_waveform(self.fig, self.current_audio, self.current_sample_rate)
    
    def create_spectrogram(self):
        """Create spectrogram visualization."""
        if self.current_audio is None:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, 'Load an audio file to view spectrogram', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        self.audio_visualizer.create_spectrogram(self.fig, self.current_audio, self.current_sample_rate)
    
    def create_chromagram(self):
        """Create chromagram visualization."""
        if self.current_audio is None:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, 'Load an audio file to view chromagram', 
                   ha='center', va='center', transform=ax.transAxes)
            return
        
        self.audio_visualizer.create_chromagram(self.fig, self.current_audio, self.current_sample_rate)
    
    def export_visualization(self):
        """Export current visualization as image."""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Error", "matplotlib is required for image export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Visualization",
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("PDF files", "*.pdf"),
                ("SVG files", "*.svg"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Success", f"Visualization exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting visualization: {str(e)}")


    # Live Performance Methods
    def setup_live_performance_components(self):
        """Initialize live performance components."""
        self.current_transpose = 0
        self.setlist_songs = []
        
    def toggle_live_mode(self):
        """Toggle live performance mode."""
        self.live_mode = not self.live_mode
        
        if self.live_mode:
            self.live_mode_btn.configure(
                text="🎤 Exit Live Mode",
                bg="#4CAF50"
            )
            # Switch to chord progression view for live performance
            self.viz_type.set("chord_progression")
            self.update_visualization()
            # Focus on live tab
            self.control_notebook.select(0)
        else:
            self.live_mode_btn.configure(
                text="🎤 Enter Live Mode",
                bg="#FF5722"
            )
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        self.fullscreen_mode = not self.fullscreen_mode
        
        if self.fullscreen_mode:
            self.window.attributes('-fullscreen', True)
            # Hide menu bar in fullscreen
            self.window.config(menu="")
        else:
            self.window.attributes('-fullscreen', False)
            # Restore menu bar
            self.create_menu_bar()
    
    def exit_fullscreen(self):
        """Exit fullscreen mode."""
        if self.fullscreen_mode:
            self.toggle_fullscreen()
    
    def load_setlist(self):
        """Load a setlist from the database."""
        try:
            # Get setlists from database
            setlists = self.db.get_setlists()
            
            if not setlists:
                messagebox.showinfo("Info", "No setlists found. Create one in the Cipher Manager first.")
                return
            
            # Create selection dialog
            selection_window = tk.Toplevel(self.window)
            selection_window.title("Select Setlist")
            selection_window.geometry("400x300")
            selection_window.transient(self.window)
            selection_window.grab_set()
            
            tk.Label(selection_window, text="Select a setlist:", font=("Arial", 12, "bold")).pack(pady=10)
            
            # Listbox for setlists
            listbox = tk.Listbox(selection_window, font=("Arial", 10))
            listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            for setlist in setlists:
                listbox.insert(tk.END, f"{setlist['name']} ({setlist['song_count']} songs)")
            
            def on_select():
                selection = listbox.curselection()
                if selection:
                    selected_setlist = setlists[selection[0]]
                    self.load_setlist_songs(selected_setlist['id'], selected_setlist['name'])
                    selection_window.destroy()
            
            tk.Button(
                selection_window,
                text="Load Setlist",
                command=on_select,
                bg="#2196F3",
                fg="white",
                font=("Arial", 10, "bold"),
                relief="flat",
                padx=20,
                pady=8
            ).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading setlists: {str(e)}")
    
    def load_setlist_songs(self, setlist_id, setlist_name):
        """Load songs from a specific setlist."""
        try:
            self.setlist_songs = self.db.get_setlist_songs(setlist_id)
            self.current_setlist = setlist_name
            self.current_song_index = 0
            
            if self.setlist_songs:
                self.update_current_song_display()
                self.load_current_song()
            else:
                messagebox.showinfo("Info", "This setlist is empty.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading setlist songs: {str(e)}")
    
    def update_current_song_display(self):
        """Update the current song display."""
        if self.setlist_songs and 0 <= self.current_song_index < len(self.setlist_songs):
            song = self.setlist_songs[self.current_song_index]
            text = f"Setlist: {self.current_setlist}\n"
            text += f"Song {self.current_song_index + 1}/{len(self.setlist_songs)}: {song['title']}"
            if song.get('artist'):
                text += f" - {song['artist']}"
            self.current_song_label.configure(text=text)
        else:
            self.current_song_label.configure(text="No setlist loaded")
    
    def load_current_song(self):
        """Load the current song from setlist."""
        if self.setlist_songs and 0 <= self.current_song_index < len(self.setlist_songs):
            song = self.setlist_songs[self.current_song_index]
            
            # Update key
            if song.get('key'):
                self.key_var.set(song['key'])
            
            # Update chord progression
            if song.get('chord_progression'):
                self.progression_text.delete(1.0, tk.END)
                self.progression_text.insert(1.0, song['chord_progression'])
            
            # Reset transpose
            self.current_transpose = 0
            self.transpose_label.configure(text="Original")
            
            # Update visualization
            self.update_visualization()
    
    def next_song(self):
        """Go to next song in setlist."""
        if self.setlist_songs and self.current_song_index < len(self.setlist_songs) - 1:
            self.current_song_index += 1
            self.update_current_song_display()
            self.load_current_song()
    
    def prev_song(self):
        """Go to previous song in setlist."""
        if self.setlist_songs and self.current_song_index > 0:
            self.current_song_index -= 1
            self.update_current_song_display()
            self.load_current_song()
    
    def transpose_current(self, semitones):
        """Transpose current song by semitones."""
        self.current_transpose += semitones
        
        # Update transpose label
        if self.current_transpose == 0:
            self.transpose_label.configure(text="Original")
        elif self.current_transpose > 0:
            self.transpose_label.configure(text=f"+{self.current_transpose}")
        else:
            self.transpose_label.configure(text=str(self.current_transpose))
        
        # Update key if available
        if hasattr(self, 'key_var') and self.key_var.get():
            try:
                # Simple transpose logic (could be enhanced with music21)
                keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                current_key = self.key_var.get()
                
                if current_key in keys:
                    current_index = keys.index(current_key)
                    new_index = (current_index + self.current_transpose) % 12
                    new_key = keys[new_index]
                    self.key_var.set(new_key)
                    
                    # Update visualization
                    self.update_visualization()
                    
            except Exception:
                pass  # Ignore transpose errors for complex keys


def show_music_visualizer(parent=None):
    """Show the Music Visualizer window."""
    return MusicVisualizerWindow(parent)


if __name__ == "__main__":
    # Test the Music Visualizer window
    app = MusicVisualizerWindow()
    app.window.mainloop()
