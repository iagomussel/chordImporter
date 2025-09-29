from __future__ import annotations

import re
from typing import List, Tuple, Optional
from enum import Enum


class AccidentalPreference(Enum):
    """Preference for displaying accidentals."""
    SHARPS = "sharps"
    FLATS = "flats"
    PRESERVE_INPUT = "preserve_input"


# Escala cromática em sustenidos
CHROMATIC_SHARPS = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
]

# Escala cromática em bemóis
CHROMATIC_FLATS = [
    "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"
]

# Mapeamento de equivalências enarmônicas
ENHARMONIC_MAP = {
    "C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb",
    "Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"
}

# Notas naturais (sem acidentes)
NATURAL_NOTES = {"C", "D", "E", "F", "G", "A", "B"}


def _is_flat_note(note: str) -> bool:
    """Check if a note uses flat notation."""
    return "b" in note


def _is_sharp_note(note: str) -> bool:
    """Check if a note uses sharp notation."""
    return "#" in note


def _normalize_note_to_chromatic_index(note: str) -> int:
    """Convert any note (sharp or flat) to chromatic scale index (0-11)."""
    # Try sharps first
    if note in CHROMATIC_SHARPS:
        return CHROMATIC_SHARPS.index(note)
    
    # Try flats
    if note in CHROMATIC_FLATS:
        return CHROMATIC_FLATS.index(note)
    
    # Try enharmonic equivalent
    if note in ENHARMONIC_MAP:
        equivalent = ENHARMONIC_MAP[note]
        if equivalent in CHROMATIC_SHARPS:
            return CHROMATIC_SHARPS.index(equivalent)
        if equivalent in CHROMATIC_FLATS:
            return CHROMATIC_FLATS.index(equivalent)
    
    raise ValueError(f"Invalid note: {note}")


def _get_note_from_index(index: int, preference: AccidentalPreference, original_note: Optional[str] = None) -> str:
    """Get note name from chromatic index based on preference."""
    index = index % 12
    
    # If the result is a natural note (C, D, E, F, G, A, B), return it as-is
    natural_result = CHROMATIC_SHARPS[index]
    if natural_result in NATURAL_NOTES:
        return natural_result
    
    if preference == AccidentalPreference.PRESERVE_INPUT and original_note:
        # If original was flat, prefer flats; if sharp, prefer sharps
        if _is_flat_note(original_note):
            return CHROMATIC_FLATS[index]
        elif _is_sharp_note(original_note):
            return CHROMATIC_SHARPS[index]
        else:
            # Natural note, use sharps as default
            return CHROMATIC_SHARPS[index]
    elif preference == AccidentalPreference.FLATS:
        return CHROMATIC_FLATS[index]
    else:  # SHARPS or default
        return CHROMATIC_SHARPS[index]


def parse_chord(chord: str) -> Tuple[str, str, Optional[str]]:
    """Parse a chord into root note, suffix, and bass note.
    
    Args:
        chord: Chord string like "C", "Am", "F#m7", "Bb/D"
        
    Returns:
        Tuple of (root_note, suffix, bass_note)
        bass_note is None if no bass inversion is present
    """
    chord = chord.strip()
    
    # Check for bass note (slash chord)
    bass_note = None
    if "/" in chord:
        chord_part, bass_part = chord.split("/", 1)
        # Parse bass note (should be just a note, possibly with accidental)
        bass_match = re.match(r'^([A-G](?:[#b]|##|bb)?)', bass_part.strip())
        if bass_match:
            bass_note = bass_match.group(1)
        chord = chord_part.strip()
    
    # Pattern to match chord root and suffix
    pattern = r'^([A-G](?:[#b]|##|bb)?)(.*)$'
    match = re.match(pattern, chord)
    
    if not match:
        return chord, "", bass_note
    
    root = match.group(1)
    suffix = match.group(2)
    
    return root, suffix, bass_note


def transpose_chord(
    chord: str, 
    semitones: int, 
    preference: AccidentalPreference = AccidentalPreference.PRESERVE_INPUT
) -> str:
    """Transpose a single chord by the given number of semitones.
    
    Args:
        chord: Original chord (e.g., "C", "Am", "F#7", "Bb/D")
        semitones: Number of semitones to transpose (positive = up, negative = down)
        preference: How to handle accidentals in output
        
    Returns:
        Transposed chord with bass note transposed if present
    """
    root, suffix, bass_note = parse_chord(chord)
    
    try:
        # Transpose root note
        root_index = _normalize_note_to_chromatic_index(root)
        new_root_index = (root_index + semitones) % 12
        new_root = _get_note_from_index(new_root_index, preference, root)
        
        # Transpose bass note if present
        new_bass = None
        if bass_note:
            bass_index = _normalize_note_to_chromatic_index(bass_note)
            new_bass_index = (bass_index + semitones) % 12
            new_bass = _get_note_from_index(new_bass_index, preference, bass_note)
        
        # Reconstruct chord
        result = new_root + suffix
        if new_bass:
            result += "/" + new_bass
            
        return result
        
    except ValueError:
        # Return original if can't transpose
        return chord


def parse_chord_sequence(sequence: str) -> List[str]:
    """Parse a chord sequence string into individual chords.
    
    Args:
        sequence: Space-separated chord sequence like "C D Em F"
        
    Returns:
        List of individual chords
    """
    # Split by spaces and filter out empty strings
    chords = [chord.strip() for chord in sequence.split() if chord.strip()]
    return chords


def transpose_sequence(
    chord_sequence: List[str], 
    semitones: int, 
    preference: AccidentalPreference = AccidentalPreference.PRESERVE_INPUT
) -> List[str]:
    """Transpose an entire chord sequence.
    
    Args:
        chord_sequence: List of chords
        semitones: Number of semitones to transpose
        preference: How to handle accidentals in output
        
    Returns:
        List of transposed chords
    """
    return [transpose_chord(chord, semitones, preference) for chord in chord_sequence]


def generate_all_transpositions(chord_sequence: str) -> List[Tuple[int, List[str]]]:
    """Generate all 12 transpositions of a chord sequence.
    
    Args:
        chord_sequence: Original chord sequence string (e.g., "C D Em")
        
    Returns:
        List of tuples (semitones, transposed_sequence)
    """
    chords = parse_chord_sequence(chord_sequence)
    transpositions = []
    
    for semitones in range(12):
        transposed = transpose_sequence(chords, semitones)
        transpositions.append((semitones, transposed))
    
    return transpositions


def format_chord_sequence_for_search(chord_sequence: List[str]) -> str:
    """Format a chord sequence for search query.
    
    Args:
        chord_sequence: List of chords
        
    Returns:
        Formatted string for search (e.g., "C+D+Em")
    """
    return "+".join(chord_sequence)


def generate_search_queries(chord_sequence: str) -> List[str]:
    """Generate all search queries for a chord sequence in all keys.
    
    Args:
        chord_sequence: Original chord sequence (e.g., "C D Em")
        
    Returns:
        List of search queries for all transpositions
    """
    transpositions = generate_all_transpositions(chord_sequence)
    queries = []
    
    for semitones, transposed_chords in transpositions:
        formatted_sequence = format_chord_sequence_for_search(transposed_chords)
        query = f'"{formatted_sequence}" site:cifraclub.com.br'
        queries.append(query)
    
    return queries


def get_key_name(semitones: int, preference: AccidentalPreference = AccidentalPreference.SHARPS) -> str:
    """Get the key name for a given number of semitones from C.
    
    Args:
        semitones: Number of semitones from C
        preference: Whether to use sharps or flats
        
    Returns:
        Key name (e.g., "C", "C#", "D", etc.)
    """
    return _get_note_from_index(semitones % 12, preference)


def describe_transposition(
    original_sequence: str, 
    semitones: int, 
    preference: AccidentalPreference = AccidentalPreference.PRESERVE_INPUT
) -> str:
    """Create a human-readable description of a transposition.
    
    Args:
        original_sequence: Original chord sequence
        semitones: Number of semitones transposed
        preference: How to handle accidentals in output
        
    Returns:
        Description string
    """
    if semitones == 0:
        return f"Tom original: {original_sequence}"
    
    key_name = get_key_name(semitones, preference)
    transposed = transpose_sequence(parse_chord_sequence(original_sequence), semitones, preference)
    transposed_str = " ".join(transposed)
    
    return f"Tom de {key_name}: {transposed_str}"
