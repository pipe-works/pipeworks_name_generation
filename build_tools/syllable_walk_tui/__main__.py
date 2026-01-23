"""
Entry point for Syllable Walker TUI.

Usage::

    python -m build_tools.syllable_walk_tui
"""

from __future__ import annotations

import sys

from build_tools.syllable_walk_tui.core import SyllableWalkerApp


def main(args: list[str] | None = None) -> int:
    """
    Launch the Syllable Walker TUI application.

    Args:
        args: Command-line arguments. If None, uses sys.argv.
            Currently unused but included for CLI consistency.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    try:
        app = SyllableWalkerApp()
        app.run()
        return 0

    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
