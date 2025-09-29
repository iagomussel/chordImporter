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


if __name__ == "__main__":
    main()