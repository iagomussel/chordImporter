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
        
        # Audio processing - COMPLETE INCLUSION
        'numpy', 'scipy', 'pyaudio', 'librosa', 'soundfile', 'sounddevice',
        
        # NumPy - ALL submodules
        'numpy.core', 'numpy.core._multiarray_umath', 'numpy.core._multiarray_tests',
        'numpy.core.multiarray', 'numpy.core.umath', 'numpy.core._internal',
        'numpy.linalg', 'numpy.linalg._umath_linalg', 'numpy.linalg.lapack_lite',
        'numpy.fft', 'numpy.fft.fftpack_lite', 'numpy.fft.pocketfft_internal',
        'numpy.random', 'numpy.random._common', 'numpy.random._pickle',
        'numpy.random.bit_generator', 'numpy.random.mtrand', 'numpy.random._generator',
        'numpy.random._mt19937', 'numpy.random._pcg64', 'numpy.random._philox', 'numpy.random._sfc64',
        'numpy.ma', 'numpy.lib', 'numpy.polynomial',
        
        # SoundDevice - ALL components
        'sounddevice._internal', 'sounddevice._sounddevice',
        'sounddevice._sounddevice_data',
        
        # CFFI - Complete support
        'cffi', 'cffi.api', 'cffi.backend_ctypes', 'cffi.cparser', 'cffi.model',
        'cffi.lock', 'cffi.error', 'cffi.vengine_cpy', 'cffi.vengine_gen',
        '_cffi_backend',
        
        # SciPy - Core modules
        'scipy.io', 'scipy.io.wavfile', 'scipy.fftpack', 'scipy.signal',
        'scipy.sparse', 'scipy.linalg', 'scipy.ndimage',
        
        # Librosa - Complete audio analysis
        'librosa.core', 'librosa.feature', 'librosa.onset', 'librosa.beat',
        'librosa.tempo', 'librosa.decompose', 'librosa.effects', 'librosa.filters',
        'librosa.util', 'librosa.display', 'librosa.segment',
        'audioread', 'audioread.ffdec', 'audioread.gstdec', 'audioread.maddec',
        'numba', 'numba.core', 'numba.typed', 'numba.types',
        'scikit-learn', 'sklearn', 'sklearn.utils', 'sklearn.base',
        'joblib', 'decorator', 'pooch', 'soxr', 'lazy_loader', 'msgpack',
        
        # SoundFile
        'soundfile._soundfile', 'soundfile._soundfile_data',
        
        # Music theory
        'music21', 'mingus',
        
        # Web scraping and requests
        'requests', 'beautifulsoup4', 'lxml', 'html.parser',
        'charset_normalizer', 'idna', 'urllib3', 'certifi',
        
        # Browser automation
        'playwright', 'playwright.sync_api',
        
        # Data processing
        'sqlite3', 'json', 'configparser', 'pathlib',
        
        # Visualization
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg',
        'matplotlib.backends._backend_tkagg',
        
        # Threading and async
        'threading', 'asyncio', 'concurrent.futures', 'queue',
        
        # System and standard library
        'webbrowser', 'subprocess', 'os', 'sys', 'time', 'math',
        'collections', 'itertools', 'functools', 'operator',
        'struct', 'array', 'ctypes', 'ctypes.util',
        
        # Platform specific
        'platform', 'winreg', 'winsound',
        
        # Error handling and logging
        'traceback', 'logging', 'warnings'
    ],
    hookspath=['hooks'],
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
    icon='icon.ico',
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
