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
from typing import TYPE_CHECKING, Any

from textual import on
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label, Static, Tree

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
        ("space", "toggle_node", "Toggle"),
        ("enter", "select_node", "Select"),
        ("escape", "cancel", "Cancel"),
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
        root_dir: Path | None = None,
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
            root_dir: Root directory for the tree. If None, uses home directory.
                      Set this higher than initial_dir to allow navigating up.
        """
        super().__init__()
        self.browser_title = title
        self.validator = validator or default_validator
        self.initial_dir = initial_dir or Path.home()
        self.root_dir = root_dir or Path.home()
        self.help_text = help_text or "Expand a directory to validate it. Click Select when valid."
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

            # Directory tree widget - use root_dir to allow navigating up
            yield DirectoryTree(str(self.root_dir), id="directory-tree")

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

    async def on_mount(self) -> None:
        """
        Handle screen mount event.

        If initial_dir differs from root_dir, attempt to expand the tree
        to show and select initial_dir after a brief delay to let the
        tree load its initial content.
        """
        if self.initial_dir != self.root_dir:
            # Schedule expansion after tree has loaded
            self.set_timer(0.1, self._expand_to_initial_dir)

    def _expand_to_initial_dir(self) -> None:
        """
        Expand tree nodes from root to initial_dir.

        This navigates the tree by expanding each directory in the path
        from root_dir to initial_dir, allowing the user to see their
        starting location while being able to navigate up.
        """
        tree = self.query_one("#directory-tree", DirectoryTree)

        # Get the relative path from root to initial_dir
        try:
            relative_parts = self.initial_dir.relative_to(self.root_dir).parts
        except ValueError:
            # initial_dir is not under root_dir, can't expand
            return

        # Walk the tree expanding each node in the path
        current_node = tree.root
        current_path = self.root_dir

        # Expand root first
        if not current_node.is_expanded:
            current_node.expand()

        # Function to find and expand child nodes
        def find_and_expand_child(node: Any, target_name: str) -> Any | None:
            """Find a child node by name and expand it."""
            for child in node.children:
                if child.data and hasattr(child.data, "path"):
                    child_path = Path(child.data.path)
                    if child_path.name == target_name:
                        if not child.is_expanded:
                            child.expand()
                        return child
            return None

        # Expand each part of the path
        for part in relative_parts:
            current_path = current_path / part
            child_node = find_and_expand_child(current_node, part)
            if child_node:
                current_node = child_node
            else:
                # Could not find node, tree might not be loaded yet
                break

        # Move cursor to the final node if we got there
        # Note: We only move the cursor, we don't validate. Validation should
        # happen when the user explicitly selects a directory (via click or Enter).
        if current_node and current_node != tree.root:
            tree.select_node(current_node)

    def _validate_and_update_status(self, path: Path) -> None:
        """
        Validate a directory and update the UI status accordingly.

        This is the core validation logic used by both DirectorySelected
        and NodeExpanded handlers to provide consistent behavior.

        Args:
            path: Directory path to validate
        """
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

    @on(DirectoryTree.DirectorySelected)
    def directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """
        Handle directory selection in tree.

        Validates the selected directory using the configured validator
        and updates the UI accordingly. Triggered when user clicks on
        a directory NAME (not the expand arrow).

        Args:
            event: Directory selection event from DirectoryTree
        """
        self._validate_and_update_status(Path(event.path))

    @on(Tree.NodeExpanded)
    def node_expanded(self, event: Tree.NodeExpanded) -> None:
        """
        Handle directory expansion in tree.

        When a user expands a directory (via arrow click or 'l' key),
        validate it and allow selection if valid. This improves UX by
        letting users select a directory after navigating into it,
        without needing to click on the directory name again.

        Note: We use Tree.NodeExpanded because DirectoryTree inherits from
        Tree and doesn't define its own NodeExpanded message class.

        Args:
            event: Node expanded event from Tree (parent class of DirectoryTree)
        """
        # NodeExpanded provides the tree node, get the path from it
        node = event.node
        if node.data and hasattr(node.data, "path"):
            # DirectoryTree nodes have DirEntry data with a path attribute
            path = Path(node.data.path)
            if path.is_dir():
                self._validate_and_update_status(path)

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """
        Handle file selection in tree.

        When a file is clicked, we don't clear the current selection since
        the user may have already validated the parent directory by expanding
        into it. Instead, we provide a gentle reminder that the parent
        directory is what will be selected.

        Args:
            event: File selection event from DirectoryTree
        """
        file_path = Path(event.path)
        parent_dir = file_path.parent

        # If the parent directory is currently selected and valid, just remind
        # the user that they can click Select
        if self.selected_path == parent_dir:
            # Don't change validation state - parent is still selected
            status_container = self.query_one("#validation-status", Static)
            status_text = self.query_one("#status-text", Label)

            # Keep the valid status but update the message
            if status_container.has_class("status-valid"):
                status_text.update(
                    f"[checkmark] Directory ready to select\n"
                    f"Click Select to use: {parent_dir.name}"
                )
                return

        # Otherwise show a helpful message without disrupting valid selection
        status_container = self.query_one("#validation-status", Static)
        status_text = self.query_one("#status-text", Label)

        # Only show warning if we don't have a valid selection
        select_button = self.query_one("#select-button", Button)
        if select_button.disabled:
            status_container.remove_class("status-valid", "status-none")
            status_container.add_class("status-invalid")
            status_text.update(
                "[x] Files cannot be selected\n" "Expand into the parent directory first"
            )
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

    def action_toggle_node(self) -> None:
        """
        Toggle expand/collapse of current node (space key).

        Expands collapsed nodes, collapses expanded nodes.
        """
        tree = self.query_one("#directory-tree", DirectoryTree)
        if tree.cursor_node:
            tree.cursor_node.toggle()

    def action_select_node(self) -> None:
        """
        Select the current node (enter key).

        If the current node is a directory, validates it.
        If already valid, confirms the selection.
        """
        tree = self.query_one("#directory-tree", DirectoryTree)
        if tree.cursor_node and tree.cursor_node.data:
            # Get path from node data
            if hasattr(tree.cursor_node.data, "path"):
                path = Path(tree.cursor_node.data.path)
                if path.is_dir():
                    self._validate_and_update_status(path)
                    # If valid and already selected, confirm
                    select_button = self.query_one("#select-button", Button)
                    if not select_button.disabled and self.selected_path == path:
                        self.dismiss(self.selected_path)

    def action_cancel(self) -> None:
        """Cancel and close the dialog (escape key)."""
        self.dismiss(None)
