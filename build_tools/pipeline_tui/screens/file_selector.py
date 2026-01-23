"""
File selector screen for Pipeline TUI.

This module provides a modal screen for selecting specific files from a directory.
Users can browse to a directory, see matching files, and select/deselect individual
files or use select all/none for batch operations.

**Features:**

- Directory tree navigation to find source folders
- File list with checkboxes for selection
- Select All / Select None buttons
- File pattern filtering
- Summary of selected files count

**Example Usage:**

.. code-block:: python

    from build_tools.pipeline_tui.screens.file_selector import FileSelectorScreen

    result = await self.app.push_screen_wait(
        FileSelectorScreen(
            initial_dir=Path("_working/codex"),
            file_pattern="*.txt",
        )
    )
    if result:
        selected_files = result  # List[Path]
        print(f"Selected {len(selected_files)} files")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual import on
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, DirectoryTree, Label, Static, Tree

if TYPE_CHECKING:
    from textual.app import ComposeResult


class FileSelectorScreen(ModalScreen[list[Path] | None]):
    """
    Modal screen for selecting multiple files from a directory.

    Displays a directory browser and a file list with checkboxes.
    When user navigates to a directory, shows all files matching
    the pattern with checkboxes for selection.

    Attributes:
        initial_dir: Starting directory for browser
        file_pattern: Glob pattern for filtering files (default: "*.txt")
        current_dir: Currently browsed directory
        selected_files: Set of selected file paths

    Returns:
        List of selected Path objects, or None if cancelled
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
        ("a", "select_all", "Select All"),
        ("n", "select_none", "Select None"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("h", "cursor_left", "Collapse"),
        ("l", "cursor_right", "Expand"),
        ("space", "toggle_node", "Toggle"),
    ]

    CSS = """
    FileSelectorScreen {
        align: center middle;
    }

    #file-selector-container {
        width: 100;
        height: 40;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }

    #selector-header {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #main-panels {
        width: 100%;
        height: 1fr;
    }

    #dir-panel {
        width: 40%;
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }

    #file-panel {
        width: 60%;
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }

    .panel-header {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    #directory-tree {
        width: 100%;
        height: 1fr;
    }

    #file-list {
        width: 100%;
        height: 1fr;
    }

    .file-checkbox {
        margin: 0;
        padding: 0;
    }

    #status-bar {
        height: 2;
        width: 100%;
        color: $text-muted;
        border-top: solid $primary;
        padding: 0 1;
        margin-top: 1;
    }

    #button-bar {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    #button-bar Button {
        margin: 0 1;
    }

    .empty-message {
        color: $text-muted;
        text-align: center;
        padding: 2;
    }
    """

    def __init__(
        self,
        initial_dir: Path | None = None,
        file_pattern: str = "*.txt",
        title: str = "Select Files",
        root_dir: Path | None = None,
    ) -> None:
        """
        Initialize file selector screen.

        Args:
            initial_dir: Starting directory for browser (default: home)
            file_pattern: Glob pattern for files (default: "*.txt")
            title: Header title for the screen
            root_dir: Root directory for tree navigation (default: home).
                      Set higher than initial_dir to allow navigating up.
        """
        super().__init__()
        self.initial_dir = initial_dir or Path.home()
        self.root_dir = root_dir or Path.home()
        self.file_pattern = file_pattern
        self.title_text = title
        self.current_dir: Path | None = None
        self.selected_files: set[Path] = set()
        self._file_checkboxes: dict[Path, Checkbox] = {}

    def compose(self) -> ComposeResult:
        """Compose the file selector UI."""
        with Container(id="file-selector-container"):
            yield Label(self.title_text, id="selector-header")

            with Horizontal(id="main-panels"):
                # Left panel: Directory browser (use root_dir to allow navigating up)
                with Vertical(id="dir-panel"):
                    yield Label("Directory", classes="panel-header")
                    yield DirectoryTree(str(self.root_dir), id="directory-tree")

                # Right panel: File list with checkboxes
                with Vertical(id="file-panel"):
                    yield Label(f"Files ({self.file_pattern})", classes="panel-header")
                    with VerticalScroll(id="file-list"):
                        yield Static(
                            "Navigate to a directory to see files",
                            classes="empty-message",
                            id="file-list-placeholder",
                        )

            # Status bar
            yield Static("No files selected", id="status-bar")

            # Buttons
            with Horizontal(id="button-bar"):
                yield Button("All", variant="default", id="select-all-button")
                yield Button("None", variant="default", id="select-none-button")
                yield Button("Select", variant="primary", id="select-button", disabled=True)
                yield Button("Cancel", variant="default", id="cancel-button")

    async def _update_file_list(self, directory: Path) -> None:
        """
        Update the file list to show files from the given directory.

        Args:
            directory: Directory to list files from
        """
        self.current_dir = directory
        file_list = self.query_one("#file-list", VerticalScroll)

        # Clear existing content (must await to ensure children are removed)
        self._file_checkboxes.clear()
        await file_list.remove_children()

        # Get matching files
        try:
            files = sorted(directory.glob(self.file_pattern))
            files = [f for f in files if f.is_file()]
        except Exception:
            files = []

        if not files:
            file_list.mount(
                Static(
                    f"No {self.file_pattern} files in this directory",
                    classes="empty-message",
                )
            )
            return

        # Create checkboxes for each file
        for file_path in files:
            # Check if this file was previously selected
            is_selected = file_path in self.selected_files
            checkbox = Checkbox(
                file_path.name,
                value=is_selected,
                classes="file-checkbox",
                id=f"file-{hash(file_path)}",
            )
            self._file_checkboxes[file_path] = checkbox
            file_list.mount(checkbox)

        self._update_status()

    def _update_status(self) -> None:
        """Update the status bar with current selection count."""
        count = len(self.selected_files)
        status = self.query_one("#status-bar", Static)
        select_button = self.query_one("#select-button", Button)

        if count == 0:
            status.update("No files selected")
            select_button.disabled = True
        elif count == 1:
            status.update("1 file selected")
            select_button.disabled = False
        else:
            status.update(f"{count} files selected")
            select_button.disabled = False

    @on(DirectoryTree.DirectorySelected)
    async def directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection in tree."""
        await self._update_file_list(Path(event.path))

    @on(Tree.NodeExpanded)
    async def node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle directory expansion - also load files."""
        node = event.node
        if node.data and hasattr(node.data, "path"):
            path = Path(node.data.path)
            if path.is_dir():
                await self._update_file_list(path)

    @on(Checkbox.Changed)
    def checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle file checkbox toggle."""
        # Find which file this checkbox belongs to
        for file_path, checkbox in self._file_checkboxes.items():
            if checkbox is event.checkbox:
                if event.value:
                    self.selected_files.add(file_path)
                else:
                    self.selected_files.discard(file_path)
                break
        self._update_status()

    @on(Button.Pressed, "#select-all-button")
    def select_all_pressed(self) -> None:
        """Select all visible files."""
        for file_path, checkbox in self._file_checkboxes.items():
            checkbox.value = True
            self.selected_files.add(file_path)
        self._update_status()

    @on(Button.Pressed, "#select-none-button")
    def select_none_pressed(self) -> None:
        """Deselect all visible files."""
        for file_path, checkbox in self._file_checkboxes.items():
            checkbox.value = False
            self.selected_files.discard(file_path)
        self._update_status()

    @on(Button.Pressed, "#select-button")
    def select_pressed(self) -> None:
        """Confirm selection and dismiss."""
        if self.selected_files:
            self.dismiss(sorted(self.selected_files))

    @on(Button.Pressed, "#cancel-button")
    def cancel_pressed(self) -> None:
        """Cancel and dismiss."""
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel action (escape key)."""
        self.dismiss(None)

    def action_confirm(self) -> None:
        """Confirm action (enter key)."""
        if self.selected_files:
            self.dismiss(sorted(self.selected_files))

    def action_select_all(self) -> None:
        """Select all files (a key)."""
        self.select_all_pressed()

    def action_select_none(self) -> None:
        """Deselect all files (n key)."""
        self.select_none_pressed()

    # -------------------------------------------------------------------------
    # Vim-style navigation actions
    # -------------------------------------------------------------------------

    async def on_mount(self) -> None:
        """
        Handle screen mount event.

        If initial_dir differs from root_dir, expand the tree
        to show initial_dir after a brief delay.
        """
        if self.initial_dir != self.root_dir:
            self.set_timer(0.1, self._expand_to_initial_dir)

    async def _expand_to_initial_dir(self) -> None:
        """Expand tree nodes from root to initial_dir."""
        tree = self.query_one("#directory-tree", DirectoryTree)

        try:
            relative_parts = self.initial_dir.relative_to(self.root_dir).parts
        except ValueError:
            return

        current_node = tree.root
        if not current_node.is_expanded:
            current_node.expand()

        for part in relative_parts:
            child_node = None
            for child in current_node.children:
                if child.data and hasattr(child.data, "path"):
                    child_path = Path(child.data.path)
                    if child_path.name == part:
                        if not child.is_expanded:
                            child.expand()
                        child_node = child
                        break
            if child_node:
                current_node = child_node
            else:
                break

        if current_node and current_node != tree.root:
            tree.select_node(current_node)
            if current_node.data and hasattr(current_node.data, "path"):
                path = Path(current_node.data.path)
                if path.is_dir():
                    await self._update_file_list(path)

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
        tree.action_cursor_left()  # type: ignore[attr-defined]

    def action_cursor_right(self) -> None:
        """Expand directory in tree (l key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        tree.action_cursor_right()  # type: ignore[attr-defined]

    def action_toggle_node(self) -> None:
        """Toggle expand/collapse of current node (space key)."""
        tree = self.query_one("#directory-tree", DirectoryTree)
        if tree.cursor_node:
            tree.cursor_node.toggle()
