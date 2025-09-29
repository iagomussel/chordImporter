from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Tuple
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

# Optional Playwright import for dynamic rendering fallback
try:  # pragma: no cover - optional dependency
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - environment may not have Playwright
    sync_playwright = None  # type: ignore[assignment]


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _normalize_lyrics_text(text: str) -> str:
    """Normalize lyrics text: unify newlines, trim line-end spaces, collapse blanks."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    normalized_lines: list[str] = []
    last_was_blank = False
    for line in lines:
        if line.strip() == "":
            if not last_was_blank:
                normalized_lines.append("")
            last_was_blank = True
        else:
            normalized_lines.append(line)
            last_was_blank = False
    while normalized_lines and normalized_lines[0] == "":
        normalized_lines.pop(0)
    while normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()
    return "\n".join(normalized_lines)


def _extract_text_from_pre(pre: Tag) -> str:
    """Extract readable text from a <pre> element without breaking inline tags.

    Uses a single space as the separator between text nodes so inline tags
    like <b> do not force artificial line breaks. Preserves original newlines
    inside the <pre>, trims trailing spaces, and collapses excessive blank lines.
    """
    # Insert a space between adjacent text nodes produced by inline tags
    # while preserving newlines that already exist in the text nodes.
    raw_text = pre.get_text(" ")
    return _normalize_lyrics_text(raw_text)


def _is_chord_token(token: str) -> bool:
    """Heuristic check if a token looks like a chord name.

    Accepts forms like: A, Bb, C#, F#m, A4, G7, D/F#, Bm7(b5), Cadd9, G°.
    Very permissive on suffixes to avoid false negatives.
    """
    t = token.strip()
    if not t:
        return False
    # Common separators-only tokens do not count as chords
    if t in {"|", "-", "—", "~", "x", "X"}:
        return True  # allow bar-like separators as chord-line glue
    # Must start with A-G
    if not t[0] in "ABCDEFG":
        return False
    # Simple pattern: root + optional accidental + optional complex suffixes and slash bass
    # We avoid importing 're' at module top; local import here keeps scope tight
    import re as _re  # local import

    pattern = _re.compile(r"^[A-G](?:#|b)?[a-zA-Z0-9+º°()#b]*?(?:/[A-G](?:#|b)?)?$")
    return bool(pattern.match(t))


def _is_chord_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    # Do not treat metadata/labels or directives as chord lines
    if stripped.startswith("[") and stripped.endswith("]"):
        return False
    if ":" in stripped:
        # Lines like "Instrumental: E  A  E  D" contain ':' and should not be dot-prefixed
        return False
    tokens = [tok for tok in stripped.split() if tok]
    if not tokens:
        return False
    # Must have at least one token that is a chord
    any_chord = False
    for tok in tokens:
        if _is_chord_token(tok):
            any_chord = True
        else:
            # If any token is clearly not a chord-ish token, bail
            # Allow separators-only tokens already handled in _is_chord_token
            return False
    return any_chord


def _format_opensong_lyrics(lyrics: str) -> str:
    """Format lyrics for OpenSong compatibility.

    - Insert [Vn] before verses by converting 'Verso n:' lines to labels
    - Prefix chord-only lines with '.' so OpenSong recognizes them as chord lines
    """
    lines = lyrics.split("\n")
    formatted: list[str] = []
    verse_counter = 0

    import re as _re
    verso_re = _re.compile(r"^\s*verso\s*(\d+)?\s*:?[\s\-]*$", _re.IGNORECASE)

    for raw_line in lines:
        line = raw_line.rstrip()
        # Convert 'Verso X:' to [Vn]
        m = verso_re.match(line)
        if m:
            num_txt = m.group(1)
            if num_txt and num_txt.isdigit():
                verse_counter = int(num_txt)
            else:
                verse_counter += 1
            formatted.append(f"[V{verse_counter}]")
            continue

        # Prefix chord-only lines with '.'
        if _is_chord_line(line):
            formatted.append("." + line)
        else:
            formatted.append(line)

    # Normalize result (trim excess blank lines, etc.)
    return _normalize_lyrics_text("\n".join(formatted))


def _extract_title_and_author(soup: BeautifulSoup) -> Tuple[str, str]:
    """Best-effort extraction of song title and author from the page.

    Tries common patterns for simple chord/lyrics pages and falls back to
    "Unknown" fields if nothing suitable is found.
    """
    title = ""
    author = ""

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)

    h2 = soup.find("h2")
    if h2 and h2.get_text(strip=True):
        author = h2.get_text(strip=True)

    if not title:
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = og_title.get("content", "").strip()

    if not title:
        if soup.title and soup.title.get_text(strip=True):
            title = soup.title.get_text(strip=True)

    if not title:
        title = "Untitled"

    if not author:
        author = "Unknown"

    return title, author


def fetch_song(
    url: str,
    timeout: int = 30,
    use_dynamic: bool = False,
    fallback_to_dynamic: bool = True,
) -> Tuple[str, str, str]:
    """Fetch a song page and parse title, author, and raw lyrics/chords text.

    Parameters
    ----------
    url: str
        The page URL containing the chord/lyric content.
    timeout: int
        HTTP request timeout in seconds.

    Returns
    -------
    (title, author, lyrics): tuple[str, str, str]
    """
    # Try flexible extraction system first
    try:
        from .flexible_extractor import extract_with_flexible_config
        title, artist, content = extract_with_flexible_config(url)
        if title or content:  # If we got some data, use it
            return title, artist, content
    except Exception as e:
        print(f"Flexible extraction failed for {url}: {e}")
    
    # Fallback to legacy CifraClub extraction
    if 'cifraclub.com.br' in url:
        try:
            song_data = fetch_cifraclub_enhanced(url)
            if song_data['title'] or song_data['content']:
                formatted_content = format_cifraclub_export(song_data)
                return song_data['title'], song_data['artist'], formatted_content
        except Exception as e:
            print(f"Legacy CifraClub extraction failed: {e}")
    
    # Fallback to dynamic rendering if requested
    if use_dynamic:
        return _fetch_song_dynamic(url, timeout)

    # Final fallback to basic extraction
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # Prefer <pre>, which CifraClub and many simple pages use for chords
    pre = soup.select_one("pre, div.cifra-container pre, article pre") or soup.find("pre")
    if not pre:
        if fallback_to_dynamic:
            return _fetch_song_dynamic(url, timeout)
        raise ValueError("Não encontrei cifra/letra no HTML (nenhuma tag <pre>).")

    # Preserve original line breaks, but avoid injecting extra ones between inline tags
    lyrics = _extract_text_from_pre(pre)
    title, author = _extract_title_and_author(soup)

    return title, author, lyrics


def _fetch_song_dynamic(url: str, timeout: int) -> Tuple[str, str, str]:
    """Use Playwright to render the page and extract <pre>. Mimics console `$(`pre`)` usage.

    Requires `pip install playwright` and `python -m playwright install`.
    """
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright não está instalado. Execute: pip install playwright && python -m playwright install"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            locale="pt-BR",
        )
        page = context.new_page()
        page.set_default_timeout(timeout * 1000)
        page.goto(url, wait_until="domcontentloaded")
        # Give late-loading content a moment; then attempt to extract
        try:
            page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        except Exception:
            pass

        js_extract = """
        () => {
          const byQS = document.querySelector('pre');
          if (byQS && byQS.innerText && byQS.innerText.trim()) {
            return { lyrics: byQS.innerText, title: document.title || '', author: '' };
          }
          if (window.$ && $('pre').length > 0) {
            const el = $('pre')[0];
            const txt = el && el.innerText ? el.innerText : '';
            return { lyrics: txt, title: document.title || '', author: '' };
          }
          return { lyrics: '', title: document.title || '', author: '' };
        }
        """
        data = page.evaluate(js_extract)
        lyrics = (data or {}).get("lyrics", "") if isinstance(data, dict) else ""
        lyrics = _normalize_lyrics_text(lyrics)

        # Title/author best-effort from DOM
        title_author = page.evaluate(
            """
            () => {
              const getText = (sel) => {
                const el = document.querySelector(sel);
                return el && el.textContent ? el.textContent.trim() : '';
              };
              let title = getText('h1');
              if (!title) {
                const meta = document.querySelector('meta[property="og:title"]');
                if (meta && meta.content) title = meta.content.trim();
              }
              if (!title) title = document.title || 'Untitled';
              let author = getText('h2');
              if (!author) author = 'Unknown';
              return [title, author];
            }
            """
        )
        page.close()
        context.close()
        browser.close()

        if not lyrics.strip():
            raise ValueError("Não encontrei cifra/letra após renderização (sem <pre>).")

        title = title_author[0] if isinstance(title_author, (list, tuple)) else "Untitled"
        author = title_author[1] if isinstance(title_author, (list, tuple)) else "Unknown"
        return title, author, lyrics


def build_opensong_xml(title: str, author: str, lyrics: str) -> str:
    """Generate OpenSong XML content from parsed song data."""
    # Apply OpenSong formatting to lyrics
    lyrics = _format_opensong_lyrics(lyrics)
    song = ET.Element("song")
    ET.SubElement(song, "title").text = title
    ET.SubElement(song, "author").text = author
    ET.SubElement(song, "copyright").text = "Public Domain or Site License"
    ET.SubElement(song, "presentation").text = "V1 C V2 C"
    ET.SubElement(song, "ccli").text = ""
    ET.SubElement(song, "theme").text = "Worship"
    ET.SubElement(song, "alttheme").text = ""
    ET.SubElement(song, "user1").text = ""

    ET.SubElement(song, "lyrics").text = lyrics

    return ET.tostring(song, encoding="utf-8", xml_declaration=True).decode("utf-8")


def save_song(filename: str, xml_content: str) -> None:
    """Write XML content to a UTF-8 file."""
    from pathlib import Path

    path = Path(filename)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml_content)


def download_cifraclub_pdf(url: str, output_path: str, timeout: int = 30) -> None:
    """Download PDF from CifraClub by adding '/imprimir.html' to the URL.
    
    Uses Playwright as the primary method since it doesn't require external dependencies.
    
    Parameters
    ----------
    url: str
        The original CifraClub URL
    output_path: str
        Path where to save the PDF file
    timeout: int
        Request timeout in seconds
    """
    # Use Playwright as primary method - it's more reliable and doesn't need external tools
    return download_cifraclub_pdf_alternative(url, output_path, timeout)


def download_cifraclub_pdf_alternative(url: str, output_path: str, timeout: int = 30) -> None:
    """Alternative method to download PDF using Playwright (if pdfkit fails).
    
    Parameters
    ----------
    url: str
        The original CifraClub URL
    output_path: str
        Path where to save the PDF file
    timeout: int
        Request timeout in seconds
    """
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright não está instalado. Execute: pip install playwright && python -m playwright install"
        )
    
    # Add '/imprimir.html' to the URL if it's a CifraClub URL
    if "cifraclub.com.br" in url:
        base_url = url.rstrip('/')
        print_url = base_url + '/imprimir.html'
    else:
        raise ValueError("URL deve ser do CifraClub (cifraclub.com.br)")
    
    # Create output directory if it doesn't exist
    from pathlib import Path
    path = Path(output_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            locale="pt-BR",
        )
        page = context.new_page()
        page.set_default_timeout(timeout * 1000)
        
        try:
            page.goto(print_url, wait_until="domcontentloaded")
            # Wait for content to load
            page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            
            # Generate PDF
            page.pdf(
                path=output_path,
                format='A4',
                margin={
                    'top': '0.75in',
                    'right': '0.75in', 
                    'bottom': '0.75in',
                    'left': '0.75in'
                },
                print_background=True
            )
        finally:
            page.close()
            context.close()
            browser.close()


def fetch_cifraclub_enhanced(url: str) -> dict:
    """
    Enhanced extraction specifically for CifraClub URLs.
    Uses the print version (/imprimir.html) for cleaner extraction.
    
    Args:
        url: CifraClub URL
        
    Returns:
        Dictionary with song information
    """
    try:
        # Convert to print URL for easier extraction
        print_url = url.rstrip('/') + '/imprimir.html'
        
        response = requests.get(print_url, headers=DEFAULT_HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Initialize result dictionary
        song_data = {
            'title': '',
            'artist': '',
            'key': '',
            'capo': '',
            'content': '',
            'metadata': {}
        }
        
        # Extract song title using print page selectors
        title_element = soup.select_one('.cifra_header > h1 > a')
        if title_element:
            song_data['title'] = title_element.get_text().strip()
        else:
            # Fallback to regular h1
            title_tag = soup.find('h1')
            if title_tag:
                song_data['title'] = title_tag.get_text().strip()
        
        # Extract artist name using print page selectors
        artist_element = soup.select_one('.cifra_header > h2 > a')
        if artist_element:
            song_data['artist'] = artist_element.get_text().strip()
        else:
            # Fallback to regular h2
            artist_tag = soup.find('h2')
            if artist_tag:
                song_data['artist'] = artist_tag.get_text().strip()
        
        # Extract key/tom information from text content
        tom_elements = soup.find_all(string=lambda text: text and 'tom:' in text.lower())
        if tom_elements:
            for tom_text in tom_elements:
                tom_str = str(tom_text).strip()
                if 'tom:' in tom_str.lower():
                    key_parts = tom_str.split('tom:')
                    if len(key_parts) > 1:
                        key_raw = key_parts[1].split('(')[0].strip()
                        song_data['key'] = key_raw
                        
                        # Extract original key from parentheses if present
                        if '(' in key_parts[1] and ')' in key_parts[1]:
                            original_key = key_parts[1].split('(')[1].split(')')[0]
                            if 'forma dos acordes no tom de' in original_key:
                                original = original_key.replace('forma dos acordes no tom de', '').strip()
                                song_data['metadata']['original_key'] = original
                        break
        
        # Extract capo information from text content
        capo_elements = soup.find_all(string=lambda text: text and 'capotraste' in text.lower())
        if capo_elements:
            import re
            for capo_text in capo_elements:
                capo_str = str(capo_text).strip()
                
                # First check if this text itself contains the full pattern
                capo_match = re.search(r'capotraste na (\d+)', capo_str.lower())
                if capo_match:
                    song_data['capo'] = f"Capotraste na {capo_match.group(1)}ª casa"
                    break
                
                # If not, check parent element for more context
                if 'capotraste' in capo_str.lower() and hasattr(capo_text, 'parent') and capo_text.parent:
                    parent_text = capo_text.parent.get_text()
                    capo_match = re.search(r'capotraste na (\d+)', parent_text.lower())
                    if capo_match:
                        song_data['capo'] = f"Capotraste na {capo_match.group(1)}ª casa"
                        break
            
            # If no specific pattern found, try searching the full page text
            if not song_data['capo']:
                full_text = soup.get_text()
                capo_match = re.search(r'capotraste na (\d+)', full_text.lower())
                if capo_match:
                    song_data['capo'] = f"Capotraste na {capo_match.group(1)}ª casa"
        
        # Extract chord progression and lyrics from <pre> tag
        pre_tag = soup.find('pre')
        if pre_tag:
            song_data['content'] = _extract_text_from_pre(pre_tag)
        else:
            # Fallback: try to find content in other containers
            content_containers = [
                soup.find('div', class_='cifra_cnt'),
                soup.find('div', class_='cifra-content'),
                soup.find('div', class_='song-content')
            ]
            
            for container in content_containers:
                if container:
                    song_data['content'] = container.get_text().strip()
                    break
        
        # Extract additional metadata from the original URL (not print version)
        try:
            original_response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
            original_soup = BeautifulSoup(original_response.content, 'html.parser')
            song_data['metadata'].update(_extract_cifraclub_metadata(original_soup))
        except:
            pass  # If original page fails, continue without metadata
        
        return song_data
        
    except Exception as e:
        print(f"Error fetching enhanced CifraClub data from {url}: {e}")
        # Fallback to original URL if print version fails
        try:
            return _fetch_cifraclub_fallback(url)
        except:
            return {
                'title': '',
                'artist': '',
                'key': '',
                'capo': '',
                'content': '',
                'metadata': {}
            }


def _fetch_cifraclub_fallback(url: str) -> dict:
    """Fallback extraction for CifraClub when print version fails."""
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    song_data = {
        'title': '',
        'artist': '',
        'key': '',
        'capo': '',
        'content': '',
        'metadata': {}
    }
    
    # Basic extraction
    title_tag = soup.find('h1')
    if title_tag:
        song_data['title'] = title_tag.get_text().strip()
    
    artist_tag = soup.find('h2')
    if artist_tag:
        song_data['artist'] = artist_tag.get_text().strip()
    
    pre_tag = soup.find('pre')
    if pre_tag:
        song_data['content'] = _extract_text_from_pre(pre_tag)
    
    return song_data


def _extract_cifraclub_metadata(soup: BeautifulSoup) -> dict:
    """Extract additional metadata from CifraClub page."""
    metadata = {}
    
    try:
        # Extract composition info
        composition_text = soup.find(text=lambda text: text and 'Composição de' in text)
        if composition_text:
            # Get the text after "Composição de"
            comp_info = composition_text.strip()
            if 'Composição de' in comp_info:
                composers = comp_info.split('Composição de')[1].strip()
                # Remove any trailing text like "Esta informação está errada?"
                if '.' in composers:
                    composers = composers.split('.')[0]
                metadata['composers'] = composers
        
        # Extract view count
        views_element = soup.find(text=lambda text: text and 'exibições' in text)
        if views_element:
            views_text = views_element.strip()
            # Extract just the number
            import re
            views_match = re.search(r'([\d.,]+)\s*exibições', views_text)
            if views_match:
                metadata['views'] = views_match.group(1)
        
        # Extract collaborators
        collab_section = soup.find(text=lambda text: text and 'Colaboração e revisão' in text)
        if collab_section:
            # Look for the next element containing names
            parent = collab_section.parent if collab_section.parent else None
            if parent:
                # Find collaborator names in nearby elements
                next_elements = parent.find_next_siblings()
                for elem in next_elements[:3]:  # Check next few elements
                    if elem and elem.get_text().strip():
                        text = elem.get_text().strip()
                        if text and not text.startswith('*') and len(text) < 100:
                            metadata['collaborators'] = text
                            break
        
        # Extract difficulty if available
        difficulty_elem = soup.find(class_='difficulty')
        if difficulty_elem:
            metadata['difficulty'] = difficulty_elem.get_text().strip()
            
        # Extract instrument info
        instrument_info = soup.find(text=lambda text: text and 'Cifra:' in text)
        if instrument_info:
            metadata['instrument_info'] = instrument_info.strip()
    
    except Exception:
        pass  # Ignore metadata extraction errors
    
    return metadata


def format_cifraclub_export(song_data: dict) -> str:
    """
    Format CifraClub song data for export.
    
    Args:
        song_data: Dictionary with song information
        
    Returns:
        Formatted string with complete song information
    """
    lines = []
    
    # Header with song info
    if song_data['title']:
        lines.append(f"TITULO: {song_data['title']}")
    
    if song_data['artist']:
        lines.append(f"ARTISTA: {song_data['artist']}")
    
    if song_data['key']:
        lines.append(f"TOM: {song_data['key']}")
        
    if song_data.get('metadata', {}).get('original_key'):
        lines.append(f"TOM ORIGINAL: {song_data['metadata']['original_key']}")
    
    if song_data['capo']:
        lines.append(f"CAPOTRASTE: {song_data['capo']}")
    
    # Metadata section
    metadata = song_data.get('metadata', {})
    if metadata.get('composers'):
        lines.append(f"COMPOSICAO: {metadata['composers']}")
    
    if metadata.get('views'):
        lines.append(f"VISUALIZACOES: {metadata['views']}")
    
    if metadata.get('collaborators'):
        lines.append(f"COLABORACAO: {metadata['collaborators']}")
    
    if metadata.get('instrument_info'):
        lines.append(f"INSTRUMENTO: {metadata['instrument_info']}")
    
    # Separator
    lines.append("")
    lines.append("=" * 50)
    lines.append("CIFRA E LETRA")
    lines.append("=" * 50)
    lines.append("")
    
    # Main content (chords and lyrics)
    if song_data['content']:
        lines.append(song_data['content'])
    
    return "\n".join(lines)


