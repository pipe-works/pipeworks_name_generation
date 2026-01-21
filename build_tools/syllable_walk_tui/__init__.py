"""
Syllable Walker TUI - Interactive Text User Interface

An interactive terminal UI for exploring phonetic space through the Syllable Walker
system. This is a **build-time tool only** - not used during runtime name generation.

Features:
- Side-by-side patch configuration (dual oscillator comparison)
- Center panel walk output with corpus provenance
- Configurable walk count per patch (default 2, "less is more")
- Profile-based parameter presets (clerical, dialect, goblin, ritual)
- Quick corpus selection with number keys (1/2)
- Keyboard-first navigation with Tab and vi-style keys
- Real-time phonetic exploration

Usage::

    python -m build_tools.syllable_walk_tui

Design Philosophy:
    Based on the eurorack modular synthesizer analogy - we patch conditions,
    not outputs. The focus is on exploring phonetic climates through
    interactive parameter tweaking.
"""

__version__ = "0.5.0"
