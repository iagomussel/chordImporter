"""Chord Importer package.

Provides functions to fetch chord/lyric content from supported webpages and
export songs in the OpenSong XML format. Includes a CLI entrypoint via
``python -m chord_importer``.
"""

try:
    # Try relative import first (for package usage)
    from .core import build_opensong_xml, fetch_song, save_song
except ImportError:
    # Fall back to absolute import (for PyInstaller)
    from chord_importer.core import build_opensong_xml, fetch_song, save_song

__all__ = [
    "fetch_song",
    "build_opensong_xml",
    "save_song",
]

__version__ = "0.1.0"



