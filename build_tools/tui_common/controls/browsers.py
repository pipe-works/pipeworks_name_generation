"""
Directory browser modal widget.

This module provides the DirectoryBrowserScreen modal for selecting
directories with customizable validation.

**Features:**

- Textual DirectoryTree widget for file system navigation
- Vim-style keybindings (h/j/k/l) for navigation
- Customizable validation callback
- Visual feedback for valid/invalid selections
- Select/Cancel buttons with state management

**Example Usage:**

.. code-block:: python

    from pathlib import Path
    from build_tools.tui_common.controls import DirectoryBrowserScreen

    # Custom validator for source directories
    def validate_source_dir(path: Path) -> tuple[bool, str, str]:
        txt_files = list(path.glob("*.txt"))
        if txt_files:
            return (True, "source", f"Found {len(txt_files)} text files")
        return (False, "", "No .txt files found")

    # In your App
    async def select_directory(self) -> None:
        result = await self.push_screen_wait(
            DirectoryBrowserScreen(
                title="Select Source Directory",
                validator=validate_source_dir,
                initial_dir=Path.cwd(),
            )
        )
        if result:
            print(f"Selected: {result}")
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


# Type alias for validator function signature
# Returns: (is_valid, type_label, message)
# - is_valid: True if directory is valid for selection
# - type_label: Short label describing what was found (e.g., "corpus", "source")
# - message: Human-readable message (error if invalid, description if valid)
DirectoryValidator = Callable[[Path], tuple[bool, str, str]]


def default_validator(path: Path) -> tuple[bool, str, str]:
    """
    Default validator that accepts any directory.

    Args:
        path: Directory path to validate

    Returns:
        Tuple of (True, "directory", path name) for any directory
    """
    return (True, "directory", path.name)


class DirectoryBrowserScreen(ModalScreen[Path | None]):
    """
    Modal screen for browsing and selecting a directory.

    A modal dialog displaying a directory tree for navigation with
    customizable validation. Returns the selected directory path
    when user confirms, or None if cancelled.

    **Validation:**

    Provide a ``validator`` callable that takes a Path and returns
    a tuple of ``(is_valid, type_label, message)``:

    - ``is_valid``: True if the directory can be selected
    - ``type_label``: Short label for valid directories (e.g., "corpus")
    - ``message``: Error message if invalid, or description if valid

    **Navigation:**

    - ``j`` / ``down``: Move cursor down
    - ``k`` / ``up``: Move cursor up
    - ``h`` / ``left``: Collapse directory
    - ``l`` / ``right``: Expand directory

    Attributes:
        browser_title: Header text displayed at top of modal
        validator: Callback function to validate selected directories
        initial_dir: Starting directory for the browser
        selected_path: Currently selected path (or None)

    Returns:
        Selected Path when "Select" is pressed, or None if cancelled

    Example:
        .. code-block:: python

            result = await self.app.push_screen_wait(
                DirectoryBrowserScreen(
                    title="Select Corpus Directory",
                    validator=validate_corpus_directory,
                    initial_dir=Path.home() / "corpora",
                )
            )
            if result:
                self.load_corpus(result)
    """

    # -------------------------------------------------------------------------
    # Vim-style navigation bindings
    # -------------------------------------------------------------------------
    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("h", "cursor_left", "Collapse"),
        ("l", "cursor_right", "Expand"),
    ]

    # -------------------------------------------------------------------------
    # Modal styling
    # -------------------------------------------------------------------------
    CSS = """
    DirectoryBrowserScreen {
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

    def __init__(
        self,
        title: str = "Select Directory",
        validator: DirectoryValidator | None = None,
        initial_dir: Path | None = None,
        help_text: str | None = None,
    ) -> None:
        """
        Initialize directory browser.

        Args:
            title: Header text displayed at top of modal
            validator: Callback function to validate directories.
                       Signature: ``(Path) -> (is_valid, type_label, message)``
                       If None, uses default_validator which accepts any directory.
            initial_dir: Starting directory for browser (defaults to home directory)
            help_text: Custom help text to display. If None, uses default help text.
        """
        super().__init__()
        self.browser_title = title
        self.validator = validator or default_validator
        self.initial_dir = initial_dir or Path.home()
        self.help_text = help_text or "Navigate with hjkl/arrows. Select a DIRECTORY."
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        """
        Create browser UI layout.

        Layout:
        - Header with title
        - Help text
        - Directory tree (expandable/collapsible)
        - Validation status display
        - Select/Cancel buttons

        Yields:
            Composed widget tree for the modal
        """
        with Container(id="browser-container"):
            yield Label(self.browser_title, id="browser-header")

            # Help text for navigation
            yield Label(self.help_text or "", id="help-text")

            # Directory tree widget
            yield DirectoryTree(str(self.initial_dir), id="directory-tree")

            # Validation status area
            with Static(id="validation-status", classes="status-none"):
                yield Label("Select a directory to validate", id="status-text")

            # Action buttons
            with Horizontal(id="button-bar"):
                yield Button(
                    "Select",
                    variant="primary",
                    id="select-button",
                    disabled=True,
                )
                yield Button("Cancel", variant="default", id="cancel-button")

    @on(DirectoryTree.DirectorySelected)
    def directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """
        Handle directory selection in tree.

        Validates the selected directory using the configured validator
        and updates the UI accordingly.

        Args:
            event: Directory selection event from DirectoryTree
        """
        path = Path(event.path)
        self.selected_path = path

        # Validate directory using configured validator
        is_valid, type_label, message = self.validator(path)

        # Update status display
        status_container = self.query_one("#validation-status", Static)
        status_text = self.query_one("#status-text", Label)
        select_button = self.query_one("#select-button", Button)

        if is_valid:
            # Valid selection - enable button, show success message
            status_container.remove_class("status-invalid", "status-none")
            status_container.add_class("status-valid")
            status_text.update(f"[checkmark] Valid {type_label}\n{path.name}")
            select_button.disabled = False
        else:
            # Invalid selection - disable button, show error
            status_container.remove_class("status-valid", "status-none")
            status_container.add_class("status-invalid")
            status_text.update(f"[x] Invalid selection\n{message}")
            select_button.disabled = True

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """
        Handle file selection in tree.

        Provides helpful feedback that directories (not files) should be selected.

        Args:
            event: File selection event from DirectoryTree
        """
        file_path = Path(event.path)

        # Update status to explain the issue
        status_container = self.query_one("#validation-status", Static)
        status_text = self.query_one("#status-text", Label)
        select_button = self.query_one("#select-button", Button)

        status_container.remove_class("status-valid", "status-none")
        status_container.add_class("status-invalid")
        status_text.update(
            f"[x] File selected: {file_path.name}\n" f"Please select the parent directory instead"
        )
        select_button.disabled = True
        self.selected_path = None

    @on(Button.Pressed, "#select-button")
    def select_pressed(self) -> None:
        """
        Handle Select button press.

        Dismisses the modal with the selected path.
        """
        if self.selected_path:
            self.dismiss(self.selected_path)

    @on(Button.Pressed, "#cancel-button")
    def cancel_pressed(self) -> None:
        """
        Handle Cancel button press.

        Dismisses the modal with None.
        """
        self.dismiss(None)

    # -------------------------------------------------------------------------
    # Vim-style navigation actions
    # -------------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        """Move cursor down in directory tree (j key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        tree.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up in directory tree (k key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        tree.action_cursor_up()

    def action_cursor_left(self) -> None:
        """
        Collapse directory in tree (h key).

        Collapses the current directory node if expanded.
        """
        tree = self.query_one("#directory-tree", DirectoryTree)
        # DirectoryTree inherits from Tree which has this action
        tree.action_cursor_left()  # type: ignore[attr-defined]

    def action_cursor_right(self) -> None:
        """
        Expand directory in tree (l key).

        Expands the current directory node if collapsed.
        """
        tree = self.query_one("#directory-tree", DirectoryTree)
        # DirectoryTree inherits from Tree which has this action
        tree.action_cursor_right()  # type: ignore[attr-defined]
