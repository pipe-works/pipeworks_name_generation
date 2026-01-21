"""
Entry point for running corpus_sqlite_builder as a module.

Usage::

    python -m build_tools.corpus_sqlite_builder [arguments]
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
