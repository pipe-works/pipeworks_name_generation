"""
Integer spinner control widget.

This module provides the IntSpinner widget for integer parameter control.
"""

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Label, Static


class IntSpinner(Static):
    """
    Integer spinner widget with increment/decrement buttons.

    Allows keyboard navigation: +/- or j/k to adjust value, Enter to edit directly.
    Also supports mouse clicks on +/- buttons.

    Attributes:
        label: Display label for the parameter
        value: Current integer value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        step: Increment/decrement step size
    """

    # Define widget-level bindings for parameter adjustment only
    # These won't interfere with app-level bindings (b, a, p, q, etc.)
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
        """Message posted when spinner value changes."""

        def __init__(self, value: int, widget_id: str | None) -> None:
            """Initialize with new value and widget ID."""
            super().__init__()
            self.value = value
            self.widget_id = widget_id

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

    IntSpinner .spinner-buttons {
        width: 3;
        padding-left: 1;
    }
    """

    def __init__(
        self,
        label: str,
        value: int,
        min_val: int,
        max_val: int,
        step: int = 1,
        *args,
        **kwargs,
    ):
        """
        Initialize integer spinner.

        Args:
            label: Display label
            value: Initial value
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            step: Increment/decrement step size
        """
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step

    def compose(self) -> ComposeResult:
        """Create spinner layout."""
        yield Label(f"{self.label_text}:", classes="spinner-label")
        yield Label(f"[{self.value:2d}", classes="spinner-value", id="value-display")
        yield Label("±]", classes="spinner-buttons")

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

    def set_value(self, value: int) -> None:
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
            display.update(f"[{self.value:2d}")
        except Exception:  # nosec B110
            pass  # Widget may not be mounted yet
