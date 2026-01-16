"""
Corpus browser modal widget.

This module provides the CorpusBrowserScreen modal for selecting corpus directories.
"""

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label, Static

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
