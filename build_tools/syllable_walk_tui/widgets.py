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
    Seed input widget with random generation button.

    Allows direct input of integer seed or clicking dice button for random seed.
    Blank input means random seed (generated when needed).

    Attributes:
        value: Current seed value (None if blank/random)
    """

    class Changed(Message):
        """Message posted when seed changes."""

        def __init__(self, value: int | None, widget_id: str | None) -> None:
            """Initialize with new seed value (None if blank) and widget ID."""
            super().__init__()
            self.value = value
            self.widget_id = widget_id

    DEFAULT_CSS = """
    SeedInput {
        layout: horizontal;
        height: 1;
        width: 100%;
    }

    SeedInput .seed-label {
        width: 7;
        text-align: right;
        padding-right: 1;
    }

    SeedInput Input {
        width: 12;
    }

    SeedInput Input:focus {
        border: tall $accent;
    }

    SeedInput Button {
        width: 5;
        min-width: 5;
        margin-left: 1;
    }

    SeedInput Button:focus {
        text-style: bold;
    }
    """

    def __init__(self, value: int | None = None, *args, **kwargs):
        """
        Initialize seed input.

        Args:
            value: Initial seed value (None for blank/random)
        """
        super().__init__(*args, **kwargs)
        self.value = value

    def on_mount(self) -> None:
        """
        Make widget focusable for keyboard navigation.

        Note: We explicitly blur focus after modal closes in app.py
        to prevent auto-focus from breaking tab switching bindings.
        """
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """Create seed input layout."""
        yield Label("Seed:", classes="seed-label")
        initial_text = str(self.value) if self.value is not None else ""
        input_widget = Input(
            placeholder="random",
            value=initial_text,
            type="integer",
            id="seed-input",
        )
        # CRITICAL: Disable focus on Input to prevent it from capturing app-level keys
        # Input widgets capture ALL keyboard input (including b, a, p, q) when focused
        # This breaks app-level bindings for tab switching and other commands
        # Users can still click the input to edit, or we can enable focus programmatically
        input_widget.can_focus = False
        yield input_widget
        yield Button("🎲", id="random-button", variant="primary")

    @on(Input.Changed, "#seed-input")
    def on_seed_input_changed(self, event: Input.Changed) -> None:
        """Handle seed input text change."""
        input_text = event.value.strip()
        if not input_text:
            # Blank input = random seed
            self.value = None
            self.post_message(self.Changed(None, self.id))
        else:
            try:
                seed = int(input_text)
                self.value = seed
                self.post_message(self.Changed(seed, self.id))
            except ValueError:
                # Invalid input - ignore for now, user still typing
                pass

    @on(Button.Pressed, "#random-button")
    def on_random_button_pressed(self) -> None:
        """Generate new random seed using system entropy."""
        import random

        new_seed = random.SystemRandom().randint(0, 2**32 - 1)
        self.value = new_seed

        # Update input field
        try:
            input_widget = self.query_one("#seed-input", Input)
            input_widget.value = str(new_seed)
        except Exception:  # nosec B110
            pass

        self.post_message(self.Changed(new_seed, self.id))


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

    def on_click(self) -> None:
        """Handle click on this profile option."""
        if not self.is_selected:
            self.post_message(self.Selected(self.profile_name, self.id))

    def set_selected(self, selected: bool) -> None:
        """Update selection state and refresh display."""
        self.is_selected = selected
        self.refresh()
