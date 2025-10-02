#!/usr/bin/env python3
"""
ChordImporter Android Setup Script
Helps set up the development environment
"""

import sys
import os
import subprocess
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def print_step(number, text):
    """Print a formatted step"""
    print(f"\n[{number}] {text}")
    print("-" * 60)

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is adequate"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"✗ Python {version.major}.{version.minor} is too old")
        print("  Please install Python 3.9 or higher")
        return False
    print(f"✓ Python {version.major}.{version.minor} is compatible")
    return True

def check_java():
    """Check if Java is installed"""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        print("✓ Java is installed")
        return True
    except FileNotFoundError:
        print("✗ Java not found")
        print("  Please install Java 11 or higher")
        print("  Download: https://adoptium.net/")
        return False

def install_dependencies(mode='desktop'):
    """Install required dependencies"""
    if mode == 'desktop':
        deps = ['kivy[base]', 'numpy', 'scipy', 'sounddevice']
        print("Installing desktop testing dependencies...")
    else:
        deps = ['kivy[base]', 'buildozer', 'cython', 'numpy', 'scipy']
        print("Installing Android build dependencies...")
    
    cmd = f"{sys.executable} -m pip install " + " ".join(deps)
    return run_command(cmd, "Dependency installation")

def test_kivy_import():
    """Test if Kivy can be imported"""
    try:
        import kivy
        print(f"✓ Kivy {kivy.__version__} imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import Kivy: {e}")
        return False

def create_test_script():
    """Create a simple test script"""
    test_script = """
from kivy.app import App
from kivy.uix.label import Label

class TestApp(App):
    def build(self):
        return Label(text='Kivy is working! ✓')

if __name__ == '__main__':
    TestApp().run()
"""
    
    with open('test_kivy.py', 'w') as f:
        f.write(test_script)
    print("✓ Created test script: test_kivy.py")

def main():
    """Main setup flow"""
    print_header("ChordImporter Android - Setup Wizard")
    
    print("This script will help you set up the development environment.")
    print("\nChoose setup mode:")
    print("  1. Desktop testing only (faster, for development)")
    print("  2. Full Android build environment (slower, for APK building)")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        return
    
    if choice not in ['1', '2']:
        print("Invalid choice. Exiting.")
        return
    
    mode = 'desktop' if choice == '1' else 'android'
    
    # Step 1: Check Python
    print_step(1, "Checking Python version")
    if not check_python_version():
        return
    
    # Step 2: Check Java (only for Android)
    if mode == 'android':
        print_step(2, "Checking Java installation")
        if not check_java():
            print("\nYou can continue with desktop testing for now.")
            print("Install Java later when you're ready to build APKs.")
            response = input("Continue with desktop mode? (y/n): ").strip().lower()
            if response == 'y':
                mode = 'desktop'
            else:
                return
    
    # Step 3: Install dependencies
    print_step(3 if mode == 'desktop' else 3, "Installing dependencies")
    print("This may take several minutes...")
    
    if not install_dependencies(mode):
        print("\nDependency installation failed. Please check the errors above.")
        return
    
    # Step 4: Test Kivy
    print_step(4 if mode == 'desktop' else 4, "Testing Kivy installation")
    if not test_kivy_import():
        print("\nKivy installation verification failed.")
        return
    
    # Step 5: Create test script
    print_step(5 if mode == 'desktop' else 5, "Creating test script")
    create_test_script()
    
    # Success!
    print_header("Setup Complete! ✓")
    
    if mode == 'desktop':
        print("You can now test the app on desktop:")
        print("  1. Run the tuner: python main.py")
        print("  2. Run the test: python test_kivy.py")
        print("\nTo build for Android later:")
        print("  1. Install Java 11+")
        print("  2. Run: pip install buildozer")
        print("  3. Run: buildozer android debug")
    else:
        print("Your environment is ready for Android development!")
        print("\nNext steps:")
        print("  1. Test on desktop: python main.py")
        print("  2. Build APK: buildozer -v android debug")
        print("  3. Deploy: buildozer android debug deploy run")
        print("\nNote: First build downloads SDK/NDK (20-60 min)")
    
    print("\nFor more information, see:")
    print("  - README.md (Getting started guide)")
    print("  - ../ANDROID_VERSION_PLAN.md (Full documentation)")
    print("  - ../ANDROID_SUMMARY.md (Quick reference)")

if __name__ == '__main__':
    main()

