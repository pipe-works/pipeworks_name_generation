"""
Float slider control widget.

This module provides the FloatSlider widget for float parameter control.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Label, Static


class FloatSlider(Static):
    """
    Float slider widget with keyboard and mouse support.

    Allows keyboard navigation: +/- or j/k to adjust value, fine control with Shift.

    Attributes:
        label: Display label for the parameter
        value: Current float value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        step: Increment/decrement step size
        precision: Number of decimal places to display
    """

    # Define widget-level bindings for parameter adjustment only
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
        """Message posted when slider value changes."""

        def __init__(self, value: float, widget_id: str | None) -> None:
            """Initialize with new value and widget ID."""
            super().__init__()
            self.value = value
            self.widget_id = widget_id

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
        suffix: Optional[str] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize float slider.

        Args:
            label: Display label
            value: Initial value
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            step: Increment/decrement step size
            precision: Number of decimal places to display
            suffix: Optional static suffix text to display after value
        """
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.precision = precision
        self.suffix = suffix or ""

    def compose(self) -> ComposeResult:
        """Create slider layout."""
        yield Label(f"{self.label_text}:", classes="slider-label")
        format_str = f"[{{:.{self.precision}f}}]"
        yield Label(format_str.format(self.value), classes="slider-value", id="value-display")
        yield Label(self.suffix, classes="slider-suffix")

    def on_mount(self) -> None:
        """
        Make widget focusable for keyboard navigation.

        Note: We explicitly blur focus after modal closes in app.py
        to prevent auto-focus from breaking tab switching bindings.
        """
        self.can_focus = True

    def action_increment(self) -> None:
        """Action: Increment value by step, clamped to max."""
        old_value = self.value
        self.value = min(self.value + self.step, self.max_val)
        if self.value != old_value:
            self._update_display()
            self.post_message(self.Changed(self.value, self.id))

    def action_decrement(self) -> None:
        """Action: Decrement value by step, clamped to min."""
        old_value = self.value
        self.value = max(self.value - self.step, self.min_val)
        if self.value != old_value:
            self._update_display()
            self.post_message(self.Changed(self.value, self.id))

    def set_value(self, value: float) -> None:
        """Set value directly, clamped to range."""
        old_value = self.value
        self.value = max(self.min_val, min(value, self.max_val))
        if self.value != old_value:
            self._update_display()
            self.post_message(self.Changed(self.value, self.id))

    def _update_display(self) -> None:
        """Update the displayed value."""
        try:
            display = self.query_one("#value-display", Label)
            format_str = f"[{{:.{self.precision}f}}]"
            display.update(format_str.format(self.value))
        except Exception:  # nosec B110
            pass  # Widget may not be mounted yet
