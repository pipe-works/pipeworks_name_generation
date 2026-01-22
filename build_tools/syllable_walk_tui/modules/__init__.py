"""
Eurorack-style modules for Syllable Walker TUI.

Each module is a self-contained component that can be composed into the instrument.
Modules include oscillators (patch panels), analyzers, blenders, generators, and
future additions like sequencers and effects.

Available Modules:
    - oscillator: Patch configuration panels (PatchState, OscillatorPanel)
    - analyzer: Statistics and export (AnalysisScreen, StatsPanel)
    - blender: Combined walk view (BlendedWalkScreen)
    - database: Corpus database viewer (DatabaseScreen)
    - generator: Name combiner controls (CombinerState, CombinerPanel)
"""

# Generator module exports (now simplified to just combiner)
from build_tools.syllable_walk_tui.modules.generator import (
    CombinerPanel,
    CombinerState,
)

__all__ = [
    # Combiner (name_combiner TUI controls)
    "CombinerState",
    "CombinerPanel",
]
