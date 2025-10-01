"""
Song data models.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class SongMetadata:
    """Metadata for a song."""
    title: str
    artist: str
    album: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    duration: Optional[float] = None
    bpm: Optional[int] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None
    capo: Optional[int] = None
    tuning: Optional[str] = None
    difficulty: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'year': self.year,
            'genre': self.genre,
            'duration': self.duration,
            'bpm': self.bpm,
            'key': self.key,
            'time_signature': self.time_signature,
            'capo': self.capo,
            'tuning': self.tuning,
            'difficulty': self.difficulty,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SongMetadata':
        """Create from dictionary."""
        return cls(
            title=data.get('title', ''),
            artist=data.get('artist', ''),
            album=data.get('album'),
            year=data.get('year'),
            genre=data.get('genre'),
            duration=data.get('duration'),
            bpm=data.get('bpm'),
            key=data.get('key'),
            time_signature=data.get('time_signature'),
            capo=data.get('capo'),
            tuning=data.get('tuning'),
            difficulty=data.get('difficulty'),
            tags=data.get('tags', [])
        )


@dataclass
class Song:
    """Song data model."""
    metadata: SongMetadata
    content: str
    chord_progression: Optional[str] = None
    lyrics: Optional[str] = None
    tabs: Optional[str] = None
    source_url: Optional[str] = None
    source_site: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    id: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    @property
    def title(self) -> str:
        """Get song title."""
        return self.metadata.title
    
    @property
    def artist(self) -> str:
        """Get song artist."""
        return self.metadata.artist
    
    @property
    def display_name(self) -> str:
        """Get display name for the song."""
        return f"{self.artist} - {self.title}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'metadata': self.metadata.to_dict(),
            'content': self.content,
            'chord_progression': self.chord_progression,
            'lyrics': self.lyrics,
            'tabs': self.tabs,
            'source_url': self.source_url,
            'source_site': self.source_site,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Song':
        """Create from dictionary."""
        metadata = SongMetadata.from_dict(data.get('metadata', {}))
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            id=data.get('id'),
            metadata=metadata,
            content=data.get('content', ''),
            chord_progression=data.get('chord_progression'),
            lyrics=data.get('lyrics'),
            tabs=data.get('tabs'),
            source_url=data.get('source_url'),
            source_site=data.get('source_site'),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def update_metadata(self, **kwargs) -> None:
        """Update song metadata."""
        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)
        self.updated_at = datetime.now()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the song."""
        if tag not in self.metadata.tags:
            self.metadata.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the song."""
        if tag in self.metadata.tags:
            self.metadata.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def has_tag(self, tag: str) -> bool:
        """Check if song has a specific tag."""
        return tag in self.metadata.tags
    
    def get_chords(self) -> List[str]:
        """Extract chords from content."""
        import re
        
        # Simple chord pattern - can be improved
        chord_pattern = r'\b[A-G][#b]?(?:maj|min|m|dim|aug|sus[24]?|add[29]|[0-9]+)?\b'
        chords = re.findall(chord_pattern, self.content)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_chords = []
        for chord in chords:
            if chord not in seen:
                seen.add(chord)
                unique_chords.append(chord)
        
        return unique_chords
    
    def transpose(self, semitones: int) -> 'Song':
        """
        Create a transposed copy of the song.
        
        Args:
            semitones: Number of semitones to transpose
            
        Returns:
            New Song object with transposed content
        """
        # This would use the chord_transposer utility
        from ..utils.chord_transposer import transpose_content
        
        transposed_content = transpose_content(self.content, semitones)
        
        # Create new song with transposed content
        new_song = Song(
            metadata=SongMetadata(
                title=self.metadata.title,
                artist=self.metadata.artist,
                album=self.metadata.album,
                year=self.metadata.year,
                genre=self.metadata.genre,
                duration=self.metadata.duration,
                bpm=self.metadata.bpm,
                key=self.metadata.key,  # Key would also need to be transposed
                time_signature=self.metadata.time_signature,
                capo=self.metadata.capo,
                tuning=self.metadata.tuning,
                difficulty=self.metadata.difficulty,
                tags=self.metadata.tags.copy()
            ),
            content=transposed_content,
            chord_progression=self.chord_progression,
            lyrics=self.lyrics,
            tabs=self.tabs,
            source_url=self.source_url,
            source_site=self.source_site
        )
        
        return new_song
