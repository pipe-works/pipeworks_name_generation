"""Entry point for python -m build_tools.name_combiner."""

import sys

from build_tools.name_combiner.cli import main

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
