"""
Shared UI Controls for Textual-based TUIs.

This module provides reusable UI widgets that can be used across multiple
TUI applications. All widgets follow consistent patterns:

**Communication Pattern:**

Each widget posts a custom Message when its value changes:

.. code-block:: python

    @on(IntSpinner.Changed)
    def handle_spinner(self, event: IntSpinner.Changed) -> None:
        print(f"Widget {event.widget_id} changed to {event.value}")

**Focus Pattern:**

Widgets are focusable for keyboard navigation but use widget-level bindings
that don't conflict with app-level bindings.

**Available Widgets:**

- :class:`FloatSlider` - Float parameter adjustment with precision control
- :class:`IntSpinner` - Integer parameter adjustment with optional suffix
- :class:`SeedInput` - Random seed input with two-box design
- :class:`RadioOption` - Radio button style option selection
- :class:`DirectoryBrowserScreen` - Modal directory browser with validation
- :class:`JKSelect` - Dropdown select with vim-style j/k navigation
"""

from build_tools.tui_common.controls.browsers import DirectoryBrowserScreen
from build_tools.tui_common.controls.inputs import RadioOption, SeedInput
from build_tools.tui_common.controls.selects import JKSelect
from build_tools.tui_common.controls.sliders import FloatSlider
from build_tools.tui_common.controls.spinners import IntSpinner

__all__ = [
    "FloatSlider",
    "IntSpinner",
    "SeedInput",
    "RadioOption",
    "DirectoryBrowserScreen",
    "JKSelect",
]
