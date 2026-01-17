"""
Seed input and radio option widgets.

This module provides input widgets for seed/random value entry and
radio-button style option selection.

**Widgets:**

- :class:`SeedInput` - Two-box seed input with random mode support
- :class:`RadioOption` - Checkbox-style radio button for option groups

**Example Usage:**

.. code-block:: python

    from build_tools.tui_common.controls import SeedInput, RadioOption
    from textual import on

    class MyApp(App):
        def compose(self) -> ComposeResult:
            # Seed input with random default
            yield SeedInput(id="seed-input")

            # Radio options for mode selection
            yield RadioOption("fast", "Quick processing", is_selected=True, id="opt-fast")
            yield RadioOption("thorough", "Deep analysis", id="opt-thorough")

        @on(SeedInput.Changed)
        def on_seed_changed(self, event: SeedInput.Changed) -> None:
            print(f"Using seed: {event.value}")

        @on(RadioOption.Selected)
        def on_option_selected(self, event: RadioOption.Selected) -> None:
            # Update other options to deselect them
            for opt in self.query(RadioOption):
                opt.set_selected(opt.option_name == event.option_name)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from textual import on
from textual.message import Message
from textual.widgets import Input, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class SeedInput(Static):
    """
    Seed input widget with two-box design.

    Displays an input field for entering a seed value and a display
    showing the actual seed being used. Supports random mode when
    input is empty or "-1".

    **Layout:**

    ``[Seed:] [Input Field] [->] [Actual Seed Used]``

    **Modes:**

    - **Manual mode**: Enter a specific integer seed value
    - **Random mode**: Enter "-1" or leave empty to auto-generate

    Attributes:
        value: Current seed value being used (always a valid integer)
        user_input: User's raw input (-1 means random mode)

    Keybindings:
        - ``r``: Set to random mode (-1)

    Messages:
        - :class:`Changed`: Posted when seed changes, includes actual seed value

    CSS Classes:
        - ``.seed-label``: "Seed:" label (width: 15)
        - ``Input``: Text input field (width: 13)
        - ``.arrow``: Arrow indicator "->" (width: 3)
        - ``.seed-used-value``: Actual seed display (width: 12, muted)
    """

    # -------------------------------------------------------------------------
    # Widget-level bindings
    # -------------------------------------------------------------------------
    BINDINGS = [
        ("r", "random", "Random"),
    ]

    class Changed(Message):
        """
        Message posted when the seed value changes.

        Attributes:
            value: The actual seed value being used (always valid integer)
            widget_id: The ID of the widget that posted this message, or None
        """

        def __init__(self, value: int, widget_id: str | None) -> None:
            """
            Initialize the Changed message.

            Args:
                value: The actual seed value
                widget_id: ID of the seed input widget that changed
            """
            super().__init__()
            self.value = value
            self.widget_id = widget_id

    # -------------------------------------------------------------------------
    # Default styling
    # -------------------------------------------------------------------------
    DEFAULT_CSS = """
    SeedInput {
        layout: horizontal;
        height: 3;
        width: 100%;
    }

    SeedInput .seed-label {
        width: 15;
        text-align: right;
        padding-right: 1;
        height: 3;
        content-align: center middle;
    }

    SeedInput Input {
        width: 13;
        height: 3;
        border: solid $primary;
    }

    SeedInput .arrow {
        width: 3;
        text-align: center;
        height: 3;
        content-align: center middle;
    }

    SeedInput .seed-used-value {
        width: 12;
        height: 3;
        text-align: left;
        content-align: center middle;
        color: $text-muted;
        background: $boost;
        padding-left: 1;
    }
    """

    def __init__(self, value: int | None = None, *args, **kwargs) -> None:
        """
        Initialize seed input with two-box design.

        Args:
            value: Initial seed value. If None, generates a random seed
                   using SystemRandom for cryptographic randomness.
            *args: Additional positional arguments passed to Static
            **kwargs: Additional keyword arguments passed to Static
        """
        super().__init__(*args, **kwargs)
        # Generate initial random seed if not provided
        # Use SystemRandom for true randomness (not affected by seed state)
        if value is None:
            self.value = random.SystemRandom().randint(0, 2**32 - 1)
        else:
            self.value = value
        # User input defaults to -1 (random mode)
        self.user_input = -1

    def compose(self) -> ComposeResult:
        """
        Create two-box seed input in single horizontal row.

        Layout: [Label] [Input] [Arrow] [Actual Value]

        Yields:
            Label and Input widgets for the two-box design
        """
        yield Label("Seed:", classes="seed-label")
        yield Input(
            placeholder="-1 (random)",
            value="-1",
            id="seed-input",
        )
        yield Label("->", classes="arrow")
        yield Label(f"{self.value}", classes="seed-used-value", id="seed-used")

    def action_random(self) -> None:
        """
        Set input to random mode (-1).

        Bound to 'r' key. Generates a new random seed.
        """
        try:
            input_widget = self.query_one("#seed-input", Input)
            input_widget.value = "-1"
            self._handle_input_change("-1")
        except Exception:  # nosec B110 - Safe widget query failure
            pass

    @on(Input.Changed, "#seed-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        """
        Handle user typing in the seed input.

        Args:
            event: Input change event from Textual
        """
        self._handle_input_change(event.value)

    def _handle_input_change(self, input_value: str) -> None:
        """
        Process input value and update actual seed.

        Handles three cases:
        1. Empty or "-1": Random mode - generate new seed
        2. Valid integer: Use that value (clamped to 32-bit range)
        3. Invalid input: Ignore and keep current value

        Args:
            input_value: Raw string from the input field
        """
        input_str = input_value.strip()

        # Handle empty or -1 as random mode
        if not input_str or input_str == "-1":
            self.user_input = -1
            # Generate new random seed using SystemRandom
            self.value = random.SystemRandom().randint(0, 2**32 - 1)
        else:
            # Try to parse as integer
            try:
                manual_seed = int(input_str)
                # Clamp to valid 32-bit unsigned range
                manual_seed = max(0, min(manual_seed, 2**32 - 1))
                self.user_input = manual_seed
                self.value = manual_seed
            except ValueError:
                # Invalid input, ignore and keep current value
                return

        # Update display and post message
        self._update_display()
        self.post_message(self.Changed(self.value, self.id))

    def _update_display(self) -> None:
        """
        Update the 'Using:' display with actual seed value.

        Called after seed changes to sync the UI.
        """
        try:
            display = self.query_one("#seed-used", Label)
            display.update(f"{self.value}")
        except Exception:  # nosec B110 - Safe widget query failure
            pass


class RadioOption(Static):
    """
    Radio button style option widget.

    Displays as a checkbox-style option that can be selected with
    keyboard or mouse. Used in groups where only one option should
    be selected at a time (managed by parent).

    **Display Format:**

    - Selected: ``[x] Label: Description`` (green, bold)
    - Unselected: ``[ ] Label: Description`` (muted)

    Attributes:
        option_name: Internal name for this option (e.g., "fast", "thorough")
        description: Brief description shown after the label
        is_selected: Whether this option is currently selected

    Keybindings:
        - ``Enter`` or ``Space``: Select this option

    Messages:
        - :class:`Selected`: Posted when this option is selected (only if not already selected)

    CSS Classes:
        - Default styles handle hover and focus states
        - ``.profile-selected`` / ``.profile-unselected``: Selection state classes

    Note:
        This widget only posts a message when selected. The parent
        is responsible for deselecting other options in the group
        by calling :meth:`set_selected` on each.
    """

    # -------------------------------------------------------------------------
    # Widget-level bindings for selection
    # -------------------------------------------------------------------------
    BINDINGS = [
        ("enter", "select", "Select Option"),
        ("space", "select", "Select Option"),
    ]

    class Selected(Message):
        """
        Message posted when this option is selected.

        Only posted if the option was not already selected.

        Attributes:
            option_name: The name of the selected option
            widget_id: The ID of the widget that posted this message, or None
            profile_name: Alias for option_name (backward compatibility)
        """

        def __init__(self, option_name: str, widget_id: str | None) -> None:
            """
            Initialize the Selected message.

            Args:
                option_name: Name of the option that was selected
                widget_id: ID of the radio option widget
            """
            super().__init__()
            self.option_name = option_name
            self.widget_id = widget_id

        @property
        def profile_name(self) -> str:
            """Alias for option_name (backward compatibility with ProfileOption)."""
            return self.option_name

    # -------------------------------------------------------------------------
    # Default styling
    # -------------------------------------------------------------------------
    DEFAULT_CSS = """
    RadioOption {
        height: 1;
        width: 100%;
    }

    RadioOption:hover {
        background: $boost;
    }

    RadioOption:focus {
        background: $accent;
    }

    .profile-selected {
        color: $success;
        text-style: bold;
    }

    .profile-unselected {
        color: $text-muted;
    }
    """

    def __init__(
        self,
        option_name: str,
        description: str,
        is_selected: bool = False,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize radio option.

        Args:
            option_name: Internal name for this option (e.g., "fast")
            description: Brief description to show after the label
            is_selected: Whether this option starts selected
            *args: Additional positional arguments passed to Static
            **kwargs: Additional keyword arguments passed to Static
        """
        super().__init__(*args, **kwargs)
        self.option_name = option_name
        self.description = description
        self.is_selected = is_selected

    def on_mount(self) -> None:
        """
        Configure widget after mounting.

        Makes the widget focusable for keyboard navigation.
        """
        self.can_focus = True

    def render(self):
        """
        Render the option as text with Rich markup.

        Returns:
            Rich Text object with checkbox, label, and description
        """
        from rich.text import Text

        # Build the display text
        # Note: Escape square brackets to prevent Rich markup interpretation
        checkbox = "\\[x]" if self.is_selected else "\\[ ]"
        label = self.option_name.capitalize()

        # Apply styling based on selection state
        if self.is_selected:
            # Selected: bold green checkbox, bold label
            return Text.from_markup(
                f"[bold green]{checkbox}[/bold green] " f"[bold]{label}[/bold]: {self.description}"
            )
        else:
            # Unselected: muted gray
            return Text.from_markup(f"[dim]{checkbox}[/dim] {label}: [dim]{self.description}[/dim]")

    def action_select(self) -> None:
        """
        Select this option (Enter/Space).

        Only posts Selected message if not already selected.
        Does not blur focus - keeps focus on selected option
        like standard radio button behavior.
        """
        if not self.is_selected:
            self.post_message(self.Selected(self.option_name, self.id))

    def on_click(self) -> None:
        """
        Handle click on this option.

        Same behavior as action_select - posts message if not selected.
        """
        if not self.is_selected:
            self.post_message(self.Selected(self.option_name, self.id))

    def set_selected(self, selected: bool) -> None:
        """
        Update selection state and refresh display.

        Called by parent to manage radio group state.
        Does not post any message.

        Args:
            selected: Whether this option should be selected
        """
        self.is_selected = selected
        self.refresh()
