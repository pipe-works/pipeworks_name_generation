"""
Seed input and profile option widgets.

This module provides SeedInput and ProfileOption widgets for configuration.
"""

from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Input, Label, Static


class SeedInput(Static):
    """
    Seed input widget with two-box design.

    Box 1 (Input): User enters seed or '-1' for random (default: -1)
    Box 2 (Display): Shows actual seed being used

    Attributes:
        value: Current seed value being used
        user_input: User's input (-1 means random)

    Keybindings:
        r: Set to random (-1)
    """

    # Define widget-level bindings
    BINDINGS = [
        ("r", "random", "Random"),
    ]

    class Changed(Message):
        """Message posted when seed changes."""

        def __init__(self, value: int, widget_id: str | None) -> None:
            """Initialize with new seed value and widget ID."""
            super().__init__()
            self.value = value
            self.widget_id = widget_id

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

    def __init__(self, value: int | None = None, *args, **kwargs):
        """
        Initialize seed input with two-box design.

        Args:
            value: Initial seed value (generates random if None)
        """
        super().__init__(*args, **kwargs)
        # Generate initial random seed
        import random

        if value is None:
            self.value = random.SystemRandom().randint(0, 2**32 - 1)
        else:
            self.value = value
        # User input defaults to -1 (random mode)
        self.user_input = -1

    def compose(self) -> ComposeResult:
        """Create two-box seed input in single horizontal row."""
        yield Label("Seed:", classes="seed-label")
        yield Input(
            placeholder="-1 (random)",
            value="-1",
            id="seed-input",
        )
        yield Label("→", classes="arrow")
        yield Label(f"{self.value}", classes="seed-used-value", id="seed-used")

    def action_random(self) -> None:
        """Action: Set input to -1 (random mode)."""
        try:
            input_widget = self.query_one("#seed-input", Input)
            input_widget.value = "-1"
            self._handle_input_change("-1")
        except Exception:  # nosec B110 - Safe widget query failure, intentionally silent
            pass

    @on(Input.Changed, "#seed-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle user typing in the seed input."""
        self._handle_input_change(event.value)

    def _handle_input_change(self, input_value: str) -> None:
        """Process input value and update actual seed."""
        import random

        input_str = input_value.strip()

        # Handle empty or -1 as random
        if not input_str or input_str == "-1":
            self.user_input = -1
            # Generate new random seed
            self.value = random.SystemRandom().randint(0, 2**32 - 1)
        else:
            # Try to parse as integer
            try:
                manual_seed = int(input_str)
                # Clamp to valid range
                manual_seed = max(0, min(manual_seed, 2**32 - 1))
                self.user_input = manual_seed
                self.value = manual_seed
            except ValueError:
                # Invalid input, ignore and keep current value
                return

        # Update display
        self._update_display()

        # Post changed message
        self.post_message(self.Changed(self.value, self.id))

    def _update_display(self) -> None:
        """Update the 'Using:' display with actual seed value."""
        try:
            display = self.query_one("#seed-used", Label)
            display.update(f"{self.value}")
        except Exception:  # nosec B110 - Safe widget query failure, intentionally silent
            pass


class ProfileOption(Static):
    """
    Single profile option widget (radio button style).

    Displays as a checkbox-style option that can be clicked or activated with keyboard.
    Follows focus management pattern: focusable, but blurs immediately after selection.

    Attributes:
        profile_name: Name of this profile ("clerical", "dialect", etc.)
        is_selected: Whether this option is currently selected
        description: Brief description shown after profile name
    """

    # Define widget-level bindings for selection
    BINDINGS = [
        ("enter", "select", "Select Profile"),
        ("space", "select", "Select Profile"),
    ]

    class Selected(Message):
        """Message posted when this profile option is selected."""

        def __init__(self, profile_name: str, widget_id: str | None) -> None:
            """Initialize with profile name and widget ID."""
            super().__init__()
            self.profile_name = profile_name
            self.widget_id = widget_id

    DEFAULT_CSS = """
    ProfileOption {
        height: 1;
        width: 100%;
    }

    ProfileOption:hover {
        background: $boost;
    }

    ProfileOption:focus {
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
        profile_name: str,
        description: str,
        is_selected: bool = False,
        *args,
        **kwargs,
    ):
        """
        Initialize profile option.

        Args:
            profile_name: Profile name (e.g., "clerical")
            description: Brief description to show
            is_selected: Whether this option starts selected
        """
        super().__init__(*args, **kwargs)
        self.profile_name = profile_name
        self.description = description
        self.is_selected = is_selected

    def on_mount(self) -> None:
        """
        Make widget focusable for keyboard navigation.

        Note: We explicitly blur focus after selection to prevent
        auto-focus from breaking tab switching bindings.
        """
        self.can_focus = True

    def render(self):
        """Render the profile option as text with Rich markup."""
        from rich.text import Text

        # Build the display text
        # Note: We escape the square brackets to prevent Rich from interpreting them as markup
        checkbox = "\\[x]" if self.is_selected else "\\[ ]"
        label = self.profile_name.capitalize()

        # Apply styling based on selection state
        if self.is_selected:
            # Selected: bold green with [x]
            return Text.from_markup(
                f"[bold green]{checkbox}[/bold green] [bold]{label}[/bold]: {self.description}"
            )
        else:
            # Unselected: muted gray with [ ]
            return Text.from_markup(f"[dim]{checkbox}[/dim] {label}: [dim]{self.description}[/dim]")

    def action_select(self) -> None:
        """Action: Select this profile option (Enter/Space)."""
        if not self.is_selected:
            self.post_message(self.Selected(self.profile_name, self.id))
        # Don't blur - keep focus on selected option like standard radio buttons
        # This prevents focus from jumping unexpectedly

    def on_click(self) -> None:
        """Handle click on this profile option."""
        if not self.is_selected:
            self.post_message(self.Selected(self.profile_name, self.id))
        # Don't blur - keep focus on selected option like standard radio buttons
        # This prevents focus from jumping unexpectedly

    def set_selected(self, selected: bool) -> None:
        """Update selection state and refresh display."""
        self.is_selected = selected
        self.refresh()
