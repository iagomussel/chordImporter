from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup


# Allow overriding endpoint via env for troubleshooting
SERPER_ENDPOINT = os.environ.get("SERPER_BASE_URL", "https://google.serper.dev") + "/search"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def _get_api_key() -> str:
    # First try to get from config file
    try:
        # Try relative imports first (for package usage)
        try:
            from ..models.settings import get_settings
        except ImportError:
            from chord_importer.models.settings import get_settings
        
        settings = get_settings()
        api_key = settings.get_serper_api_key()
        if api_key:
            return api_key
    except Exception:
        pass
    
    # Fallback to environment variable for backward compatibility
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        load_dotenv = None  # type: ignore
    if load_dotenv:
        try:
            load_dotenv()
        except Exception:
            pass

    api_key = os.environ.get("SERPER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "SERPER_API_KEY não configurado. Configure a chave API nas configurações do aplicativo ou defina a variável de ambiente SERPER_API_KEY."
        )
    return api_key


def _is_probable_cifraclub_song_url(url: str) -> bool:
    """Heuristic filter:
    - Host must include "cifraclub.com.br"
    - Path must be at least /artist/song/ (2+ non-empty segments)
    - Exclude obvious non-song paths
    """
    parsed = urlparse(url)
    if "cifraclub.com.br" not in (parsed.netloc or ""):
        return False
    segments = [s for s in (parsed.path or "").split("/") if s]
    if len(segments) < 2:
        return False
    excluded = {
        "fotos.html",
        "letra",
        "videos",
        "videolesson",
        "blog",
        "aprenda",
        "enviar",
        "assine",
    }
    # If any excluded segment appears, deprioritize
    if any(seg in excluded for seg in segments[2:]):
        return False
    return True


DEFAULT_SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _normalize_duck_href(href: str) -> str:
    """DuckDuckGo html results often use redirect links like /l/?uddg=ENC.
    Extract the actual target when present; otherwise return href.
    """
    try:
        if href.startswith("/l/") or href.startswith("https://duckduckgo.com/l/"):
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            uddg = qs.get("uddg", [])
            if uddg:
                return unquote(uddg[0])
    except Exception:
        pass
    return href


def _duckduckgo_search(term: str, num: int = 10) -> List[SearchResult]:
    """Fallback search using DuckDuckGo HTML page (no API key required)."""
    query = term if "site:cifraclub.com.br" in term.lower() else f"site:cifraclub.com.br {term}"
    resp = requests.post(
        "https://duckduckgo.com/html/",
        headers=DEFAULT_SEARCH_HEADERS,
        data={"q": query},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results: List[SearchResult] = []
    for a in soup.select("a.result__a"):
        href = a.get("href") or ""
        href = _normalize_duck_href(href)
        title = a.get_text(strip=True)
        if href and "cifraclub.com.br" in href:
            results.append(SearchResult(title=title or href, url=href, snippet=""))
            if len(results) >= num:
                break

    if results:
        return results

    # Fallback: any anchor with CifraClub
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        href = _normalize_duck_href(href)
        title = a.get_text(strip=True)
        if href and "cifraclub.com.br" in href:
            results.append(SearchResult(title=title or href, url=href, snippet=""))
            if len(results) >= num:
                break
    return results


def search_cifraclub(term: str, country: str = "br", language: str = "pt-br", num: int = 10) -> List[SearchResult]:
    """Search for CifraClub song pages. Try DuckDuckGo first; Serper as fallback."""
    # Prefer DuckDuckGo HTML first
    ddg = _duckduckgo_search(term, num=num)
    if ddg:
        return ddg

    # Fallback to Serper when DDG fails to return anything useful
    query = term if "site:cifraclub.com.br" in term.lower() else f"site:cifraclub.com.br {term}"
    try:
        api_key = _get_api_key()
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = {"q": query, "gl": country, "hl": language, "num": num}
        resp = requests.post(SERPER_ENDPOINT, headers=headers, json=payload, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"Serper API error {resp.status_code}: {resp.text}")

        data = resp.json()
        organic = data.get("organic", []) or []
        results: List[SearchResult] = []
        for item in organic:
            url = item.get("link") or item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("snippet") or ""
            if not url:
                continue
            results.append(SearchResult(title=title or url, url=url, snippet=snippet))

        filtered = [r for r in results if _is_probable_cifraclub_song_url(r.url)]
        if filtered:
            return filtered[:num]
        if results:
            return results[:num]
    except Exception:
        pass

    return []


def _has_ext(href: str, filetype: Optional[str]) -> bool:
    if not filetype:
        return True
    ext = "." + filetype.lower().lstrip(".")
    return ext in (href or "").lower()


def _duckduckgo_generic(term: str, num: int = 10, filetype: Optional[str] = None) -> List[SearchResult]:
    resp = requests.post(
        "https://duckduckgo.com/html/",
        headers=DEFAULT_SEARCH_HEADERS,
        data={"q": term},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results: List[SearchResult] = []
    for a in soup.select("a.result__a"):
        href = a.get("href") or ""
        href = _normalize_duck_href(href)
        title = a.get_text(strip=True)
        if href and _has_ext(href, filetype):
            results.append(SearchResult(title=title or href, url=href, snippet=""))
            if len(results) >= num:
                break
    if results:
        return results

    # Fallback: any anchor; if filetype provided, prefer URLs containing extension
    ext = f".{filetype.lower()}" if filetype else None
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        href = _normalize_duck_href(href)
        if not href.startswith("http"):
            continue
        if ext and ext not in href.lower():
            continue
        title = a.get_text(strip=True)
        results.append(SearchResult(title=title or href, url=href, snippet=""))
        if len(results) >= num:
            break
    return results


def search_filetype(term: str, filetype: str, country: str = "br", language: str = "pt-br", num: int = 10) -> List[SearchResult]:
    """Generic dork search using filetype: (e.g., epub, mp3).
    Prefers DuckDuckGo; falls back to Serper if needed.
    """
    queries = [
        f"{term} filetype:{filetype}",
        f"{term} ext:{filetype}",
        f"{term} {filetype}",
    ]

    # Try DuckDuckGo variants first
    for q in queries:
        results = _duckduckgo_generic(q, num=num, filetype=filetype)
        if results:
            return results

    # Fallback to Serper with the strongest query
    query = queries[0]
    try:
        api_key = _get_api_key()
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = {"q": query, "gl": country, "hl": language, "num": num}
        resp = requests.post(SERPER_ENDPOINT, headers=headers, json=payload, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"Serper API error {resp.status_code}: {resp.text}")

        data = resp.json()
        organic = data.get("organic", []) or []
        results: List[SearchResult] = []
        for item in organic:
            url = item.get("link") or item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("snippet") or ""
            if not url:
                continue
            results.append(SearchResult(title=title or url, url=url, snippet=snippet))
        if results:
            return results[:num]
    except Exception:
        pass

    return []


def search_query(query: str, country: str = "br", language: str = "pt-br", num: int = 10, filetype: Optional[str] = None) -> List[SearchResult]:
    """Generic search by query; prefers DuckDuckGo and falls back to Serper."""
    results = _duckduckgo_generic(query, num=num, filetype=filetype)
    if results:
        return results
    try:
        api_key = _get_api_key()
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = {"q": query, "gl": country, "hl": language, "num": num}
        resp = requests.post(SERPER_ENDPOINT, headers=headers, json=payload, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"Serper API error {resp.status_code}: {resp.text}")
        data = resp.json()
        organic = data.get("organic", []) or []
        results = []
        for item in organic:
            url = item.get("link") or item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("snippet") or ""
            if not url:
                continue
            results.append(SearchResult(title=title or url, url=url, snippet=snippet))
        return results[:num]
    except Exception:
        return []


def search_chord_sequence(chord_sequence: str, country: str = "br", language: str = "pt-br", num_per_key: int = 10) -> List[SearchResult]:
    """Search for songs with a specific chord sequence in all keys.
    
    Args:
        chord_sequence: Chord sequence like "C D Em" or "Am F C G"
        country: Country code for search
        language: Language code for search
        num_per_key: Maximum results per key/transposition
        
    Returns:
        Aggregated and deduplicated search results from all keys
    """
    try:
        from ..utils.chord_transposer import generate_search_queries, describe_transposition, parse_chord_sequence, transpose_sequence
    except ImportError:
        from chord_importer.utils.chord_transposer import generate_search_queries, describe_transposition, parse_chord_sequence, transpose_sequence
    
    # Generate all search queries for different keys
    queries = generate_search_queries(chord_sequence)
    
    all_results: List[SearchResult] = []
    seen_urls: Set[str] = set()
    
    original_chords = parse_chord_sequence(chord_sequence)
    
    # Search each transposition
    for i, query in enumerate(queries):
        try:
            # Use the existing search_query function for each transposition
            key_results = search_query(query, country=country, language=language, num=num_per_key)
            
            # Add key information to results and deduplicate
            for result in key_results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    
                    # Add key information to the title or snippet
                    try:
                        from ..utils.chord_transposer import AccidentalPreference
                    except ImportError:
                        from chord_importer.utils.chord_transposer import AccidentalPreference
                    transposed_chords = transpose_sequence(original_chords, i, AccidentalPreference.PRESERVE_INPUT)
                    key_info = describe_transposition(chord_sequence, i, AccidentalPreference.PRESERVE_INPUT)
                    
                    # Create enhanced result with key information
                    enhanced_result = SearchResult(
                        title=f"{result.title} [{key_info}]",
                        url=result.url,
                        snippet=f"{key_info} | {result.snippet}" if result.snippet else key_info
                    )
                    all_results.append(enhanced_result)
                    
        except Exception:
            # Continue with other keys if one fails
            continue
    
    return all_results


def search_chord_sequence_dynamic(chord_sequence: str, callback=None, country: str = "br", language: str = "pt-br", num_per_key: int = 10):
    """Dynamic search for chord sequences that calls callback for each key searched.
    
    Args:
        chord_sequence: Chord sequence like "C D Em" or "Am F C G"
        callback: Function called with (key_index, key_name, results) for each key
        country: Country code for search
        language: Language code for search
        num_per_key: Maximum results per key/transposition (EXACTLY this many per key)
        
    Yields:
        Tuple of (key_index, key_name, results) for each key searched
    """
    try:
        from ..utils.chord_transposer import (
            generate_search_queries, 
            describe_transposition, 
            parse_chord_sequence, 
            transpose_sequence,
            get_key_name,
            AccidentalPreference
        )
    except ImportError:
        from chord_importer.utils.chord_transposer import (
            generate_search_queries, 
            describe_transposition, 
            parse_chord_sequence, 
            transpose_sequence,
            get_key_name,
            AccidentalPreference
        )
    
    # Generate all search queries for different keys
    queries = generate_search_queries(chord_sequence)
    original_chords = parse_chord_sequence(chord_sequence)
    global_seen_urls: Set[str] = set()  # Track globally to avoid complete duplicates
    
    # Search each transposition dynamically
    for i, query in enumerate(queries):
        try:
            # Get key name for this transposition
            key_name = get_key_name(i, AccidentalPreference.PRESERVE_INPUT)
            
            # Request more results to account for potential duplicates
            # We'll request 2x to ensure we get enough unique results for this key
            search_limit = max(num_per_key * 2, 100)
            key_results = search_query(query, country=country, language=language, num=search_limit)
            
            # Process and enhance results for this key
            enhanced_results = []
            key_seen_urls: Set[str] = set()  # Track URLs for this specific key
            
            for result in key_results:
                # Allow same URL in different keys, but not within the same key
                if result.url not in key_seen_urls:
                    key_seen_urls.add(result.url)
                    global_seen_urls.add(result.url)
                    
                    # Add key information to the title or snippet
                    transposed_chords = transpose_sequence(original_chords, i, AccidentalPreference.PRESERVE_INPUT)
                    key_info = describe_transposition(chord_sequence, i, AccidentalPreference.PRESERVE_INPUT)
                    
                    # Create enhanced result with key information
                    enhanced_result = SearchResult(
                        title=f"{result.title} [{key_info}]",
                        url=result.url,
                        snippet=f"{key_info} | {result.snippet}" if result.snippet else key_info
                    )
                    enhanced_results.append(enhanced_result)
                    
                    # Stop when we have enough results for this key
                    if len(enhanced_results) >= num_per_key:
                        break
            
            # Call callback if provided
            if callback:
                callback(i, key_name, enhanced_results)
            
            # Yield results for this key
            yield i, key_name, enhanced_results
                    
        except Exception:
            # Continue with other keys if one fails
            if callback:
                callback(i, get_key_name(i), [])
            yield i, get_key_name(i), []


def search_with_source_dorks(query: str, source_id: Optional[str] = None, country: str = "br", language: str = "pt-br") -> List[SearchResult]:
    """Search using dorks from source configurations.
    
    Args:
        query: Search query
        source_id: Specific source ID to use dorks from, or None for all sources
        country: Country code for search
        language: Language code for search
        
    Returns:
        List of search results from all applicable dorks
    """
    try:
        # Import source manager
        try:
            from .source_configs import get_source_manager
        except ImportError:
            from chord_importer.source_configs import get_source_manager
        
        source_manager = get_source_manager()
        all_results = []
        seen_urls = set()
        
        # Get search queries from dorks
        search_queries = source_manager.search_with_dorks(query, source_id)
        
        if not search_queries:
            # Fallback to basic search if no dorks available
            return search_query(query, country, language)
        
        # Execute each dork query
        for dork_query in search_queries[:5]:  # Limit to top 5 dorks to avoid too many requests
            try:
                # Use existing search_query function
                results = search_query(dork_query, country, language, num=10)
                
                # Add unique results
                for result in results:
                    if result.url not in seen_urls:
                        seen_urls.add(result.url)
                        all_results.append(result)
                        
                        # Limit total results
                        if len(all_results) >= 50:
                            break
                
                if len(all_results) >= 50:
                    break
                    
            except Exception as e:
                print(f"Error executing dork query '{dork_query}': {e}")
                continue
        
        return all_results
        
    except Exception as e:
        print(f"Error in search_with_source_dorks: {e}")
        # Fallback to basic search
        return search_query(query, country, language)


def search_cifraclub_with_dorks(query: str) -> List[SearchResult]:
    """Search CifraClub using its configured dorks."""
    return search_with_source_dorks(query, source_id="cifraclub")


def search_all_sources_with_dorks(query: str) -> List[SearchResult]:
    """Search all sources using their configured dorks."""
    return search_with_source_dorks(query, source_id=None)

