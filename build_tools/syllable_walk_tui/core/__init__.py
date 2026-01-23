"""
Core application framework for Syllable Walker TUI.

This module contains the main application class and global state management.
"""

from build_tools.syllable_walk_tui.core import ui_updates
from build_tools.syllable_walk_tui.core.app import SyllableWalkerApp
from build_tools.syllable_walk_tui.core.state import AppState

__all__ = ["SyllableWalkerApp", "AppState", "ui_updates"]
