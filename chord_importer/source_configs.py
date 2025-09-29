#!/usr/bin/env python3
"""
Source Configuration System for Musical Sites
Allows users to configure custom extraction rules for different music sites.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class SourceSelector:
    """Configuration for extracting a specific field from a music site."""
    css_selector: Optional[str] = None
    xpath_selector: Optional[str] = None
    regex_pattern: Optional[str] = None
    text_search: Optional[str] = None
    attribute: Optional[str] = None  # For extracting attributes instead of text
    fallback_selectors: List[str] = None  # Alternative selectors to try
    join_separator: Optional[str] = None  # Separator for joining multiple elements (e.g., ", ", " | ", "\n")
    
    def __post_init__(self):
        if self.fallback_selectors is None:
            self.fallback_selectors = []

@dataclass
class SourceConfig:
    """Complete configuration for a music site source."""
    name: str
    domain_patterns: List[str]  # URL patterns to match (e.g., ["cifraclub.com.br"])
    url_suffix: str = ""  # Suffix to add to URL (e.g., "/imprimir.html")
    
    # Field selectors
    title_selector: SourceSelector = None
    artist_selector: SourceSelector = None
    key_selector: SourceSelector = None
    capo_selector: SourceSelector = None
    content_selector: SourceSelector = None
    
    # Metadata selectors (optional)
    composer_selector: SourceSelector = None
    views_selector: SourceSelector = None
    difficulty_selector: SourceSelector = None
    instrument_selector: SourceSelector = None
    
    # Processing options
    remove_scripts: bool = True
    remove_styles: bool = True
    encoding: str = "utf-8"
    timeout: int = 15
    
    def __post_init__(self):
        # Initialize selectors if None
        if self.title_selector is None:
            self.title_selector = SourceSelector()
        if self.artist_selector is None:
            self.artist_selector = SourceSelector()
        if self.key_selector is None:
            self.key_selector = SourceSelector()
        if self.capo_selector is None:
            self.capo_selector = SourceSelector()
        if self.content_selector is None:
            self.content_selector = SourceSelector()
        if self.composer_selector is None:
            self.composer_selector = SourceSelector()
        if self.views_selector is None:
            self.views_selector = SourceSelector()
        if self.difficulty_selector is None:
            self.difficulty_selector = SourceSelector()
        if self.instrument_selector is None:
            self.instrument_selector = SourceSelector()

class SourceConfigManager:
    """Manages source configurations for different music sites."""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            # Default to user's home directory
            home_dir = Path.home()
            config_dir = home_dir / ".chord_importer" / "sources"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "sources.json"
        
        self.sources: Dict[str, SourceConfig] = {}
        self.load_sources()
        
        # Initialize with default CifraClub configuration if no sources exist
        if not self.sources:
            self._create_default_sources()
    
    def _create_default_sources(self):
        """Load default source configurations from JSON file."""
        try:
            # Try to load from package default file
            import os
            default_file = os.path.join(os.path.dirname(__file__), "default_sources.json")
            
            if os.path.exists(default_file):
                with open(default_file, 'r', encoding='utf-8') as f:
                    default_data = json.load(f)
                
                for source_id, source_data in default_data.items():
                    config = self._dict_to_source_config(source_data)
                    self.add_source(source_id, config)
                
                self.save_sources()
                print(f"Loaded {len(default_data)} default source configurations")
                return
                
        except Exception as e:
            print(f"Error loading default sources from JSON: {e}")
        
        # Fallback: Create minimal default configuration
        self._create_minimal_defaults()
    
    def _create_minimal_defaults(self):
        """Create minimal default configurations as fallback."""
        # Minimal CifraClub configuration
        cifraclub_config = SourceConfig(
            name="CifraClub",
            domain_patterns=["cifraclub.com.br"],
            url_suffix="/imprimir.html",
            title_selector=SourceSelector(
                css_selector=".cifra_header > h1 > a",
                fallback_selectors=["h1", "title"]
            ),
            artist_selector=SourceSelector(
                css_selector=".cifra_header > h2 > a",
                fallback_selectors=["h2", ".artist-name"]
            ),
            content_selector=SourceSelector(
                css_selector="pre",
                fallback_selectors=[".cifra_cnt", ".song-content", ".lyrics"]
            )
        )
        
        # Minimal generic configuration
        generic_config = SourceConfig(
            name="Generic",
            domain_patterns=["*"],
            title_selector=SourceSelector(
                css_selector="h1",
                fallback_selectors=["title", ".song-title", ".title"]
            ),
            artist_selector=SourceSelector(
                css_selector="h2",
                fallback_selectors=[".artist", ".artist-name", ".singer"]
            ),
            content_selector=SourceSelector(
                css_selector="pre",
                fallback_selectors=[".lyrics", ".song-content", ".content"]
            )
        )
        
        self.add_source("cifraclub", cifraclub_config)
        self.add_source("generic", generic_config)
        self.save_sources()
        print("Created minimal default source configurations")
    
    def load_sources(self):
        """Load source configurations from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for source_id, source_data in data.items():
                    # Convert dict back to SourceConfig
                    config = self._dict_to_source_config(source_data)
                    self.sources[source_id] = config
                    
            except Exception as e:
                print(f"Error loading source configurations: {e}")
    
    def save_sources(self):
        """Save source configurations to file."""
        try:
            data = {}
            for source_id, config in self.sources.items():
                data[source_id] = self._source_config_to_dict(config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving source configurations: {e}")
    
    def _source_config_to_dict(self, config: SourceConfig) -> Dict:
        """Convert SourceConfig to dictionary for JSON serialization."""
        return asdict(config)
    
    def _dict_to_source_config(self, data: Dict) -> SourceConfig:
        """Convert dictionary to SourceConfig."""
        # Convert nested selector dictionaries to SourceSelector objects
        for field in ['title_selector', 'artist_selector', 'key_selector', 
                     'capo_selector', 'content_selector', 'composer_selector',
                     'views_selector', 'difficulty_selector', 'instrument_selector']:
            if field in data and data[field]:
                data[field] = SourceSelector(**data[field])
        
        return SourceConfig(**data)
    
    def add_source(self, source_id: str, config: SourceConfig):
        """Add or update a source configuration."""
        self.sources[source_id] = config
    
    def remove_source(self, source_id: str):
        """Remove a source configuration."""
        if source_id in self.sources:
            del self.sources[source_id]
    
    def get_source(self, source_id: str) -> Optional[SourceConfig]:
        """Get a source configuration by ID."""
        return self.sources.get(source_id)
    
    def find_source_for_url(self, url: str) -> Optional[SourceConfig]:
        """Find the best matching source configuration for a URL."""
        url_lower = url.lower()
        
        # First try exact domain matches
        for config in self.sources.values():
            for pattern in config.domain_patterns:
                if pattern != "*" and pattern.lower() in url_lower:
                    return config
        
        # Fallback to generic configuration
        for config in self.sources.values():
            if "*" in config.domain_patterns:
                return config
        
        return None
    
    def list_sources(self) -> Dict[str, str]:
        """List all available sources with their names."""
        return {source_id: config.name for source_id, config in self.sources.items()}
    
    def export_source(self, source_id: str, file_path: str):
        """Export a source configuration to a file."""
        if source_id not in self.sources:
            raise ValueError(f"Source '{source_id}' not found")
        
        config_data = {source_id: self._source_config_to_dict(self.sources[source_id])}
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def import_source(self, file_path: str) -> List[str]:
        """Import source configuration(s) from a file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported_sources = []
        for source_id, source_data in data.items():
            config = self._dict_to_source_config(source_data)
            self.add_source(source_id, config)
            imported_sources.append(source_id)
        
        return imported_sources
    
    def reset_to_defaults(self):
        """Reset all sources to default configurations."""
        self.sources.clear()
        self._create_default_sources()
        return list(self.sources.keys())
    
    def update_defaults_from_file(self, file_path: str):
        """Update default configurations from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Backup current sources
            backup_sources = self.sources.copy()
            
            try:
                # Clear and load new defaults
                self.sources.clear()
                for source_id, source_data in data.items():
                    config = self._dict_to_source_config(source_data)
                    self.add_source(source_id, config)
                
                self.save_sources()
                return True
                
            except Exception as e:
                # Restore backup on error
                self.sources = backup_sources
                raise e
                
        except Exception as e:
            print(f"Error updating defaults from file: {e}")
            return False


# Global instance
_source_manager = None

def get_source_manager() -> SourceConfigManager:
    """Get the global source configuration manager."""
    global _source_manager
    if _source_manager is None:
        _source_manager = SourceConfigManager()
    return _source_manager
