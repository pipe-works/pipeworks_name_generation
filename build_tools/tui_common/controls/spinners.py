"""
Integer spinner control widget.

This module provides the IntSpinner widget for integer parameter control
with keyboard support and optional dynamic suffix.

**Features:**

- Keyboard navigation: ``+``/``-`` or ``j``/``k`` or arrow keys to adjust
- Configurable step size and min/max range
- Optional suffix function for dynamic labels (e.g., "5 items", "10 chars")
- Posts ``Changed`` message when value updates
- Focusable with visual feedback

**Example Usage:**

.. code-block:: python

    from build_tools.tui_common.controls import IntSpinner
    from textual import on

    class MyApp(App):
        def compose(self) -> ComposeResult:
            # Simple spinner with static label
            yield IntSpinner(
                label="Count",
                value=5,
                min_val=1,
                max_val=100,
                id="count-spinner",
            )

            # Spinner with dynamic suffix based on value
            yield IntSpinner(
                label="Walk Steps",
                value=5,
                min_val=0,
                max_val=20,
                suffix_fn=lambda v: f"-> {v + 1} syllables",
                id="steps-spinner",
            )

        @on(IntSpinner.Changed)
        def on_spinner_changed(self, event: IntSpinner.Changed) -> None:
            print(f"Spinner {event.widget_id} = {event.value}")
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class IntSpinner(Static):
    """
    Integer spinner widget with increment/decrement support.

    A horizontal widget displaying a label, current value in brackets,
    and optional dynamic suffix. Users can adjust the value using keyboard
    shortcuts while the widget has focus.

    Attributes:
        label_text: Display label shown before the value
        value: Current integer value (clamped to min/max range)
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        step: Amount to increment/decrement per keypress
        suffix_fn: Optional callable that generates suffix text from current value

    Keybindings:
        - ``+`` or ``=`` or ``j`` or ``down``: Increment value by step
        - ``-`` or ``_`` or ``k`` or ``up``: Decrement value by step

    Messages:
        - :class:`Changed`: Posted when value changes, includes new value and widget ID

    CSS Classes:
        - ``.spinner-label``: Label element (width: 15, right-aligned)
        - ``.spinner-value``: Value display (width: 6, centered, highlighted on focus)
        - ``.spinner-suffix``: Suffix text (auto width, muted color)
    """

    # -------------------------------------------------------------------------
    # Widget-level bindings for parameter adjustment
    # These don't interfere with app-level bindings (q, a, v, etc.)
    # -------------------------------------------------------------------------
    BINDINGS = [
        ("+", "increment", "Increment"),
        ("=", "increment", "Increment"),
        ("j", "increment", "Increment"),
        ("down", "increment", "Increment"),
        ("-", "decrement", "Decrement"),
        ("_", "decrement", "Decrement"),
        ("k", "decrement", "Decrement"),
        ("up", "decrement", "Decrement"),
    ]

    class Changed(Message):
        """
        Message posted when the spinner value changes.

        Attributes:
            value: The new integer value after the change
            widget_id: The ID of the widget that posted this message, or None
        """

        def __init__(self, value: int, widget_id: str | None) -> None:
            """
            Initialize the Changed message.

            Args:
                value: The new spinner value
                widget_id: ID of the spinner widget that changed
            """
            super().__init__()
            self.value = value
            self.widget_id = widget_id

    # -------------------------------------------------------------------------
    # Default styling using Textual's CSS variables for theme compatibility
    # -------------------------------------------------------------------------
    DEFAULT_CSS = """
    IntSpinner {
        layout: horizontal;
        height: 1;
        width: 100%;
    }

    IntSpinner .spinner-label {
        width: 15;
        text-align: right;
        padding-right: 1;
    }

    IntSpinner .spinner-value {
        width: 6;
        text-align: center;
        background: $boost;
    }

    IntSpinner:focus .spinner-value {
        background: $accent;
        text-style: bold;
    }

    IntSpinner .spinner-suffix {
        width: auto;
        padding-left: 1;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        label: str,
        value: int,
        min_val: int,
        max_val: int,
        step: int = 1,
        suffix_fn: Callable[[int], str] | None = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize integer spinner.

        Args:
            label: Display label shown before the value
            value: Initial value (will be clamped to min/max range)
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            step: Increment/decrement step size (default: 1)
            suffix_fn: Optional callback to generate suffix text from current value.
                       Called with current value, returns string to display.
                       Example: ``lambda v: f"-> {v + 1} items"``
            *args: Additional positional arguments passed to Static
            **kwargs: Additional keyword arguments passed to Static
        """
        super().__init__(*args, **kwargs)
        self.label_text = label
        # Clamp initial value to valid range
        self.value = max(min_val, min(value, max_val))
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.suffix_fn = suffix_fn

    def compose(self) -> ComposeResult:
        """
        Create the spinner layout.

        Layout: [Label:] [value] [suffix]

        Yields:
            Label widgets for label, value display, and optional suffix
        """
        yield Label(f"{self.label_text}:", classes="spinner-label")
        yield Label(f"[{self.value:2d}]", classes="spinner-value", id="value-display")
        # Generate initial suffix if function provided
        suffix_text = self.suffix_fn(self.value) if self.suffix_fn else ""
        yield Label(suffix_text, classes="spinner-suffix", id="suffix-display")

    def on_mount(self) -> None:
        """
        Configure widget after mounting.

        Makes the widget focusable for keyboard navigation.
        Focus state is used to highlight the value display.
        """
        self.can_focus = True

    def action_increment(self) -> None:
        """
        Increment value by step, clamped to max.

        Only posts Changed message if value actually changed.
        Updates both value display and suffix if present.
        """
        old_value = self.value
        self.value = min(self.value + self.step, self.max_val)
        if self.value != old_value:
            self._update_display()
            self.post_message(self.Changed(self.value, self.id))

    def action_decrement(self) -> None:
        """
        Decrement value by step, clamped to min.

        Only posts Changed message if value actually changed.
        Updates both value display and suffix if present.
        """
        old_value = self.value
        self.value = max(self.value - self.step, self.min_val)
        if self.value != old_value:
            self._update_display()
            self.post_message(self.Changed(self.value, self.id))

    def set_value(self, value: int) -> None:
        """
        Set value programmatically, clamped to range.

        Use this method to update the spinner value from code.
        Posts Changed message if value actually changed.

        Args:
            value: New value (will be clamped to min/max range)
        """
        old_value = self.value
        self.value = max(self.min_val, min(value, self.max_val))
        if self.value != old_value:
            self._update_display()
            self.post_message(self.Changed(self.value, self.id))

    def _update_display(self) -> None:
        """
        Update the displayed value and suffix labels.

        Called after value changes to sync the UI.
        Silently handles cases where widget isn't mounted yet.
        """
        try:
            # Update value display
            display = self.query_one("#value-display", Label)
            display.update(f"[{self.value:2d}]")
            # Update suffix if function provided
            if self.suffix_fn:
                suffix = self.query_one("#suffix-display", Label)
                suffix.update(self.suffix_fn(self.value))
        except Exception:  # nosec B110 - Widget may not be mounted yet
            pass
