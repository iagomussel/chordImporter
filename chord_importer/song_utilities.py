"""
Song Utilities Module
Advanced tools for song analysis, transposition, and arrangement assistance.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Tuple, Any
import re
import math
from dataclasses import dataclass
from enum import Enum

try:
    import music21
    from music21 import chord, key, scale, interval, pitch, roman, stream, meter
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

try:
    from .database import get_database
    from .settings import get_settings
except ImportError:
    from chord_importer.database import get_database
    from chord_importer.settings import get_settings


class ChordQuality(Enum):
    """Chord quality types."""
    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"
    AUGMENTED = "augmented"
    DOMINANT = "dominant7"
    MAJOR7 = "major7"
    MINOR7 = "minor7"
    SUSPENDED = "suspended"


@dataclass
class ChordAnalysis:
    """Analysis result for a chord."""
    chord_name: str
    root: str
    quality: ChordQuality
    extensions: List[str]
    bass_note: Optional[str] = None
    roman_numeral: Optional[str] = None
    function: Optional[str] = None


@dataclass
class KeyAnalysis:
    """Analysis result for a key."""
    key_name: str
    mode: str
    scale_degrees: List[str]
    relative_key: str
    parallel_key: str
    circle_of_fifths_position: int


@dataclass
class TranspositionResult:
    """Result of a transposition operation."""
    original_key: str
    target_key: str
    semitones: int
    chord_mapping: Dict[str, str]
    transposed_content: str


class MusicTheoryEngine:
    """Core music theory engine for analysis and manipulation."""
    
    # Circle of fifths
    CIRCLE_OF_FIFTHS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'Ab', 'Eb', 'Bb', 'F']
    
    # Chromatic scale
    CHROMATIC_SCALE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Common chord patterns
    CHORD_PATTERNS = {
        'major': [0, 4, 7],
        'minor': [0, 3, 7],
        'diminished': [0, 3, 6],
        'augmented': [0, 4, 8],
        'major7': [0, 4, 7, 11],
        'minor7': [0, 3, 7, 10],
        'dominant7': [0, 4, 7, 10],
        'suspended2': [0, 2, 7],
        'suspended4': [0, 5, 7]
    }
    
    # Roman numeral patterns for major keys
    MAJOR_ROMAN_NUMERALS = ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii°']
    MINOR_ROMAN_NUMERALS = ['i', 'ii°', 'III', 'iv', 'v', 'VI', 'VII']
    
    @classmethod
    def parse_chord(cls, chord_name: str) -> Optional[ChordAnalysis]:
        """Parse a chord name into its components."""
        if not chord_name:
            return None
        
        # Enhanced chord parsing regex to handle more variations
        chord_pattern = r'^([A-G](?:[#b]|##|bb)?)([^/]*?)(?:/([A-G](?:[#b]|##|bb)?(?:\d+)?))?$'
        match = re.match(chord_pattern, chord_name.strip())
        
        if not match:
            return None
        
        root = match.group(1)
        quality_str = match.group(2) or ""
        bass_note = match.group(3)
        
        # Determine chord quality
        quality = cls._determine_chord_quality(quality_str)
        extensions = cls._parse_extensions(quality_str)
        
        return ChordAnalysis(
            chord_name=chord_name,
            root=root,
            quality=quality,
            extensions=extensions,
            bass_note=bass_note
        )
    
    @classmethod
    def _determine_chord_quality(cls, quality_str: str) -> ChordQuality:
        """Determine chord quality from string."""
        quality_str_lower = quality_str.lower()
        quality_str_orig = quality_str  # Keep original for case-sensitive checks
        
        # Check for 7th chords first (more specific)
        if 'm7' in quality_str_lower:
            return ChordQuality.MINOR7
        elif 'maj7' in quality_str_lower or 'M7' in quality_str_orig or '7M' in quality_str_orig:
            return ChordQuality.MAJOR7
        elif '7' in quality_str_lower:
            return ChordQuality.DOMINANT
        # Check for basic qualities
        elif 'm' in quality_str_lower or 'min' in quality_str_lower:
            return ChordQuality.MINOR
        elif 'dim' in quality_str_lower or '°' in quality_str_orig or 'º' in quality_str_orig:
            return ChordQuality.DIMINISHED
        elif 'aug' in quality_str_lower or '+' in quality_str_orig:
            return ChordQuality.AUGMENTED
        elif 'sus' in quality_str_lower:
            return ChordQuality.SUSPENDED
        else:
            return ChordQuality.MAJOR
    
    @classmethod
    def _parse_extensions(cls, quality_str: str) -> List[str]:
        """Parse chord extensions from quality string."""
        extensions = []
        
        # Look for common extensions
        if '9' in quality_str:
            extensions.append('9')
        if '11' in quality_str:
            extensions.append('11')
        if '13' in quality_str:
            extensions.append('13')
        if 'add9' in quality_str:
            extensions.append('add9')
        if 'sus2' in quality_str:
            extensions.append('sus2')
        if 'sus4' in quality_str:
            extensions.append('sus4')
        
        return extensions
    
    @classmethod
    def transpose_chord(cls, chord_name: str, semitones: int) -> str:
        """Transpose a chord by the given number of semitones.
        
        Uses chord decomposition to ensure valid chord construction.
        """
        if not chord_name or semitones == 0:
            return chord_name
            
        chord_analysis = cls.parse_chord(chord_name)
        if not chord_analysis:
            return chord_name
        
        # Transpose root note
        new_root = cls.transpose_note(chord_analysis.root, semitones)
        
        # Transpose bass note if present
        new_bass = None
        if chord_analysis.bass_note:
            new_bass = cls.transpose_note(chord_analysis.bass_note, semitones)
        
        # Reconstruct chord carefully
        # Extract the quality/extension part (everything after the root, before bass)
        root_len = len(chord_analysis.root)
        quality_part = chord_name[root_len:]
        
        # Remove bass note part if present
        if chord_analysis.bass_note:
            bass_part = f"/{chord_analysis.bass_note}"
            if quality_part.endswith(bass_part):
                quality_part = quality_part[:-len(bass_part)]
        
        # Build new chord name
        new_chord = new_root + quality_part
        
        # Add bass note if present
        if new_bass:
            new_chord += f"/{new_bass}"
        
        # Validate the result - check if it's a reasonable chord
        if cls._is_valid_chord(new_chord):
            return new_chord
        else:
            # If invalid, try alternative enharmonic spelling
            alt_root = cls._get_enharmonic_equivalent(new_root)
            if alt_root and alt_root != new_root:
                alt_chord = alt_root + quality_part
                if new_bass:
                    alt_bass = cls._get_enharmonic_equivalent(new_bass)
                    alt_chord += f"/{alt_bass or new_bass}"
                
                if cls._is_valid_chord(alt_chord):
                    return alt_chord
            
            # If still invalid, return original
            return chord_name
    
    @classmethod
    def transpose_note(cls, note: str, semitones: int) -> str:
        """Transpose a single note by the given number of semitones.
        
        Uses smart enharmonic selection to avoid double sharps/flats.
        """
        if not note:
            return note
        
        # Parse note to separate root from accidentals
        import re
        match = re.match(r'^([A-G])((?:[#b]|##|bb)?)$', note)
        if not match:
            return note
        
        root = match.group(1)
        accidental = match.group(2)
        
        # Convert to chromatic index
        base_notes = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
        if root not in base_notes:
            return note
        
        current_index = base_notes[root]
        
        # Apply accidentals
        if accidental == '#':
            current_index += 1
        elif accidental == 'b':
            current_index -= 1
        elif accidental == '##':
            current_index += 2
        elif accidental == 'bb':
            current_index -= 2
        
        # Transpose
        new_index = (current_index + semitones) % 12
        
        # Smart enharmonic selection - prefer naturals, then sharps, avoid double accidentals
        enharmonic_options = {
            0: ['C'],
            1: ['C#', 'Db'],
            2: ['D'],
            3: ['D#', 'Eb'],
            4: ['E'],
            5: ['F'],
            6: ['F#', 'Gb'],
            7: ['G'],
            8: ['G#', 'Ab'],
            9: ['A'],
            10: ['A#', 'Bb'],
            11: ['B']
        }
        
        options = enharmonic_options.get(new_index, [cls.CHROMATIC_SCALE[new_index]])
        
        # Prefer natural notes first
        for option in options:
            if len(option) == 1:  # Natural note
                return option
        
        # Then prefer sharps over flats (unless original was flat)
        if 'b' in accidental:
            # Original was flat, prefer flats
            for option in options:
                if 'b' in option:
                    return option
        
        # Default to first option (usually sharp)
        return options[0]
    
    @classmethod
    def _is_valid_chord(cls, chord_name: str) -> bool:
        """Check if a chord name represents a valid, commonly used chord."""
        if not chord_name:
            return False
        
        # Parse the chord
        chord_analysis = cls.parse_chord(chord_name)
        if not chord_analysis:
            return False
        
        # Check for problematic combinations
        root = chord_analysis.root
        
        # Avoid double sharps and double flats
        if '##' in root or 'bb' in root:
            return False
        
        # Avoid uncommon enharmonic spellings like B#, E#, Cb, Fb
        uncommon_notes = {'B#', 'E#', 'Cb', 'Fb'}
        if root in uncommon_notes:
            return False
        
        # Check bass note too
        if chord_analysis.bass_note:
            if '##' in chord_analysis.bass_note or 'bb' in chord_analysis.bass_note:
                return False
            if chord_analysis.bass_note in uncommon_notes:
                return False
        
        return True
    
    @classmethod
    def _get_enharmonic_equivalent(cls, note: str) -> Optional[str]:
        """Get the enharmonic equivalent of a note."""
        enharmonic_map = {
            'C#': 'Db', 'Db': 'C#',
            'D#': 'Eb', 'Eb': 'D#',
            'F#': 'Gb', 'Gb': 'F#',
            'G#': 'Ab', 'Ab': 'G#',
            'A#': 'Bb', 'Bb': 'A#'
        }
        return enharmonic_map.get(note)
    
    @classmethod
    def get_key_signature(cls, key_name: str) -> KeyAnalysis:
        """Get detailed information about a key signature."""
        if MUSIC21_AVAILABLE:
            try:
                key_obj = key.Key(key_name)
                scale_obj = key_obj.getScale()
                
                return KeyAnalysis(
                    key_name=key_name,
                    mode=key_obj.mode,
                    scale_degrees=[str(p) for p in scale_obj.pitches],
                    relative_key=str(key_obj.relative),
                    parallel_key=str(key_obj.parallel),
                    circle_of_fifths_position=cls._get_circle_position(key_name)
                )
            except Exception:
                pass
        
        # Fallback implementation
        return KeyAnalysis(
            key_name=key_name,
            mode="major",
            scale_degrees=cls._get_scale_degrees_fallback(key_name),
            relative_key=cls._get_relative_key_fallback(key_name),
            parallel_key=cls._get_parallel_key_fallback(key_name),
            circle_of_fifths_position=cls._get_circle_position(key_name)
        )
    
    @classmethod
    def _get_circle_position(cls, key_name: str) -> int:
        """Get position in circle of fifths."""
        try:
            return cls.CIRCLE_OF_FIFTHS.index(key_name.upper())
        except ValueError:
            return 0
    
    @classmethod
    def _get_scale_degrees_fallback(cls, key_name: str) -> List[str]:
        """Fallback method to get scale degrees."""
        root = key_name[0].upper()
        try:
            root_index = cls.CHROMATIC_SCALE.index(root)
            major_intervals = [0, 2, 4, 5, 7, 9, 11]
            return [cls.CHROMATIC_SCALE[(root_index + interval) % 12] for interval in major_intervals]
        except ValueError:
            return []
    
    @classmethod
    def _get_relative_key_fallback(cls, key_name: str) -> str:
        """Fallback method to get relative key."""
        if 'm' in key_name.lower():
            # Minor to major (up minor third)
            root = cls.transpose_note(key_name[0], 3)
            return root
        else:
            # Major to minor (down minor third)
            root = cls.transpose_note(key_name[0], -3)
            return root + 'm'
    
    @classmethod
    def _get_parallel_key_fallback(cls, key_name: str) -> str:
        """Fallback method to get parallel key."""
        if 'm' in key_name.lower():
            return key_name.replace('m', '')
        else:
            return key_name + 'm'
    
    @classmethod
    def analyze_chord_progression(cls, chords: List[str], key_name: str = None) -> Dict[str, Any]:
        """Analyze a chord progression."""
        if not chords:
            return {}
        
        analysis = {
            'chords': [],
            'key_suggestions': [],
            'roman_numerals': [],
            'functions': [],
            'modulations': []
        }
        
        # Analyze each chord
        for chord_name in chords:
            chord_analysis = cls.parse_chord(chord_name)
            if chord_analysis:
                analysis['chords'].append(chord_analysis)
        
        # Suggest keys if not provided
        if not key_name and analysis['chords']:
            analysis['key_suggestions'] = cls._suggest_keys(chords)
        
        # Analyze in context of key
        if key_name:
            analysis['roman_numerals'] = cls._get_roman_numerals(chords, key_name)
            analysis['functions'] = cls._analyze_functions(chords, key_name)
        
        return analysis
    
    @classmethod
    def _suggest_keys(cls, chords: List[str]) -> List[str]:
        """Suggest possible keys for a chord progression."""
        # Simple key suggestion based on chord roots
        chord_roots = []
        for chord_name in chords:
            chord_analysis = cls.parse_chord(chord_name)
            if chord_analysis:
                chord_roots.append(chord_analysis.root)
        
        # Count occurrences and suggest most common roots as potential keys
        from collections import Counter
        root_counts = Counter(chord_roots)
        return [root for root, count in root_counts.most_common(3)]
    
    @classmethod
    def _get_roman_numerals(cls, chords: List[str], key_name: str) -> List[str]:
        """Get roman numeral analysis for chords in a key."""
        if not MUSIC21_AVAILABLE:
            return []
        
        try:
            key_obj = key.Key(key_name)
            roman_numerals = []
            
            for chord_name in chords:
                try:
                    chord_obj = chord.Chord(chord_name)
                    roman_num = roman.romanNumeralFromChord(chord_obj, key_obj)
                    roman_numerals.append(str(roman_num))
                except Exception:
                    roman_numerals.append("?")
            
            return roman_numerals
        except Exception:
            return []
    
    @classmethod
    def _analyze_functions(cls, chords: List[str], key_name: str) -> List[str]:
        """Analyze harmonic functions of chords."""
        functions = []
        
        for chord_name in chords:
            chord_analysis = cls.parse_chord(chord_name)
            if not chord_analysis:
                functions.append("Unknown")
                continue
            
            # Simple function analysis
            root = chord_analysis.root
            key_root = key_name[0] if key_name else 'C'
            
            # Calculate interval from key root
            try:
                key_index = cls.CHROMATIC_SCALE.index(key_root)
                chord_index = cls.CHROMATIC_SCALE.index(root)
                interval = (chord_index - key_index) % 12
                
                function_map = {
                    0: "Tonic",
                    2: "Supertonic", 
                    4: "Mediant",
                    5: "Subdominant",
                    7: "Dominant",
                    9: "Submediant",
                    11: "Leading Tone"
                }
                
                functions.append(function_map.get(interval, "Other"))
            except ValueError:
                functions.append("Unknown")
        
        return functions
    
    @classmethod
    def calculate_capo_position(cls, original_key: str, target_key: str) -> int:
        """Calculate capo position needed to transpose from original to target key."""
        try:
            orig_index = cls.CHROMATIC_SCALE.index(original_key[0])
            target_index = cls.CHROMATIC_SCALE.index(target_key[0])
            semitones = (target_index - orig_index) % 12
            return semitones if semitones <= 7 else semitones - 12
        except ValueError:
            return 0


class TranspositionEngine:
    """Engine for advanced transposition operations."""
    
    @staticmethod
    def transpose_content(content: str, semitones: int) -> TranspositionResult:
        """Transpose all chords in content by the given number of semitones."""
        if not content:
            return TranspositionResult("", "", 0, {}, content)
        
        # Find all chord patterns in the content - improved regex
        chord_pattern = r'\b([A-G](?:[#b]|##|bb)?(?:maj|min|m|dim|aug|sus|add|°|º|\+|M)?(?:\d+)?(?:M)?(?:\([^)]*\))?(?:sus[24]?|add\d+|no\d+)*(?:/[A-G](?:[#b]|##|bb)?)?)\b'
        
        chord_mapping = {}
        transposed_content = content
        
        # Find all unique chords
        matches = re.findall(chord_pattern, content)
        unique_chords = set(matches)
        
        # Transpose each unique chord
        for chord_name in unique_chords:
            transposed_chord = MusicTheoryEngine.transpose_chord(chord_name, semitones)
            chord_mapping[chord_name] = transposed_chord
            
            # Replace in content (whole word only)
            transposed_content = re.sub(
                r'\b' + re.escape(chord_name) + r'\b',
                transposed_chord,
                transposed_content
            )
        
        return TranspositionResult(
            original_key="",
            target_key="",
            semitones=semitones,
            chord_mapping=chord_mapping,
            transposed_content=transposed_content
        )
    
    @staticmethod
    def transpose_by_key(content: str, original_key: str, target_key: str) -> TranspositionResult:
        """Transpose content from one key to another."""
        # Calculate semitones difference
        try:
            orig_index = MusicTheoryEngine.CHROMATIC_SCALE.index(original_key[0])
            target_index = MusicTheoryEngine.CHROMATIC_SCALE.index(target_key[0])
            semitones = (target_index - orig_index) % 12
            if semitones > 6:
                semitones -= 12
        except ValueError:
            semitones = 0
        
        result = TranspositionEngine.transpose_content(content, semitones)
        result.original_key = original_key
        result.target_key = target_key
        
        return result


class PracticeMetronome:
    """Simple metronome for practice sessions."""
    
    def __init__(self, window=None):
        self.window = window
        self.is_running = False
        self.bpm = 120
        self.beat_count = 4
        self.current_beat = 0
        self.after_id = None
        self.click_callback = None
        self.sound_enabled = True
        
        # Try to initialize sound system
        self._init_sound()
    
    def _init_sound(self):
        """Initialize sound system for metronome clicks."""
        try:
            import winsound
            self.winsound = winsound
            self.sound_method = 'winsound'
        except ImportError:
            try:
                import pygame
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self.pygame = pygame
                self.sound_method = 'pygame'
                # Create simple click sounds
                self._create_click_sounds()
            except ImportError:
                print("Warning: No sound library available. Metronome will be visual only.")
                self.sound_enabled = False
                self.sound_method = None
    
    def _create_click_sounds(self):
        """Create click sounds using pygame."""
        if self.sound_method != 'pygame':
            return
        
        import numpy as np
        
        # Create high-pitched click for downbeat
        sample_rate = 22050
        duration = 0.1
        frequency_high = 1000
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        wave_high = np.sin(2 * np.pi * frequency_high * t) * np.exp(-t * 10)
        wave_high = (wave_high * 32767).astype(np.int16)
        
        # Create lower-pitched click for other beats
        frequency_low = 800
        wave_low = np.sin(2 * np.pi * frequency_low * t) * np.exp(-t * 10)
        wave_low = (wave_low * 32767).astype(np.int16)
        
        # Convert to pygame sound
        try:
            self.click_high = self.pygame.sndarray.make_sound(np.array([wave_high, wave_high]).T)
            self.click_low = self.pygame.sndarray.make_sound(np.array([wave_low, wave_low]).T)
        except:
            # Fallback if numpy is not available
            self.sound_enabled = False
    
    def _play_click(self, is_downbeat=False):
        """Play metronome click sound."""
        if not self.sound_enabled:
            return
        
        try:
            if self.sound_method == 'winsound':
                # Use system beep
                if is_downbeat:
                    self.winsound.Beep(1000, 100)  # Higher pitch for downbeat
                else:
                    self.winsound.Beep(800, 100)   # Lower pitch for other beats
            elif self.sound_method == 'pygame':
                # Use generated sounds
                if is_downbeat and hasattr(self, 'click_high'):
                    self.click_high.play()
                elif hasattr(self, 'click_low'):
                    self.click_low.play()
        except Exception as e:
            print(f"Error playing metronome sound: {e}")
    
    def set_tempo(self, bpm: int):
        """Set the metronome tempo."""
        self.bpm = max(40, min(300, bpm))
    
    def set_time_signature(self, beats: int):
        """Set the time signature (beats per measure)."""
        self.beat_count = max(1, min(12, beats))
    
    def toggle_sound(self):
        """Toggle sound on/off."""
        self.sound_enabled = not self.sound_enabled
        return self.sound_enabled
    
    def is_sound_enabled(self):
        """Check if sound is enabled."""
        return self.sound_enabled
    
    def start(self, click_callback=None):
        """Start the metronome."""
        self.click_callback = click_callback
        self.is_running = True
        self.current_beat = 0
        self._tick()
    
    def stop(self):
        """Stop the metronome."""
        self.is_running = False
        if self.after_id and self.window:
            self.window.after_cancel(self.after_id)
            self.after_id = None
    
    def _tick(self):
        """Internal tick method."""
        if not self.is_running:
            return
        
        self.current_beat = (self.current_beat + 1) % self.beat_count
        is_downbeat = self.current_beat == 0
        
        # Play sound
        self._play_click(is_downbeat)
        
        # Update visual callback
        if self.click_callback:
            self.click_callback(self.current_beat, is_downbeat)
        
        # Calculate interval in milliseconds
        interval = int(60000 / self.bpm)
        
        # Schedule next tick
        if self.window and self.is_running:
            self.after_id = self.window.after(interval, self._tick)


class SongUtilitiesWindow:
    """Main window for Song Utilities."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.db = get_database()
        self.settings = get_settings()
        
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("Song Utilities - Musical Tools Suite")
        self.window.geometry("1000x700")
        self.window.resizable(True, True)
        
        # Initialize metronome
        self.metronome = PracticeMetronome(window=self.window)
        
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
        # Create notebook for different tools
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_transposition_tab()
        self.create_analysis_tab()
        self.create_practice_tab()
        self.create_chord_tools_tab()
    
    def create_transposition_tab(self):
        """Create the transposition tools tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Transposition")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input section
        input_frame = tk.LabelFrame(main_frame, text="Input", font=("Arial", 12, "bold"))
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Song selection
        song_frame = tk.Frame(input_frame)
        song_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(song_frame, text="Select Song:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.song_combo = ttk.Combobox(song_frame, state="readonly", width=40)
        self.song_combo.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.song_combo.bind("<<ComboboxSelected>>", self.on_song_selected)
        
        tk.Button(song_frame, text="Load", command=self.load_song_list).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Content input
        content_frame = tk.Frame(input_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(content_frame, text="Content:", font=("Arial", 10)).pack(anchor=tk.W)
        
        self.content_text = tk.Text(content_frame, height=8, wrap=tk.WORD, font=("Consolas", 10))
        content_scroll = tk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scroll.set)
        
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Transposition controls
        controls_frame = tk.LabelFrame(main_frame, text="Transposition Controls", font=("Arial", 12, "bold"))
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Method selection
        method_frame = tk.Frame(controls_frame)
        method_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(method_frame, text="Method:", font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.transpose_method = tk.StringVar(value="semitones")
        tk.Radiobutton(method_frame, text="By Semitones", variable=self.transpose_method, 
                      value="semitones", command=self.on_method_changed).pack(side=tk.LEFT, padx=(10, 0))
        tk.Radiobutton(method_frame, text="By Key", variable=self.transpose_method, 
                      value="key", command=self.on_method_changed).pack(side=tk.LEFT, padx=(10, 0))
        tk.Radiobutton(method_frame, text="By Capo", variable=self.transpose_method, 
                      value="capo", command=self.on_method_changed).pack(side=tk.LEFT, padx=(10, 0))
        
        # Semitones control
        self.semitones_frame = tk.Frame(controls_frame)
        self.semitones_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.semitones_frame, text="Semitones:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.semitones_var = tk.IntVar(value=0)
        semitones_scale = tk.Scale(self.semitones_frame, from_=-12, to=12, orient=tk.HORIZONTAL,
                                 variable=self.semitones_var, length=200)
        semitones_scale.pack(side=tk.LEFT, padx=(10, 0))
        
        # Key control
        self.key_frame = tk.Frame(controls_frame)
        
        tk.Label(self.key_frame, text="From Key:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.from_key_combo = ttk.Combobox(self.key_frame, values=MusicTheoryEngine.CHROMATIC_SCALE, 
                                         state="readonly", width=8)
        self.from_key_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(self.key_frame, text="To Key:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.to_key_combo = ttk.Combobox(self.key_frame, values=MusicTheoryEngine.CHROMATIC_SCALE, 
                                       state="readonly", width=8)
        self.to_key_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Capo control
        self.capo_frame = tk.Frame(controls_frame)
        
        tk.Label(self.capo_frame, text="Capo Position:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.capo_var = tk.IntVar(value=0)
        capo_scale = tk.Scale(self.capo_frame, from_=0, to=12, orient=tk.HORIZONTAL,
                            variable=self.capo_var, length=200)
        capo_scale.pack(side=tk.LEFT, padx=(10, 0))
        
        # Action buttons
        action_frame = tk.Frame(controls_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(action_frame, text="Transpose", command=self.transpose_content,
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(action_frame, text="Clear", command=self.clear_content,
                 bg="#f44336", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(action_frame, text="Save Result", command=self.save_transposed_content,
                 bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        
        # Result section
        result_frame = tk.LabelFrame(main_frame, text="Transposed Result", font=("Arial", 12, "bold"))
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(result_frame, height=8, wrap=tk.WORD, font=("Consolas", 10),
                                 state=tk.DISABLED, bg="#f8f9fa")
        result_scroll = tk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scroll.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Initialize UI state
        self.on_method_changed()
        self.load_song_list()
    
    def create_analysis_tab(self):
        """Create the chord analysis tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Analysis")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input section
        input_frame = tk.LabelFrame(main_frame, text="Chord Progression Input", font=("Arial", 12, "bold"))
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Chord input
        chord_input_frame = tk.Frame(input_frame)
        chord_input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(chord_input_frame, text="Chords (space-separated):", font=("Arial", 10)).pack(anchor=tk.W)
        self.chord_input = tk.Entry(chord_input_frame, font=("Arial", 12))
        self.chord_input.pack(fill=tk.X, pady=(5, 0))
        self.chord_input.bind("<Return>", lambda e: self.analyze_progression())
        
        # Key input
        key_input_frame = tk.Frame(input_frame)
        key_input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(key_input_frame, text="Key (optional):", font=("Arial", 10)).pack(side=tk.LEFT)
        self.analysis_key_combo = ttk.Combobox(key_input_frame, values=MusicTheoryEngine.CHROMATIC_SCALE, 
                                             width=8)
        self.analysis_key_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(key_input_frame, text="Analyze", command=self.analyze_progression,
                 bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        
        # Results section
        results_frame = tk.LabelFrame(main_frame, text="Analysis Results", font=("Arial", 12, "bold"))
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for results
        columns = ("Chord", "Root", "Quality", "Roman", "Function")
        self.analysis_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.analysis_tree.heading(col, text=col)
            self.analysis_tree.column(col, width=100)
        
        analysis_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.analysis_tree.yview)
        self.analysis_tree.configure(yscrollcommand=analysis_scroll.set)
        
        self.analysis_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        analysis_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Key suggestions
        suggestions_frame = tk.Frame(results_frame)
        suggestions_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(suggestions_frame, text="Suggested Keys:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.key_suggestions_label = tk.Label(suggestions_frame, text="", font=("Arial", 10))
        self.key_suggestions_label.pack(anchor=tk.W)
    
    def create_practice_tab(self):
        """Create the practice tools tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Practice Tools")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Metronome section
        metronome_frame = tk.LabelFrame(main_frame, text="Metronome", font=("Arial", 12, "bold"))
        metronome_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tempo controls
        tempo_frame = tk.Frame(metronome_frame)
        tempo_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(tempo_frame, text="Tempo (BPM):", font=("Arial", 10)).pack(side=tk.LEFT)
        self.tempo_var = tk.IntVar(value=120)
        tempo_scale = tk.Scale(tempo_frame, from_=40, to=300, orient=tk.HORIZONTAL,
                             variable=self.tempo_var, length=200, command=self.on_tempo_changed)
        tempo_scale.pack(side=tk.LEFT, padx=(10, 0))
        
        self.tempo_display = tk.Label(tempo_frame, text="120", font=("Arial", 12, "bold"))
        self.tempo_display.pack(side=tk.LEFT, padx=(10, 0))
        
        # Time signature
        time_sig_frame = tk.Frame(metronome_frame)
        time_sig_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(time_sig_frame, text="Time Signature:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.time_sig_var = tk.IntVar(value=4)
        time_sig_combo = ttk.Combobox(time_sig_frame, textvariable=self.time_sig_var,
                                    values=[2, 3, 4, 5, 6, 8], state="readonly", width=5)
        time_sig_combo.pack(side=tk.LEFT, padx=(10, 0))
        time_sig_combo.bind("<<ComboboxSelected>>", self.on_time_sig_changed)
        
        # Metronome controls
        metro_controls = tk.Frame(metronome_frame)
        metro_controls.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.metro_start_btn = tk.Button(metro_controls, text="Start", command=self.start_metronome,
                                       bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.metro_start_btn.pack(side=tk.LEFT)
        
        self.metro_stop_btn = tk.Button(metro_controls, text="Stop", command=self.stop_metronome,
                                      bg="#f44336", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED)
        self.metro_stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Beat indicator
        self.beat_indicator = tk.Label(metro_controls, text="♩", font=("Arial", 24), fg="#666666")
        self.beat_indicator.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Tempo trainer section
        trainer_frame = tk.LabelFrame(main_frame, text="Tempo Trainer", font=("Arial", 12, "bold"))
        trainer_frame.pack(fill=tk.X, pady=(0, 10))
        
        trainer_controls = tk.Frame(trainer_frame)
        trainer_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(trainer_controls, text="Start BPM:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.start_bpm_var = tk.IntVar(value=80)
        start_bpm_spin = tk.Spinbox(trainer_controls, from_=40, to=200, textvariable=self.start_bpm_var, width=8)
        start_bpm_spin.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(trainer_controls, text="Target BPM:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.target_bpm_var = tk.IntVar(value=120)
        target_bpm_spin = tk.Spinbox(trainer_controls, from_=40, to=300, textvariable=self.target_bpm_var, width=8)
        target_bpm_spin.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(trainer_controls, text="Increment:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.increment_var = tk.IntVar(value=5)
        increment_spin = tk.Spinbox(trainer_controls, from_=1, to=20, textvariable=self.increment_var, width=8)
        increment_spin.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(trainer_controls, text="Start Training", command=self.start_tempo_training,
                 bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        
        # Practice session tracking
        session_frame = tk.LabelFrame(main_frame, text="Practice Session", font=("Arial", 12, "bold"))
        session_frame.pack(fill=tk.BOTH, expand=True)
        
        session_controls = tk.Frame(session_frame)
        session_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(session_controls, text="Current Song:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.practice_song_combo = ttk.Combobox(session_controls, state="readonly", width=30)
        self.practice_song_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(session_controls, text="Start Session", command=self.start_practice_session,
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        
        # Session info
        session_info = tk.Frame(session_frame)
        session_info.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.session_time_label = tk.Label(session_info, text="Session Time: 00:00", font=("Arial", 12))
        self.session_time_label.pack(anchor=tk.W)
        
        self.session_notes_text = tk.Text(session_info, height=4, wrap=tk.WORD)
        self.session_notes_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Load songs for practice
        self.load_practice_songs()
    
    def create_chord_tools_tab(self):
        """Create the chord tools tab."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text="Chord Tools")
        
        # Main container
        main_frame = tk.Frame(tab_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chord finder section
        finder_frame = tk.LabelFrame(main_frame, text="Chord Finder", font=("Arial", 12, "bold"))
        finder_frame.pack(fill=tk.X, pady=(0, 10))
        
        finder_controls = tk.Frame(finder_frame)
        finder_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(finder_controls, text="Root Note:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.chord_root_combo = ttk.Combobox(finder_controls, values=MusicTheoryEngine.CHROMATIC_SCALE,
                                           state="readonly", width=8)
        self.chord_root_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(finder_controls, text="Quality:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 0))
        chord_qualities = ["major", "minor", "diminished", "augmented", "major7", "minor7", "dominant7"]
        self.chord_quality_combo = ttk.Combobox(finder_controls, values=chord_qualities,
                                              state="readonly", width=12)
        self.chord_quality_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(finder_controls, text="Find Chord", command=self.find_chord,
                 bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        
        # Chord display
        chord_display = tk.Frame(finder_frame)
        chord_display.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.chord_name_label = tk.Label(chord_display, text="", font=("Arial", 16, "bold"))
        self.chord_name_label.pack(anchor=tk.W)
        
        self.chord_notes_label = tk.Label(chord_display, text="", font=("Arial", 12))
        self.chord_notes_label.pack(anchor=tk.W)
        
        # Scale finder section
        scale_frame = tk.LabelFrame(main_frame, text="Scale Finder", font=("Arial", 12, "bold"))
        scale_frame.pack(fill=tk.X, pady=(0, 10))
        
        scale_controls = tk.Frame(scale_frame)
        scale_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(scale_controls, text="Key:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.scale_key_combo = ttk.Combobox(scale_controls, values=MusicTheoryEngine.CHROMATIC_SCALE,
                                          state="readonly", width=8)
        self.scale_key_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Label(scale_controls, text="Mode:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 0))
        scale_modes = ["major", "minor", "dorian", "phrygian", "lydian", "mixolydian", "locrian"]
        self.scale_mode_combo = ttk.Combobox(scale_controls, values=scale_modes,
                                           state="readonly", width=12)
        self.scale_mode_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(scale_controls, text="Find Scale", command=self.find_scale,
                 bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        
        # Scale display
        scale_display = tk.Frame(scale_frame)
        scale_display.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.scale_name_label = tk.Label(scale_display, text="", font=("Arial", 16, "bold"))
        self.scale_name_label.pack(anchor=tk.W)
        
        self.scale_notes_label = tk.Label(scale_display, text="", font=("Arial", 12))
        self.scale_notes_label.pack(anchor=tk.W)
        
        # Chord progression builder
        builder_frame = tk.LabelFrame(main_frame, text="Chord Progression Builder", font=("Arial", 12, "bold"))
        builder_frame.pack(fill=tk.BOTH, expand=True)
        
        builder_controls = tk.Frame(builder_frame)
        builder_controls.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(builder_controls, text="Key:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.builder_key_combo = ttk.Combobox(builder_controls, values=MusicTheoryEngine.CHROMATIC_SCALE,
                                            state="readonly", width=8)
        self.builder_key_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.builder_key_combo.bind("<<ComboboxSelected>>", self.on_builder_key_changed)
        
        tk.Button(builder_controls, text="Generate Common Progressions", command=self.generate_progressions,
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        
        # Progression list
        self.progression_listbox = tk.Listbox(builder_frame, height=8, font=("Consolas", 10))
        progression_scroll = tk.Scrollbar(builder_frame, orient=tk.VERTICAL, command=self.progression_listbox.yview)
        self.progression_listbox.configure(yscrollcommand=progression_scroll.set)
        
        self.progression_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        progression_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))
    
    # Event handlers and methods
    
    def on_method_changed(self):
        """Handle transposition method change."""
        method = self.transpose_method.get()
        
        # Hide all frames first
        self.semitones_frame.pack_forget()
        self.key_frame.pack_forget()
        self.capo_frame.pack_forget()
        
        # Show appropriate frame
        if method == "semitones":
            self.semitones_frame.pack(fill=tk.X, padx=10, pady=5)
        elif method == "key":
            self.key_frame.pack(fill=tk.X, padx=10, pady=5)
        elif method == "capo":
            self.capo_frame.pack(fill=tk.X, padx=10, pady=5)
    
    def load_song_list(self):
        """Load songs from database."""
        try:
            songs = self.db.get_songs()
            song_names = [f"{song['title']} - {song.get('artist', 'Unknown')}" for song in songs]
            
            # Update song combo if it exists
            if hasattr(self, 'song_combo'):
                self.song_combo['values'] = song_names
            
            # Update practice song combo if it exists
            if hasattr(self, 'practice_song_combo'):
                self.practice_song_combo['values'] = song_names
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading songs: {str(e)}")
    
    def load_practice_songs(self):
        """Load songs for practice session."""
        self.load_song_list()
    
    def on_song_selected(self, event=None):
        """Handle song selection."""
        selection = self.song_combo.get()
        if not selection:
            return
        
        try:
            # Extract song title from selection
            title = selection.split(" - ")[0]
            songs = self.db.get_songs(search_term=title)
            
            if songs:
                song = songs[0]
                content = song.get('content') or song.get('lyrics') or ""
                self.content_text.delete(1.0, tk.END)
                self.content_text.insert(1.0, content)
                
                # Set key if available
                if song.get('key_signature'):
                    self.from_key_combo.set(song['key_signature'])
                    self.analysis_key_combo.set(song['key_signature'])
        except Exception as e:
            messagebox.showerror("Error", f"Error loading song: {str(e)}")
    
    def transpose_content(self):
        """Transpose the content based on selected method."""
        content = self.content_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "Please enter content to transpose.")
            return
        
        try:
            method = self.transpose_method.get()
            
            if method == "semitones":
                semitones = self.semitones_var.get()
                result = TranspositionEngine.transpose_content(content, semitones)
            elif method == "key":
                from_key = self.from_key_combo.get()
                to_key = self.to_key_combo.get()
                if not from_key or not to_key:
                    messagebox.showwarning("Warning", "Please select both keys.")
                    return
                result = TranspositionEngine.transpose_by_key(content, from_key, to_key)
            elif method == "capo":
                capo_pos = self.capo_var.get()
                # Capo effectively transposes down
                result = TranspositionEngine.transpose_content(content, -capo_pos)
            else:
                return
            
            # Display result
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, result.transposed_content)
            self.result_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error transposing content: {str(e)}")
    
    def clear_content(self):
        """Clear all content."""
        self.content_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)
    
    def save_transposed_content(self):
        """Save the transposed content."""
        content = self.result_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "No transposed content to save.")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                title="Save Transposed Content",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Content saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving content: {str(e)}")
    
    def analyze_progression(self):
        """Analyze the chord progression."""
        chord_input = self.chord_input.get().strip()
        if not chord_input:
            messagebox.showwarning("Warning", "Please enter chords to analyze.")
            return
        
        try:
            chords = chord_input.split()
            key_name = self.analysis_key_combo.get() or None
            
            analysis = MusicTheoryEngine.analyze_chord_progression(chords, key_name)
            
            # Clear previous results
            for item in self.analysis_tree.get_children():
                self.analysis_tree.delete(item)
            
            # Populate results
            for i, chord_analysis in enumerate(analysis.get('chords', [])):
                roman = analysis.get('roman_numerals', [None] * len(chords))[i] or ""
                function = analysis.get('functions', [None] * len(chords))[i] or ""
                
                self.analysis_tree.insert("", tk.END, values=(
                    chord_analysis.chord_name,
                    chord_analysis.root,
                    chord_analysis.quality.value,
                    roman,
                    function
                ))
            
            # Show key suggestions
            suggestions = analysis.get('key_suggestions', [])
            if suggestions:
                self.key_suggestions_label.config(text=", ".join(suggestions))
            else:
                self.key_suggestions_label.config(text="No suggestions available")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error analyzing progression: {str(e)}")
    
    def on_tempo_changed(self, value):
        """Handle tempo change."""
        tempo = int(float(value))
        self.tempo_display.config(text=str(tempo))
        self.metronome.set_tempo(tempo)
    
    def on_time_sig_changed(self, event=None):
        """Handle time signature change."""
        beats = self.time_sig_var.get()
        self.metronome.set_time_signature(beats)
    
    def start_metronome(self):
        """Start the metronome."""
        self.metronome.start(self.on_metronome_click)
        self.metro_start_btn.config(state=tk.DISABLED)
        self.metro_stop_btn.config(state=tk.NORMAL)
    
    def stop_metronome(self):
        """Stop the metronome."""
        self.metronome.stop()
        self.metro_start_btn.config(state=tk.NORMAL)
        self.metro_stop_btn.config(state=tk.DISABLED)
        self.beat_indicator.config(text="♩", fg="#666666")
    
    def on_metronome_click(self, beat_number, is_downbeat):
        """Handle metronome click."""
        if is_downbeat:
            self.beat_indicator.config(text="♩", fg="#ff0000", font=("Arial", 28))
        else:
            self.beat_indicator.config(text="♪", fg="#333333", font=("Arial", 24))
        
        # Schedule beat indicator reset
        self.window.after(100, lambda: self.beat_indicator.config(fg="#666666"))
    
    def start_tempo_training(self):
        """Start tempo training session."""
        messagebox.showinfo("Tempo Training", "Tempo training feature coming soon!")
    
    def start_practice_session(self):
        """Start a practice session."""
        song_selection = self.practice_song_combo.get()
        if not song_selection:
            messagebox.showwarning("Warning", "Please select a song to practice.")
            return
        
        messagebox.showinfo("Practice Session", "Practice session tracking feature coming soon!")
    
    def find_chord(self):
        """Find and display chord information."""
        root = self.chord_root_combo.get()
        quality = self.chord_quality_combo.get()
        
        if not root or not quality:
            messagebox.showwarning("Warning", "Please select both root and quality.")
            return
        
        try:
            chord_name = root + ("m" if quality == "minor" else "")
            if quality not in ["major", "minor"]:
                chord_name += quality.replace("major", "maj").replace("dominant", "")
            
            chord_analysis = MusicTheoryEngine.parse_chord(chord_name)
            if chord_analysis:
                self.chord_name_label.config(text=chord_name)
                
                # Calculate chord notes (simplified)
                if MUSIC21_AVAILABLE:
                    try:
                        chord_obj = chord.Chord(chord_name)
                        notes = [str(p) for p in chord_obj.pitches]
                        self.chord_notes_label.config(text=f"Notes: {', '.join(notes)}")
                    except Exception:
                        self.chord_notes_label.config(text="Notes: Unable to calculate")
                else:
                    self.chord_notes_label.config(text="Notes: music21 library required")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error finding chord: {str(e)}")
    
    def find_scale(self):
        """Find and display scale information."""
        key_name = self.scale_key_combo.get()
        mode = self.scale_mode_combo.get()
        
        if not key_name or not mode:
            messagebox.showwarning("Warning", "Please select both key and mode.")
            return
        
        try:
            scale_name = f"{key_name} {mode}"
            key_analysis = MusicTheoryEngine.get_key_signature(key_name)
            
            self.scale_name_label.config(text=scale_name)
            self.scale_notes_label.config(text=f"Notes: {', '.join(key_analysis.scale_degrees)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error finding scale: {str(e)}")
    
    def on_builder_key_changed(self, event=None):
        """Handle key change in progression builder."""
        self.generate_progressions()
    
    def generate_progressions(self):
        """Generate common chord progressions."""
        key_name = self.builder_key_combo.get()
        if not key_name:
            return
        
        try:
            # Common progressions in Roman numerals
            common_progressions = [
                "I - V - vi - IV",
                "vi - IV - I - V", 
                "I - vi - IV - V",
                "ii - V - I",
                "I - IV - V - I",
                "vi - ii - V - I",
                "I - iii - vi - IV",
                "I - V - vi - iii - IV - I - IV - V"
            ]
            
            self.progression_listbox.delete(0, tk.END)
            
            for progression in common_progressions:
                # Convert Roman numerals to actual chords (simplified)
                chord_progression = self._convert_roman_to_chords(progression, key_name)
                self.progression_listbox.insert(tk.END, chord_progression)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error generating progressions: {str(e)}")
    
    def _convert_roman_to_chords(self, roman_progression: str, key_name: str) -> str:
        """Convert Roman numeral progression to actual chords."""
        # Simplified conversion - would need more sophisticated implementation
        roman_to_chord = {
            'I': key_name,
            'ii': MusicTheoryEngine.transpose_note(key_name, 2) + 'm',
            'iii': MusicTheoryEngine.transpose_note(key_name, 4) + 'm',
            'IV': MusicTheoryEngine.transpose_note(key_name, 5),
            'V': MusicTheoryEngine.transpose_note(key_name, 7),
            'vi': MusicTheoryEngine.transpose_note(key_name, 9) + 'm',
            'vii°': MusicTheoryEngine.transpose_note(key_name, 11) + 'dim'
        }
        
        parts = roman_progression.split(' - ')
        chord_parts = []
        
        for part in parts:
            chord = roman_to_chord.get(part.strip(), part.strip())
            chord_parts.append(chord)
        
        return ' - '.join(chord_parts)


def show_song_utilities(parent=None):
    """Show the Song Utilities window."""
    return SongUtilitiesWindow(parent)


if __name__ == "__main__":
    # Test the Song Utilities window
    app = SongUtilitiesWindow()
    app.window.mainloop()
