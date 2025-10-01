"""
Musical Tools Suite - Main Application
"""

import sys
import os

def main() -> None:
    """Launch the Musical Tools Suite dashboard."""
    try:
        # Try relative import first (for package usage)
        from .ui.main_dashboard import run_dashboard
    except ImportError:
        try:
            # Try absolute import (for PyInstaller)
            from chord_importer.ui.main_dashboard import run_dashboard
        except ImportError:
            # Add parent directory to path for direct execution
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from chord_importer.ui.main_dashboard import run_dashboard
    run_dashboard()


if __name__ == "__main__":
    main()