"""
Float slider control widget.

This module provides the FloatSlider widget for float parameter control
with keyboard and mouse support.

**Features:**

- Keyboard navigation: ``+``/``-`` or ``j``/``k`` or arrow keys to adjust
- Configurable step size and decimal precision
- Optional suffix text display
- Posts ``Changed`` message when value updates
- Focusable with visual feedback

**Example Usage:**

.. code-block:: python

    from build_tools.tui_common.controls import FloatSlider
    from textual import on

    class MyApp(App):
        def compose(self) -> ComposeResult:
            yield FloatSlider(
                label="Temperature",
                value=0.5,
                min_val=0.0,
                max_val=1.0,
                step=0.1,
                precision=2,
                suffix="bias",
                id="temperature-slider",
            )

        @on(FloatSlider.Changed)
        def on_slider_changed(self, event: FloatSlider.Changed) -> None:
            print(f"Slider {event.widget_id} = {event.value}")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class FloatSlider(Static):
    """
    Float slider widget with keyboard and mouse support.

    A horizontal widget displaying a label, current value in brackets,
    and optional suffix. Users can adjust the value using keyboard
    shortcuts while the widget has focus.

    Attributes:
        label_text: Display label shown before the value
        value: Current float value (clamped to min/max range)
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        step: Amount to increment/decrement per keypress
        precision: Number of decimal places to display
        suffix: Optional text shown after the value

    Keybindings:
        - ``+`` or ``=`` or ``j`` or ``down``: Increment value by step
        - ``-`` or ``_`` or ``k`` or ``up``: Decrement value by step

    Messages:
        - :class:`Changed`: Posted when value changes, includes new value and widget ID

    CSS Classes:
        - ``.slider-label``: Label element (width: 15, right-aligned)
        - ``.slider-value``: Value display (width: 8, centered, highlighted on focus)
        - ``.slider-suffix``: Suffix text (auto width, muted color)
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
        Message posted when the slider value changes.

        Attributes:
            value: The new float value after the change
            widget_id: The ID of the widget that posted this message, or None
        """

        def __init__(self, value: float, widget_id: str | None) -> None:
            """
            Initialize the Changed message.

            Args:
                value: The new slider value
                widget_id: ID of the slider widget that changed
            """
            super().__init__()
            self.value = value
            self.widget_id = widget_id

    # -------------------------------------------------------------------------
    # Default styling using Textual's CSS variables for theme compatibility
    # -------------------------------------------------------------------------
    DEFAULT_CSS = """
    FloatSlider {
        layout: horizontal;
        height: 1;
        width: 100%;
    }

    FloatSlider .slider-label {
        width: 15;
        text-align: right;
        padding-right: 1;
    }

    FloatSlider .slider-value {
        width: 8;
        text-align: center;
        background: $boost;
    }

    FloatSlider:focus .slider-value {
        background: $accent;
        text-style: bold;
    }

    FloatSlider .slider-suffix {
        width: auto;
        padding-left: 1;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        label: str,
        value: float,
        min_val: float,
        max_val: float,
        step: float = 0.1,
        precision: int = 1,
        suffix: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize float slider.

        Args:
            label: Display label shown before the value
            value: Initial value (will be clamped to min/max range)
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            step: Increment/decrement step size (default: 0.1)
            precision: Number of decimal places to display (default: 1)
            suffix: Optional static suffix text to display after value
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
        self.precision = precision
        self.suffix = suffix or ""

    def compose(self) -> ComposeResult:
        """
        Create the slider layout.

        Layout: [Label:] [value] [suffix]

        Yields:
            Label widgets for label, value display, and suffix
        """
        yield Label(f"{self.label_text}:", classes="slider-label")
        # Format value with specified precision in brackets
        format_str = f"[{{:.{self.precision}f}}]"
        yield Label(
            format_str.format(self.value),
            classes="slider-value",
            id="value-display",
        )
        yield Label(self.suffix, classes="slider-suffix")

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
        """
        old_value = self.value
        self.value = max(self.value - self.step, self.min_val)
        if self.value != old_value:
            self._update_display()
            self.post_message(self.Changed(self.value, self.id))

    def set_value(self, value: float) -> None:
        """
        Set value programmatically, clamped to range.

        Use this method to update the slider value from code.
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
        Update the displayed value label.

        Called after value changes to sync the UI.
        Silently handles cases where widget isn't mounted yet.
        """
        try:
            display = self.query_one("#value-display", Label)
            format_str = f"[{{:.{self.precision}f}}]"
            display.update(format_str.format(self.value))
        except Exception:  # nosec B110 - Widget may not be mounted yet
            pass
