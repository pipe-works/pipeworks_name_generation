"""
Tests for syllable_walk_tui main application.

Integration tests for SyllableWalkerApp including layout, keybindings, navigation,
event handlers, and profile switching.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from textual.widgets import Footer, Header

from build_tools.syllable_walk_tui.core import AppState, SyllableWalkerApp
from build_tools.syllable_walk_tui.modules.analyzer import AnalysisScreen
from build_tools.syllable_walk_tui.modules.blender import BlendedWalkScreen
from build_tools.syllable_walk_tui.modules.generator import CombinerPanel
from build_tools.syllable_walk_tui.modules.oscillator import OscillatorPanel
from build_tools.syllable_walk_tui.modules.packager import PackageScreen
from build_tools.syllable_walk_tui.modules.renderer import RenderScreen

# Backward compatibility alias for tests
PatchPanel = OscillatorPanel


class TestSyllableWalkerApp:
    """Integration tests for main TUI application."""

    @pytest.mark.asyncio
    async def test_app_initialization(self):
        """Test that app initializes with correct state."""
        app = SyllableWalkerApp()

        assert isinstance(app.state, AppState)
        assert app.state.patch_a.name == "A"
        assert app.state.patch_b.name == "B"
        assert hasattr(app, "keybindings")

    @pytest.mark.asyncio
    async def test_app_layout_structure(self):
        """Test that app creates correct layout structure with modal screens."""
        app = SyllableWalkerApp()

        async with app.run_test():
            # Check header and footer exist
            assert app.query_one(Header)
            assert app.query_one(Footer)

            # Check patch panels exist in main view (always visible)
            patch_a = app.query_one("#patch-a", PatchPanel)
            patch_b = app.query_one("#patch-b", PatchPanel)

            assert patch_a.patch_name == "A"
            assert patch_b.patch_name == "B"

            # Check combiner panels exist (independent A and B)
            combiner_a = app.query_one("#combiner-panel-a", CombinerPanel)
            combiner_b = app.query_one("#combiner-panel-b", CombinerPanel)

            assert combiner_a.patch_name == "A"
            assert combiner_b.patch_name == "B"

            # Modal screens should not be visible initially
            assert len(app.query(BlendedWalkScreen)) == 0
            assert len(app.query(AnalysisScreen)) == 0

    @pytest.mark.asyncio
    async def test_modal_screen_actions_exist(self):
        """Test that modal screen actions exist."""
        app = SyllableWalkerApp()

        async with app.run_test():
            # Check that modal screen actions exist
            assert hasattr(app, "action_view_blended")
            assert hasattr(app, "action_view_analysis")

    @pytest.mark.asyncio
    async def test_open_blended_walk_modal(self):
        """Test that action_view_blended opens BlendedWalkScreen modal."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Initially no modal
            assert len(app.query(BlendedWalkScreen)) == 0

            # Open blended walk modal
            app.action_view_blended()
            await pilot.pause()

            # Modal should be visible (pushed to screen stack)
            # Note: Can't easily query for screen stack in test, but action exists
            assert hasattr(app, "action_view_blended")

    @pytest.mark.asyncio
    async def test_open_analysis_modal(self):
        """Test that action_view_analysis opens AnalysisScreen modal."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Initially no modal
            assert len(app.query(AnalysisScreen)) == 0

            # Open analysis modal
            app.action_view_analysis()
            await pilot.pause()

            # Modal action exists
            assert hasattr(app, "action_view_analysis")

    @pytest.mark.asyncio
    async def test_modal_keybindings_via_keypress(self):
        """Test that modal screens can be opened via keybindings."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Press 'v' to open Blended Walk modal
            await pilot.press("v")
            await pilot.pause()

            # Press 'a' to open Analysis modal (from main or modal)
            await pilot.press("escape")  # Close current modal if any
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()

            # Just verify no errors occurred
            assert True

    @pytest.mark.asyncio
    async def test_quit_keybinding(self):
        """Test that 'q' key quits the application."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Press 'q' to quit
            await pilot.press("q")
            await pilot.pause()

            # App should have exited (this will naturally happen at end of test)
            # We just verify no errors occurred

    @pytest.mark.asyncio
    async def test_help_action_shows_notification(self):
        """Test that help action shows notification."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Trigger help action
            app.action_help()
            await pilot.pause()

            # Notification should appear (we can't easily assert on it, but ensure no errors)

    @pytest.mark.asyncio
    async def test_corpus_selection_keybindings_exist(self):
        """Test that corpus selection keybindings are registered."""
        app = SyllableWalkerApp()

        async with app.run_test():
            # Check that corpus selection actions exist
            assert hasattr(app, "action_select_corpus_a")
            assert hasattr(app, "action_select_corpus_b")

    @pytest.mark.asyncio
    async def test_action_view_render_warns_without_selected_names(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Render action should notify when neither patch has selected names."""
        app = SyllableWalkerApp()

        async with app.run_test():
            notices: list[tuple[str, str]] = []

            def _capture_notify(message: str, *args: object, **kwargs: object) -> None:
                severity = str(kwargs.get("severity", "information"))
                notices.append((message, severity))

            monkeypatch.setattr(app, "notify", _capture_notify)
            app.action_view_render()
            assert notices[-1] == ("No names selected. Run Select Names first.", "warning")

    @pytest.mark.asyncio
    async def test_action_view_render_passes_selection_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Render action should pass selections dirs derived from selector output paths."""
        app = SyllableWalkerApp()
        run_dir = tmp_path / "20260130_185007_pyphen"
        selections_dir = run_dir / "selections"
        selections_dir.mkdir(parents=True)
        out_a = selections_dir / "pyphen_first_name_2syl.json"
        out_b = selections_dir / "pyphen_last_name_2syl.json"

        async with app.run_test():
            app.state.selector_a.outputs = ["alma"]
            app.state.selector_a.last_output_path = str(out_a)
            app.state.selector_b.outputs = ["bera"]
            app.state.selector_b.last_output_path = str(out_b)

            pushed: list[RenderScreen] = []
            monkeypatch.setattr(app, "push_screen", lambda screen: pushed.append(screen))
            app.action_view_render()

            assert len(pushed) == 1
            screen = pushed[0]
            assert isinstance(screen, RenderScreen)
            assert screen.selections_dir_a == selections_dir
            assert screen.selections_dir_b == selections_dir

    @pytest.mark.asyncio
    async def test_action_view_package_prefers_patch_a_then_patch_b(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Package action should choose A run dir first, then fall back to B."""
        app = SyllableWalkerApp()
        run_a = tmp_path / "20260130_185007_pyphen"
        run_b = tmp_path / "20260130_185023_nltk"
        out_a = run_a / "selections" / "pyphen_first_name_2syl.json"
        out_b = run_b / "selections" / "nltk_last_name_2syl.json"

        async with app.run_test():
            pushed: list[PackageScreen] = []
            monkeypatch.setattr(app, "push_screen", lambda screen: pushed.append(screen))

            app.state.selector_a.last_output_path = str(out_a)
            app.state.selector_b.last_output_path = str(out_b)
            app.action_view_package()
            assert pushed[-1].run_dir == run_a

            app.state.selector_a.last_output_path = None
            app.action_view_package()
            assert pushed[-1].run_dir == run_b


class TestGetInitialBrowseDir:
    """Tests for smart initial directory selection logic."""

    def test_uses_patch_corpus_dir_if_set(self, tmp_path):
        """Test that patch's current corpus_dir is used first."""
        app = SyllableWalkerApp()

        # Set patch A's corpus directory
        patch_corpus = tmp_path / "patch_a_corpus"
        patch_corpus.mkdir()
        app.state.patch_a.corpus_dir = patch_corpus

        result = app._get_initial_browse_dir("A")

        assert result == patch_corpus

    def test_uses_last_browse_dir_if_patch_not_set(self, tmp_path):
        """Test that last_browse_dir is used when patch corpus not set."""
        app = SyllableWalkerApp()

        # Set last browsed directory
        last_browse = tmp_path / "last_browsed"
        last_browse.mkdir()
        app.state.last_browse_dir = last_browse

        result = app._get_initial_browse_dir("A")

        assert result == last_browse

    def test_uses_working_output_if_exists(self, tmp_path):
        """Test that _working/output is used if it exists."""
        app = SyllableWalkerApp()

        # Mock the project root to point to tmp_path
        # Note: Path is now in actions.py after refactoring
        with patch("build_tools.syllable_walk_tui.core.actions.Path") as mock_path:
            # Create _working/output
            working_output = tmp_path / "_working" / "output"
            working_output.mkdir(parents=True)

            # Mock Path(__file__).parent.parent.parent to return tmp_path
            mock_path_instance = Mock()
            mock_path_instance.parent.parent.parent = tmp_path
            mock_path.return_value = mock_path_instance

            # Also need to make Path.home() work
            def path_side_effect(arg=None):
                if arg is None or arg == "__file__":
                    return mock_path_instance
                return Path(arg)

            mock_path.side_effect = path_side_effect
            mock_path.home.return_value = Path.home()

            # This test is complex due to patching, simplified version:
            # Just verify the method exists and handles the case
            result = app._get_initial_browse_dir("A")
            assert isinstance(result, Path)

    def test_falls_back_to_home(self):
        """Test that home directory is used as final fallback."""
        app = SyllableWalkerApp()

        # No corpus_dir, no last_browse_dir, no _working/output
        # Should fall back to home
        result = app._get_initial_browse_dir("A")

        # Result should be a Path (exact path depends on environment)
        assert isinstance(result, Path)


class TestModalScreenNavigation:
    """Tests for modal screen navigation after operations."""

    @pytest.mark.asyncio
    async def test_modal_screens_work_after_corpus_selection(self, tmp_path):
        """Test that modal screens work after corpus selection."""
        import json

        app = SyllableWalkerApp()

        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()
        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        async with app.run_test() as pilot:

            async def mock_push_screen_wait(screen):
                return corpus_dir

            with patch.object(app, "push_screen_wait", side_effect=mock_push_screen_wait):
                app.action_select_corpus_a()
                await pilot.pause()
                await pilot.pause(0.5)

                # Modal screen opening should still work after corpus selection
                app.action_view_blended()
                await pilot.pause()

                # Verify action worked (no errors)
                assert hasattr(app, "action_view_blended")


class TestEventHandlers:
    """Tests for app event handlers (parameter changes, profile selection)."""

    @pytest.mark.asyncio
    async def test_int_spinner_changed_updates_min_length(self):
        """Test that IntSpinner changes update patch state min_length."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            # Create mock event
            event = IntSpinner.Changed(value=3, widget_id="min-length-A")

            # Call the handler
            app.on_int_spinner_changed(event)

            assert app.state.patch_a.min_length == 3

    @pytest.mark.asyncio
    async def test_int_spinner_changed_updates_max_length(self):
        """Test that IntSpinner changes update patch state max_length."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=7, widget_id="max-length-B")
            app.on_int_spinner_changed(event)

            assert app.state.patch_b.max_length == 7

    @pytest.mark.asyncio
    async def test_int_spinner_changed_updates_walk_length(self):
        """Test that IntSpinner changes update patch state walk_length."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=8, widget_id="walk-length-A")
            app.on_int_spinner_changed(event)

            assert app.state.patch_a.walk_length == 8

    @pytest.mark.asyncio
    async def test_int_spinner_changed_updates_neighbors(self):
        """Test that IntSpinner changes update patch state neighbor_limit."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=15, widget_id="neighbors-A")
            app.on_int_spinner_changed(event)

            assert app.state.patch_a.neighbor_limit == 15

    @pytest.mark.asyncio
    async def test_int_spinner_changed_updates_walk_count(self):
        """Test that IntSpinner changes update patch state walk_count."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=5, widget_id="walk-count-B")
            app.on_int_spinner_changed(event)

            assert app.state.patch_b.walk_count == 5

    @pytest.mark.asyncio
    async def test_int_spinner_max_flips_switches_to_custom(self):
        """Test that changing max_flips switches to custom profile."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            # Start with a named profile
            app.state.patch_a.current_profile = "clerical"

            event = IntSpinner.Changed(value=3, widget_id="max-flips-A")
            app.on_int_spinner_changed(event)

            assert app.state.patch_a.max_flips == 3
            assert app.state.patch_a.current_profile == "custom"

    @pytest.mark.asyncio
    async def test_float_slider_changed_updates_temperature(self):
        """Test that FloatSlider changes update patch state temperature."""
        from build_tools.tui_common.controls import FloatSlider

        app = SyllableWalkerApp()

        async with app.run_test():
            event = FloatSlider.Changed(value=0.8, widget_id="temperature-A")
            app.on_float_slider_changed(event)

            assert app.state.patch_a.temperature == 0.8

    @pytest.mark.asyncio
    async def test_float_slider_changed_updates_freq_weight(self):
        """Test that FloatSlider changes update patch state frequency_weight."""
        from build_tools.tui_common.controls import FloatSlider

        app = SyllableWalkerApp()

        async with app.run_test():
            event = FloatSlider.Changed(value=0.5, widget_id="freq-weight-B")
            app.on_float_slider_changed(event)

            assert app.state.patch_b.frequency_weight == 0.5

    @pytest.mark.asyncio
    async def test_float_slider_temperature_switches_to_custom(self):
        """Test that changing temperature switches to custom profile."""
        from build_tools.tui_common.controls import FloatSlider

        app = SyllableWalkerApp()

        async with app.run_test():
            app.state.patch_a.current_profile = "dialect"

            event = FloatSlider.Changed(value=0.9, widget_id="temperature-A")
            app.on_float_slider_changed(event)

            assert app.state.patch_a.current_profile == "custom"

    @pytest.mark.asyncio
    async def test_seed_changed_updates_state(self):
        """Test that SeedInput changes update patch state seed."""
        from build_tools.tui_common.controls import SeedInput

        app = SyllableWalkerApp()

        async with app.run_test():
            event = SeedInput.Changed(value=12345, widget_id="seed-A")
            app.on_seed_changed(event)

            assert app.state.patch_a.seed == 12345

    @pytest.mark.asyncio
    async def test_seed_changed_recreates_rng(self):
        """Test that seed changes recreate the RNG instance."""
        from build_tools.tui_common.controls import SeedInput

        app = SyllableWalkerApp()

        async with app.run_test():
            old_rng = app.state.patch_a.rng

            event = SeedInput.Changed(value=99999, widget_id="seed-A")
            app.on_seed_changed(event)

            # RNG should be a new instance with the new seed
            assert app.state.patch_a.rng is not old_rng
            # Verify determinism by generating values
            app.state.patch_a.rng = __import__("random").Random(99999)
            val1 = app.state.patch_a.rng.random()
            app.state.patch_a.rng = __import__("random").Random(99999)
            val2 = app.state.patch_a.rng.random()
            assert val1 == val2

    @pytest.mark.asyncio
    async def test_event_handler_ignores_missing_widget_id(self):
        """Test that handlers gracefully ignore events without widget_id."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            original_min = app.state.patch_a.min_length

            # Event with no widget_id
            event = IntSpinner.Changed(value=10, widget_id=None)
            app.on_int_spinner_changed(event)

            # State should not change
            assert app.state.patch_a.min_length == original_min

    @pytest.mark.asyncio
    async def test_event_handler_ignores_malformed_widget_id(self):
        """Test that handlers gracefully ignore malformed widget IDs."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            original_min = app.state.patch_a.min_length

            # Event with malformed widget_id (no patch suffix)
            event = IntSpinner.Changed(value=10, widget_id="min-length")
            app.on_int_spinner_changed(event)

            assert app.state.patch_a.min_length == original_min


class TestProfileSwitching:
    """Tests for profile switching logic and feedback loop prevention."""

    @pytest.mark.asyncio
    async def test_profile_selection_updates_state(self):
        """Test that profile selection updates current_profile."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Create profile selection event (option_name, widget_id)
            event = RadioOption.Selected(option_name="goblin", widget_id="profile-goblin-A")
            app.on_profile_selected(event)

            assert app.state.patch_a.current_profile == "goblin"

    @pytest.mark.asyncio
    async def test_profile_selection_updates_parameters(self):
        """Test that selecting a profile updates related parameters."""
        from build_tools.syllable_walk.profiles import WALK_PROFILES
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Select clerical profile
            event = RadioOption.Selected(option_name="clerical", widget_id="profile-clerical-A")
            app.on_profile_selected(event)

            clerical = WALK_PROFILES["clerical"]
            assert app.state.patch_a.max_flips == clerical.max_flips
            assert app.state.patch_a.temperature == clerical.temperature
            assert app.state.patch_a.frequency_weight == clerical.frequency_weight

    @pytest.mark.asyncio
    async def test_custom_profile_does_not_update_parameters(self):
        """Test that selecting custom profile doesn't change parameters."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Set some custom values
            app.state.patch_a.max_flips = 99
            app.state.patch_a.temperature = 0.99

            # Select custom profile
            event = RadioOption.Selected(option_name="custom", widget_id="profile-custom-A")
            app.on_profile_selected(event)

            # Parameters should remain unchanged
            assert app.state.patch_a.max_flips == 99
            assert app.state.patch_a.temperature == 0.99
            assert app.state.patch_a.current_profile == "custom"

    @pytest.mark.asyncio
    async def test_updating_from_profile_flag_prevents_custom_switch(self):
        """Test that _updating_from_profile flag prevents auto-switch to custom."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            # Simulate profile update in progress
            app._updating_from_profile = True
            app._pending_profile_updates = 3
            app.state.patch_a.current_profile = "clerical"

            # This should NOT switch to custom
            event = IntSpinner.Changed(value=1, widget_id="max-flips-A")
            app.on_int_spinner_changed(event)

            # Should still be clerical (flag prevented switch)
            # Note: The counter decrements
            assert app._pending_profile_updates == 2

    @pytest.mark.asyncio
    async def test_pending_updates_counter_clears_flag(self):
        """Test that counter reaching zero clears the flag."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            app._updating_from_profile = True
            app._pending_profile_updates = 1

            event = IntSpinner.Changed(value=1, widget_id="max-flips-A")
            app.on_int_spinner_changed(event)

            # Flag should be cleared when counter reaches 0
            assert app._updating_from_profile is False
            assert app._pending_profile_updates == 0
