"""
Centralized import management to eliminate duplicated import patterns.
"""

import sys
import importlib
from typing import Any, Optional, Dict, List, Tuple


class ImportManager:
    """Centralized import manager to handle all dynamic imports."""
    
    _cache: Dict[str, Any] = {}
    _failed_imports: List[str] = []
    
    @classmethod
    def safe_import(cls, module_name: str, fallback: Optional[Any] = None) -> Any:
        """
        Safely import a module with caching and fallback support.
        
        Args:
            module_name: Name of the module to import
            fallback: Fallback value if import fails
            
        Returns:
            Imported module or fallback value
        """
        if module_name in cls._cache:
            return cls._cache[module_name]
            
        if module_name in cls._failed_imports:
            return fallback
            
        try:
            module = importlib.import_module(module_name)
            cls._cache[module_name] = module
            return module
        except ImportError:
            cls._failed_imports.append(module_name)
            return fallback
    
    @classmethod
    def import_from(cls, module_name: str, item_name: str, fallback: Optional[Any] = None) -> Any:
        """
        Import a specific item from a module.
        
        Args:
            module_name: Name of the module
            item_name: Name of the item to import
            fallback: Fallback value if import fails
            
        Returns:
            Imported item or fallback value
        """
        cache_key = f"{module_name}.{item_name}"
        
        if cache_key in cls._cache:
            return cls._cache[cache_key]
            
        if cache_key in cls._failed_imports:
            return fallback
            
        try:
            module = cls.safe_import(module_name)
            if module is None:
                cls._failed_imports.append(cache_key)
                return fallback
                
            item = getattr(module, item_name, None)
            if item is None:
                cls._failed_imports.append(cache_key)
                return fallback
                
            cls._cache[cache_key] = item
            return item
        except (ImportError, AttributeError):
            cls._failed_imports.append(cache_key)
            return fallback
    
    @classmethod
    def get_available_modules(cls, module_list: List[str]) -> Dict[str, Any]:
        """
        Get all available modules from a list.
        
        Args:
            module_list: List of module names to check
            
        Returns:
            Dictionary of available modules
        """
        available = {}
        for module_name in module_list:
            module = cls.safe_import(module_name)
            if module is not None:
                available[module_name] = module
        return available
    
    @classmethod
    def check_dependencies(cls, dependencies: List[str]) -> Tuple[List[str], List[str]]:
        """
        Check which dependencies are available.
        
        Args:
            dependencies: List of dependency names
            
        Returns:
            Tuple of (available, missing) dependencies
        """
        available = []
        missing = []
        
        for dep in dependencies:
            if cls.safe_import(dep) is not None:
                available.append(dep)
            else:
                missing.append(dep)
                
        return available, missing


# Convenience function for backward compatibility
def safe_import(module_name: str, fallback: Optional[Any] = None) -> Any:
    """Convenience function for safe imports."""
    return ImportManager.safe_import(module_name, fallback)


# Common imports used across the application
AUDIO_MODULES = [
    'sounddevice',
    'pyaudio',
    'librosa',
    'numpy',
    'scipy'
]

WEB_MODULES = [
    'requests',
    'bs4',
    'playwright',
    'selenium'
]

GUI_MODULES = [
    'tkinter',
    'PIL',
    'matplotlib'
]

MUSIC_MODULES = [
    'music21',
    'mido',
    'pretty_midi'
]
