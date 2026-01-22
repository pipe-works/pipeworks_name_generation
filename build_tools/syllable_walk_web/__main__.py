"""Entry point for syllable walker web interface.

This module allows the web interface to be run as a module:

    python -m build_tools.syllable_walk_web

All command-line arguments are handled by the cli module.
"""

import sys

from build_tools.syllable_walk_web.cli import main

if __name__ == "__main__":
    sys.exit(main())
