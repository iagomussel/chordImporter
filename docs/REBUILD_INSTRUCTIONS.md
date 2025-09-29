# Rebuild Instructions for Musical Tools Suite

## Problem
The current executable asks users to install `sounddevice` and `numpy` because these dependencies weren't properly included in the PyInstaller build.

## Solution
Updated the build process to properly include all audio processing dependencies.

## Files Modified/Added

### 1. Updated PyInstaller Specification
- **File**: `ChordImporter.spec`
- **Changes**: 
  - Added `sounddevice` to hiddenimports
  - Added numpy internals and sounddevice internals
  - Added hooks directory path
  - Added missing standard library modules

### 2. Created PyInstaller Hooks
- **File**: `hooks/hook-sounddevice.py` - Ensures sounddevice is properly collected
- **File**: `hooks/hook-numpy.py` - Ensures all numpy submodules are included

### 3. Enhanced Build Script
- **File**: `build_with_audio.py` - Automated build process with dependency checking

## How to Rebuild

### Option 1: Using the Enhanced Build Script (Recommended)
```bash
python build_with_audio.py
```

This script will:
- Check all required dependencies
- Clean previous builds
- Create necessary hooks
- Build with proper audio support
- Verify the build

### Option 2: Manual PyInstaller Build
```bash
# Clean previous builds
rmdir /s build dist

# Build with the updated spec
pyinstaller --clean --noconfirm ChordImporter.spec
```

### Option 3: Step-by-Step Manual Process
```bash
# 1. Ensure dependencies are installed
pip install sounddevice numpy pyinstaller

# 2. Clean previous builds
rmdir /s build
rmdir /s dist

# 3. Create hooks directory (if not exists)
mkdir hooks

# 4. Run PyInstaller
pyinstaller --clean --noconfirm --log-level=INFO ChordImporter.spec
```

## Verification

After building, verify the executable includes audio dependencies:

1. **Check file size**: Should be larger than before (due to included audio libraries)
2. **Check _internal directory**: Should contain numpy and sounddevice related files
3. **Test the tuner**: 
   - Run `dist/MusicalToolsSuite/MusicalToolsSuite.exe`
   - Click "Advanced Tuner"
   - Should open without asking for installations

## Expected Results

✅ **Before Fix**: Executable asks user to install sounddevice and numpy
✅ **After Fix**: Tuner opens immediately with all dependencies bundled

## Dependencies Now Included

- **sounddevice**: Modern audio I/O library
- **numpy**: Numerical computing (with all submodules)
- **cffi**: C Foreign Function Interface (required by sounddevice)
- **All numpy internals**: Core, linalg, fft, random modules

## Build Output Location

The rebuilt executable will be at:
```
dist/MusicalToolsSuite/MusicalToolsSuite.exe
```

## Troubleshooting

### If build fails:
1. Check that all dependencies are installed: `pip install -r requirements.txt`
2. Ensure Python and PyInstaller are up to date
3. Run with verbose logging: `pyinstaller --log-level=DEBUG ChordImporter.spec`

### If executable still asks for dependencies:
1. Check the `_internal` directory for numpy/sounddevice files
2. Verify hooks were applied (check build log)
3. Try rebuilding with `--clean` flag

### If tuner doesn't work:
1. Check Windows audio permissions
2. Ensure microphone access is enabled
3. Test with different audio devices

## File Sizes (Approximate)

- **Before**: ~50-80 MB
- **After**: ~120-150 MB (due to included audio libraries)

This size increase is normal and necessary for standalone audio functionality.

## Notes

- The hooks ensure that PyInstaller finds and includes all necessary audio processing modules
- The enhanced build script provides better error checking and verification
- All audio functionality now works out-of-the-box without requiring users to install additional packages
