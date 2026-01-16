"""
State management for Syllable Walker TUI.

This module provides the global AppState dataclass. Individual patch state
is managed by the oscillator module.
"""

from dataclasses import dataclass, field
from pathlib import Path

from build_tools.syllable_walk_tui.modules.oscillator import PatchState

# PatchState moved to modules.oscillator.state.PatchState


@dataclass
class AppState:
    """
    Global application state.

    Attributes:
        patch_a: Configuration for patch A
        patch_b: Configuration for patch B
        current_focus: Currently focused panel ("patch_a", "patch_b", or "stats")
        last_browse_dir: Last directory browsed (for remembering location)
    """

    patch_a: PatchState = field(default_factory=lambda: PatchState(name="A"))
    patch_b: PatchState = field(default_factory=lambda: PatchState(name="B"))
    current_focus: str = "patch_a"
    last_browse_dir: Path | None = None
