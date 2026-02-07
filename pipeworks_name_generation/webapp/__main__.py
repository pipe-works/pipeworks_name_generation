"""Module entry point for ``python -m pipeworks_name_generation.webapp``."""

from __future__ import annotations

import sys

from pipeworks_name_generation.webapp.cli import main

if __name__ == "__main__":
    sys.exit(main())
