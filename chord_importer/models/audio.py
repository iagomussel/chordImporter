"""
Audio-related data models.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


class AudioFormat(Enum):
    """Audio format enumeration."""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"
    M4A = "m4a"


class WindowType(Enum):
    """Window function types for audio processing."""
    HANNING = "hanning"
    HAMMING = "hamming"
    BLACKMAN = "blackman"
    RECTANGULAR = "rectangular"


@dataclass
class DeviceInfo:
    """Audio device information."""
    index: int
    name: str
    channels: int
    sample_rate: float
    is_input: bool = True
    is_output: bool = False
    is_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'index': self.index,
            'name': self.name,
            'channels': self.channels,
            'sample_rate': self.sample_rate,
            'is_input': self.is_input,
            'is_output': self.is_output,
            'is_default': self.is_default
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """Create from dictionary."""
        return cls(
            index=data.get('index', 0),
            name=data.get('name', ''),
            channels=data.get('channels', 1),
            sample_rate=data.get('sample_rate', 44100.0),
            is_input=data.get('is_input', True),
            is_output=data.get('is_output', False),
            is_default=data.get('is_default', False)
        )


@dataclass
class AudioConfig:
    """Audio configuration settings."""
    sample_rate: int = 44100
    channels: int = 1
    chunk_size: int = 1024
    format: AudioFormat = AudioFormat.WAV
    device_index: Optional[int] = None
    window_type: WindowType = WindowType.HANNING
    overlap: float = 0.5
    
    # Processing parameters
    min_frequency: float = 80.0
    max_frequency: float = 2000.0
    threshold: float = 0.01
    
    # Tuner-specific settings
    reference_frequency: float = 440.0  # A4
    cents_tolerance: float = 10.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunk_size': self.chunk_size,
            'format': self.format.value,
            'device_index': self.device_index,
            'window_type': self.window_type.value,
            'overlap': self.overlap,
            'min_frequency': self.min_frequency,
            'max_frequency': self.max_frequency,
            'threshold': self.threshold,
            'reference_frequency': self.reference_frequency,
            'cents_tolerance': self.cents_tolerance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioConfig':
        """Create from dictionary."""
        return cls(
            sample_rate=data.get('sample_rate', 44100),
            channels=data.get('channels', 1),
            chunk_size=data.get('chunk_size', 1024),
            format=AudioFormat(data.get('format', 'wav')),
            device_index=data.get('device_index'),
            window_type=WindowType(data.get('window_type', 'hanning')),
            overlap=data.get('overlap', 0.5),
            min_frequency=data.get('min_frequency', 80.0),
            max_frequency=data.get('max_frequency', 2000.0),
            threshold=data.get('threshold', 0.01),
            reference_frequency=data.get('reference_frequency', 440.0),
            cents_tolerance=data.get('cents_tolerance', 10.0)
        )
    
    def validate(self) -> Tuple[bool, str]:
        """
        Validate audio configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.sample_rate <= 0:
            return False, "Sample rate must be positive"
        
        if self.channels <= 0:
            return False, "Channels must be positive"
        
        if self.chunk_size <= 0:
            return False, "Chunk size must be positive"
        
        if not (0.0 <= self.overlap < 1.0):
            return False, "Overlap must be between 0.0 and 1.0"
        
        if self.min_frequency >= self.max_frequency:
            return False, "Min frequency must be less than max frequency"
        
        if self.threshold < 0:
            return False, "Threshold must be non-negative"
        
        if self.reference_frequency <= 0:
            return False, "Reference frequency must be positive"
        
        if self.cents_tolerance < 0:
            return False, "Cents tolerance must be non-negative"
        
        return True, ""


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis."""
    frequency: float
    amplitude: float
    confidence: float
    note: Optional[str] = None
    octave: Optional[int] = None
    cents_offset: Optional[float] = None
    harmonics: List[float] = field(default_factory=list)
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'frequency': self.frequency,
            'amplitude': self.amplitude,
            'confidence': self.confidence,
            'note': self.note,
            'octave': self.octave,
            'cents_offset': self.cents_offset,
            'harmonics': self.harmonics,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioAnalysisResult':
        """Create from dictionary."""
        return cls(
            frequency=data.get('frequency', 0.0),
            amplitude=data.get('amplitude', 0.0),
            confidence=data.get('confidence', 0.0),
            note=data.get('note'),
            octave=data.get('octave'),
            cents_offset=data.get('cents_offset'),
            harmonics=data.get('harmonics', []),
            timestamp=data.get('timestamp')
        )
    
    @property
    def is_valid(self) -> bool:
        """Check if the result is valid."""
        return (
            self.frequency > 0 and
            self.confidence > 0 and
            self.amplitude > 0
        )
    
    @property
    def note_display(self) -> str:
        """Get formatted note display."""
        if self.note and self.octave is not None:
            cents_str = ""
            if self.cents_offset is not None:
                if self.cents_offset > 0:
                    cents_str = f" (+{self.cents_offset:.0f}¢)"
                elif self.cents_offset < 0:
                    cents_str = f" ({self.cents_offset:.0f}¢)"
            return f"{self.note}{self.octave}{cents_str}"
        return "N/A"


@dataclass
class ChordAnalysisResult:
    """Result of chord analysis."""
    chord: str
    confidence: float
    notes: List[str] = field(default_factory=list)
    bass_note: Optional[str] = None
    quality: Optional[str] = None  # major, minor, diminished, etc.
    extensions: List[str] = field(default_factory=list)
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'chord': self.chord,
            'confidence': self.confidence,
            'notes': self.notes,
            'bass_note': self.bass_note,
            'quality': self.quality,
            'extensions': self.extensions,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChordAnalysisResult':
        """Create from dictionary."""
        return cls(
            chord=data.get('chord', ''),
            confidence=data.get('confidence', 0.0),
            notes=data.get('notes', []),
            bass_note=data.get('bass_note'),
            quality=data.get('quality'),
            extensions=data.get('extensions', []),
            timestamp=data.get('timestamp')
        )
    
    @property
    def is_valid(self) -> bool:
        """Check if the result is valid."""
        return bool(self.chord and self.confidence > 0)
    
    @property
    def full_chord_name(self) -> str:
        """Get full chord name with extensions."""
        name = self.chord
        
        if self.extensions:
            name += "".join(self.extensions)
        
        if self.bass_note and self.bass_note != self.chord:
            name += f"/{self.bass_note}"
        
        return name
