# -*- mode: python ; coding: utf-8 -*-
# Musical Tools Suite - PyInstaller Specification

import os

a = Analysis(
    ['chord_importer\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('chord_importer\\default_sources.json', 'chord_importer'),
        ('chord_importer\\SOURCE_CONFIG_GUIDE.md', 'chord_importer'),
        ('chord_importer', 'chord_importer')
    ],
    hiddenimports=[
        # GUI frameworks
        'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox',
        # Audio processing
        'numpy', 'scipy', 'pyaudio', 'librosa', 'soundfile', 'sounddevice',
        # Music theory
        'music21', 'mingus',
        # Web scraping and requests
        'requests', 'beautifulsoup4', 'lxml', 'html.parser',
        # Browser automation
        'playwright', 'playwright.sync_api',
        # Data processing
        'sqlite3', 'json', 'configparser', 'pathlib',
        # Visualization
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg',
        # Threading and async
        'threading', 'asyncio', 'concurrent.futures',
        # System
        'webbrowser', 'subprocess', 'os', 'sys'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['test', 'tests', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MusicalToolsSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MusicalToolsSuite',
)
