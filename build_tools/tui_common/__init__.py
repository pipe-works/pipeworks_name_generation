"""
Shared TUI Components - Common UI widgets and services for Textual-based TUIs.

This package provides reusable components for building Terminal User Interfaces
using the Textual framework. It is designed to be shared across multiple TUI
applications within the pipeworks_name_generation project.

**Design Philosophy:**

- **Decoupled**: Widgets communicate via Textual Messages, not direct state access
- **Configurable**: Validators and callbacks allow domain-specific customization
- **Consistent**: Common styling patterns, keybindings, and interaction models
- **Tested**: All components have comprehensive test coverage

**Package Structure:**

.. code-block:: text

    tui_common/
    ├── __init__.py           # This file - package entry point
    ├── cli_utils.py          # Shared CLI utilities (tab completion, file discovery)
    ├── controls/             # Reusable UI widgets
    │   ├── sliders.py        # FloatSlider - float parameter control
    │   ├── spinners.py       # IntSpinner - integer parameter control
    │   ├── inputs.py         # SeedInput, RadioOption - input widgets
    │   └── browsers.py       # DirectoryBrowserScreen - file browser modal
    └── services/             # Backend services
        └── config.py         # KeybindingConfig - keybinding management

**Usage Example:**

.. code-block:: python

    from build_tools.tui_common.controls import (
        FloatSlider,
        IntSpinner,
        SeedInput,
        RadioOption,
        DirectoryBrowserScreen,
    )
    from build_tools.tui_common.services import KeybindingConfig, load_keybindings

    # In your Textual App
    class MyApp(App):
        def compose(self) -> ComposeResult:
            yield IntSpinner("Count", value=5, min_val=1, max_val=100, id="count")
            yield FloatSlider("Temperature", value=0.5, min_val=0.0, max_val=1.0, id="temp")

        @on(IntSpinner.Changed)
        def on_spinner_changed(self, event: IntSpinner.Changed) -> None:
            self.notify(f"Spinner {event.widget_id} changed to {event.value}")

**Message-Based Communication:**

All widgets post Messages when their values change:

- ``IntSpinner.Changed(value: int, widget_id: str | None)``
- ``FloatSlider.Changed(value: float, widget_id: str | None)``
- ``SeedInput.Changed(value: int, widget_id: str | None)``
- ``RadioOption.Selected(option_name: str, widget_id: str | None)``

**Keybinding Patterns:**

Widgets define widget-level bindings that don't interfere with app-level navigation:

- ``+``/``-`` or ``j``/``k``: Increment/decrement values
- ``Enter``/``Space``: Activate/select options
- ``h``/``j``/``k``/``l``: Vim-style navigation in browsers

App-level bindings (``q`` for quit, number keys for tabs, etc.) remain
unaffected when child widgets have focus.
"""

from build_tools.tui_common.controls import (
    DirectoryBrowserScreen,
    FloatSlider,
    IntSpinner,
    RadioOption,
    SeedInput,
)
from build_tools.tui_common.services import KeybindingConfig, detect_conflicts, load_keybindings

__all__ = [
    # Controls
    "FloatSlider",
    "IntSpinner",
    "SeedInput",
    "RadioOption",
    "DirectoryBrowserScreen",
    # Services
    "KeybindingConfig",
    "load_keybindings",
    "detect_conflicts",
]
