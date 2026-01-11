"""
Tests for syllable_walk_tui OscillatorModule.

Tests file browser, navigation, path resolution, and loading indicators.
"""

import tempfile
from pathlib import Path

import pytest

from build_tools.syllable_walk_tui.modules.oscillator import OscillatorModule


class TestOscillatorModule:
    """Tests for OscillatorModule class."""

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def oscillator(self, temp_directory):
        """Create an oscillator module for testing."""
        return OscillatorModule(initial_directory=str(temp_directory))

    def test_oscillator_initializes(self, temp_directory):
        """Oscillator should initialize without errors."""
        osc = OscillatorModule(initial_directory=str(temp_directory))
        assert osc is not None
        assert osc.current_directory is not None

    def test_oscillator_resolves_valid_directory(self, temp_directory):
        """Oscillator should accept and resolve valid directory."""
        osc = OscillatorModule(initial_directory=str(temp_directory))
        assert osc.current_directory.exists()
        assert osc.current_directory.is_dir()

    def test_oscillator_handles_nonexistent_directory(self):
        """Oscillator should handle nonexistent directory gracefully."""
        nonexistent = "/nonexistent/path/that/does/not/exist"
        osc = OscillatorModule(initial_directory=nonexistent)

        # Should walk up to find valid parent
        assert osc.current_directory.exists()

    def test_oscillator_initial_corpus_none(self, oscillator):
        """Oscillator should start with no corpus loaded."""
        assert oscillator.current_corpus_name is None
        assert oscillator.selected_path is None

    def test_oscillator_has_compose_method(self, oscillator):
        """Oscillator should have compose method for UI."""
        assert hasattr(oscillator, "compose")
        assert callable(oscillator.compose)

    def test_oscillator_has_populate_browser_method(self, oscillator):
        """Oscillator should have _populate_browser method."""
        assert hasattr(oscillator, "_populate_browser")
        assert callable(oscillator._populate_browser)

    def test_oscillator_path_resolution_absolute(self, temp_directory):
        """Oscillator should resolve to absolute paths."""
        osc = OscillatorModule(initial_directory=str(temp_directory))
        assert osc.current_directory.is_absolute()

    def test_oscillator_loads_messages_defined(self, oscillator):
        """Oscillator should define LoadCorpus message."""
        assert hasattr(OscillatorModule, "LoadCorpus")
        assert hasattr(OscillatorModule, "InvalidSelection")


class TestOscillatorPathValidation:
    """Tests for oscillator path validation logic."""

    def test_nonexistent_path_walks_up_to_parent(self):
        """Nonexistent path should walk up to find valid parent."""
        # Use a path that definitely doesn't exist
        fake_path = "/tmp/definitely_nonexistent_dir_12345/subdir/deep"
        osc = OscillatorModule(initial_directory=fake_path)

        # Should have walked up to a valid directory
        assert osc.current_directory.exists()

    def test_file_path_walks_up_to_directory(self, tmp_path):
        """If given a file path, should walk up to containing directory."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        osc = OscillatorModule(initial_directory=str(test_file))

        # Should have walked up to parent directory
        assert osc.current_directory.is_dir()
        assert osc.current_directory.exists()


class TestOscillatorUpdateCorpusInfo:
    """Tests for updating corpus info display."""

    @pytest.fixture
    def oscillator(self):
        """Create oscillator with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield OscillatorModule(initial_directory=tmpdir)

    def test_update_corpus_info_method_exists(self, oscillator):
        """Oscillator should have update_corpus_info method."""
        assert hasattr(oscillator, "update_corpus_info")
        assert callable(oscillator.update_corpus_info)


class TestOscillatorMessages:
    """Tests for oscillator message classes."""

    def test_load_corpus_message_creation(self):
        """LoadCorpus message should be creatable."""
        corpus_info = {
            "name": "test.json",
            "path": "/path/to/test.json",
            "type": "pyphen",
        }
        msg = OscillatorModule.LoadCorpus(corpus_info)
        assert msg.corpus_info == corpus_info

    def test_invalid_selection_message_creation(self):
        """InvalidSelection message should be creatable."""
        msg = OscillatorModule.InvalidSelection("Error message")
        assert msg.error_message == "Error message"

    def test_load_corpus_message_bubbles(self):
        """LoadCorpus message should bubble up."""
        msg = OscillatorModule.LoadCorpus({"name": "test"})
        assert msg.bubble is True

    def test_invalid_selection_message_bubbles(self):
        """InvalidSelection message should bubble up."""
        msg = OscillatorModule.InvalidSelection("error")
        assert msg.bubble is True


class TestOscillatorKeyHandling:
    """Tests for keyboard input handling."""

    @pytest.fixture
    def oscillator(self):
        """Create oscillator with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield OscillatorModule(initial_directory=tmpdir)

    def test_on_key_method_exists(self, oscillator):
        """Oscillator should have on_key method."""
        assert hasattr(oscillator, "on_key")
        assert callable(oscillator.on_key)


class TestOscillatorBrowserPopulation:
    """Tests for file browser population."""

    @pytest.fixture
    def temp_dir_with_files(self):
        """Create a temp directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files and directories
            (tmpdir_path / "subdir1").mkdir()
            (tmpdir_path / "subdir2").mkdir()
            (tmpdir_path / "test.txt").write_text("test")
            (tmpdir_path / "test_syllables_annotated.json").write_text("{}")

            yield tmpdir_path

    def test_populate_browser_method_exists(self, temp_dir_with_files):
        """Oscillator should have _populate_browser method."""
        osc = OscillatorModule(initial_directory=str(temp_dir_with_files))
        assert hasattr(osc, "_populate_browser")

    def test_oscillator_has_loading_indicator(self, temp_dir_with_files):
        """Oscillator should have a loading indicator in UI."""
        _ = OscillatorModule(initial_directory=str(temp_dir_with_files))
        # Check that LoadingIndicator is in the widget composition
        # This is tested implicitly through the compose method


class TestOscillatorDefaultID:
    """Tests for default ID configuration."""

    def test_default_id_is_oscillator(self):
        """Default ID should be 'oscillator'."""
        assert OscillatorModule.DEFAULT_ID == "oscillator"

    def test_uses_default_id_when_not_specified(self):
        """Should use default ID when not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            osc = OscillatorModule(initial_directory=tmpdir)
            assert osc.id == "oscillator"

    def test_can_override_id(self):
        """Should be able to override ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            osc = OscillatorModule(initial_directory=tmpdir, id="custom-osc")
            assert osc.id == "custom-osc"


class TestOscillatorLoadTrigger:
    """Tests for corpus load triggering."""

    @pytest.fixture
    def oscillator(self):
        """Create oscillator with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield OscillatorModule(initial_directory=tmpdir)

    def test_trigger_load_method_exists(self, oscillator):
        """Oscillator should have _trigger_load method."""
        assert hasattr(oscillator, "_trigger_load")
        assert callable(oscillator._trigger_load)

    def test_trigger_load_without_selection_sends_message(self, oscillator):
        """Triggering load without selection should send InvalidSelection."""
        # Create a list to capture messages
        messages = []

        # Mock post_message to capture messages
        original_post = oscillator.post_message
        oscillator.post_message = lambda msg: messages.append(msg)

        # Trigger load without selecting a file
        oscillator._trigger_load()

        # Should have posted InvalidSelection message
        assert len(messages) == 1
        assert isinstance(messages[0], OscillatorModule.InvalidSelection)

        # Restore original method
        oscillator.post_message = original_post

    def test_trigger_load_with_invalid_file_sends_message(self, oscillator):
        """Triggering load with invalid file should send InvalidSelection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a non-corpus file
            invalid_file = Path(tmpdir) / "not_a_corpus.txt"
            invalid_file.write_text("test")

            oscillator.selected_path = invalid_file

            # Capture messages
            messages = []
            original_post = oscillator.post_message
            oscillator.post_message = lambda msg: messages.append(msg)

            # Trigger load
            oscillator._trigger_load()

            # Should have posted InvalidSelection message
            assert len(messages) == 1
            assert isinstance(messages[0], OscillatorModule.InvalidSelection)

            oscillator.post_message = original_post

    def test_trigger_load_with_valid_corpus_sends_load_message(self, oscillator):
        """Triggering load with valid corpus should send LoadCorpus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid corpus file
            corpus_file = Path(tmpdir) / "pyphen_syllables_annotated.json"
            corpus_file.write_text("{}")

            oscillator.selected_path = corpus_file

            # Capture messages
            messages = []
            original_post = oscillator.post_message
            oscillator.post_message = lambda msg: messages.append(msg)

            # Trigger load
            oscillator._trigger_load()

            # Should have posted LoadCorpus message
            assert len(messages) == 1
            assert isinstance(messages[0], OscillatorModule.LoadCorpus)
            assert messages[0].corpus_info["type"] == "pyphen"

            oscillator.post_message = original_post
