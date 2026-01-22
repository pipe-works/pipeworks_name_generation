"""
Name Combiner module for Syllable Walker TUI.

This module provides TUI controls for the name_combiner build tool.
It mirrors the exact CLI options as UI controls.

CLI Options → TUI Controls:
    --run-dir          → Uses currently loaded patch's corpus_dir
    --syllables        → Syllables selector (2/3/4)
    --count            → Count spinner (default: 10000)
    --seed             → Seed input (None = random)
    --frequency-weight → Frequency weight slider (0.0-1.0)

Components:
    - CombinerState: State dataclass mirroring CLI options
    - CombinerPanel: UI panel with controls matching CLI

Usage:
    >>> from build_tools.syllable_walk_tui.modules.generator import (
    ...     CombinerState,
    ...     CombinerPanel,
    ... )
    >>> state = CombinerState()
    >>> state.syllables = 3
    >>> state.count = 5000
"""

from build_tools.syllable_walk_tui.modules.generator.panel import CombinerPanel
from build_tools.syllable_walk_tui.modules.generator.state import CombinerState

__all__ = [
    "CombinerState",
    "CombinerPanel",
]
