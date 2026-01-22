"""
Name Generation module for Syllable Walker TUI.

This module provides TUI controls for the name_combiner and name_selector
build tools. It mirrors the exact CLI options as UI controls.

Combiner CLI Options → TUI Controls:
    --run-dir          → Uses currently loaded patch's corpus_dir
    --syllables        → Syllables selector (2/3/4)
    --count            → Count spinner (default: 10000)
    --seed             → Seed input (None = random)
    --frequency-weight → Frequency weight slider (0.0-1.0)

Selector CLI Options → TUI Controls:
    --run-dir          → Uses currently loaded patch's corpus_dir
    --candidates       → Determined by combiner output (syllables)
    --name-class       → Name class dropdown
    --count            → Count spinner (default: 100)
    --mode             → Mode radio (hard/soft)

Components:
    - CombinerState: State dataclass mirroring combiner CLI options
    - CombinerPanel: UI panel with controls matching combiner CLI
    - SelectorState: State dataclass mirroring selector CLI options
    - SelectorPanel: UI panel with controls matching selector CLI
    - NAME_CLASSES: List of available name class options

Usage:
    >>> from build_tools.syllable_walk_tui.modules.generator import (
    ...     CombinerState,
    ...     CombinerPanel,
    ...     SelectorState,
    ...     SelectorPanel,
    ...     NAME_CLASSES,
    ... )
"""

from build_tools.syllable_walk_tui.modules.generator.panel import CombinerPanel
from build_tools.syllable_walk_tui.modules.generator.selector_panel import SelectorPanel
from build_tools.syllable_walk_tui.modules.generator.state import (
    NAME_CLASSES,
    CombinerState,
    SelectorState,
)

__all__ = [
    "CombinerState",
    "CombinerPanel",
    "SelectorState",
    "SelectorPanel",
    "NAME_CLASSES",
]
