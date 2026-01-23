"""
Entry point for running nltk_syllable_extractor as a module.

Usage::

    python -m build_tools.nltk_syllable_extractor
"""

import sys

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
