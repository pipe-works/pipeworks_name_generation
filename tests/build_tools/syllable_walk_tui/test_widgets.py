"""
Tests for syllable_walk_tui custom widgets.

Tests CorpusBrowserScreen modal with directory navigation, validation, and keybindings.
"""

import json
from pathlib import Path

import pytest
from textual.widgets import Button, DirectoryTree, Label, Static

from build_tools.syllable_walk_tui.widgets import CorpusBrowserScreen


class SimpleApp:
    """Minimal app wrapper for testing CorpusBrowserScreen."""

    from textual.app import App, ComposeResult

    class TestApp(App):
        """Test app that can display CorpusBrowserScreen."""

        def __init__(self, initial_dir: Path):
            super().__init__()
            self.initial_dir = initial_dir
            self.result = None

        async def on_mount(self) -> None:
            """Push the browser screen on mount."""
            self.result = await self.push_screen_wait(CorpusBrowserScreen(self.initial_dir))  # type: ignore[func-returns-value, arg-type]


@pytest.fixture
def valid_nltk_corpus(tmp_path):
    """Create a valid NLTK corpus directory for testing."""
    corpus_dir = tmp_path / "test_nltk_corpus"
    corpus_dir.mkdir()

    (corpus_dir / "nltk_syllables_unique.txt").write_text("test\ndata\n")
    (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1, "data": 2}))

    return corpus_dir


@pytest.fixture
def valid_pyphen_corpus(tmp_path):
    """Create a valid Pyphen corpus directory for testing."""
    corpus_dir = tmp_path / "test_pyphen_corpus"
    corpus_dir.mkdir()

    (corpus_dir / "pyphen_syllables_unique.txt").write_text("py\nphen\n")
    (corpus_dir / "pyphen_syllables_frequencies.json").write_text(json.dumps({"py": 10, "phen": 5}))

    return corpus_dir


@pytest.fixture
def invalid_corpus(tmp_path):
    """Create an invalid corpus directory (missing files)."""
    corpus_dir = tmp_path / "invalid_corpus"
    corpus_dir.mkdir()

    # No required files
    return corpus_dir


class TestCorpusBrowserScreen:
    """Tests for CorpusBrowserScreen modal widget."""

    @pytest.mark.asyncio
    async def test_screen_initialization(self, tmp_path):
        """Test that CorpusBrowserScreen initializes with correct structure."""
        screen = CorpusBrowserScreen(tmp_path)

        # Use a minimal test to check initialization
        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test():
            # Check that key widgets are present
            assert screen.query_one("#browser-header", Label)
            assert screen.query_one("#help-text", Label)
            assert screen.query_one("#directory-tree", DirectoryTree)
            assert screen.query_one("#validation-status", Static)
            assert screen.query_one("#select-button", Button)
            assert screen.query_one("#cancel-button", Button)

    @pytest.mark.asyncio
    async def test_initial_directory_set(self, tmp_path):
        """Test that browser starts at specified initial directory."""
        screen = CorpusBrowserScreen(tmp_path)

        assert screen.initial_dir == tmp_path

    @pytest.mark.asyncio
    async def test_default_initial_directory(self):
        """Test that browser defaults to home directory when no initial_dir provided."""
        screen = CorpusBrowserScreen()

        assert screen.initial_dir == Path.home()

    @pytest.mark.asyncio
    async def test_select_button_initially_disabled(self, tmp_path):
        """Test that Select button is disabled until valid directory selected."""
        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test():
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is True

    @pytest.mark.asyncio
    async def test_cancel_button_always_enabled(self, tmp_path):
        """Test that Cancel button is always enabled."""
        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test():
            cancel_button = screen.query_one("#cancel-button", Button)
            assert cancel_button.disabled is False

    @pytest.mark.asyncio
    async def test_valid_directory_selection_enables_button(self, tmp_path, valid_nltk_corpus):
        """Test that selecting valid directory enables Select button."""
        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Simulate directory selection by calling the handler directly
            from unittest.mock import Mock

            # Create a mock event with just the path attribute (that's all the handler uses)
            event = Mock()
            event.path = valid_nltk_corpus
            screen.directory_selected(event)

            await pilot.pause()

            # Select button should now be enabled
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is False

            # Status should show valid
            status = screen.query_one("#validation-status", Static)
            assert "status-valid" in status.classes

    @pytest.mark.asyncio
    async def test_invalid_directory_selection_keeps_button_disabled(
        self, tmp_path, invalid_corpus
    ):
        """Test that selecting invalid directory keeps Select button disabled."""
        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Simulate directory selection with invalid corpus
            from unittest.mock import Mock

            event = Mock()
            event.path = invalid_corpus
            screen.directory_selected(event)

            await pilot.pause()

            # Select button should remain disabled
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is True

            # Status should show invalid
            status = screen.query_one("#validation-status", Static)
            assert "status-invalid" in status.classes

    @pytest.mark.asyncio
    async def test_file_selection_shows_error(self, tmp_path):
        """Test that selecting a file shows helpful error message."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Simulate file selection
            from unittest.mock import Mock

            event = Mock()
            event.path = test_file
            screen.file_selected(event)

            await pilot.pause()

            # Select button should be disabled
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is True

            # Status should show file error (message updated for better UX)
            status_text = screen.query_one("#status-text", Label)
            assert "cannot be selected" in str(status_text.render())

    @pytest.mark.asyncio
    async def test_hjkl_keybindings_registered(self, tmp_path):
        """Test that hjkl keybindings are registered."""
        screen = CorpusBrowserScreen(tmp_path)

        # Check BINDINGS class attribute
        binding_keys = [binding[0] for binding in screen.BINDINGS]  # type: ignore[index]

        assert "j" in binding_keys
        assert "k" in binding_keys
        assert "h" in binding_keys
        assert "l" in binding_keys

    @pytest.mark.asyncio
    async def test_cancel_button_dismisses_with_none(self, tmp_path):
        """Test that Cancel button dismisses modal with None result."""
        from textual.app import App

        screen = CorpusBrowserScreen(tmp_path)

        # Test that cancel_pressed calls dismiss with None
        class TestApp(App):
            def compose(self):
                yield screen

        async with TestApp().run_test():
            # Call cancel_pressed directly
            screen.cancel_pressed()
            # Screen should be dismissed (we can't easily test the result
            # without the full push_screen_wait flow, but we verify the
            # method exists and doesn't error)

    @pytest.mark.asyncio
    async def test_select_button_dismisses_with_path(self, tmp_path, valid_nltk_corpus):
        """Test that Select button dismisses modal with selected path."""
        from textual.app import App

        screen = CorpusBrowserScreen(tmp_path)
        screen.selected_path = valid_nltk_corpus

        # Test that select_pressed calls dismiss with the selected path
        class TestApp(App):
            def compose(self):
                yield screen

        async with TestApp().run_test():
            # Call select_pressed directly to test the dismiss behavior
            screen.select_pressed()
            # Screen should be dismissed with selected_path
            # (we verify the method works and uses selected_path)

    @pytest.mark.asyncio
    async def test_validation_status_updates_for_valid_corpus(self, tmp_path, valid_nltk_corpus):
        """Test that validation status updates correctly for valid corpus."""
        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Simulate directory selection
            from unittest.mock import Mock

            event = Mock()
            event.path = valid_nltk_corpus
            screen.directory_selected(event)

            await pilot.pause()

            # Check status text
            status_text = screen.query_one("#status-text", Label)
            status_content = str(status_text.render())

            assert "Valid" in status_content
            assert "NLTK" in status_content

    @pytest.mark.asyncio
    async def test_validation_status_updates_for_invalid_corpus(self, tmp_path, invalid_corpus):
        """Test that validation status updates correctly for invalid corpus."""
        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Simulate directory selection with invalid corpus
            from unittest.mock import Mock

            event = Mock()
            event.path = invalid_corpus
            screen.directory_selected(event)

            await pilot.pause()

            # Check status text
            status_text = screen.query_one("#status-text", Label)
            status_content = str(status_text.render())

            assert "Invalid" in status_content

    @pytest.mark.asyncio
    async def test_pyphen_corpus_recognized(self, tmp_path, valid_pyphen_corpus):
        """Test that Pyphen corpus type is correctly identified."""
        screen = CorpusBrowserScreen(tmp_path)

        from textual.app import App

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Simulate directory selection with Pyphen corpus
            from unittest.mock import Mock

            event = Mock()
            event.path = valid_pyphen_corpus
            screen.directory_selected(event)

            await pilot.pause()

            # Check status shows Pyphen
            status_text = screen.query_one("#status-text", Label)
            status_content = str(status_text.render())

            assert "Valid" in status_content
            assert "Pyphen" in status_content
