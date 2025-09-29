# 🔧 Technical Specifications - Musical Tools Suite

## Database Schema Design

### Core Tables

```sql
-- Songs and Ciphers
CREATE TABLE songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT,
    album TEXT,
    key_signature TEXT,
    tempo INTEGER,
    time_signature TEXT DEFAULT '4/4',
    genre TEXT,
    difficulty_rating INTEGER CHECK(difficulty_rating BETWEEN 1 AND 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT,
    source_url TEXT,
    notes TEXT
);

-- Chord Progressions
CREATE TABLE chord_progressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
    section_name TEXT, -- verse, chorus, bridge, etc.
    bar_number INTEGER,
    beat_position REAL,
    chord_symbol TEXT NOT NULL,
    duration REAL DEFAULT 1.0,
    bass_note TEXT,
    chord_quality TEXT, -- major, minor, dominant7, etc.
    roman_numeral TEXT,
    function TEXT -- tonic, dominant, subdominant, etc.
);

-- Lyrics with Chord Annotations
CREATE TABLE lyrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
    line_number INTEGER,
    text_content TEXT,
    chord_positions TEXT, -- JSON array of chord positions
    section_name TEXT
);

-- Practice Sessions
CREATE TABLE practice_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER REFERENCES songs(id),
    session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_minutes INTEGER,
    tempo_practiced INTEGER,
    accuracy_score REAL,
    notes TEXT,
    tool_used TEXT -- tuner, chord_identifier, etc.
);

-- Custom Tunings
CREATE TABLE custom_tunings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    instrument TEXT NOT NULL,
    string_count INTEGER,
    tuning_notes TEXT NOT NULL, -- JSON array
    created_by_user BOOLEAN DEFAULT TRUE,
    description TEXT
);

-- Audio Analysis Cache
CREATE TABLE audio_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE NOT NULL,
    file_path TEXT,
    analysis_type TEXT, -- chord_detection, pitch_analysis, etc.
    analysis_data TEXT, -- JSON results
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes for Performance

```sql
-- Search optimization
CREATE INDEX idx_songs_title ON songs(title);
CREATE INDEX idx_songs_artist ON songs(artist);
CREATE INDEX idx_songs_key ON songs(key_signature);
CREATE INDEX idx_songs_genre ON songs(genre);

-- Chord progression queries
CREATE INDEX idx_chord_progressions_song ON chord_progressions(song_id);
CREATE INDEX idx_chord_progressions_chord ON chord_progressions(chord_symbol);
CREATE INDEX idx_chord_progressions_section ON chord_progressions(section_name);

-- Full-text search
CREATE VIRTUAL TABLE songs_fts USING fts5(title, artist, album, notes, content='songs', content_rowid='id');
```

---

## Audio Processing Architecture

### Real-time Audio Pipeline

```python
class AudioProcessor:
    """Core audio processing engine for all tools."""
    
    def __init__(self, sample_rate=44100, buffer_size=1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.audio_stream = None
        self.processors = []  # Chain of audio processors
        
    def add_processor(self, processor):
        """Add audio processor to the chain."""
        self.processors.append(processor)
        
    def process_audio_frame(self, audio_data):
        """Process single audio frame through all processors."""
        result = audio_data
        for processor in self.processors:
            result = processor.process(result)
        return result

class PitchDetector:
    """High-precision pitch detection using multiple algorithms."""
    
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.yin_detector = YINPitchDetector(sample_rate)
        self.autocorr_detector = AutocorrelationDetector(sample_rate)
        self.fft_detector = FFTPitchDetector(sample_rate)
        
    def detect_pitch(self, audio_data):
        """Combine multiple pitch detection methods for accuracy."""
        pitches = []
        confidences = []
        
        # YIN algorithm (good for monophonic sources)
        yin_pitch, yin_conf = self.yin_detector.detect(audio_data)
        if yin_conf > 0.8:
            pitches.append(yin_pitch)
            confidences.append(yin_conf)
            
        # Autocorrelation (robust to noise)
        autocorr_pitch, autocorr_conf = self.autocorr_detector.detect(audio_data)
        if autocorr_conf > 0.7:
            pitches.append(autocorr_pitch)
            confidences.append(autocorr_conf)
            
        # FFT-based (good for harmonic content)
        fft_pitch, fft_conf = self.fft_detector.detect(audio_data)
        if fft_conf > 0.6:
            pitches.append(fft_pitch)
            confidences.append(fft_conf)
            
        # Weighted average of detected pitches
        if pitches:
            weighted_pitch = np.average(pitches, weights=confidences)
            avg_confidence = np.mean(confidences)
            return weighted_pitch, avg_confidence
        
        return 0.0, 0.0

class ChordDetector:
    """Polyphonic chord detection using chromagram analysis."""
    
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.chroma_extractor = ChromaExtractor(sample_rate)
        self.chord_templates = self.load_chord_templates()
        
    def detect_chord(self, audio_data):
        """Detect chord from audio using template matching."""
        # Extract chromagram
        chroma = self.chroma_extractor.extract(audio_data)
        
        # Normalize chromagram
        chroma_norm = chroma / (np.sum(chroma) + 1e-8)
        
        # Template matching
        best_match = None
        best_score = 0.0
        
        for chord_name, template in self.chord_templates.items():
            # Calculate correlation with template
            score = np.corrcoef(chroma_norm, template)[0, 1]
            if score > best_score:
                best_score = score
                best_match = chord_name
                
        return best_match, best_score
```

---

## Music Theory Engine

### Chord and Scale Representation

```python
class Note:
    """Represents a musical note with enharmonic handling."""
    
    CHROMATIC_SCALE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    FLAT_SCALE = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
    
    def __init__(self, note_name, octave=4, accidental_preference='sharp'):
        self.note_name = note_name
        self.octave = octave
        self.accidental_preference = accidental_preference
        
    def to_midi_number(self):
        """Convert to MIDI note number."""
        note_index = self.CHROMATIC_SCALE.index(self.note_name.replace('b', '#'))
        return (self.octave + 1) * 12 + note_index
        
    def transpose(self, semitones):
        """Transpose note by semitones."""
        midi_num = self.to_midi_number() + semitones
        new_octave = (midi_num // 12) - 1
        note_index = midi_num % 12
        
        if self.accidental_preference == 'flat':
            new_note = self.FLAT_SCALE[note_index]
        else:
            new_note = self.CHROMATIC_SCALE[note_index]
            
        return Note(new_note, new_octave, self.accidental_preference)

class Chord:
    """Represents a musical chord with full harmonic analysis."""
    
    CHORD_QUALITIES = {
        'major': [0, 4, 7],
        'minor': [0, 3, 7],
        'dominant7': [0, 4, 7, 10],
        'major7': [0, 4, 7, 11],
        'minor7': [0, 3, 7, 10],
        'diminished': [0, 3, 6],
        'augmented': [0, 4, 8],
        'sus2': [0, 2, 7],
        'sus4': [0, 5, 7],
        'add9': [0, 4, 7, 14],
        'minor9': [0, 3, 7, 10, 14],
        'major9': [0, 4, 7, 11, 14],
        'dominant9': [0, 4, 7, 10, 14],
        'minor11': [0, 3, 7, 10, 14, 17],
        'major11': [0, 4, 7, 11, 14, 17],
        'dominant11': [0, 4, 7, 10, 14, 17],
        'minor13': [0, 3, 7, 10, 14, 17, 21],
        'major13': [0, 4, 7, 11, 14, 17, 21],
        'dominant13': [0, 4, 7, 10, 14, 17, 21]
    }
    
    def __init__(self, root_note, quality='major', bass_note=None, inversion=0):
        self.root_note = Note(root_note) if isinstance(root_note, str) else root_note
        self.quality = quality
        self.bass_note = Note(bass_note) if bass_note and isinstance(bass_note, str) else bass_note
        self.inversion = inversion
        
    def get_notes(self):
        """Get all notes in the chord."""
        intervals = self.CHORD_QUALITIES[self.quality]
        root_midi = self.root_note.to_midi_number()
        
        chord_notes = []
        for interval in intervals:
            note_midi = root_midi + interval
            octave = (note_midi // 12) - 1
            note_index = note_midi % 12
            note_name = Note.CHROMATIC_SCALE[note_index]
            chord_notes.append(Note(note_name, octave))
            
        # Apply inversion
        if self.inversion > 0:
            for _ in range(self.inversion):
                chord_notes.append(chord_notes.pop(0).transpose(12))
                
        return chord_notes
        
    def to_roman_numeral(self, key):
        """Convert chord to roman numeral analysis."""
        # Implementation for roman numeral analysis
        pass

class Scale:
    """Represents musical scales and modes."""
    
    SCALE_PATTERNS = {
        'major': [0, 2, 4, 5, 7, 9, 11],
        'natural_minor': [0, 2, 3, 5, 7, 8, 10],
        'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
        'melodic_minor': [0, 2, 3, 5, 7, 9, 11],
        'dorian': [0, 2, 3, 5, 7, 9, 10],
        'phrygian': [0, 1, 3, 5, 7, 8, 10],
        'lydian': [0, 2, 4, 6, 7, 9, 11],
        'mixolydian': [0, 2, 4, 5, 7, 9, 10],
        'locrian': [0, 1, 3, 5, 6, 8, 10],
        'blues': [0, 3, 5, 6, 7, 10],
        'pentatonic_major': [0, 2, 4, 7, 9],
        'pentatonic_minor': [0, 3, 5, 7, 10]
    }
    
    def __init__(self, root_note, scale_type='major'):
        self.root_note = Note(root_note) if isinstance(root_note, str) else root_note
        self.scale_type = scale_type
        
    def get_notes(self):
        """Get all notes in the scale."""
        pattern = self.SCALE_PATTERNS[self.scale_type]
        root_midi = self.root_note.to_midi_number()
        
        scale_notes = []
        for interval in pattern:
            note_midi = root_midi + interval
            octave = (note_midi // 12) - 1
            note_index = note_midi % 12
            note_name = Note.CHROMATIC_SCALE[note_index]
            scale_notes.append(Note(note_name, octave))
            
        return scale_notes
        
    def get_chords(self, chord_type='triad'):
        """Generate chords from scale degrees."""
        scale_notes = self.get_notes()
        chords = []
        
        for i, root in enumerate(scale_notes):
            if chord_type == 'triad':
                # Build triad (1-3-5)
                third = scale_notes[(i + 2) % len(scale_notes)]
                fifth = scale_notes[(i + 4) % len(scale_notes)]
                
                # Determine chord quality
                third_interval = (third.to_midi_number() - root.to_midi_number()) % 12
                fifth_interval = (fifth.to_midi_number() - root.to_midi_number()) % 12
                
                if third_interval == 4 and fifth_interval == 7:
                    quality = 'major'
                elif third_interval == 3 and fifth_interval == 7:
                    quality = 'minor'
                elif third_interval == 3 and fifth_interval == 6:
                    quality = 'diminished'
                else:
                    quality = 'major'  # fallback
                    
                chords.append(Chord(root.note_name, quality))
                
        return chords
```

---

## MIDI Generation System

### Chord Progression to MIDI

```python
class MIDIGenerator:
    """Generate MIDI files from chord progressions."""
    
    def __init__(self, tempo=120, time_signature=(4, 4)):
        self.tempo = tempo
        self.time_signature = time_signature
        self.ticks_per_beat = 480
        
    def chord_progression_to_midi(self, chord_progression, style='piano'):
        """Convert chord progression to MIDI file."""
        mid = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        # Add tempo and time signature
        track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(self.tempo)))
        track.append(mido.MetaMessage('time_signature', numerator=self.time_signature[0], 
                                    denominator=self.time_signature[1]))
        
        current_time = 0
        
        for chord_info in chord_progression:
            chord = Chord(chord_info['root'], chord_info['quality'])
            duration_ticks = int(chord_info['duration'] * self.ticks_per_beat)
            
            if style == 'piano':
                self._add_piano_chord(track, chord, current_time, duration_ticks)
            elif style == 'guitar':
                self._add_guitar_chord(track, chord, current_time, duration_ticks)
            elif style == 'bass':
                self._add_bass_line(track, chord, current_time, duration_ticks)
                
            current_time += duration_ticks
            
        return mid
        
    def _add_piano_chord(self, track, chord, start_time, duration):
        """Add piano-style chord to MIDI track."""
        notes = chord.get_notes()
        velocity = 64
        
        # Note on messages
        for i, note in enumerate(notes):
            track.append(mido.Message('note_on', channel=0, note=note.to_midi_number(),
                                    velocity=velocity, time=start_time if i == 0 else 0))
        
        # Note off messages
        for i, note in enumerate(notes):
            track.append(mido.Message('note_off', channel=0, note=note.to_midi_number(),
                                    velocity=0, time=duration if i == 0 else 0))
                                    
    def _add_guitar_chord(self, track, chord, start_time, duration):
        """Add guitar-style strumming pattern."""
        notes = chord.get_notes()
        strum_delay = 20  # Ticks between notes in strum
        
        # Downstroke
        for i, note in enumerate(notes):
            track.append(mido.Message('note_on', channel=0, note=note.to_midi_number(),
                                    velocity=80, time=start_time + (i * strum_delay)))
            track.append(mido.Message('note_off', channel=0, note=note.to_midi_number(),
                                    velocity=0, time=duration - (i * strum_delay)))

class RhythmGenerator:
    """Generate rhythm patterns for different styles."""
    
    PATTERNS = {
        'rock_4_4': [1, 0, 0.5, 0, 1, 0, 0.5, 0],  # Strong on 1 and 3
        'ballad_4_4': [1, 0, 0, 0, 0.7, 0, 0, 0],  # Emphasis on 1 and 3
        'waltz_3_4': [1, 0, 0, 0.6, 0, 0, 0.6, 0, 0],  # 3/4 time
        'reggae_4_4': [0, 0, 1, 0, 0, 0, 1, 0],  # Off-beat emphasis
        'bossa_nova': [1, 0, 0.3, 0.7, 0, 0.5, 0, 0.8]  # Syncopated
    }
    
    def apply_rhythm(self, chord_progression, pattern_name='rock_4_4'):
        """Apply rhythm pattern to chord progression."""
        pattern = self.PATTERNS[pattern_name]
        rhythmic_progression = []
        
        for chord_info in chord_progression:
            base_duration = chord_info['duration']
            subdivision = base_duration / len(pattern)
            
            for i, accent in enumerate(pattern):
                if accent > 0:
                    rhythmic_chord = chord_info.copy()
                    rhythmic_chord['duration'] = subdivision
                    rhythmic_chord['velocity'] = int(127 * accent)
                    rhythmic_chord['start_time'] = i * subdivision
                    rhythmic_progression.append(rhythmic_chord)
                    
        return rhythmic_progression
```

---

## Plugin Architecture

### Plugin Interface

```python
class MusicalToolPlugin:
    """Base class for all musical tool plugins."""
    
    def __init__(self, name, version, description):
        self.name = name
        self.version = version
        self.description = description
        self.enabled = True
        
    def initialize(self, app_context):
        """Initialize plugin with application context."""
        self.app_context = app_context
        
    def get_menu_items(self):
        """Return menu items to add to application menu."""
        return []
        
    def get_toolbar_items(self):
        """Return toolbar items to add to application toolbar."""
        return []
        
    def process_audio(self, audio_data):
        """Process audio data (optional)."""
        return audio_data
        
    def handle_chord_change(self, chord):
        """Handle chord change events (optional)."""
        pass
        
    def cleanup(self):
        """Cleanup resources when plugin is disabled."""
        pass

class PluginManager:
    """Manages loading and execution of plugins."""
    
    def __init__(self, plugin_directory='plugins'):
        self.plugin_directory = plugin_directory
        self.plugins = {}
        self.enabled_plugins = set()
        
    def load_plugins(self):
        """Load all plugins from plugin directory."""
        import importlib.util
        import os
        
        for filename in os.listdir(self.plugin_directory):
            if filename.endswith('.py') and not filename.startswith('__'):
                plugin_path = os.path.join(self.plugin_directory, filename)
                spec = importlib.util.spec_from_file_location(filename[:-3], plugin_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for plugin class
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, MusicalToolPlugin) and 
                        attr != MusicalToolPlugin):
                        
                        plugin_instance = attr()
                        self.plugins[plugin_instance.name] = plugin_instance
                        
    def enable_plugin(self, plugin_name):
        """Enable a plugin."""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = True
            self.enabled_plugins.add(plugin_name)
            
    def disable_plugin(self, plugin_name):
        """Disable a plugin."""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = False
            self.plugins[plugin_name].cleanup()
            self.enabled_plugins.discard(plugin_name)
            
    def broadcast_chord_change(self, chord):
        """Broadcast chord change to all enabled plugins."""
        for plugin_name in self.enabled_plugins:
            plugin = self.plugins[plugin_name]
            try:
                plugin.handle_chord_change(chord)
            except Exception as e:
                print(f"Plugin {plugin_name} error: {e}")
```

---

## Performance Optimization

### Audio Processing Optimization

```python
class OptimizedAudioProcessor:
    """Optimized audio processor using circular buffers and threading."""
    
    def __init__(self, sample_rate=44100, buffer_size=1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        
        # Circular buffer for audio data
        self.audio_buffer = np.zeros(buffer_size * 4, dtype=np.float32)
        self.write_pos = 0
        self.read_pos = 0
        
        # Pre-allocated arrays for processing
        self.fft_buffer = np.zeros(buffer_size, dtype=np.complex64)
        self.window = np.hanning(buffer_size).astype(np.float32)
        
        # Threading for real-time processing
        self.processing_thread = None
        self.stop_processing = threading.Event()
        
    def add_audio_data(self, data):
        """Add audio data to circular buffer."""
        data_len = len(data)
        
        # Handle buffer wrap-around
        if self.write_pos + data_len <= len(self.audio_buffer):
            self.audio_buffer[self.write_pos:self.write_pos + data_len] = data
        else:
            # Split write across buffer boundary
            first_part = len(self.audio_buffer) - self.write_pos
            self.audio_buffer[self.write_pos:] = data[:first_part]
            self.audio_buffer[:data_len - first_part] = data[first_part:]
            
        self.write_pos = (self.write_pos + data_len) % len(self.audio_buffer)
        
    def get_latest_buffer(self):
        """Get latest buffer_size samples."""
        if self.write_pos >= self.buffer_size:
            return self.audio_buffer[self.write_pos - self.buffer_size:self.write_pos]
        else:
            # Handle wrap-around
            first_part = self.buffer_size - self.write_pos
            result = np.zeros(self.buffer_size, dtype=np.float32)
            result[:first_part] = self.audio_buffer[len(self.audio_buffer) - first_part:]
            result[first_part:] = self.audio_buffer[:self.write_pos]
            return result
            
    def process_with_fft(self, audio_data):
        """Optimized FFT processing."""
        # Apply window
        windowed = audio_data * self.window
        
        # In-place FFT
        self.fft_buffer[:len(windowed)] = windowed
        np.fft.fft(self.fft_buffer, overwrite_x=True)
        
        return self.fft_buffer
```

### Database Query Optimization

```python
class OptimizedSongDatabase:
    """Optimized database operations with caching."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection_pool = []
        self.query_cache = {}
        self.cache_size = 100
        
    def get_connection(self):
        """Get database connection from pool."""
        if self.connection_pool:
            return self.connection_pool.pop()
        else:
            return sqlite3.connect(self.db_path)
            
    def return_connection(self, conn):
        """Return connection to pool."""
        if len(self.connection_pool) < 10:  # Max pool size
            self.connection_pool.append(conn)
        else:
            conn.close()
            
    def search_songs_optimized(self, query, limit=50):
        """Optimized song search with caching."""
        cache_key = f"search:{query}:{limit}"
        
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
            
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Use FTS for full-text search
            cursor.execute("""
                SELECT s.id, s.title, s.artist, s.key_signature, s.tempo
                FROM songs s
                JOIN songs_fts fts ON s.id = fts.rowid
                WHERE songs_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = cursor.fetchall()
            
            # Cache results
            if len(self.query_cache) >= self.cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self.query_cache))
                del self.query_cache[oldest_key]
                
            self.query_cache[cache_key] = results
            return results
            
        finally:
            self.return_connection(conn)
```

---

This technical specification provides the foundation for implementing a robust, scalable musical tools suite with professional-grade audio processing, efficient database operations, and extensible plugin architecture.
