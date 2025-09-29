"""
Settings management for Chord Importer application.
"""

import configparser
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os

class ChordImporterSettings:
    """Settings manager for Chord Importer application."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize settings manager."""
        if config_path is None:
            # Create config in user's home directory
            home_dir = Path.home()
            app_dir = home_dir / ".chord_importer"
            app_dir.mkdir(exist_ok=True)
            config_path = app_dir / "config.cfg"
        
        self.config_path = str(config_path)
        self.config = configparser.ConfigParser()
        
        # Default settings
        self.defaults = {
            'General': {
                'language': 'pt_BR',
                'theme': 'default',
                'auto_save_searches': 'true',
                'max_search_results': '50',
                'default_export_format': 'pdf',
                'export_directory': str(Path.home() / "Downloads" / "ChordImporter"),
                'auto_detect_chords': 'true',
                'show_advanced_options': 'false'
            },
            'API': {
                'serper_api_key': '',
                'enable_fallback_search': 'true',
                'api_timeout': '30',
                'max_retries': '3'
            },
            'Audio': {
                'sample_rate': '44100',
                'buffer_size': '4096',
                'noise_floor': '0.001',
                'stability_threshold': '2.0',
                'hps_harmonics': '5',
                'auto_detect_strings': 'true',
                'default_microphone': 'default',
                'tuner_precision': '0.5'
            },
            'Search': {
                'default_dork': 'cifras',
                'results_per_key': '10',
                'search_timeout': '30',
                'enable_chord_sequence_search': 'true',
                'preserve_accidental_preference': 'true',
                'auto_transpose_results': 'false'
            },
            'Export': {
                'pdf_quality': 'high',
                'xml_format': 'opensong',
                'include_metadata': 'true',
                'auto_open_exports': 'false',
                'backup_exports': 'true',
                'compress_exports': 'false'
            },
            'Database': {
                'auto_cleanup_days': '90',
                'backup_frequency': 'weekly',
                'max_search_history': '1000',
                'enable_statistics': 'true'
            },
            'UI': {
                'window_width': '800',
                'window_height': '600',
                'remember_window_position': 'true',
                'show_tooltips': 'true',
                'compact_mode': 'false',
                'show_status_bar': 'true',
                'log_level': 'info'
            }
        }
        
        self.load_settings()
    
    def load_settings(self):
        """Load settings from config file."""
        # Load defaults first
        for section, options in self.defaults.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            for key, value in options.items():
                self.config.set(section, key, value)
        
        # Load from file if exists
        if os.path.exists(self.config_path):
            try:
                self.config.read(self.config_path, encoding='utf-8')
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
                # Use defaults
    
    def save_settings(self):
        """Save settings to config file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """Get a setting value."""
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get a boolean setting value."""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Get an integer setting value."""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get a float setting value."""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def set(self, section: str, key: str, value: Any):
        """Set a setting value."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, key, str(value))
    
    def get_section(self, section: str) -> Dict[str, str]:
        """Get all settings from a section."""
        if self.config.has_section(section):
            return dict(self.config.items(section))
        return {}
    
    def set_section(self, section: str, settings: Dict[str, Any]):
        """Set multiple settings in a section."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        for key, value in settings.items():
            self.config.set(section, key, str(value))
    
    def reset_to_defaults(self, section: str = None):
        """Reset settings to defaults."""
        if section:
            if section in self.defaults:
                self.set_section(section, self.defaults[section])
        else:
            # Reset all sections
            self.config.clear()
            for section, options in self.defaults.items():
                self.set_section(section, options)
    
    def export_settings(self, file_path: str):
        """Export settings to a file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, file_path: str):
        """Import settings from a file."""
        try:
            temp_config = configparser.ConfigParser()
            temp_config.read(file_path, encoding='utf-8')
            
            # Merge with current config
            for section in temp_config.sections():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                
                for key, value in temp_config.items(section):
                    self.config.set(section, key, value)
            
            return True
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
    
    def get_export_directory(self) -> str:
        """Get the export directory, creating it if necessary."""
        export_dir = self.get('General', 'export_directory')
        
        # Expand user path
        export_dir = os.path.expanduser(export_dir)
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(export_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create export directory: {e}")
            # Fall back to Downloads
            export_dir = str(Path.home() / "Downloads")
        
        return export_dir
    
    def get_tuner_settings(self) -> Dict[str, Any]:
        """Get tuner-specific settings."""
        return {
            'sample_rate': self.get_int('Audio', 'sample_rate', 44100),
            'buffer_size': self.get_int('Audio', 'buffer_size', 4096),
            'noise_floor': self.get_float('Audio', 'noise_floor', 0.001),
            'stability_threshold': self.get_float('Audio', 'stability_threshold', 2.0),
            'hps_harmonics': self.get_int('Audio', 'hps_harmonics', 5),
            'auto_detect_strings': self.get_bool('Audio', 'auto_detect_strings', True),
            'default_microphone': self.get('Audio', 'default_microphone', 'default'),
            'tuner_precision': self.get_float('Audio', 'tuner_precision', 0.5)
        }
    
    def get_search_settings(self) -> Dict[str, Any]:
        """Get search-specific settings."""
        return {
            'default_dork': self.get('Search', 'default_dork', 'cifras'),
            'results_per_key': self.get_int('Search', 'results_per_key', 10),
            'search_timeout': self.get_int('Search', 'search_timeout', 30),
            'enable_chord_sequence_search': self.get_bool('Search', 'enable_chord_sequence_search', True),
            'preserve_accidental_preference': self.get_bool('Search', 'preserve_accidental_preference', True),
            'auto_transpose_results': self.get_bool('Search', 'auto_transpose_results', False)
        }
    
    def get_api_settings(self) -> Dict[str, Any]:
        """Get API-specific settings."""
        return {
            'serper_api_key': self.get('API', 'serper_api_key', ''),
            'enable_fallback_search': self.get_bool('API', 'enable_fallback_search', True),
            'api_timeout': self.get_int('API', 'api_timeout', 30),
            'max_retries': self.get_int('API', 'max_retries', 3)
        }
    
    def get_serper_api_key(self) -> str:
        """Get the Serper API key."""
        return self.get('API', 'serper_api_key', '').strip()
    
    def set_serper_api_key(self, api_key: str):
        """Set the Serper API key."""
        self.set('API', 'serper_api_key', api_key.strip())
    
    def validate_settings(self) -> List[str]:
        """Validate current settings and return list of issues."""
        issues = []
        
        # Validate numeric ranges
        sample_rate = self.get_int('Audio', 'sample_rate')
        if sample_rate not in [22050, 44100, 48000, 96000]:
            issues.append(f"Invalid sample rate: {sample_rate}")
        
        buffer_size = self.get_int('Audio', 'buffer_size')
        if buffer_size < 1024 or buffer_size > 16384:
            issues.append(f"Buffer size should be between 1024 and 16384: {buffer_size}")
        
        results_per_key = self.get_int('Search', 'results_per_key')
        if results_per_key < 1 or results_per_key > 50:
            issues.append(f"Results per key should be between 1 and 50: {results_per_key}")
        
        # Validate paths
        export_dir = self.get('General', 'export_directory')
        try:
            os.makedirs(os.path.expanduser(export_dir), exist_ok=True)
        except Exception as e:
            issues.append(f"Invalid export directory: {export_dir} ({e})")
        
        return issues

# Global settings instance
_settings_instance = None

def get_settings() -> ChordImporterSettings:
    """Get the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ChordImporterSettings()
    return _settings_instance
