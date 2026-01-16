"""
Custom widgets for Syllable Walker TUI.

This module provides backward compatibility imports for widgets that have been
moved to the controls module. New code should import directly from
build_tools.syllable_walk_tui.controls.

Deprecated:
    This module is deprecated. Import from controls module instead:
    - CorpusBrowserScreen moved to controls.browsers
    - IntSpinner moved to controls.spinners
    - FloatSlider moved to controls.sliders
    - SeedInput, ProfileOption moved to controls.inputs
"""

# Re-export from new locations for backward compatibility
from build_tools.syllable_walk_tui.controls import (
    CorpusBrowserScreen,
    FloatSlider,
    IntSpinner,
    ProfileOption,
    SeedInput,
)

__all__ = [
    "CorpusBrowserScreen",
    "IntSpinner",
    "FloatSlider",
    "SeedInput",
    "ProfileOption",
]
