#!/usr/bin/env python3
"""
Flexible Content Extractor for Musical Sites
Uses configurable selectors to extract data from any music site.
"""

import re
import requests
from typing import Dict, Optional, Tuple, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin

try:
    from ..models.source_configs import get_source_manager, SourceConfig, SourceSelector
    from .core import DEFAULT_HEADERS, _normalize_lyrics_text, _extract_text_from_pre
except ImportError:
    from chord_importer.models.source_configs import get_source_manager, SourceConfig, SourceSelector
    from chord_importer.services.core import DEFAULT_HEADERS, _normalize_lyrics_text, _extract_text_from_pre


class FlexibleExtractor:
    """Flexible extractor that can work with any configured music site."""
    
    def __init__(self):
        self.source_manager = get_source_manager()
    
    def extract_song_data(self, url: str, source_config: Optional[SourceConfig] = None) -> Dict[str, Any]:
        """
        Extract song data from a URL using flexible configuration.
        
        Args:
            url: The URL to extract from
            source_config: Optional specific configuration to use
            
        Returns:
            Dictionary with extracted song data
        """
        if source_config is None:
            source_config = self.source_manager.find_source_for_url(url)
            if source_config is None:
                raise ValueError(f"No source configuration found for URL: {url}")
        
        # Modify URL if suffix is specified
        target_url = url
        if source_config.url_suffix:
            target_url = url.rstrip('/') + source_config.url_suffix
        
        # Fetch the page
        try:
            response = requests.get(target_url, headers=DEFAULT_HEADERS, timeout=source_config.timeout)
            response.raise_for_status()
        except Exception as e:
            # If modified URL fails, try original URL
            if source_config.url_suffix:
                response = requests.get(url, headers=DEFAULT_HEADERS, timeout=source_config.timeout)
                response.raise_for_status()
            else:
                raise e
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Clean up HTML if requested
        if source_config.remove_scripts:
            for script in soup(["script"]):
                script.decompose()
        
        if source_config.remove_styles:
            for style in soup(["style"]):
                style.decompose()
        
        # Extract data using configured selectors
        song_data = {
            'title': self._extract_field(soup, source_config.title_selector, 'title'),
            'artist': self._extract_field(soup, source_config.artist_selector, 'artist'),
            'key': self._extract_field(soup, source_config.key_selector, 'key'),
            'capo': self._extract_field(soup, source_config.capo_selector, 'capo'),
            'content': self._extract_field(soup, source_config.content_selector, 'content'),
            'metadata': {}
        }
        
        # Extract metadata fields
        metadata_fields = {
            'composers': source_config.composer_selector,
            'views': source_config.views_selector,
            'difficulty': source_config.difficulty_selector,
            'instrument_info': source_config.instrument_selector
        }
        
        for field_name, selector in metadata_fields.items():
            if selector and (selector.css_selector or selector.xpath_selector or 
                           selector.text_search or selector.regex_pattern):
                value = self._extract_field(soup, selector, field_name)
                if value:
                    song_data['metadata'][field_name] = value
        
        return song_data
    
    def _extract_field(self, soup: BeautifulSoup, selector: SourceSelector, field_type: str) -> str:
        """Extract a field using the configured selector."""
        if not selector:
            return ""
        
        # Try CSS selector first
        if selector.css_selector:
            # Check if we should get multiple elements or just one
            if selector.join_separator is not None:
                elements = soup.select(selector.css_selector)
                if elements:
                    texts = []
                    for element in elements:
                        text = self._extract_text_from_element(element, selector, field_type)
                        if text.strip():
                            texts.append(text.strip())
                    if texts:
                        return selector.join_separator.join(texts)
            else:
                element = soup.select_one(selector.css_selector)
                if element:
                    return self._extract_text_from_element(element, selector, field_type)
        
        # Try XPath selector (convert to CSS if possible, or use lxml)
        if selector.xpath_selector:
            # Note: BeautifulSoup doesn't support XPath directly
            # This would require lxml or selenium for full XPath support
            pass
        
        # Try text search with regex
        if selector.text_search and selector.regex_pattern:
            text_elements = soup.find_all(string=lambda text: text and selector.text_search.lower() in text.lower())
            matches = []
            for text_elem in text_elements:
                text_str = str(text_elem).strip()
                match = re.search(selector.regex_pattern, text_str, re.IGNORECASE)
                if match:
                    result = match.group(1) if match.groups() else match.group(0)
                    if selector.join_separator is not None:
                        matches.append(result)
                    else:
                        return result
                
                # Also check parent element text
                if hasattr(text_elem, 'parent') and text_elem.parent:
                    parent_text = text_elem.parent.get_text()
                    match = re.search(selector.regex_pattern, parent_text, re.IGNORECASE)
                    if match:
                        result = match.group(1) if match.groups() else match.group(0)
                        if selector.join_separator is not None:
                            matches.append(result)
                        else:
                            return result
            
            if matches and selector.join_separator is not None:
                return selector.join_separator.join(matches)
        
        # Try text search without regex
        if selector.text_search:
            text_elements = soup.find_all(string=lambda text: text and selector.text_search.lower() in text.lower())
            texts = []
            for text_elem in text_elements:
                if hasattr(text_elem, 'parent') and text_elem.parent:
                    text = text_elem.parent.get_text().strip()
                else:
                    text = str(text_elem).strip()
                
                if selector.join_separator is not None:
                    if text:
                        texts.append(text)
                else:
                    return text
            
            if texts and selector.join_separator is not None:
                return selector.join_separator.join(texts)
        
        # Try fallback selectors
        for fallback_selector in selector.fallback_selectors:
            if selector.join_separator is not None:
                elements = soup.select(fallback_selector)
                if elements:
                    texts = []
                    for element in elements:
                        text = self._extract_text_from_element(element, selector, field_type)
                        if text.strip():
                            texts.append(text.strip())
                    if texts:
                        return selector.join_separator.join(texts)
            else:
                element = soup.select_one(fallback_selector)
                if element:
                    return self._extract_text_from_element(element, selector, field_type)
        
        return ""
    
    def _extract_text_from_element(self, element, selector: SourceSelector, field_type: str) -> str:
        """Extract text from an element, handling special cases."""
        if selector.attribute:
            return element.get(selector.attribute, "")
        
        # Special handling for content field
        if field_type == 'content' and element.name == 'pre':
            return _extract_text_from_pre(element)
        
        # Regular text extraction
        text = element.get_text().strip()
        
        # Apply regex if specified
        if selector.regex_pattern:
            match = re.search(selector.regex_pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return text
    
    def format_song_export(self, song_data: Dict[str, Any], source_name: str = "") -> str:
        """Format extracted song data for export."""        
        return _normalize_lyrics_text(song_data['content'])


def extract_with_flexible_config(url: str) -> Tuple[str, str, str]:
    """
    Extract song data using flexible configuration system.
    Returns tuple compatible with existing fetch_song function.
    
    Args:
        url: URL to extract from
        
    Returns:
        Tuple of (title, artist, formatted_content)
    """
    extractor = FlexibleExtractor()
    
    try:
        song_data = extractor.extract_song_data(url)
        source_config = extractor.source_manager.find_source_for_url(url)
        source_name = source_config.name if source_config else "Unknown"
        
        formatted_content = extractor.format_song_export(song_data, source_name)
        
        return song_data.get('title', ''), song_data.get('artist', ''), formatted_content
        
    except Exception as e:
        print(f"Error in flexible extraction for {url}: {e}")
        return "", "", ""
