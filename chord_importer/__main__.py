"""
Musical Tools Suite - Main Application
"""

def main() -> None:
    """Launch the Musical Tools Suite dashboard."""
    try:
        # Try relative import first (for package usage)
        from .main_dashboard import run_dashboard
    except ImportError:
        # Fall back to absolute import (for PyInstaller)
        from chord_importer.main_dashboard import run_dashboard
    run_dashboard()

def main_legacy() -> None:
    """Launch the legacy Chord Importer GUI application."""
    try:
        # Try relative import first (for package usage)
        from .gui import run
    except ImportError:
        # Fall back to absolute import (for PyInstaller)
        from chord_importer.gui import run
    run()


if __name__ == "__main__":
    main()