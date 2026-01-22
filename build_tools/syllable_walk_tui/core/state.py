"""
State management for Syllable Walker TUI.

This module provides the global AppState dataclass. Individual patch state
is managed by the oscillator module, and combiner/selector state by the generator module.
"""

from dataclasses import dataclass, field
from pathlib import Path

from build_tools.syllable_walk_tui.modules.generator import CombinerState, SelectorState
from build_tools.syllable_walk_tui.modules.oscillator import PatchState


@dataclass
class AppState:
    """
    Global application state.

    Attributes:
        patch_a: Configuration for patch A
        patch_b: Configuration for patch B
        combiner_a: Configuration for Patch A name_combiner (mirrors CLI options)
        combiner_b: Configuration for Patch B name_combiner (mirrors CLI options)
        selector_a: Configuration for Patch A name_selector (mirrors CLI options)
        selector_b: Configuration for Patch B name_selector (mirrors CLI options)
        current_focus: Currently focused panel ("patch_a", "patch_b", or "stats")
        last_browse_dir: Last directory browsed (for remembering location)
    """

    patch_a: PatchState = field(default_factory=lambda: PatchState(name="A"))
    patch_b: PatchState = field(default_factory=lambda: PatchState(name="B"))
    combiner_a: CombinerState = field(default_factory=CombinerState)
    combiner_b: CombinerState = field(default_factory=CombinerState)
    selector_a: SelectorState = field(default_factory=SelectorState)
    selector_b: SelectorState = field(default_factory=SelectorState)
    current_focus: str = "patch_a"
    last_browse_dir: Path | None = None
