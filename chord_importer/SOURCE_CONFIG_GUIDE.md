# Source Configuration Guide

This guide explains how to configure extraction rules for different music websites using the Musical Tools Suite.

## Overview

The Musical Tools Suite uses a flexible configuration system that allows you to extract song data from any music website by defining CSS selectors, text patterns, and other extraction rules.

## Configuration File Location

- **Default configurations**: `chord_importer/default_sources.json`
- **User configurations**: `~/.chord_importer/sources/sources.json`

## Configuration Structure

Each source configuration contains:

```json
{
  "source_id": {
    "name": "Site Name",
    "domain_patterns": ["domain.com", "subdomain.domain.com"],
    "url_suffix": "/print",
    "title_selector": { /* selector config */ },
    "artist_selector": { /* selector config */ },
    "key_selector": { /* selector config */ },
    "capo_selector": { /* selector config */ },
    "content_selector": { /* selector config */ },
    "composer_selector": { /* selector config */ },
    "views_selector": { /* selector config */ },
    "difficulty_selector": { /* selector config */ },
    "instrument_selector": { /* selector config */ },
    "remove_scripts": true,
    "remove_styles": true,
    "encoding": "utf-8",
    "timeout": 15
  }
}
```

## Selector Configuration

Each selector can use multiple extraction methods:

```json
{
  "css_selector": ".song-title",
  "xpath_selector": "//h1[@class='title']",
  "regex_pattern": "Title:\\s*(.+)",
  "text_search": "Title:",
  "attribute": "data-title",
  "fallback_selectors": ["h1", ".title", "#song-name"],
  "join_separator": ", "
}
```

### Selector Types

1. **CSS Selector**: Standard CSS selector syntax
   - `"h1"` - Select h1 elements
   - `".song-title"` - Select elements with class "song-title"
   - `"#title"` - Select element with ID "title"
   - `".header > h1 > a"` - Select nested elements

2. **Text Search + Regex**: Find text and extract with regex
   - `"text_search": "Tom:"` - Find text containing "Tom:"
   - `"regex_pattern": "Tom:\\s*([A-G][#b]?)"` - Extract key after "Tom:"

3. **Fallback Selectors**: Alternative selectors if primary fails
   - `["h1", ".title", "#song-name"]` - Try each selector in order

4. **Join Separator**: Combine multiple elements into one result
   - `", "` - Join with comma and space: "Author 1, Author 2, Author 3"
   - `" | "` - Join with pipe: "Genre 1 | Genre 2 | Genre 3"
   - `"\n"` - Join with newlines (useful for lyrics or multiple verses)
   - `null` or empty - Extract only the first matching element

## Example Configurations

### CifraClub (Print Version)

```json
{
  "cifraclub": {
    "name": "CifraClub",
    "domain_patterns": ["cifraclub.com.br"],
    "url_suffix": "/imprimir.html",
    "title_selector": {
      "css_selector": ".cifra_header > h1 > a",
      "fallback_selectors": ["h1", "title"]
    },
    "artist_selector": {
      "css_selector": ".cifra_header > h2 > a",
      "fallback_selectors": ["h2", ".artist-name"]
    },
    "key_selector": {
      "text_search": "tom:",
      "regex_pattern": "tom:\\s*([A-G][#b]?)",
      "fallback_selectors": [".cifra_tom", "#cifra_tom"]
    },
    "capo_selector": {
      "text_search": "capotraste",
      "regex_pattern": "capotraste na (\\d+)",
      "fallback_selectors": [".cifra_capo", "#cifra_capo"]
    },
    "content_selector": {
      "css_selector": "pre",
      "fallback_selectors": [".cifra_cnt", ".song-content", ".lyrics"]
    }
  }
}
```

### Ultimate Guitar

```json
{
  "ultimate_guitar": {
    "name": "Ultimate Guitar",
    "domain_patterns": ["ultimate-guitar.com"],
    "url_suffix": "",
    "title_selector": {
      "css_selector": "h1._3xXoI",
      "fallback_selectors": ["h1", ".song-title"]
    },
    "artist_selector": {
      "css_selector": ".t4Dkh a",
      "fallback_selectors": [".artist-name"]
    },
    "key_selector": {
      "text_search": "Key:",
      "regex_pattern": "Key:\\s*([A-G][#b]?)"
    },
    "capo_selector": {
      "text_search": "Capo:",
      "regex_pattern": "Capo:\\s*(\\d+)"
    },
    "content_selector": {
      "css_selector": "pre._3sw45",
      "fallback_selectors": ["pre", ".tab-content"]
    }
  }
}
```

### Generic Site

```json
{
  "generic": {
    "name": "Generic",
    "domain_patterns": ["*"],
    "url_suffix": "",
    "title_selector": {
      "css_selector": "h1",
      "fallback_selectors": ["title", ".song-title", ".title"]
    },
    "artist_selector": {
      "css_selector": "h2",
      "fallback_selectors": [".artist", ".artist-name", ".singer"]
    },
    "content_selector": {
      "css_selector": "pre",
      "fallback_selectors": [".lyrics", ".song-content", ".content"]
    }
  }
}
```

## How to Add a New Site

1. **Analyze the Website Structure**:
   - Inspect the HTML elements containing song data
   - Note CSS classes, IDs, and text patterns
   - Check if there's a print/clean version

2. **Create Configuration**:
   - Open Source Configuration in the app
   - Click "Nova Fonte" (New Source)
   - Fill in the basic information
   - Configure selectors for each field

3. **Test the Configuration**:
   - Use the "Teste" tab to validate extraction
   - Adjust selectors as needed
   - Save when working correctly

### Multiple Elements Example

For sites that list multiple composers, genres, or collaborators:

```json
{
  "composer_selector": {
    "css_selector": ".composer-name",
    "join_separator": ", ",
    "fallback_selectors": [".author", ".writer"]
  },
  "genre_selector": {
    "css_selector": ".genre-tag",
    "join_separator": " | ",
    "fallback_selectors": [".category", ".style"]
  },
  "collaborators_selector": {
    "css_selector": ".collaborator",
    "join_separator": "\n",
    "fallback_selectors": [".featuring", ".guest"]
  }
}
```

**Results**:
- **Composers**: "João Silva, Maria Santos, Pedro Oliveira"
- **Genres**: "Rock | Pop | Blues"
- **Collaborators**: "Artist 1\nArtist 2\nArtist 3"

## Advanced Features

### URL Suffix

Some sites have cleaner versions for printing:
- CifraClub: `/imprimir.html`
- Some sites: `/print`, `/clean`, `/text`

### Domain Patterns

You can specify multiple domains:
```json
"domain_patterns": ["site.com", "www.site.com", "m.site.com"]
```

### Regex Patterns

Common patterns for music data:
- **Key**: `"([A-G][#b]?)"`
- **Capo**: `"capo.*?(\\d+)"`
- **Tempo**: `"(\\d+)\\s*bpm"`
- **Time Signature**: `"(\\d+/\\d+)"`

### Processing Options

```json
{
  "remove_scripts": true,    // Remove <script> tags
  "remove_styles": true,     // Remove <style> tags
  "encoding": "utf-8",       // Text encoding
  "timeout": 15              // Request timeout in seconds
}
```

## Management Commands

### Via GUI

1. **Open Configuration**: Dashboard → "🌐 Source Configuration"
2. **Import/Export**: Share configurations with others
3. **Reset to Defaults**: Restore original configurations
4. **Test**: Validate configurations before saving

### Via Code

```python
from chord_importer.source_configs import get_source_manager

manager = get_source_manager()

# List all sources
sources = manager.list_sources()

# Get specific source
config = manager.get_source("cifraclub")

# Add new source
manager.add_source("new_site", config)

# Reset to defaults
manager.reset_to_defaults()
```

## Troubleshooting

### Common Issues

1. **No Data Extracted**: Check CSS selectors in browser dev tools
2. **Wrong Data**: Verify regex patterns and text search
3. **Timeout Errors**: Increase timeout or check URL suffix
4. **Encoding Issues**: Try different encoding (utf-8, latin1, etc.)

### Debugging Tips

1. Use browser "Inspect Element" to find correct selectors
2. Test regex patterns online (regex101.com)
3. Check if site has anti-bot protection
4. Try different URL variations (www, mobile, print versions)

## Best Practices

1. **Start Simple**: Begin with basic title/artist extraction
2. **Use Fallbacks**: Always provide alternative selectors
3. **Test Thoroughly**: Validate with multiple songs
4. **Document Changes**: Keep notes on selector updates
5. **Share Configurations**: Export working configs for others

## Contributing

If you create configurations for popular music sites, consider:
1. Testing with multiple songs
2. Adding comprehensive fallback selectors
3. Sharing via GitHub or community forums
4. Documenting any special requirements

## Support

For help with configurations:
1. Check existing configurations in `default_sources.json`
2. Use the built-in test functionality
3. Consult browser developer tools
4. Ask in community forums or GitHub issues
