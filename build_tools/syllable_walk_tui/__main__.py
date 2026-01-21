"""
Entry point for Syllable Walker TUI.

Usage::

    python -m build_tools.syllable_walk_tui
"""

from build_tools.syllable_walk_tui.core import SyllableWalkerApp


def main():
    """Launch the Syllable Walker TUI application."""
    app = SyllableWalkerApp()
    app.run()


if __name__ == "__main__":
    main()
