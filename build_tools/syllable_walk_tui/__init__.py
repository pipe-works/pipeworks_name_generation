"""
Syllable Walk TUI - Terminal-Based Phonetic Discovery Interface

A eurorack-inspired terminal interface for exploring syllable space and
discovering phonetic textures. This is a **build-time discovery tool** - not
used during runtime name generation.

Features:
- Modular rack interface with 8 phonetic processing modules
- Real-time parameter adjustment and live output generation
- Condition logging and patch management
- Corpus comparison and phonetic space exploration

Core Modules:
- Oscillator: Syllable inventory selection (NLTK, pyphen, mixed)
- Filter: Feature-based syllable filtering
- Envelope: Walk length and temporal shape control
- LFO: Stochastic bias and probability modulation
- Attenuator: Sampling limits and restraint controls
- Patch Cable: Corpus routing and A/B comparison
- Output: Live word generation display
- Conditions Log: Patch management and discovery journal

Usage:
    # Launch the TUI
    python -m build_tools.syllable_walk_tui

    # Or from code
    from build_tools.syllable_walk_tui.app import SyllableWalkApp
    app = SyllableWalkApp()
    app.run()

Philosophy:
    This tool is for discovering phonetic climates, not designing specific
    outputs. We patch conditions and listen to what emerges.

    "We are not trying to produce consistent outputs.
     We are trying to produce consistent conditions."
"""

__version__ = "0.1.0"

# Lazy import to avoid requiring textual for basic package imports
# Import SyllableWalkApp directly when needed:
#   from build_tools.syllable_walk_tui.app import SyllableWalkApp

__all__ = ["SyllableWalkApp"]


def __getattr__(name: str):
    """Lazy import for textual-dependent components."""
    if name == "SyllableWalkApp":
        from build_tools.syllable_walk_tui.app import SyllableWalkApp

        return SyllableWalkApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
