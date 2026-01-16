"""
Oscillator module - Patch A/B syllable walker.

The oscillator module provides the main syllable generation interface, with
configurable parameters and independent RNG state.
"""

from build_tools.syllable_walk_tui.modules.oscillator.panel import OscillatorPanel
from build_tools.syllable_walk_tui.modules.oscillator.state import PatchState

__all__ = ["OscillatorPanel", "PatchState"]
