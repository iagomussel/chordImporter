# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent

block_cipher = None

# Define the main script
main_script = project_root / 'chord_importer' / '__main__.py'

# Collect all Python files from the chord_importer package
chord_importer_files = []
chord_importer_dir = project_root / 'chord_importer'
for py_file in chord_importer_dir.glob('*.py'):
    if py_file.name != '__main__.py':
        chord_importer_files.append((str(py_file), 'chord_importer'))

# Hidden imports for dependencies that might not be auto-detected
hidden_imports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'numpy',
    'pyaudio',
    'scipy',
    'scipy.io',
    'scipy.io.wavfile',
    'scipy.fftpack',
    'requests',
    'beautifulsoup4',
    'playwright',
    'pdfkit',
    'dotenv',
    'threading',
    'sqlite3',
    'json',
    'pathlib',
    'webbrowser',
    'math',
    'time',
    'os',
    'sys',
    'subprocess',
    'datetime',
    'copy',
    'wave',
]

# Data files to include
datas = [
    # Include any data files if needed
    # ('path/to/data', 'destination/in/bundle'),
]

a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'setuptools',
        'pip',
        'wheel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ChordImporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'path/to/icon.ico'
    version_file=None,  # Add version file here if needed
)

# For Windows, create a directory distribution instead of single file
# This is often more reliable for complex applications
if sys.platform.startswith('win'):
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='ChordImporter'
    )
