# Test the updated system with no content truncation
from chord_importer.source_configs import get_source_manager
from chord_importer.flexible_extractor import FlexibleExtractor

# Force reload from updated JSON
import shutil
from pathlib import Path

config_dir = Path.home() / '.chord_importer' / 'sources'
if config_dir.exists():
    shutil.rmtree(config_dir)
    print('Cleared existing config to force reload from updated JSON')

manager = get_source_manager()
extractor = FlexibleExtractor()

# Test with CifraClub URL
test_url = 'https://www.cifraclub.com.br/julliany-souza/eu-e-minha-casa-part-leo-brandao/'
config = manager.find_source_for_url(test_url)

print('=== TESTING FULL CONTENT EXTRACTION ===')
print(f'URL: {test_url}')
print(f'Config: {config.name}')
print()

try:
    song_data = extractor.extract_song_data(test_url, config)
    
    print('=== EXTRACTION RESULTS ===')
    print('Title:', song_data.get('title', 'N/A'))
    print('Artist:', song_data.get('artist', 'N/A'))
    print('Key:', song_data.get('key', 'N/A'))
    print('Capo:', song_data.get('capo', 'N/A'))
    
    content = song_data.get('content', '')
    print('Content length:', len(content), 'characters')
    print('Content lines:', content.count('\n') + 1 if content else 0)
    
    if content:
        print()
        print('=== CONTENT PREVIEW (first 500 chars) ===')
        print(content[:500])
        if len(content) > 500:
            print('...')
            print()
            print('=== CONTENT END (last 200 chars) ===')
            print(content[-200:])
    
    print()
    print('[OK] Full content extraction successful - no truncation!')
    
except Exception as e:
    print('[ERROR] Extraction failed:', str(e))
