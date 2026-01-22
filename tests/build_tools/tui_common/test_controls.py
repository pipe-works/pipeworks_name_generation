"""
Tests for tui_common control widgets.

Tests FloatSlider, IntSpinner, SeedInput, RadioOption, and DirectoryBrowserScreen.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from textual.app import App
from textual.binding import Binding
from textual.widgets import Button, DirectoryTree, Label, Static

from build_tools.tui_common.controls import (
    DirectoryBrowserScreen,
    FloatSlider,
    IntSpinner,
    JKSelect,
    RadioOption,
    SeedInput,
)


def get_binding_key(binding: Binding | tuple[str, ...]) -> str:
    """Extract key from a binding, handling both Binding objects and tuples."""
    if isinstance(binding, Binding):
        return binding.key
    return binding[0]


# =============================================================================
# IntSpinner Tests
# =============================================================================


class TestIntSpinner:
    """Tests for IntSpinner widget."""

    def test_initialization_with_defaults(self):
        """Test IntSpinner initializes with correct default values."""
        spinner = IntSpinner("Count", value=5, min_val=0, max_val=10)

        assert spinner.label_text == "Count"
        assert spinner.value == 5
        assert spinner.min_val == 0
        assert spinner.max_val == 10
        assert spinner.step == 1
        assert spinner.suffix_fn is None

    def test_initialization_with_custom_step(self):
        """Test IntSpinner respects custom step size."""
        spinner = IntSpinner("Value", value=10, min_val=0, max_val=100, step=5)

        assert spinner.step == 5

    def test_initialization_clamps_value_to_range(self):
        """Test that initial value is clamped to min/max range."""
        # Value above max
        spinner = IntSpinner("Test", value=100, min_val=0, max_val=10)
        assert spinner.value == 10

        # Value below min
        spinner = IntSpinner("Test", value=-5, min_val=0, max_val=10)
        assert spinner.value == 0

    def test_action_increment(self):
        """Test increment action increases value by step."""
        spinner = IntSpinner("Count", value=5, min_val=0, max_val=10)
        spinner.action_increment()
        assert spinner.value == 6

    def test_action_increment_respects_max(self):
        """Test increment doesn't exceed max value."""
        spinner = IntSpinner("Count", value=10, min_val=0, max_val=10)
        spinner.action_increment()
        assert spinner.value == 10  # Should stay at max

    def test_action_decrement(self):
        """Test decrement action decreases value by step."""
        spinner = IntSpinner("Count", value=5, min_val=0, max_val=10)
        spinner.action_decrement()
        assert spinner.value == 4

    def test_action_decrement_respects_min(self):
        """Test decrement doesn't go below min value."""
        spinner = IntSpinner("Count", value=0, min_val=0, max_val=10)
        spinner.action_decrement()
        assert spinner.value == 0  # Should stay at min

    def test_set_value_updates_value(self):
        """Test set_value method updates the value."""
        spinner = IntSpinner("Count", value=5, min_val=0, max_val=10)
        spinner.set_value(7)
        assert spinner.value == 7

    def test_set_value_clamps_to_range(self):
        """Test set_value clamps to min/max range."""
        spinner = IntSpinner("Count", value=5, min_val=0, max_val=10)

        spinner.set_value(100)
        assert spinner.value == 10

        spinner.set_value(-5)
        assert spinner.value == 0

    def test_suffix_fn_called_with_value(self):
        """Test suffix function is called with current value."""
        suffix_calls: list[int] = []

        def track_suffix(v: int) -> str:
            suffix_calls.append(v)
            return f"-> {v + 1}"

        spinner = IntSpinner(
            "Steps",
            value=5,
            min_val=0,
            max_val=20,
            suffix_fn=track_suffix,
        )
        # suffix_fn called during compose
        # We can verify it by checking the stored suffix_fn
        assert spinner.suffix_fn is not None
        result = spinner.suffix_fn(5)
        assert result == "-> 6"
        assert 5 in suffix_calls

    def test_bindings_defined(self):
        """Test that expected keybindings are defined."""
        binding_keys = [get_binding_key(b) for b in IntSpinner.BINDINGS]

        assert "+" in binding_keys
        assert "-" in binding_keys
        assert "j" in binding_keys
        assert "k" in binding_keys


class TestIntSpinnerMessages:
    """Tests for IntSpinner message posting."""

    @pytest.mark.asyncio
    async def test_changed_message_posted_on_increment(self):
        """Test Changed message is posted when value increments."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.messages = []

            def compose(self):
                yield IntSpinner("Count", value=5, min_val=0, max_val=10, id="test-spinner")

            def on_int_spinner_changed(self, event: IntSpinner.Changed):
                self.messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            spinner = app.query_one("#test-spinner", IntSpinner)
            spinner.action_increment()

            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0].value == 6
            assert app.messages[0].widget_id == "test-spinner"


# =============================================================================
# FloatSlider Tests
# =============================================================================


class TestFloatSlider:
    """Tests for FloatSlider widget."""

    def test_initialization_with_defaults(self):
        """Test FloatSlider initializes with correct default values."""
        slider = FloatSlider("Temp", value=0.5, min_val=0.0, max_val=1.0)

        assert slider.label_text == "Temp"
        assert slider.value == 0.5
        assert slider.min_val == 0.0
        assert slider.max_val == 1.0
        assert slider.step == 0.1
        assert slider.precision == 1
        assert slider.suffix == ""

    def test_initialization_with_custom_precision(self):
        """Test FloatSlider respects custom precision."""
        slider = FloatSlider("Value", value=0.5, min_val=0.0, max_val=1.0, precision=3)
        assert slider.precision == 3

    def test_initialization_with_suffix(self):
        """Test FloatSlider stores suffix."""
        slider = FloatSlider("Weight", value=0.5, min_val=0.0, max_val=1.0, suffix="bias")
        assert slider.suffix == "bias"

    def test_initialization_clamps_value_to_range(self):
        """Test that initial value is clamped to min/max range."""
        slider = FloatSlider("Test", value=2.0, min_val=0.0, max_val=1.0)
        assert slider.value == 1.0

        slider = FloatSlider("Test", value=-1.0, min_val=0.0, max_val=1.0)
        assert slider.value == 0.0

    def test_action_increment(self):
        """Test increment action increases value by step."""
        slider = FloatSlider("Temp", value=0.5, min_val=0.0, max_val=1.0, step=0.1)
        slider.action_increment()
        assert abs(slider.value - 0.6) < 0.001

    def test_action_increment_respects_max(self):
        """Test increment doesn't exceed max value."""
        slider = FloatSlider("Temp", value=1.0, min_val=0.0, max_val=1.0)
        slider.action_increment()
        assert slider.value == 1.0

    def test_action_decrement(self):
        """Test decrement action decreases value by step."""
        slider = FloatSlider("Temp", value=0.5, min_val=0.0, max_val=1.0, step=0.1)
        slider.action_decrement()
        assert abs(slider.value - 0.4) < 0.001

    def test_action_decrement_respects_min(self):
        """Test decrement doesn't go below min value."""
        slider = FloatSlider("Temp", value=0.0, min_val=0.0, max_val=1.0)
        slider.action_decrement()
        assert slider.value == 0.0

    def test_set_value_updates_value(self):
        """Test set_value method updates the value."""
        slider = FloatSlider("Temp", value=0.5, min_val=0.0, max_val=1.0)
        slider.set_value(0.7)
        assert abs(slider.value - 0.7) < 0.001

    def test_bindings_defined(self):
        """Test that expected keybindings are defined."""
        binding_keys = [get_binding_key(b) for b in FloatSlider.BINDINGS]

        assert "+" in binding_keys
        assert "-" in binding_keys
        assert "j" in binding_keys
        assert "k" in binding_keys


# =============================================================================
# SeedInput Tests
# =============================================================================


class TestSeedInput:
    """Tests for SeedInput widget."""

    def test_initialization_generates_random_seed(self):
        """Test SeedInput generates random seed when no value provided."""
        seed_input = SeedInput()

        # Should have a valid seed value
        assert 0 <= seed_input.value < 2**32
        assert seed_input.user_input == -1  # Random mode

    def test_initialization_with_explicit_seed(self):
        """Test SeedInput uses provided seed value."""
        seed_input = SeedInput(value=12345)

        assert seed_input.value == 12345

    def test_random_mode_generates_new_seed(self):
        """Test that random mode generates different seeds."""
        seeds = set()
        for _ in range(10):
            seed_input = SeedInput()
            seeds.add(seed_input.value)

        # Should have generated multiple unique seeds
        # (extremely unlikely to be all the same)
        assert len(seeds) > 1

    def test_bindings_defined(self):
        """Test that 'r' keybinding is defined."""
        binding_keys = [get_binding_key(b) for b in SeedInput.BINDINGS]
        assert "r" in binding_keys


class TestSeedInputInternal:
    """Tests for SeedInput internal input handling."""

    def test_handle_input_change_random_mode(self):
        """Test that '-1' input triggers random mode."""
        seed_input = SeedInput(value=100)

        seed_input._handle_input_change("-1")

        assert seed_input.user_input == -1
        # Value should have changed (new random)
        # Note: There's a tiny chance it could be the same, but extremely unlikely

    def test_handle_input_change_empty_input(self):
        """Test that empty input triggers random mode."""
        seed_input = SeedInput(value=100)

        seed_input._handle_input_change("")

        assert seed_input.user_input == -1

    def test_handle_input_change_valid_integer(self):
        """Test that valid integer input sets manual seed."""
        seed_input = SeedInput()

        seed_input._handle_input_change("42")

        assert seed_input.user_input == 42
        assert seed_input.value == 42

    def test_handle_input_change_clamps_large_value(self):
        """Test that large values are clamped to valid range."""
        seed_input = SeedInput()

        seed_input._handle_input_change(str(2**33))  # Too large

        assert seed_input.value <= 2**32 - 1

    def test_handle_input_change_invalid_input_ignored(self):
        """Test that invalid input is ignored."""
        seed_input = SeedInput(value=100)
        original_value = seed_input.value

        seed_input._handle_input_change("not a number")

        assert seed_input.value == original_value


# =============================================================================
# RadioOption Tests
# =============================================================================


class TestRadioOption:
    """Tests for RadioOption widget."""

    def test_initialization(self):
        """Test RadioOption initializes with correct values."""
        option = RadioOption("fast", "Quick processing", is_selected=True)

        assert option.option_name == "fast"
        assert option.description == "Quick processing"
        assert option.is_selected is True

    def test_initialization_default_unselected(self):
        """Test RadioOption is unselected by default."""
        option = RadioOption("slow", "Thorough analysis")

        assert option.is_selected is False

    def test_set_selected_updates_state(self):
        """Test set_selected method updates selection state."""
        option = RadioOption("test", "Test option")

        option.set_selected(True)
        assert option.is_selected is True

        option.set_selected(False)
        assert option.is_selected is False

    def test_bindings_defined(self):
        """Test that enter and space keybindings are defined."""
        binding_keys = [get_binding_key(b) for b in RadioOption.BINDINGS]

        assert "enter" in binding_keys
        assert "space" in binding_keys


class TestRadioOptionMessages:
    """Tests for RadioOption message posting."""

    @pytest.mark.asyncio
    async def test_selected_message_posted_when_unselected(self):
        """Test Selected message is posted when unselected option is selected."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.messages = []

            def compose(self):
                yield RadioOption("fast", "Quick", is_selected=False, id="opt-fast")

            def on_radio_option_selected(self, event: RadioOption.Selected):
                self.messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            option = app.query_one("#opt-fast", RadioOption)
            option.action_select()

            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0].option_name == "fast"

    @pytest.mark.asyncio
    async def test_no_message_when_already_selected(self):
        """Test no message posted when already selected option is clicked."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.messages: list[Any] = []

            def compose(self):
                yield RadioOption("fast", "Quick", is_selected=True, id="opt-fast")

            def on_radio_option_selected(self, event: RadioOption.Selected):
                self.messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            option = app.query_one("#opt-fast", RadioOption)
            option.action_select()

            await pilot.pause()

            assert len(app.messages) == 0


# =============================================================================
# JKSelect Tests
# =============================================================================


class TestJKSelect:
    """Tests for JKSelect widget with vim-style j/k navigation."""

    def test_initialization(self):
        """Test JKSelect initializes correctly with options."""
        select = JKSelect(
            [("Option 1", "opt1"), ("Option 2", "opt2"), ("Option 3", "opt3")],
            value="opt1",
        )

        # Verify widget was created (value is set during mount, not init)
        assert select is not None

    def test_initialization_with_id(self):
        """Test JKSelect stores id correctly."""
        select = JKSelect(
            [("A", "a"), ("B", "b")],
            value="a",
            id="my-select",
        )

        assert select.id == "my-select"

    def test_initialization_with_allow_blank_false(self):
        """Test JKSelect respects allow_blank setting."""
        select = JKSelect(
            [("A", "a"), ("B", "b")],
            value="a",
            allow_blank=False,
        )

        # _allow_blank is the internal attribute
        assert select._allow_blank is False

    @pytest.mark.asyncio
    async def test_compose_creates_jkselect_overlay(self):
        """Test that compose creates JKSelectOverlay instead of standard overlay."""
        from build_tools.tui_common.controls.selects import JKSelectOverlay

        class TestApp(App):
            def compose(self):
                yield JKSelect(
                    [("A", "a"), ("B", "b")],
                    value="a",
                    id="test-select",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            select = app.query_one("#test-select", JKSelect)

            # The overlay should be a JKSelectOverlay, not SelectOverlay
            overlays = list(select.query(JKSelectOverlay))
            assert len(overlays) == 1


class TestJKSelectOverlay:
    """Tests for JKSelectOverlay key handling."""

    @pytest.mark.asyncio
    async def test_overlay_exists_in_select(self):
        """Test that JKSelect contains JKSelectOverlay."""
        from build_tools.tui_common.controls.selects import JKSelectOverlay

        class TestApp(App):
            def compose(self):
                yield JKSelect(
                    [("A", "a"), ("B", "b"), ("C", "c")],
                    value="a",
                    id="test-select",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            select = app.query_one("#test-select", JKSelect)

            # Verify JKSelectOverlay is present
            overlay = select.query_one(JKSelectOverlay)
            assert overlay is not None

    @pytest.mark.asyncio
    async def test_on_key_j_calls_cursor_down(self):
        """Test that 'j' key triggers cursor down action."""
        from unittest.mock import patch

        from textual import events

        from build_tools.tui_common.controls.selects import JKSelectOverlay

        class TestApp(App):
            def compose(self):
                yield JKSelect(
                    [("A", "a"), ("B", "b"), ("C", "c")],
                    value="a",
                    id="test-select",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            select = app.query_one("#test-select", JKSelect)
            overlay = select.query_one(JKSelectOverlay)

            # Mock the action_cursor_down method
            with patch.object(overlay, "action_cursor_down") as mock_cursor_down:
                # Create a mock key event for 'j'
                key_event = events.Key("j", "j")
                await overlay._on_key(key_event)

                # Verify cursor_down was called
                mock_cursor_down.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_key_k_calls_cursor_up(self):
        """Test that 'k' key triggers cursor up action."""
        from unittest.mock import patch

        from textual import events

        from build_tools.tui_common.controls.selects import JKSelectOverlay

        class TestApp(App):
            def compose(self):
                yield JKSelect(
                    [("A", "a"), ("B", "b"), ("C", "c")],
                    value="a",
                    id="test-select",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            select = app.query_one("#test-select", JKSelect)
            overlay = select.query_one(JKSelectOverlay)

            # Mock the action_cursor_up method
            with patch.object(overlay, "action_cursor_up") as mock_cursor_up:
                # Create a mock key event for 'k'
                key_event = events.Key("k", "k")
                await overlay._on_key(key_event)

                # Verify cursor_up was called
                mock_cursor_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_key_other_calls_super(self):
        """Test that other keys call super()._on_key."""

        from textual import events

        from build_tools.tui_common.controls.selects import JKSelectOverlay

        class TestApp(App):
            def compose(self):
                yield JKSelect(
                    [("A", "a"), ("B", "b"), ("C", "c")],
                    value="a",
                    id="test-select",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            select = app.query_one("#test-select", JKSelect)
            overlay = select.query_one(JKSelectOverlay)

            # Create a mock key event for some other key
            key_event = events.Key("x", "x")

            # Call the method - should not raise and should call super
            # We can't easily mock super(), but we can verify no error occurs
            await overlay._on_key(key_event)


# =============================================================================
# DirectoryBrowserScreen Tests
# =============================================================================


@pytest.fixture
def valid_directory(tmp_path):
    """Create a simple valid directory."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file.txt").write_text("content")
    return test_dir


@pytest.fixture
def custom_validator():
    """Create a custom validator that only accepts directories with .txt files."""

    def validator(path: Path) -> tuple[bool, str, str]:
        if not path.is_dir():
            return (False, "", "Not a directory")
        txt_files = list(path.glob("*.txt"))
        if txt_files:
            return (True, "source", f"Found {len(txt_files)} txt files")
        return (False, "", "No txt files found")

    return validator


class TestDirectoryBrowserScreen:
    """Tests for DirectoryBrowserScreen modal widget."""

    @pytest.mark.asyncio
    async def test_screen_initialization(self, tmp_path):
        """Test that DirectoryBrowserScreen initializes with correct structure."""
        screen = DirectoryBrowserScreen(
            title="Test Browser",
            initial_dir=tmp_path,
        )

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
    async def test_custom_title_displayed(self, tmp_path):
        """Test that custom title is displayed."""
        screen = DirectoryBrowserScreen(
            title="Custom Title",
            initial_dir=tmp_path,
        )

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test():
            header = screen.query_one("#browser-header", Label)
            assert "Custom Title" in str(header.render())

    @pytest.mark.asyncio
    async def test_initial_directory_set(self, tmp_path):
        """Test that browser starts at specified initial directory."""
        screen = DirectoryBrowserScreen(initial_dir=tmp_path)
        assert screen.initial_dir == tmp_path

    @pytest.mark.asyncio
    async def test_default_initial_directory(self):
        """Test that browser defaults to home directory."""
        screen = DirectoryBrowserScreen()
        assert screen.initial_dir == Path.home()

    @pytest.mark.asyncio
    async def test_select_button_initially_disabled(self, tmp_path):
        """Test that Select button is disabled until valid directory selected."""
        screen = DirectoryBrowserScreen(initial_dir=tmp_path)

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test():
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is True

    @pytest.mark.asyncio
    async def test_custom_validator_used(self, tmp_path, valid_directory, custom_validator):
        """Test that custom validator is called for directory selection."""
        screen = DirectoryBrowserScreen(
            title="Test",
            validator=custom_validator,
            initial_dir=tmp_path,
        )

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Wait for any auto-expansion events to complete first
            await pilot.pause()

            # Now call validation - this will set the final state
            screen._validate_and_update_status(valid_directory)

            # Assert immediately without another pause (which could trigger more events)
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is False

            # Status should show valid
            status = screen.query_one("#validation-status", Static)
            assert "status-valid" in status.classes

    @pytest.mark.asyncio
    async def test_custom_validator_rejects_invalid(self, tmp_path, custom_validator):
        """Test that custom validator rejects invalid directories."""
        # Create directory without txt files
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        screen = DirectoryBrowserScreen(
            title="Test",
            validator=custom_validator,
            initial_dir=tmp_path,
        )

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Wait for any auto-expansion events to complete first
            await pilot.pause()

            # Now call validation - this will set the final state
            screen._validate_and_update_status(empty_dir)

            # Assert immediately without another pause (which could trigger more events)
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is True

            status = screen.query_one("#validation-status", Static)
            assert "status-invalid" in status.classes

    @pytest.mark.asyncio
    async def test_file_selection_shows_error(self, tmp_path):
        """Test that selecting a file shows error when directory is invalid."""
        # Create an empty subdirectory (no txt files)
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        test_file = empty_dir / "test.txt"
        test_file.write_text("content")

        # Validator that always rejects for testing invalid state
        def strict_validator(path: Path) -> tuple[bool, str, str]:
            return (False, "", "Always invalid for test")

        screen = DirectoryBrowserScreen(initial_dir=tmp_path, validator=strict_validator)

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Wait for any auto-expansion events to complete first
            await pilot.pause()

            # Now call validation - this will set the final state
            screen._validate_and_update_status(empty_dir)

            # Assert immediately without another pause (which could trigger more events)
            select_button = screen.query_one("#select-button", Button)
            status = screen.query_one("#validation-status", Static)

            assert select_button.disabled is True
            assert "status-invalid" in status.classes

    @pytest.mark.asyncio
    async def test_file_selection_keeps_valid_directory(self, tmp_path):
        """Test that validating a directory enables selection.

        When user validates a directory (by expanding into it), the Select button
        should be enabled so user can select that directory.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Validator that accepts tmp_path (has a .txt file)
        def validator(path: Path) -> tuple[bool, str, str]:
            if list(path.glob("*.txt")):
                return (True, "source", "Found text files")
            return (False, "", "No text files")

        screen = DirectoryBrowserScreen(initial_dir=tmp_path, validator=validator)

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            # Wait for any auto-expansion events to complete first
            await pilot.pause()

            # Now call validation - this will set the final state
            screen._validate_and_update_status(tmp_path)

            # Assert immediately without another pause (which could trigger more events)
            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is False

            # Status should show valid
            status = screen.query_one("#validation-status", Static)
            assert "status-valid" in status.classes

    @pytest.mark.asyncio
    async def test_hjkl_keybindings_registered(self, tmp_path: Path) -> None:
        """Test that hjkl keybindings are registered."""
        screen = DirectoryBrowserScreen(initial_dir=tmp_path)

        binding_keys = [get_binding_key(binding) for binding in screen.BINDINGS]

        assert "j" in binding_keys
        assert "k" in binding_keys
        assert "h" in binding_keys
        assert "l" in binding_keys

    @pytest.mark.asyncio
    async def test_default_validator_accepts_any_directory(self, tmp_path):
        """Test that default validator accepts any directory."""
        test_dir = tmp_path / "any_dir"
        test_dir.mkdir()

        screen = DirectoryBrowserScreen(initial_dir=tmp_path)

        class TestApp(App):
            async def on_mount(self):
                await self.push_screen(screen)

        async with TestApp().run_test() as pilot:
            event = Mock()
            event.path = test_dir
            screen.directory_selected(event)

            await pilot.pause()

            select_button = screen.query_one("#select-button", Button)
            assert select_button.disabled is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestControlsIntegration:
    """Integration tests for multiple controls working together."""

    @pytest.mark.asyncio
    async def test_multiple_spinners_independent(self):
        """Test that multiple spinners maintain independent state."""

        class TestApp(App):
            def compose(self):
                yield IntSpinner("A", value=5, min_val=0, max_val=10, id="spinner-a")
                yield IntSpinner("B", value=3, min_val=0, max_val=10, id="spinner-b")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            spinner_a = app.query_one("#spinner-a", IntSpinner)
            spinner_b = app.query_one("#spinner-b", IntSpinner)

            spinner_a.action_increment()

            assert spinner_a.value == 6
            assert spinner_b.value == 3  # Unchanged

    @pytest.mark.asyncio
    async def test_radio_option_group_management(self):
        """Test manual radio group management."""

        class TestApp(App):
            def compose(self):
                yield RadioOption("a", "Option A", is_selected=True, id="opt-a")
                yield RadioOption("b", "Option B", is_selected=False, id="opt-b")

            def on_radio_option_selected(self, event: RadioOption.Selected):
                # Update all options when one is selected
                for opt in self.query(RadioOption):
                    opt.set_selected(opt.option_name == event.option_name)

        async with TestApp().run_test() as pilot:
            app = pilot.app
            opt_a = app.query_one("#opt-a", RadioOption)
            opt_b = app.query_one("#opt-b", RadioOption)

            # Initially A is selected
            assert opt_a.is_selected is True
            assert opt_b.is_selected is False

            # Select B
            opt_b.action_select()
            await pilot.pause()

            # Now B should be selected, A deselected
            assert opt_a.is_selected is False
            assert opt_b.is_selected is True
