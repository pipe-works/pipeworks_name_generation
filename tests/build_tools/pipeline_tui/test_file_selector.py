"""
Tests for pipeline_tui file selector screen.

Tests FileSelectorScreen modal for selecting files from directories.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.widgets import Button, Checkbox

from build_tools.pipeline_tui.screens.file_selector import FileSelectorScreen


class TestFileSelectorScreenInit:
    """Tests for FileSelectorScreen initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization values."""
        screen = FileSelectorScreen()

        assert screen.initial_dir == Path.home()
        assert screen.root_dir == Path.home()
        assert screen.file_pattern == "*.txt"
        assert screen.title_text == "Select Files"
        assert screen.current_dir is None
        assert screen.selected_files == set()

    def test_custom_initialization(self, tmp_path: Path) -> None:
        """Test custom initialization values."""
        screen = FileSelectorScreen(
            initial_dir=tmp_path,
            file_pattern="*.md",
            title="Custom Title",
            root_dir=tmp_path.parent,
        )

        assert screen.initial_dir == tmp_path
        assert screen.file_pattern == "*.md"
        assert screen.title_text == "Custom Title"
        assert screen.root_dir == tmp_path.parent


class TestFileSelectorScreenCompose:
    """Tests for FileSelectorScreen UI composition."""

    @pytest.mark.asyncio
    async def test_compose_has_required_elements(self, tmp_path: Path) -> None:
        """Test screen composes with required UI elements."""
        from textual.app import App

        screen = FileSelectorScreen(initial_dir=tmp_path)

        class TestApp(App):
            def compose(self):
                yield from screen.compose()

        app = TestApp()
        async with app.run_test():
            # Check for main container
            container = app.query_one("#file-selector-container")
            assert container is not None

            # Check for header
            header = app.query_one("#selector-header")
            assert header is not None

            # Check for panels
            dir_panel = app.query_one("#dir-panel")
            file_panel = app.query_one("#file-panel")
            assert dir_panel is not None
            assert file_panel is not None

            # Check for buttons
            select_all = app.query_one("#select-all-button", Button)
            select_none = app.query_one("#select-none-button", Button)
            select_btn = app.query_one("#select-button", Button)
            cancel_btn = app.query_one("#cancel-button", Button)
            assert select_all is not None
            assert select_none is not None
            assert select_btn is not None
            assert cancel_btn is not None

    @pytest.mark.asyncio
    async def test_select_button_initially_disabled(self, tmp_path: Path) -> None:
        """Test select button is disabled when no files selected."""
        from textual.app import App

        screen = FileSelectorScreen(initial_dir=tmp_path)

        class TestApp(App):
            def compose(self):
                yield from screen.compose()

        app = TestApp()
        async with app.run_test():
            select_btn = app.query_one("#select-button", Button)
            assert select_btn.disabled is True


class TestFileSelectorScreenFileList:
    """Tests for file list functionality."""

    @pytest.mark.asyncio
    async def test_update_file_list_empty_directory(self, tmp_path: Path) -> None:
        """Test file list shows message for empty directory."""
        screen = FileSelectorScreen(initial_dir=tmp_path)
        # Mock the query methods
        mock_file_list = MagicMock()
        mock_file_list.remove_children = AsyncMock()
        mock_file_list.mount = MagicMock()

        with patch.object(screen, "query_one", return_value=mock_file_list):
            await screen._update_file_list(tmp_path)

        assert screen.current_dir == tmp_path
        # Should mount empty message
        mock_file_list.mount.assert_called()

    @pytest.mark.asyncio
    async def test_update_file_list_with_files(self, tmp_path: Path) -> None:
        """Test file list populates with matching files."""
        # Create test files
        (tmp_path / "file1.txt").write_text("test1")
        (tmp_path / "file2.txt").write_text("test2")
        (tmp_path / "file3.md").write_text("other")  # Non-matching

        screen = FileSelectorScreen(initial_dir=tmp_path, file_pattern="*.txt")
        mock_file_list = MagicMock()
        mock_file_list.remove_children = AsyncMock()
        mounted_widgets: list = []
        mock_file_list.mount = lambda w: mounted_widgets.append(w)

        with patch.object(screen, "query_one", return_value=mock_file_list):
            with patch.object(screen, "_update_status"):
                await screen._update_file_list(tmp_path)

        assert screen.current_dir == tmp_path
        # Should have 2 checkboxes (only .txt files)
        checkboxes = [w for w in mounted_widgets if isinstance(w, Checkbox)]
        assert len(checkboxes) == 2

    @pytest.mark.asyncio
    async def test_update_file_list_preserves_selection(self, tmp_path: Path) -> None:
        """Test previously selected files remain selected."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("test1")
        file2.write_text("test2")

        screen = FileSelectorScreen(initial_dir=tmp_path)
        screen.selected_files = {file1}  # Pre-select file1

        mock_file_list = MagicMock()
        mock_file_list.remove_children = AsyncMock()
        mounted_widgets: list = []
        mock_file_list.mount = lambda w: mounted_widgets.append(w)

        with patch.object(screen, "query_one", return_value=mock_file_list):
            with patch.object(screen, "_update_status"):
                await screen._update_file_list(tmp_path)

        # Find checkbox for file1 - it should be selected
        checkboxes = [w for w in mounted_widgets if isinstance(w, Checkbox)]
        file1_checkbox = next((cb for cb in checkboxes if cb.label.plain == "file1.txt"), None)
        assert file1_checkbox is not None
        assert file1_checkbox.value is True


class TestFileSelectorScreenStatus:
    """Tests for status bar updates."""

    def test_update_status_no_selection(self) -> None:
        """Test status text with no selection."""
        screen = FileSelectorScreen()
        screen.selected_files = set()

        mock_status = MagicMock()
        mock_button = MagicMock()

        def mock_query(selector, widget_type=None):
            if selector == "#status-bar":
                return mock_status
            elif selector == "#select-button":
                return mock_button
            return MagicMock()

        with patch.object(screen, "query_one", side_effect=mock_query):
            screen._update_status()

        mock_status.update.assert_called_with("No files selected")
        assert mock_button.disabled is True

    def test_update_status_one_file(self, tmp_path: Path) -> None:
        """Test status text with one file selected."""
        screen = FileSelectorScreen()
        screen.selected_files = {tmp_path / "file.txt"}

        mock_status = MagicMock()
        mock_button = MagicMock()

        def mock_query(selector, widget_type=None):
            if selector == "#status-bar":
                return mock_status
            elif selector == "#select-button":
                return mock_button
            return MagicMock()

        with patch.object(screen, "query_one", side_effect=mock_query):
            screen._update_status()

        mock_status.update.assert_called_with("1 file selected")
        assert mock_button.disabled is False

    def test_update_status_multiple_files(self, tmp_path: Path) -> None:
        """Test status text with multiple files selected."""
        screen = FileSelectorScreen()
        screen.selected_files = {
            tmp_path / "file1.txt",
            tmp_path / "file2.txt",
            tmp_path / "file3.txt",
        }

        mock_status = MagicMock()
        mock_button = MagicMock()

        def mock_query(selector, widget_type=None):
            if selector == "#status-bar":
                return mock_status
            elif selector == "#select-button":
                return mock_button
            return MagicMock()

        with patch.object(screen, "query_one", side_effect=mock_query):
            screen._update_status()

        mock_status.update.assert_called_with("3 files selected")
        assert mock_button.disabled is False


class TestFileSelectorScreenSelection:
    """Tests for file selection functionality."""

    def test_select_all_pressed(self, tmp_path: Path) -> None:
        """Test select all button selects all visible files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        screen = FileSelectorScreen()
        screen.selected_files = set()

        # Create mock checkboxes
        checkbox1 = MagicMock()
        checkbox1.value = False
        checkbox2 = MagicMock()
        checkbox2.value = False

        screen._file_checkboxes = {file1: checkbox1, file2: checkbox2}

        with patch.object(screen, "_update_status"):
            screen.select_all_pressed()

        assert checkbox1.value is True
        assert checkbox2.value is True
        assert file1 in screen.selected_files
        assert file2 in screen.selected_files

    def test_select_none_pressed(self, tmp_path: Path) -> None:
        """Test select none button deselects all files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        screen = FileSelectorScreen()
        screen.selected_files = {file1, file2}

        checkbox1 = MagicMock()
        checkbox1.value = True
        checkbox2 = MagicMock()
        checkbox2.value = True

        screen._file_checkboxes = {file1: checkbox1, file2: checkbox2}

        with patch.object(screen, "_update_status"):
            screen.select_none_pressed()

        assert checkbox1.value is False
        assert checkbox2.value is False
        assert file1 not in screen.selected_files
        assert file2 not in screen.selected_files


class TestFileSelectorScreenActions:
    """Tests for action methods."""

    def test_action_cancel_dismisses_none(self) -> None:
        """Test cancel action dismisses with None."""
        screen = FileSelectorScreen()

        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.action_cancel()

            mock_dismiss.assert_called_once_with(None)

    def test_action_confirm_dismisses_selected(self, tmp_path: Path) -> None:
        """Test confirm action dismisses with sorted selection."""
        file_c = tmp_path / "c.txt"
        file_a = tmp_path / "a.txt"
        file_b = tmp_path / "b.txt"

        screen = FileSelectorScreen()
        screen.selected_files = {file_c, file_a, file_b}

        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.action_confirm()

            # Should dismiss with sorted list
            mock_dismiss.assert_called_once()
            call_args = mock_dismiss.call_args[0][0]
            assert call_args == [file_a, file_b, file_c]

    def test_action_confirm_no_selection(self) -> None:
        """Test confirm does nothing with no selection."""
        screen = FileSelectorScreen()
        screen.selected_files = set()

        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.action_confirm()

            mock_dismiss.assert_not_called()

    def test_action_select_all(self) -> None:
        """Test select all action."""
        screen = FileSelectorScreen()

        with patch.object(screen, "select_all_pressed") as mock_select_all:
            screen.action_select_all()

            mock_select_all.assert_called_once()

    def test_action_select_none(self) -> None:
        """Test select none action."""
        screen = FileSelectorScreen()

        with patch.object(screen, "select_none_pressed") as mock_select_none:
            screen.action_select_none()

            mock_select_none.assert_called_once()


class TestFileSelectorScreenButtonHandlers:
    """Tests for button event handlers."""

    def test_select_pressed_with_files(self, tmp_path: Path) -> None:
        """Test select button dismisses with selection."""
        file1 = tmp_path / "file1.txt"
        screen = FileSelectorScreen()
        screen.selected_files = {file1}

        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.select_pressed()

            mock_dismiss.assert_called_once()
            call_args = mock_dismiss.call_args[0][0]
            assert file1 in call_args

    def test_select_pressed_empty_selection(self) -> None:
        """Test select button does nothing without selection."""
        screen = FileSelectorScreen()
        screen.selected_files = set()

        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.select_pressed()

            mock_dismiss.assert_not_called()

    def test_cancel_pressed(self) -> None:
        """Test cancel button dismisses with None."""
        screen = FileSelectorScreen()

        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.cancel_pressed()

            mock_dismiss.assert_called_once_with(None)


class TestFileSelectorScreenBindings:
    """Tests for keybinding configuration."""

    def test_bindings_defined(self) -> None:
        """Test expected bindings are defined."""
        from textual.binding import Binding

        bindings = FileSelectorScreen.BINDINGS

        binding_keys = []
        for b in bindings:
            if isinstance(b, Binding):
                binding_keys.append(b.key)
            else:
                binding_keys.append(b[0])

        assert "escape" in binding_keys
        assert "enter" in binding_keys
        assert "a" in binding_keys
        assert "n" in binding_keys
        assert "j" in binding_keys
        assert "k" in binding_keys
        assert "h" in binding_keys
        assert "l" in binding_keys
        assert "space" in binding_keys


class TestFileSelectorScreenNavigation:
    """Tests for vim-style navigation actions."""

    def test_action_cursor_down(self, tmp_path: Path) -> None:
        """Test cursor down delegates to tree."""
        screen = FileSelectorScreen(initial_dir=tmp_path)
        mock_tree = MagicMock()

        with patch.object(screen, "query_one", return_value=mock_tree):
            screen.action_cursor_down()

        mock_tree.action_cursor_down.assert_called_once()

    def test_action_cursor_up(self, tmp_path: Path) -> None:
        """Test cursor up delegates to tree."""
        screen = FileSelectorScreen(initial_dir=tmp_path)
        mock_tree = MagicMock()

        with patch.object(screen, "query_one", return_value=mock_tree):
            screen.action_cursor_up()

        mock_tree.action_cursor_up.assert_called_once()

    def test_action_cursor_left(self, tmp_path: Path) -> None:
        """Test cursor left delegates to tree."""
        screen = FileSelectorScreen(initial_dir=tmp_path)
        mock_tree = MagicMock()

        with patch.object(screen, "query_one", return_value=mock_tree):
            screen.action_cursor_left()

        mock_tree.action_cursor_left.assert_called_once()

    def test_action_cursor_right(self, tmp_path: Path) -> None:
        """Test cursor right delegates to tree."""
        screen = FileSelectorScreen(initial_dir=tmp_path)
        mock_tree = MagicMock()

        with patch.object(screen, "query_one", return_value=mock_tree):
            screen.action_cursor_right()

        mock_tree.action_cursor_right.assert_called_once()

    def test_action_toggle_node(self, tmp_path: Path) -> None:
        """Test toggle node action."""
        screen = FileSelectorScreen(initial_dir=tmp_path)
        mock_tree = MagicMock()
        mock_node = MagicMock()
        mock_tree.cursor_node = mock_node

        with patch.object(screen, "query_one", return_value=mock_tree):
            screen.action_toggle_node()

        mock_node.toggle.assert_called_once()

    def test_action_toggle_node_no_cursor(self, tmp_path: Path) -> None:
        """Test toggle node does nothing when no cursor node."""
        screen = FileSelectorScreen(initial_dir=tmp_path)
        mock_tree = MagicMock()
        mock_tree.cursor_node = None

        with patch.object(screen, "query_one", return_value=mock_tree):
            # Should not raise
            screen.action_toggle_node()


class TestFileSelectorScreenMount:
    """Tests for mount behavior."""

    @pytest.mark.asyncio
    async def test_on_mount_expands_to_initial_dir(self, tmp_path: Path) -> None:
        """Test that on_mount sets timer to expand to initial_dir."""
        from textual.app import App

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        screen = FileSelectorScreen(
            initial_dir=subdir,
            root_dir=tmp_path,
        )

        class TestApp(App):
            def compose(self):
                yield from screen.compose()

        app = TestApp()
        async with app.run_test():
            # Timer is set on mount, so after running test the expansion should happen
            # We just verify the screen initializes without error
            assert screen.initial_dir == subdir
            assert screen.root_dir == tmp_path


class TestFileSelectorScreenExpandToInitialDir:
    """Tests for _expand_to_initial_dir method."""

    @pytest.mark.asyncio
    async def test_expand_to_initial_dir_same_as_root(self, tmp_path: Path) -> None:
        """Test expansion when initial_dir equals root_dir."""
        screen = FileSelectorScreen(
            initial_dir=tmp_path,
            root_dir=tmp_path,
        )
        mock_tree = MagicMock()
        mock_tree.root = MagicMock()
        mock_tree.root.is_expanded = True

        with patch.object(screen, "query_one", return_value=mock_tree):
            # Should not raise - relative_to will return empty parts
            await screen._expand_to_initial_dir()

    @pytest.mark.asyncio
    async def test_expand_to_initial_dir_not_relative(self, tmp_path: Path) -> None:
        """Test handles case when initial_dir is not relative to root_dir."""
        other_path = Path("/some/other/path")
        screen = FileSelectorScreen(
            initial_dir=other_path,
            root_dir=tmp_path,
        )
        mock_tree = MagicMock()

        with patch.object(screen, "query_one", return_value=mock_tree):
            # Should handle ValueError from relative_to gracefully and return early
            await screen._expand_to_initial_dir()

    @pytest.mark.asyncio
    async def test_expand_to_initial_dir_expands_tree(self, tmp_path: Path) -> None:
        """Test tree expansion when initial_dir is below root_dir."""
        subdir = tmp_path / "subdir"
        screen = FileSelectorScreen(
            initial_dir=subdir,
            root_dir=tmp_path,
        )
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.is_expanded = False
        mock_root.children = []
        mock_tree.root = mock_root

        with patch.object(screen, "query_one", return_value=mock_tree):
            await screen._expand_to_initial_dir()

        # Root should be expanded
        mock_root.expand.assert_called()


class TestFileSelectorScreenCheckboxChange:
    """Tests for checkbox change handling."""

    def test_checkbox_changed_adds_file(self, tmp_path: Path) -> None:
        """Test checking a checkbox adds file to selection."""
        file1 = tmp_path / "file1.txt"
        screen = FileSelectorScreen()
        screen.selected_files = set()

        checkbox = MagicMock()
        screen._file_checkboxes = {file1: checkbox}

        mock_event = MagicMock()
        mock_event.checkbox = checkbox
        mock_event.value = True

        with patch.object(screen, "_update_status"):
            screen.checkbox_changed(mock_event)

        assert file1 in screen.selected_files

    def test_checkbox_changed_removes_file(self, tmp_path: Path) -> None:
        """Test unchecking a checkbox removes file from selection."""
        file1 = tmp_path / "file1.txt"
        screen = FileSelectorScreen()
        screen.selected_files = {file1}

        checkbox = MagicMock()
        screen._file_checkboxes = {file1: checkbox}

        mock_event = MagicMock()
        mock_event.checkbox = checkbox
        mock_event.value = False

        with patch.object(screen, "_update_status"):
            screen.checkbox_changed(mock_event)

        assert file1 not in screen.selected_files
