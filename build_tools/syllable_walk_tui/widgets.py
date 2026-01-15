"""
Custom widgets for Syllable Walker TUI.

This module contains reusable UI widgets including:
- CorpusBrowserScreen: Modal file browser for corpus selection
- IntSpinner: Integer parameter control with keyboard navigation
- FloatSlider: Float parameter control with keyboard navigation
- SeedInput: Random seed input with validation
- ProfileOption: Radio-button style profile selector
"""

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Label, Static

from build_tools.syllable_walk_tui.corpus import validate_corpus_directory


class CorpusBrowserScreen(ModalScreen[Path | None]):
    """
    Modal screen for browsing and selecting a corpus directory.

    Returns the selected directory path when user confirms selection,
    or None if cancelled.

    Usage:
        result = await self.app.push_screen_wait(CorpusBrowserScreen())
        if result:
            print(f"Selected: {result}")
    """

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("h", "cursor_left", "Left"),
        ("l", "cursor_right", "Right"),
    ]

    CSS = """
    CorpusBrowserScreen {
        align: center middle;
    }

    #browser-container {
        width: 80;
        height: 30;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }

    #browser-header {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #directory-tree {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }

    #help-text {
        height: 2;
        width: 100%;
        color: $text-muted;
        text-align: center;
        margin-bottom: 1;
    }

    #validation-status {
        height: 3;
        width: 100%;
        border: solid $primary;
        padding: 0 1;
        margin-bottom: 1;
    }

    .status-valid {
        color: $success;
    }

    .status-invalid {
        color: $error;
    }

    .status-none {
        color: $text-muted;
    }

    #button-bar {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #button-bar Button {
        margin: 0 1;
    }
    """

    def __init__(self, initial_dir: Path | None = None):
        """
        Initialize corpus browser.

        Args:
            initial_dir: Starting directory for browser (defaults to home directory)
        """
        super().__init__()
        self.initial_dir = initial_dir or Path.home()
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        """Create browser UI."""
        with Container(id="browser-container"):
            yield Label("Select Corpus Directory", id="browser-header")

            # Help text
            yield Label(
                "Navigate with hjkl/arrows. Select the DIRECTORY (not files inside it).",
                id="help-text",
            )

            # Directory tree
            yield DirectoryTree(str(self.initial_dir), id="directory-tree")

            # Validation status
            with Static(id="validation-status", classes="status-none"):
                yield Label("Select a directory to validate", id="status-text")

            # Buttons
            with Horizontal(id="button-bar"):
                yield Button("Select", variant="primary", id="select-button", disabled=True)
                yield Button("Cancel", variant="default", id="cancel-button")

    @on(DirectoryTree.DirectorySelected)
    def directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """
        Handle directory selection in tree.

        Args:
            event: Directory selection event
        """
        path = Path(event.path)
        self.selected_path = path

        # Validate directory
        is_valid, corpus_type, error = validate_corpus_directory(path)

        # Update status display
        status_container = self.query_one("#validation-status", Static)
        status_text = self.query_one("#status-text", Label)
        select_button = self.query_one("#select-button", Button)

        if is_valid:
            status_container.remove_class("status-invalid", "status-none")
            status_container.add_class("status-valid")
            status_text.update(f"✓ Valid {corpus_type} corpus\n{path.name}")
            select_button.disabled = False
        else:
            status_container.remove_class("status-valid", "status-none")
            status_container.add_class("status-invalid")
            status_text.update(f"✗ Invalid corpus\n{error}")
            select_button.disabled = True

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """
        Handle file selection in tree.

        Provides helpful feedback that directories (not files) should be selected.

        Args:
            event: File selection event
        """
        file_path = Path(event.path)

        # Update status to explain the issue
        status_container = self.query_one("#validation-status", Static)
        status_text = self.query_one("#status-text", Label)
        select_button = self.query_one("#select-button", Button)

        status_container.remove_class("status-valid", "status-none")
        status_container.add_class("status-invalid")
        status_text.update(
            f"✗ File selected: {file_path.name}\n" f"Please select the parent directory instead"
        )
        select_button.disabled = True
        self.selected_path = None

    @on(Button.Pressed, "#select-button")
    def select_pressed(self) -> None:
        """Handle Select button press."""
        if self.selected_path:
            self.dismiss(self.selected_path)

    @on(Button.Pressed, "#cancel-button")
    def cancel_pressed(self) -> None:
        """Handle Cancel button press."""
        self.dismiss(None)

    def action_cursor_down(self) -> None:
        """Move cursor down in directory tree (j key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        tree.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up in directory tree (k key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        tree.action_cursor_up()

    def action_cursor_left(self) -> None:
        """Collapse directory in tree (h key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        # For DirectoryTree, left collapses the current node
        tree.action_cursor_left()  # type: ignore[attr-defined]

    def action_cursor_right(self) -> None:
        """Expand directory in tree (l key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        # For DirectoryTree, right expands the current node
        tree.action_cursor_right()  # type: ignore[attr-defined]


# =============================================================================
# Parameter Control Widgets
# =============================================================================


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

    FloatSlider .slider-bar {
        width: 3;
        padding-left: 1;
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
        """
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.precision = precision

    def compose(self) -> ComposeResult:
        """Create slider layout."""
        yield Label(f"{self.label_text}:", classes="slider-label")
        format_str = f"[{{:.{self.precision}f}}"
        yield Label(format_str.format(self.value), classes="slider-value", id="value-display")
        yield Label("─]", classes="slider-bar")

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
            format_str = f"[{{:.{self.precision}f}}"
            display.update(format_str.format(self.value))
        except Exception:  # nosec B110
            pass  # Widget may not be mounted yet


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
