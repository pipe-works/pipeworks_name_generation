"""
Syllable Walker TUI - Interactive Text User Interface

An interactive terminal UI for exploring phonetic space through the Syllable Walker
system. This is a **build-time tool only** - not used during runtime name generation.

Features:
- Four-column layout: Oscillator A | Generator A | Generator B | Oscillator B
- Side-by-side patch configuration (dual oscillator comparison)
- Name Combiner integration for candidate generation (mirrors CLI)
- Name Selector integration for policy-based filtering (mirrors CLI)
- Render Screen for styled name display (title/UPPER/lower case)
- Package Screen for bundling selections into ZIP archives
- TXT export for selected names
- Profile-based parameter presets (clerical, dialect, goblin, ritual, custom)
- Modal screens: Blended Walk (v), Analysis (a), Render (r), Database (d/D)
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
