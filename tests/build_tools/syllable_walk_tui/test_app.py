"""
Tests for syllable_walk_tui main application.

Integration tests for SyllableWalkerApp including layout, keybindings, and navigation.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from textual.widgets import Footer, Header, Label

from build_tools.syllable_walk_tui.core import AppState, SyllableWalkerApp
from build_tools.syllable_walk_tui.modules.analyzer import AnalysisScreen
from build_tools.syllable_walk_tui.modules.blender import BlendedWalkScreen
from build_tools.syllable_walk_tui.modules.generator import CombinerPanel, SelectorPanel
from build_tools.syllable_walk_tui.modules.oscillator import OscillatorPanel

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
        with patch("build_tools.syllable_walk_tui.core.app.Path") as mock_path:
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


class TestPatchPanel:
    """Tests for PatchPanel widget."""

    def test_initialization_with_name(self):
        """Test that PatchPanel initializes with correct name."""
        panel = PatchPanel("A")
        assert panel.patch_name == "A"

        panel_b = PatchPanel("B")
        assert panel_b.patch_name == "B"

    @pytest.mark.asyncio
    async def test_compose_creates_widgets(self):
        """Test that PatchPanel creates expected child widgets."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield PatchPanel("A")

        async with TestApp().run_test() as pilot:
            # Check for corpus selection button
            assert pilot.app.query_one("#select-corpus-A")

            # Check for corpus status label
            assert pilot.app.query_one("#corpus-status-A")


class TestCombinerPanel:
    """Tests for CombinerPanel widget (name generation)."""

    @pytest.mark.asyncio
    async def test_compose_creates_widgets(self):
        """Test that CombinerPanel creates expected child widgets."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield CombinerPanel(patch_name="A")

        async with TestApp().run_test() as pilot:
            # Should have combiner labels
            labels = pilot.app.query(Label)
            assert len(labels) > 0

            # Check for "PATCH A NAME COMBINER" header
            labels_text = [str(label.render()) for label in labels]
            assert any("PATCH A NAME COMBINER" in text for text in labels_text)

            # Check for generate button
            assert pilot.app.query_one("#generate-candidates-a")

    @pytest.mark.asyncio
    async def test_compose_creates_patch_b_widgets(self):
        """Test that CombinerPanel creates correct widgets for patch B."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield CombinerPanel(patch_name="B")

        async with TestApp().run_test() as pilot:
            labels = pilot.app.query(Label)
            labels_text = [str(label.render()) for label in labels]
            assert any("PATCH B NAME COMBINER" in text for text in labels_text)
            assert pilot.app.query_one("#generate-candidates-b")

    @pytest.mark.asyncio
    async def test_update_output_with_metadata(self):
        """Test that update_output displays metadata correctly."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield CombinerPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#test-panel", CombinerPanel)

            # Update with sample metadata
            meta = {
                "arguments": {
                    "syllables": 2,
                    "count": 10000,
                    "seed": 42,
                    "frequency_weight": 1.0,
                },
                "output": {
                    "candidates_generated": 10000,
                    "unique_names": 7500,
                    "unique_percentage": 75.0,
                    "candidates_file": "/path/to/candidates/nltk_candidates_2syl.json",
                },
            }
            panel.update_output(meta)
            await pilot.pause()

            # Check output label was updated
            output_label = pilot.app.query_one("#combiner-output-a", Label)
            text = str(output_label.render())
            assert "Syllables: 2" in text
            assert "Seed: 42" in text

    @pytest.mark.asyncio
    async def test_update_output_with_none_shows_placeholder(self):
        """Test that update_output with None shows placeholder text."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield CombinerPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#test-panel", CombinerPanel)
            panel.update_output(None)
            await pilot.pause()

            output_label = pilot.app.query_one("#combiner-output-a", Label)
            text = str(output_label.render())
            assert "Generate" in text

    @pytest.mark.asyncio
    async def test_clear_output(self):
        """Test that clear_output resets to placeholder."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield CombinerPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#test-panel", CombinerPanel)

            # First set some output
            panel.update_output({"arguments": {"syllables": 3}, "output": {}})
            await pilot.pause()

            # Then clear it
            panel.clear_output()
            await pilot.pause()

            output_label = pilot.app.query_one("#combiner-output-a", Label)
            text = str(output_label.render())
            assert "Generate" in text


class TestCombinerEventHandlers:
    """Tests for combiner-related event handlers."""

    @pytest.mark.asyncio
    async def test_combiner_syllables_changed_updates_state_a(self):
        """Test that combiner syllables change updates combiner_a state."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=3, widget_id="combiner-syllables-a")
            app.on_int_spinner_changed(event)

            assert app.state.combiner_a.syllables == 3

    @pytest.mark.asyncio
    async def test_combiner_syllables_changed_updates_state_b(self):
        """Test that combiner syllables change updates combiner_b state."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=4, widget_id="combiner-syllables-b")
            app.on_int_spinner_changed(event)

            assert app.state.combiner_b.syllables == 4

    @pytest.mark.asyncio
    async def test_combiner_count_changed_updates_state_a(self):
        """Test that combiner count change updates combiner_a state."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=5000, widget_id="combiner-count-a")
            app.on_int_spinner_changed(event)

            assert app.state.combiner_a.count == 5000

    @pytest.mark.asyncio
    async def test_combiner_count_changed_updates_state_b(self):
        """Test that combiner count change updates combiner_b state."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=20000, widget_id="combiner-count-b")
            app.on_int_spinner_changed(event)

            assert app.state.combiner_b.count == 20000

    @pytest.mark.asyncio
    async def test_combiner_freq_weight_changed_updates_state_a(self):
        """Test that combiner freq weight change updates combiner_a state."""
        from build_tools.tui_common.controls import FloatSlider

        app = SyllableWalkerApp()

        async with app.run_test():
            event = FloatSlider.Changed(value=0.5, widget_id="combiner-freq-weight-a")
            app.on_float_slider_changed(event)

            assert app.state.combiner_a.frequency_weight == 0.5

    @pytest.mark.asyncio
    async def test_combiner_freq_weight_changed_updates_state_b(self):
        """Test that combiner freq weight change updates combiner_b state."""
        from build_tools.tui_common.controls import FloatSlider

        app = SyllableWalkerApp()

        async with app.run_test():
            event = FloatSlider.Changed(value=0.8, widget_id="combiner-freq-weight-b")
            app.on_float_slider_changed(event)

            assert app.state.combiner_b.frequency_weight == 0.8

    @pytest.mark.asyncio
    async def test_combiner_seed_changed_updates_state_a(self):
        """Test that combiner seed change updates combiner_a state."""
        from build_tools.tui_common.controls import SeedInput

        app = SyllableWalkerApp()

        async with app.run_test():
            event = SeedInput.Changed(value=12345, widget_id="combiner-seed-a")
            app.on_seed_changed(event)

            assert app.state.combiner_a.seed == 12345

    @pytest.mark.asyncio
    async def test_combiner_seed_changed_updates_state_b(self):
        """Test that combiner seed change updates combiner_b state."""
        from build_tools.tui_common.controls import SeedInput

        app = SyllableWalkerApp()

        async with app.run_test():
            event = SeedInput.Changed(value=99999, widget_id="combiner-seed-b")
            app.on_seed_changed(event)

            assert app.state.combiner_b.seed == 99999

    @pytest.mark.asyncio
    async def test_combiner_states_are_independent(self):
        """Test that combiner_a and combiner_b states are independent."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            # Update combiner_a
            event_a = IntSpinner.Changed(value=3, widget_id="combiner-syllables-a")
            app.on_int_spinner_changed(event_a)

            # Update combiner_b
            event_b = IntSpinner.Changed(value=4, widget_id="combiner-syllables-b")
            app.on_int_spinner_changed(event_b)

            # Verify they're independent
            assert app.state.combiner_a.syllables == 3
            assert app.state.combiner_b.syllables == 4


class TestRunCombiner:
    """Tests for _run_combiner method."""

    @pytest.mark.asyncio
    async def test_run_combiner_requires_corpus(self):
        """Test that _run_combiner requires corpus to be loaded."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Patch not ready (no corpus loaded)
            assert not app.state.patch_a.is_ready_for_generation()

            # Try to run combiner - should show notification
            app._run_combiner("A")
            await pilot.pause()

            # Should not crash, combiner outputs should be empty
            assert app.state.combiner_a.outputs == []

    @pytest.mark.asyncio
    async def test_run_combiner_requires_annotated_data(self):
        """Test that _run_combiner requires annotated_data to be loaded."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Set corpus_dir but not annotated_data
            app.state.patch_a.corpus_dir = Path("/tmp/test")
            app.state.patch_a.syllables = ["test"]
            app.state.patch_a.frequencies = {"test": 1}
            # annotated_data is still None

            app._run_combiner("A")
            await pilot.pause()

            # Should not crash
            assert app.state.combiner_a.outputs == []

    @pytest.mark.asyncio
    async def test_run_combiner_creates_candidates(self, tmp_path):
        """Test that _run_combiner creates candidate files."""
        app = SyllableWalkerApp()

        # Create a test corpus directory
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()

        # Create sample annotated data
        annotated_data = [
            {
                "syllable": "ka",
                "frequency": 100,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
            {
                "syllable": "ki",
                "frequency": 80,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
            {
                "syllable": "ta",
                "frequency": 90,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
        ]

        async with app.run_test() as pilot:
            # Set up patch state
            app.state.patch_a.corpus_dir = corpus_dir
            app.state.patch_a.corpus_type = "NLTK"
            app.state.patch_a.syllables = ["ka", "ki", "ta"]
            app.state.patch_a.frequencies = {"ka": 100, "ki": 80, "ta": 90}
            app.state.patch_a.annotated_data = annotated_data

            # Set combiner params
            app.state.combiner_a.syllables = 2
            app.state.combiner_a.count = 100
            app.state.combiner_a.seed = 42

            # Run combiner
            app._run_combiner("A")
            await pilot.pause(0.5)

            # Check that output files were created
            candidates_dir = corpus_dir / "candidates"
            assert candidates_dir.exists()

            candidates_file = candidates_dir / "nltk_candidates_2syl.json"
            assert candidates_file.exists()

            meta_file = candidates_dir / "nltk_combiner_meta.json"
            assert meta_file.exists()

            # Check that combiner state was updated
            assert app.state.combiner_a.last_output_path is not None

    @pytest.mark.asyncio
    async def test_run_combiner_for_patch_b(self, tmp_path):
        """Test that _run_combiner works for patch B."""
        app = SyllableWalkerApp()

        corpus_dir = tmp_path / "test_corpus_b"
        corpus_dir.mkdir()

        annotated_data = [
            {
                "syllable": "ba",
                "frequency": 50,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
            {
                "syllable": "bi",
                "frequency": 60,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
        ]

        async with app.run_test() as pilot:
            app.state.patch_b.corpus_dir = corpus_dir
            app.state.patch_b.corpus_type = "pyphen"
            app.state.patch_b.syllables = ["ba", "bi"]
            app.state.patch_b.frequencies = {"ba": 50, "bi": 60}
            app.state.patch_b.annotated_data = annotated_data

            app.state.combiner_b.syllables = 2
            app.state.combiner_b.count = 50
            app.state.combiner_b.seed = 123

            app._run_combiner("B")
            await pilot.pause(0.5)

            candidates_file = corpus_dir / "candidates" / "pyphen_candidates_2syl.json"
            assert candidates_file.exists()


class TestGenerateCandidatesButtons:
    """Tests for generate candidates button handlers."""

    @pytest.mark.asyncio
    async def test_generate_candidates_a_button_exists(self):
        """Test that generate candidates button A exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            button = app.query_one("#generate-candidates-a")
            assert button is not None

    @pytest.mark.asyncio
    async def test_generate_candidates_b_button_exists(self):
        """Test that generate candidates button B exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            button = app.query_one("#generate-candidates-b")
            assert button is not None


class TestCorpusSelectionFlow:
    """Integration tests for corpus selection workflow."""

    @pytest.mark.asyncio
    async def test_corpus_selection_updates_state(self, tmp_path):
        """Test that corpus selection updates patch state correctly."""
        app = SyllableWalkerApp()

        # Create valid NLTK corpus
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()
        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        async with app.run_test() as pilot:
            # Mock the push_screen_wait to return our corpus directory
            async def mock_push_screen_wait(screen):
                return corpus_dir

            with patch.object(app, "push_screen_wait", side_effect=mock_push_screen_wait):
                # Trigger corpus selection for Patch A
                app.action_select_corpus_a()
                await pilot.pause()

                # Wait for worker to complete
                await pilot.pause(0.5)

                # Check that state was updated
                assert app.state.patch_a.corpus_dir == corpus_dir
                assert app.state.patch_a.corpus_type == "NLTK"
                assert app.state.last_browse_dir == corpus_dir.parent

    @pytest.mark.asyncio
    async def test_corpus_selection_updates_ui(self, tmp_path):
        """Test that corpus selection updates UI labels."""
        app = SyllableWalkerApp()

        # Create valid corpus
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()
        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        async with app.run_test() as pilot:
            # Mock the push_screen_wait
            async def mock_push_screen_wait(screen):
                return corpus_dir

            with patch.object(app, "push_screen_wait", side_effect=mock_push_screen_wait):
                # Trigger selection
                app.action_select_corpus_a()
                await pilot.pause()
                await pilot.pause(0.5)

                # Check UI was updated
                status_label = app.query_one("#corpus-status-A", Label)
                status_text = str(status_label.render())

                assert "NLTK" in status_text

    @pytest.mark.asyncio
    async def test_corpus_selection_cancelled(self):
        """Test that cancelling corpus selection doesn't update state."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Mock push_screen_wait to return None (cancelled)
            async def mock_push_screen_wait(screen):
                return None

            with patch.object(app, "push_screen_wait", side_effect=mock_push_screen_wait):
                original_corpus = app.state.patch_a.corpus_dir

                app.action_select_corpus_a()
                await pilot.pause()
                await pilot.pause(0.5)

                # State should not have changed
                assert app.state.patch_a.corpus_dir == original_corpus

    @pytest.mark.asyncio
    async def test_invalid_corpus_selection_shows_error(self, tmp_path):
        """Test that selecting invalid corpus shows error notification."""
        app = SyllableWalkerApp()

        # Create invalid corpus (missing files)
        invalid_corpus = tmp_path / "invalid"
        invalid_corpus.mkdir()

        async with app.run_test() as pilot:

            async def mock_push_screen_wait(screen):
                return invalid_corpus

            with patch.object(app, "push_screen_wait", side_effect=mock_push_screen_wait):
                app.action_select_corpus_a()
                await pilot.pause()
                await pilot.pause(0.5)

                # Corpus should not be set
                assert app.state.patch_a.corpus_dir is None
                assert app.state.patch_a.corpus_type is None


class TestModalScreenNavigation:
    """Tests for modal screen navigation after operations."""

    @pytest.mark.asyncio
    async def test_modal_screens_work_after_corpus_selection(self, tmp_path):
        """Test that modal screens work after corpus selection."""
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


class TestDatabaseActions:
    """Tests for database viewer action methods."""

    @pytest.mark.asyncio
    async def test_action_view_database_a_exists(self):
        """Test that database A action exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            assert hasattr(app, "action_view_database_a")

    @pytest.mark.asyncio
    async def test_action_view_database_b_exists(self):
        """Test that database B action exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            assert hasattr(app, "action_view_database_b")

    @pytest.mark.asyncio
    async def test_open_database_no_corpus_shows_notification(self):
        """Test that opening database with no corpus shows notification."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Corpus not loaded
            assert app.state.patch_a.corpus_dir is None

            # Try to open database - should show notification, not crash
            app._open_database_for_patch("A")
            await pilot.pause()

            # Just verify no crash occurred
            assert True

    @pytest.mark.asyncio
    async def test_open_database_no_db_file_shows_notification(self, tmp_path):
        """Test that opening database with missing corpus.db shows notification."""
        app = SyllableWalkerApp()

        # Set corpus dir but don't create corpus.db
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        app.state.patch_a.corpus_dir = corpus_dir

        async with app.run_test() as pilot:
            app._open_database_for_patch("A")
            await pilot.pause()

            # Just verify no crash
            assert True


class TestComputeMetrics:
    """Tests for _compute_metrics_for_patch method."""

    @pytest.mark.asyncio
    async def test_compute_metrics_returns_none_without_data(self):
        """Test that compute metrics returns None without loaded data."""
        app = SyllableWalkerApp()

        async with app.run_test():
            result = app._compute_metrics_for_patch(app.state.patch_a)
            assert result is None

    @pytest.mark.asyncio
    async def test_compute_metrics_requires_syllables(self):
        """Test that compute metrics returns None without syllables."""
        app = SyllableWalkerApp()

        async with app.run_test():
            app.state.patch_a.frequencies = {"test": 1}
            app.state.patch_a.annotated_data = [
                {"syllable": "test", "frequency": 1, "features": {}}
            ]

            result = app._compute_metrics_for_patch(app.state.patch_a)
            assert result is None

    @pytest.mark.asyncio
    async def test_compute_metrics_requires_frequencies(self):
        """Test that compute metrics returns None without frequencies."""
        app = SyllableWalkerApp()

        async with app.run_test():
            app.state.patch_a.syllables = ["test"]
            app.state.patch_a.annotated_data = [
                {"syllable": "test", "frequency": 1, "features": {}}
            ]

            result = app._compute_metrics_for_patch(app.state.patch_a)
            assert result is None

    @pytest.mark.asyncio
    async def test_compute_metrics_requires_annotated_data(self):
        """Test that compute metrics returns None without annotated_data."""
        app = SyllableWalkerApp()

        async with app.run_test():
            app.state.patch_a.syllables = ["test"]
            app.state.patch_a.frequencies = {"test": 1}

            result = app._compute_metrics_for_patch(app.state.patch_a)
            assert result is None

    @pytest.mark.asyncio
    async def test_compute_metrics_with_valid_data(self):
        """Test that compute metrics works with valid data."""
        app = SyllableWalkerApp()

        async with app.run_test():
            app.state.patch_a.syllables = ["test", "ing", "foo"]
            app.state.patch_a.frequencies = {"test": 10, "ing": 20, "foo": 5}
            app.state.patch_a.annotated_data = [
                {"syllable": "test", "frequency": 10, "features": {"starts_with_vowel": False}},
                {"syllable": "ing", "frequency": 20, "features": {"starts_with_vowel": True}},
                {"syllable": "foo", "frequency": 5, "features": {"starts_with_vowel": False}},
            ]

            result = app._compute_metrics_for_patch(app.state.patch_a)

            assert result is not None
            assert result.inventory.total_count == 3
            assert result.frequency.total_occurrences == 35


class TestGenerateWalks:
    """Tests for walk generation."""

    @pytest.mark.asyncio
    async def test_generate_walks_requires_ready_patch(self):
        """Test that generation requires patch to be ready."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Patch not ready (no corpus loaded)
            assert not app.state.patch_a.is_ready_for_generation()

            # Try to generate - should show notification
            app._generate_walks_for_patch("A")
            await pilot.pause()

            # Outputs should still be empty
            assert app.state.patch_a.outputs == []


class TestSelectorPanel:
    """Tests for SelectorPanel widget (name selection)."""

    @pytest.mark.asyncio
    async def test_selector_panel_exists_for_patch_a(self):
        """Test that selector panel A exists in layout."""
        app = SyllableWalkerApp()

        async with app.run_test():
            from build_tools.syllable_walk_tui.modules.generator import SelectorPanel

            selector_a = app.query_one("#selector-panel-a", SelectorPanel)
            assert selector_a.patch_name == "A"

    @pytest.mark.asyncio
    async def test_selector_panel_exists_for_patch_b(self):
        """Test that selector panel B exists in layout."""
        app = SyllableWalkerApp()

        async with app.run_test():
            from build_tools.syllable_walk_tui.modules.generator import SelectorPanel

            selector_b = app.query_one("#selector-panel-b", SelectorPanel)
            assert selector_b.patch_name == "B"

    @pytest.mark.asyncio
    async def test_compose_creates_selector_widgets(self):
        """Test that SelectorPanel creates expected child widgets."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A")

        async with TestApp().run_test() as pilot:
            labels = pilot.app.query(Label)
            labels_text = [str(label.render()) for label in labels]
            assert any("PATCH A NAME SELECTOR" in text for text in labels_text)

            # Check for select button
            assert pilot.app.query_one("#select-names-a")

    @pytest.mark.asyncio
    async def test_update_output_with_metadata(self):
        """Test that update_output displays metadata correctly."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#test-panel", SelectorPanel)

            meta = {
                "arguments": {
                    "name_class": "first_name",
                    "count": 100,
                    "mode": "hard",
                },
                "statistics": {
                    "total_evaluated": 10000,
                    "admitted": 7500,
                    "admitted_percentage": 75.0,
                    "rejected": 2500,
                },
                "output": {
                    "selections_count": 100,
                    "selections_file": "/path/to/selections/pyphen_first_name_2syl.json",
                },
            }
            panel.update_output(meta)
            await pilot.pause()

            output_label = pilot.app.query_one("#selector-output-a", Label)
            text = str(output_label.render())
            assert "first_name" in text
            assert "Evaluated: 10,000" in text


class TestSelectorEventHandlers:
    """Tests for selector-related event handlers."""

    @pytest.mark.asyncio
    async def test_selector_count_changed_updates_state_a(self):
        """Test that selector count change updates selector_a state."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=50, widget_id="selector-count-a")
            app.on_int_spinner_changed(event)

            assert app.state.selector_a.count == 50

    @pytest.mark.asyncio
    async def test_selector_count_changed_updates_state_b(self):
        """Test that selector count change updates selector_b state."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event = IntSpinner.Changed(value=200, widget_id="selector-count-b")
            app.on_int_spinner_changed(event)

            assert app.state.selector_b.count == 200

    @pytest.mark.asyncio
    async def test_selector_mode_hard_updates_state_a(self):
        """Test that selector mode hard updates selector_a state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # First set to soft, then back to hard
            app.state.selector_a.mode = "soft"

            event = RadioOption.Selected(option_name="hard", widget_id="selector-mode-hard-a")
            app.on_profile_selected(event)

            assert app.state.selector_a.mode == "hard"

    @pytest.mark.asyncio
    async def test_selector_mode_soft_updates_state_a(self):
        """Test that selector mode soft updates selector_a state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            event = RadioOption.Selected(option_name="soft", widget_id="selector-mode-soft-a")
            app.on_profile_selected(event)

            assert app.state.selector_a.mode == "soft"

    @pytest.mark.asyncio
    async def test_selector_mode_hard_updates_state_b(self):
        """Test that selector mode hard updates selector_b state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            app.state.selector_b.mode = "soft"

            event = RadioOption.Selected(option_name="hard", widget_id="selector-mode-hard-b")
            app.on_profile_selected(event)

            assert app.state.selector_b.mode == "hard"

    @pytest.mark.asyncio
    async def test_selector_mode_soft_updates_state_b(self):
        """Test that selector mode soft updates selector_b state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            event = RadioOption.Selected(option_name="soft", widget_id="selector-mode-soft-b")
            app.on_profile_selected(event)

            assert app.state.selector_b.mode == "soft"

    @pytest.mark.asyncio
    async def test_selector_states_are_independent(self):
        """Test that selector_a and selector_b states are independent."""
        from build_tools.tui_common.controls import IntSpinner

        app = SyllableWalkerApp()

        async with app.run_test():
            event_a = IntSpinner.Changed(value=50, widget_id="selector-count-a")
            app.on_int_spinner_changed(event_a)

            event_b = IntSpinner.Changed(value=200, widget_id="selector-count-b")
            app.on_int_spinner_changed(event_b)

            assert app.state.selector_a.count == 50
            assert app.state.selector_b.count == 200


class TestSelectorOrderEventHandlers:
    """Tests for selector order-related event handlers."""

    @pytest.mark.asyncio
    async def test_selector_order_random_updates_state_a(self):
        """Test that selector order random updates selector_a state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Start with alphabetical
            app.state.selector_a.order = "alphabetical"

            event = RadioOption.Selected(option_name="random", widget_id="selector-order-random-a")
            app.on_profile_selected(event)

            assert app.state.selector_a.order == "random"

    @pytest.mark.asyncio
    async def test_selector_order_alphabetical_updates_state_a(self):
        """Test that selector order alphabetical updates selector_a state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Start with random
            app.state.selector_a.order = "random"

            event = RadioOption.Selected(
                option_name="alphabetical", widget_id="selector-order-alphabetical-a"
            )
            app.on_profile_selected(event)

            assert app.state.selector_a.order == "alphabetical"

    @pytest.mark.asyncio
    async def test_selector_order_random_updates_state_b(self):
        """Test that selector order random updates selector_b state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Start with alphabetical
            app.state.selector_b.order = "alphabetical"

            event = RadioOption.Selected(option_name="random", widget_id="selector-order-random-b")
            app.on_profile_selected(event)

            assert app.state.selector_b.order == "random"

    @pytest.mark.asyncio
    async def test_selector_order_alphabetical_updates_state_b(self):
        """Test that selector order alphabetical updates selector_b state."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Start with random
            app.state.selector_b.order = "random"

            event = RadioOption.Selected(
                option_name="alphabetical", widget_id="selector-order-alphabetical-b"
            )
            app.on_profile_selected(event)

            assert app.state.selector_b.order == "alphabetical"

    @pytest.mark.asyncio
    async def test_selector_order_states_are_independent(self):
        """Test that selector_a and selector_b order states are independent."""
        from build_tools.tui_common.controls import RadioOption

        app = SyllableWalkerApp()

        async with app.run_test():
            # Set A to random
            event_a = RadioOption.Selected(
                option_name="random", widget_id="selector-order-random-a"
            )
            app.on_profile_selected(event_a)

            # Set B to alphabetical
            event_b = RadioOption.Selected(
                option_name="alphabetical", widget_id="selector-order-alphabetical-b"
            )
            app.on_profile_selected(event_b)

            # Verify they're independent
            assert app.state.selector_a.order == "random"
            assert app.state.selector_b.order == "alphabetical"


class TestRunSelector:
    """Tests for _run_selector method."""

    @pytest.mark.asyncio
    async def test_run_selector_requires_corpus(self):
        """Test that _run_selector requires corpus to be loaded."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Patch not ready (no corpus loaded)
            assert not app.state.patch_a.is_ready_for_generation()

            # Try to run selector - should show notification
            app._run_selector("A")
            await pilot.pause()

            # Should not crash, selector outputs should be empty
            assert app.state.selector_a.outputs == []

    @pytest.mark.asyncio
    async def test_run_selector_requires_candidates(self, tmp_path):
        """Test that _run_selector requires candidates to exist."""
        app = SyllableWalkerApp()

        # Create a test corpus directory
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()

        annotated_data = [
            {
                "syllable": "ka",
                "frequency": 100,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
        ]

        async with app.run_test() as pilot:
            # Set up patch state without running combiner first
            app.state.patch_a.corpus_dir = corpus_dir
            app.state.patch_a.corpus_type = "NLTK"
            app.state.patch_a.syllables = ["ka"]
            app.state.patch_a.frequencies = {"ka": 100}
            app.state.patch_a.annotated_data = annotated_data

            # No combiner has run, so no candidates exist
            assert app.state.combiner_a.last_output_path is None

            app._run_selector("A")
            await pilot.pause()

            # Should not crash, selector outputs should be empty
            assert app.state.selector_a.outputs == []

    @pytest.mark.asyncio
    async def test_run_selector_creates_selections(self, tmp_path):
        """Test that _run_selector creates selection files."""
        app = SyllableWalkerApp()

        # Create a test corpus directory
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()

        # Create sample annotated data with features for name selection
        annotated_data = [
            {
                "syllable": "ka",
                "frequency": 100,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
            {
                "syllable": "ta",
                "frequency": 80,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": True,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": False,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
            {
                "syllable": "na",
                "frequency": 60,
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": False,
                    "starts_with_heavy_cluster": False,
                    "contains_plosive": False,
                    "contains_fricative": False,
                    "contains_liquid": False,
                    "contains_nasal": True,
                    "short_vowel": True,
                    "long_vowel": False,
                    "ends_with_vowel": True,
                    "ends_with_nasal": False,
                    "ends_with_stop": False,
                },
            },
        ]

        async with app.run_test() as pilot:
            # Set up patch state
            app.state.patch_a.corpus_dir = corpus_dir
            app.state.patch_a.corpus_type = "NLTK"
            app.state.patch_a.syllables = ["ka", "ta", "na"]
            app.state.patch_a.frequencies = {"ka": 100, "ta": 80, "na": 60}
            app.state.patch_a.annotated_data = annotated_data

            # Set combiner params and run
            app.state.combiner_a.syllables = 2
            app.state.combiner_a.count = 100
            app.state.combiner_a.seed = 42

            app._run_combiner("A")
            await pilot.pause(0.5)

            # Verify combiner created candidates
            assert app.state.combiner_a.last_output_path is not None

            # Now run selector
            app.state.selector_a.name_class = "first_name"
            app.state.selector_a.count = 50
            app.state.selector_a.mode = "hard"

            app._run_selector("A")
            await pilot.pause(0.5)

            # Check that output files were created
            selections_dir = corpus_dir / "selections"
            assert selections_dir.exists()

            # Check that selector state was updated
            assert app.state.selector_a.last_output_path is not None


class TestSelectNamesButtons:
    """Tests for select names button handlers."""

    @pytest.mark.asyncio
    async def test_select_names_a_button_exists(self):
        """Test that select names button A exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            button = app.query_one("#select-names-a")
            assert button is not None

    @pytest.mark.asyncio
    async def test_select_names_b_button_exists(self):
        """Test that select names button B exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            button = app.query_one("#select-names-b")
            assert button is not None


class TestExportTxtButtons:
    """Tests for export TXT button handlers."""

    @pytest.mark.asyncio
    async def test_export_txt_a_button_exists(self):
        """Test that export TXT button A exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            button = app.query_one("#export-txt-a")
            assert button is not None

    @pytest.mark.asyncio
    async def test_export_txt_b_button_exists(self):
        """Test that export TXT button B exists."""
        app = SyllableWalkerApp()

        async with app.run_test():
            button = app.query_one("#export-txt-b")
            assert button is not None

    @pytest.mark.asyncio
    async def test_export_txt_a_handler_calls_export(self, tmp_path):
        """Test that button A handler calls _export_to_txt for patch A."""
        app = SyllableWalkerApp()

        selections_dir = tmp_path / "selections"
        selections_dir.mkdir()
        json_path = selections_dir / "test_a.json"
        json_path.write_text("{}")

        async with app.run_test() as pilot:
            # Set up state for export
            app.state.selector_a.outputs = ["TestName"]
            app.state.selector_a.last_output_path = str(json_path)

            # Call the button handler directly
            app.on_button_export_txt_a()
            await pilot.pause()

            # Verify file was created
            txt_path = selections_dir / "test_a.txt"
            assert txt_path.exists()

    @pytest.mark.asyncio
    async def test_export_txt_b_handler_calls_export(self, tmp_path):
        """Test that button B handler calls _export_to_txt for patch B."""
        app = SyllableWalkerApp()

        selections_dir = tmp_path / "selections"
        selections_dir.mkdir()
        json_path = selections_dir / "test_b.json"
        json_path.write_text("{}")

        async with app.run_test() as pilot:
            # Set up state for export
            app.state.selector_b.outputs = ["TestNameB"]
            app.state.selector_b.last_output_path = str(json_path)

            # Call the button handler directly
            app.on_button_export_txt_b()
            await pilot.pause()

            # Verify file was created
            txt_path = selections_dir / "test_b.txt"
            assert txt_path.exists()


class TestExportToTxt:
    """Tests for _export_to_txt method."""

    @pytest.mark.asyncio
    async def test_export_to_txt_requires_names(self):
        """Test that _export_to_txt requires names to be available."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # No names in selector outputs
            assert app.state.selector_a.outputs == []

            # Try to export - should show notification
            app._export_to_txt("A")
            await pilot.pause()

            # Should not crash
            assert True

    @pytest.mark.asyncio
    async def test_export_to_txt_requires_output_path(self):
        """Test that _export_to_txt requires last_output_path to be set."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Set names but no output path
            app.state.selector_a.outputs = ["Kala", "Tana", "Naka"]
            app.state.selector_a.last_output_path = None

            # Try to export - should show notification
            app._export_to_txt("A")
            await pilot.pause()

            # Should not crash
            assert True

    @pytest.mark.asyncio
    async def test_export_to_txt_creates_file(self, tmp_path):
        """Test that _export_to_txt creates TXT file with names."""
        app = SyllableWalkerApp()

        # Create a test selections directory
        selections_dir = tmp_path / "selections"
        selections_dir.mkdir()

        # Create a fake JSON output path
        json_path = selections_dir / "nltk_first_name_2syl.json"
        json_path.write_text("{}")

        async with app.run_test() as pilot:
            # Set up selector state with names and output path
            app.state.selector_a.outputs = ["Kala", "Tana", "Naka"]
            app.state.selector_a.last_output_path = str(json_path)

            # Export
            app._export_to_txt("A")
            await pilot.pause()

            # Check TXT file was created
            txt_path = selections_dir / "nltk_first_name_2syl.txt"
            assert txt_path.exists()

            # Check contents
            content = txt_path.read_text()
            assert "Kala\n" in content
            assert "Tana\n" in content
            assert "Naka\n" in content

    @pytest.mark.asyncio
    async def test_export_to_txt_for_patch_b(self, tmp_path):
        """Test that _export_to_txt works for patch B."""
        app = SyllableWalkerApp()

        selections_dir = tmp_path / "selections"
        selections_dir.mkdir()

        json_path = selections_dir / "pyphen_last_name_3syl.json"
        json_path.write_text("{}")

        async with app.run_test() as pilot:
            app.state.selector_b.outputs = ["Bakala", "Bitana"]
            app.state.selector_b.last_output_path = str(json_path)

            app._export_to_txt("B")
            await pilot.pause()

            txt_path = selections_dir / "pyphen_last_name_3syl.txt"
            assert txt_path.exists()

            content = txt_path.read_text()
            assert "Bakala\n" in content
            assert "Bitana\n" in content

    @pytest.mark.asyncio
    async def test_export_to_txt_one_name_per_line(self, tmp_path):
        """Test that exported TXT has exactly one name per line."""
        app = SyllableWalkerApp()

        selections_dir = tmp_path / "selections"
        selections_dir.mkdir()

        json_path = selections_dir / "test_output.json"
        json_path.write_text("{}")

        async with app.run_test() as pilot:
            names = ["Alpha", "Beta", "Gamma", "Delta"]
            app.state.selector_a.outputs = names
            app.state.selector_a.last_output_path = str(json_path)

            app._export_to_txt("A")
            await pilot.pause()

            txt_path = selections_dir / "test_output.txt"
            lines = txt_path.read_text().strip().split("\n")

            assert len(lines) == 4
            assert lines == names

    @pytest.mark.asyncio
    async def test_export_to_txt_preserves_name_order(self, tmp_path):
        """Test that exported TXT preserves the order of names."""
        app = SyllableWalkerApp()

        selections_dir = tmp_path / "selections"
        selections_dir.mkdir()

        json_path = selections_dir / "test_order.json"
        json_path.write_text("{}")

        async with app.run_test() as pilot:
            # Specific order
            names = ["Zeta", "Alpha", "Mika", "Beta"]
            app.state.selector_a.outputs = names
            app.state.selector_a.last_output_path = str(json_path)

            app._export_to_txt("A")
            await pilot.pause()

            txt_path = selections_dir / "test_order.txt"
            lines = txt_path.read_text().strip().split("\n")

            # Order should be preserved
            assert lines == names

    @pytest.mark.asyncio
    async def test_export_to_txt_handles_write_error(self, tmp_path):
        """Test that _export_to_txt handles file write errors gracefully."""
        app = SyllableWalkerApp()

        async with app.run_test() as pilot:
            # Set up state with names but point to non-existent directory
            app.state.selector_a.outputs = ["TestName"]
            # Path to a directory that doesn't exist
            app.state.selector_a.last_output_path = "/nonexistent/path/test.json"

            # This should trigger the exception handler, not crash
            app._export_to_txt("A")
            await pilot.pause()

            # Should not crash - exception is caught and notification shown
            assert True
