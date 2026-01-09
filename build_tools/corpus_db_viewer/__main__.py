"""
Entry point for running corpus_db_viewer as a module.

This allows: python -m build_tools.corpus_db_viewer
"""

from .cli import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
