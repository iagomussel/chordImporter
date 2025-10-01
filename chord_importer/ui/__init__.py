"""
UI package for ChordImporter.
Contains all user interface components and windows.
"""

from .main_dashboard import MusicalToolsDashboard, run_dashboard
from .settings_window import SettingsWindow
from .cipher_manager import CipherManagerWindow
from .tuner import AdvancedGuitarTuner
from .chord_identifier import ChordIdentifierWindow
from .music_visualizer import SimpleMusicVisualizer
# MelodyAnalyzer removed - replaced with VoicePitchTuner

__all__ = [
    'MusicalToolsDashboard',
    'run_dashboard',
    'SettingsWindow',
    'CipherManagerWindow',
    'AdvancedGuitarTuner',
    'ChordIdentifierWindow',
    'SimpleMusicVisualizer',
    # 'MelodyAnalyzer' removed
]
