=========================
TUI Common Components
=========================

.. currentmodule:: build_tools.tui_common

Overview
--------

.. automodule:: build_tools.tui_common
   :no-members:

The TUI Common package provides shared components for building Terminal User Interfaces
using the `Textual <https://textual.textualize.io/>`_ framework. These components are
designed to be reused across multiple TUI applications in the project.

**Key Features:**

- **Reusable Controls**: Spinners, sliders, seed inputs, radio buttons, and vim-enabled dropdowns
- **Directory Browser**: Configurable modal with custom validation callbacks
- **Keybinding Config**: TOML-based configuration management with conflict detection
- **Consistent Patterns**: Message-based communication, focus management, vim-style navigation

**Design Philosophy:**

- Components are decoupled from specific use cases via callbacks and validators
- Widgets communicate via Textual Messages, not direct state manipulation
- CSS styling uses Textual theme variables for consistent appearance
- Widget-level keybindings don't conflict with app-level navigation

Controls
--------

IntSpinner
~~~~~~~~~~

Integer parameter adjustment widget with keyboard navigation.

**Features:**

- Keyboard: ``+``/``-`` or ``j``/``k`` to increment/decrement
- Configurable min/max/step
- Optional dynamic suffix function
- Posts ``IntSpinner.Changed`` message

.. code-block:: python

    from build_tools.tui_common.controls import IntSpinner

    yield IntSpinner(
        "Walk Steps",
        value=5,
        min_val=0,
        max_val=20,
        suffix_fn=lambda v: f"-> {v + 1} syllables",
        id="steps-spinner",
    )

FloatSlider
~~~~~~~~~~~

Float parameter adjustment widget with precision control.

**Features:**

- Keyboard: ``+``/``-`` or ``j``/``k`` to adjust
- Configurable precision (decimal places)
- Optional static suffix text
- Posts ``FloatSlider.Changed`` message

.. code-block:: python

    from build_tools.tui_common.controls import FloatSlider

    yield FloatSlider(
        "Temperature",
        value=0.5,
        min_val=0.0,
        max_val=1.0,
        step=0.1,
        precision=2,
        suffix="bias",
        id="temp-slider",
    )

SeedInput
~~~~~~~~~

Random seed input with two-box design showing input and actual seed used.

**Features:**

- Two-box display: input field and "Using:" display
- Random mode (``-1`` or empty) auto-generates seed
- ``r`` key to reset to random
- Posts ``SeedInput.Changed`` message

.. code-block:: python

    from build_tools.tui_common.controls import SeedInput

    yield SeedInput(id="seed-input")  # Starts in random mode

RadioOption
~~~~~~~~~~~

Radio button style option widget for exclusive selection groups.

**Features:**

- Checkbox display: ``[x]`` selected, ``[ ]`` unselected
- ``Enter``/``Space`` to select
- Rich text rendering with color feedback
- Posts ``RadioOption.Selected`` message

.. code-block:: python

    from build_tools.tui_common.controls import RadioOption

    yield RadioOption("fast", "Quick processing", is_selected=True, id="opt-fast")
    yield RadioOption("thorough", "Deep analysis", id="opt-thorough")

    # Handle selection in app
    @on(RadioOption.Selected)
    def on_option_selected(self, event: RadioOption.Selected) -> None:
        for opt in self.query(RadioOption):
            opt.set_selected(opt.option_name == event.option_name)

JKSelect
~~~~~~~~

Dropdown select widget with vim-style j/k navigation support.

**Features:**

- Extends Textual's ``Select`` widget
- ``j``/``k`` keys navigate down/up in the dropdown (in addition to arrow keys)
- Type-to-search still works for other letters
- Drop-in replacement for standard ``Select``

.. code-block:: python

    from build_tools.tui_common.controls import JKSelect

    yield JKSelect(
        [
            ("First Name", "first_name"),
            ("Last Name", "last_name"),
            ("Place Name", "place_name"),
        ],
        value="first_name",
        id="name-class-select",
    )

**Usage Notes:**

- When the dropdown is open, press ``j`` to move down and ``k`` to move up
- Arrow keys continue to work as expected
- Type any other letter to jump to options starting with that letter
- Press ``Enter`` to select the highlighted option

DirectoryBrowserScreen
~~~~~~~~~~~~~~~~~~~~~~

Modal directory browser with customizable validation.

**Features:**

- Textual DirectoryTree for file system navigation
- Vim-style keybindings (``h``/``j``/``k``/``l``, ``Space``, ``Enter``, ``Esc``)
- Custom validator callback for domain-specific validation
- Visual feedback for valid/invalid selections
- Configurable tree root (``root_dir``) to allow navigation to parent directories

.. code-block:: python

    from build_tools.tui_common.controls import DirectoryBrowserScreen

    # Custom validator function
    def validate_source_dir(path: Path) -> tuple[bool, str, str]:
        txt_files = list(path.glob("*.txt"))
        if txt_files:
            return (True, "source", f"Found {len(txt_files)} files")
        return (False, "", "No .txt files found")

    # Use in async action
    @work
    async def action_select_source(self) -> None:
        result = await self.push_screen_wait(
            DirectoryBrowserScreen(
                title="Select Source Directory",
                validator=validate_source_dir,
                initial_dir=Path("/some/deep/path"),
                root_dir=Path.home(),  # Allows navigating up to home
            )
        )
        if result:
            self.load_source(result)

Services
--------

KeybindingConfig
~~~~~~~~~~~~~~~~

Keybinding configuration dataclass with context-based organization.

**Contexts:**

- ``global``: Application-wide actions (quit, help)
- ``tabs``: Tab/screen switching
- ``navigation``: Movement (up, down, left, right)
- ``controls``: Widget manipulation (activate, increment)
- ``actions``: Domain-specific operations

.. code-block:: python

    from build_tools.tui_common.services import KeybindingConfig, load_keybindings

    # Load with defaults
    config = load_keybindings()

    # Get primary key for display
    quit_key = config.get_primary_key("global", "quit")  # "q"
    quit_display = config.get_display_key("global", "quit")  # "q"

**TOML Configuration:**

.. code-block:: toml

    # ~/.config/pipeworks_tui/keybindings.toml
    [keybindings.global]
    quit = ["q", "ctrl+q"]
    help = ["?", "f1"]

    [keybindings.navigation]
    up = ["k", "up"]
    down = ["j", "down"]

Integration Guide
-----------------

Using in New TUIs
~~~~~~~~~~~~~~~~~

To use tui_common in a new TUI application:

.. code-block:: python

    from textual.app import App, ComposeResult
    from textual import on

    from build_tools.tui_common.controls import (
        IntSpinner,
        FloatSlider,
        JKSelect,
        RadioOption,
        DirectoryBrowserScreen,
    )

    class MyApp(App):
        def compose(self) -> ComposeResult:
            yield IntSpinner("Count", value=5, min_val=1, max_val=10, id="count")
            yield FloatSlider("Weight", value=0.5, min_val=0.0, max_val=1.0, id="weight")
            yield JKSelect([("A", "a"), ("B", "b")], value="a", id="choice")

        @on(IntSpinner.Changed)
        def on_spinner_changed(self, event: IntSpinner.Changed) -> None:
            # Handle value changes
            self.state.count = event.value

Extending DirectoryBrowserScreen
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create domain-specific browser subclasses:

.. code-block:: python

    from build_tools.tui_common.controls import DirectoryBrowserScreen

    class CorpusBrowserScreen(DirectoryBrowserScreen):
        \"\"\"Browser pre-configured for corpus selection.\"\"\"

        # CSS must be redeclared for subclass (Textual CSS is class-specific)
        CSS = \"\"\"
        CorpusBrowserScreen {
            align: center middle;
        }
        # ... rest of CSS
        \"\"\"

        def __init__(self, initial_dir: Path | None = None) -> None:
            super().__init__(
                title="Select Corpus Directory",
                validator=validate_corpus_directory,
                initial_dir=initial_dir,
            )

**Important:** Textual CSS selectors are class-name specific. Subclasses must
redeclare CSS with their own class name for proper styling.

Notes
-----

**Dependencies:**

Requires Textual library:

.. code-block:: bash

    pip install -r requirements-dev.txt

**Python Version:**

Requires Python 3.12+ for type hints.

**Related Documentation:**

- :doc:`syllable_walk_tui` - Uses tui_common for corpus browsing and controls
- :doc:`pipeline_tui` - Uses tui_common for directory selection and configuration

API Reference
-------------

Controls
~~~~~~~~

.. automodule:: build_tools.tui_common.controls
   :members:
   :undoc-members:
   :show-inheritance:

Services
~~~~~~~~

.. automodule:: build_tools.tui_common.services
   :members:
   :undoc-members:
   :show-inheritance:
