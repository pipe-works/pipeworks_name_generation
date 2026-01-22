"""
Shared UI controls for Syllable Walker TUI.

This module re-exports shared controls from ``build_tools.tui_common``.
The implementations have been moved to the shared package for reuse
across multiple TUIs (syllable_walk_tui, pipeline_tui, etc.).

**Migration Note:**

For new code, prefer importing directly from ``build_tools.tui_common``:

.. code-block:: python

    # Preferred (direct import from shared package)
    from build_tools.tui_common.controls import IntSpinner, FloatSlider

    # Also works (backward compatible re-export)
    from build_tools.syllable_walk_tui.controls import IntSpinner, FloatSlider

**Local Overrides:**

- :class:`CorpusBrowserScreen`: Wraps the shared DirectoryBrowserScreen
  with corpus-specific validation.
- :class:`ProfileOption`: Alias for RadioOption (syllable_walk naming convention)
"""

# Import local corpus browser that wraps the shared browser with validation
from build_tools.syllable_walk_tui.controls.browsers import CorpusBrowserScreen

# Re-export shared controls from tui_common
from build_tools.tui_common.controls import (
    DirectoryBrowserScreen,
    FloatSlider,
    IntSpinner,
    JKSelect,
    RadioOption,
    SeedInput,
)

# ProfileOption is an alias for RadioOption (backward compatibility)
ProfileOption = RadioOption

__all__ = [
    # Shared controls (re-exported)
    "DirectoryBrowserScreen",
    "IntSpinner",
    "FloatSlider",
    "SeedInput",
    "RadioOption",
    "JKSelect",
    # Local controls
    "CorpusBrowserScreen",
    # Alias for backward compatibility
    "ProfileOption",
]
