"""
Tests for syllable_walk_tui.core.actions module.

Tests the action helper functions for patch validation, panel updates, and navigation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from build_tools.syllable_walk_tui.core.actions import (
    PatchValidationResult,
    compute_metrics_for_patch,
    get_initial_browse_dir,
    open_database_for_patch,
    update_combiner_panel,
    update_selector_panel,
    validate_patch_ready,
)


class TestPatchValidationResult:
    """Tests for PatchValidationResult dataclass."""

    def test_default_values(self):
        """Test default values for dataclass."""
        result = PatchValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.patch is None
        assert result.error_message is None

    def test_with_patch(self):
        """Test with patch provided."""
        mock_patch = MagicMock()
        result = PatchValidationResult(is_valid=True, patch=mock_patch)
        assert result.patch is mock_patch

    def test_with_error(self):
        """Test with error message."""
        result = PatchValidationResult(is_valid=False, error_message="Test error")
        assert result.is_valid is False
        assert result.error_message == "Test error"


class TestValidatePatchReady:
    """Tests for validate_patch_ready function."""

    def test_returns_invalid_when_patch_not_ready(self):
        """Test that invalid result is returned when patch is not ready."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        mock_patch.is_ready_for_generation.return_value = False
        mock_app.state.patch_a = mock_patch

        result = validate_patch_ready(mock_app, "A")

        assert result.is_valid is False
        assert result.error_message is not None
        assert "Corpus not loaded" in result.error_message
        mock_app.notify.assert_called_once()

    def test_returns_valid_when_patch_ready(self):
        """Test that valid result is returned when patch is ready."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        mock_patch.is_ready_for_generation.return_value = True
        mock_app.state.patch_a = mock_patch

        result = validate_patch_ready(mock_app, "A")

        assert result.is_valid is True
        assert result.patch is mock_patch
        mock_app.notify.assert_not_called()

    def test_uses_patch_b_for_b_name(self):
        """Test that patch B is used when patch_name is 'B'."""
        mock_app = MagicMock()
        mock_patch_a = MagicMock()
        mock_patch_b = MagicMock()
        mock_patch_b.is_ready_for_generation.return_value = True
        mock_app.state.patch_a = mock_patch_a
        mock_app.state.patch_b = mock_patch_b

        result = validate_patch_ready(mock_app, "B")

        assert result.patch is mock_patch_b

    def test_error_message_includes_correct_key_hint_for_a(self):
        """Test error message includes key hint '1' for patch A."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        mock_patch.is_ready_for_generation.return_value = False
        mock_app.state.patch_a = mock_patch

        result = validate_patch_ready(mock_app, "A")

        assert result.error_message is not None
        assert "Press 1" in result.error_message

    def test_error_message_includes_correct_key_hint_for_b(self):
        """Test error message includes key hint '2' for patch B."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        mock_patch.is_ready_for_generation.return_value = False
        mock_app.state.patch_b = mock_patch

        result = validate_patch_ready(mock_app, "B")

        assert result.error_message is not None
        assert "Press 2" in result.error_message


class TestUpdateCombinerPanel:
    """Tests for update_combiner_panel function."""

    def test_updates_panel_with_metadata(self):
        """Test that panel is updated with metadata."""
        mock_app = MagicMock()
        mock_panel = MagicMock()
        mock_app.query_one.return_value = mock_panel
        meta_output = {"candidates": 1000, "output_path": "test.json"}

        update_combiner_panel(mock_app, "A", meta_output)

        mock_panel.update_output.assert_called_once_with(meta_output)

    def test_handles_query_exception_gracefully(self, capsys):
        """Test that exceptions are caught and logged."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise
        update_combiner_panel(mock_app, "A", {})

        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_uses_lowercase_patch_name_in_query(self):
        """Test that lowercase patch name is used in widget ID."""
        mock_app = MagicMock()
        mock_panel = MagicMock()
        mock_app.query_one.return_value = mock_panel

        update_combiner_panel(mock_app, "A", {})

        call_args = mock_app.query_one.call_args
        assert "#combiner-panel-a" in call_args[0][0]


class TestUpdateSelectorPanel:
    """Tests for update_selector_panel function."""

    def test_updates_panel_with_metadata_and_names(self):
        """Test that panel is updated with metadata and names."""
        mock_app = MagicMock()
        mock_panel = MagicMock()
        mock_app.query_one.return_value = mock_panel
        meta_output = {"selected": 100}
        names = ["Alice", "Bob", "Charlie"]

        update_selector_panel(mock_app, "B", meta_output, names)

        mock_panel.update_output.assert_called_once_with(meta_output, names)

    def test_handles_query_exception_gracefully(self, capsys):
        """Test that exceptions are caught and logged."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise
        update_selector_panel(mock_app, "B", {}, [])

        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestComputeMetricsForPatch:
    """Tests for compute_metrics_for_patch function."""

    def test_returns_none_when_syllables_missing(self):
        """Test that None is returned when syllables are missing."""
        mock_patch = MagicMock()
        mock_patch.syllables = None
        mock_patch.frequencies = {"a": 1}
        mock_patch.annotated_data = [{"text": "a"}]

        result = compute_metrics_for_patch(mock_patch)

        assert result is None

    def test_returns_none_when_frequencies_missing(self):
        """Test that None is returned when frequencies are missing."""
        mock_patch = MagicMock()
        mock_patch.syllables = ["a", "b"]
        mock_patch.frequencies = None
        mock_patch.annotated_data = [{"text": "a"}]

        result = compute_metrics_for_patch(mock_patch)

        assert result is None

    def test_returns_none_when_annotated_data_missing(self):
        """Test that None is returned when annotated data is missing."""
        mock_patch = MagicMock()
        mock_patch.syllables = ["a", "b"]
        mock_patch.frequencies = {"a": 1}
        mock_patch.annotated_data = None

        result = compute_metrics_for_patch(mock_patch)

        assert result is None

    def test_returns_metrics_when_all_data_present(self):
        """Test that metrics are computed when all data is present."""
        mock_patch = MagicMock()
        mock_patch.syllables = ["a", "b"]
        mock_patch.frequencies = {"a": 1, "b": 2}
        mock_patch.annotated_data = [
            {"text": "a", "short_vowel": True},
            {"text": "b", "short_vowel": False},
        ]

        with patch(
            "build_tools.syllable_walk_tui.services.metrics.compute_corpus_shape_metrics"
        ) as mock_compute:
            mock_compute.return_value = MagicMock(total_syllables=2)
            result = compute_metrics_for_patch(mock_patch)

            assert result is not None
            mock_compute.assert_called_once()

    def test_returns_none_when_computation_fails(self):
        """Test that None is returned when computation raises an exception."""
        mock_patch = MagicMock()
        mock_patch.syllables = ["a", "b"]
        mock_patch.frequencies = {"a": 1, "b": 2}
        mock_patch.annotated_data = [{"text": "a"}]

        with patch(
            "build_tools.syllable_walk_tui.services.metrics.compute_corpus_shape_metrics"
        ) as mock_compute:
            mock_compute.side_effect = Exception("Computation failed")
            result = compute_metrics_for_patch(mock_patch)

            assert result is None


class TestGetInitialBrowseDir:
    """Tests for get_initial_browse_dir function."""

    def test_returns_patch_corpus_dir_when_set(self, tmp_path):
        """Test that patch's corpus dir is returned when set."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        mock_patch.corpus_dir = corpus_dir
        mock_app.state.patch_a = mock_patch

        result = get_initial_browse_dir(mock_app, "A")

        assert result == corpus_dir

    def test_returns_last_browse_dir_when_patch_not_set(self, tmp_path):
        """Test that last browse dir is used when patch corpus not set."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        mock_patch.corpus_dir = None
        mock_app.state.patch_a = mock_patch

        last_browse = tmp_path / "last"
        last_browse.mkdir()
        mock_app.state.last_browse_dir = last_browse

        result = get_initial_browse_dir(mock_app, "A")

        assert result == last_browse

    def test_returns_home_as_fallback(self):
        """Test that home directory is used as fallback when _working/output doesn't exist."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        mock_patch.corpus_dir = None
        mock_app.state.patch_a = mock_patch
        mock_app.state.last_browse_dir = None

        result = get_initial_browse_dir(mock_app, "A")

        # Result should be a Path (either _working/output or home directory)
        assert isinstance(result, Path)


class TestOpenDatabaseForPatch:
    """Tests for open_database_for_patch function."""

    def test_notifies_when_no_corpus_loaded(self):
        """Test that notification is shown when no corpus is loaded."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        mock_patch.corpus_dir = None
        mock_app.state.patch_a = mock_patch

        open_database_for_patch(mock_app, "A")

        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "No corpus loaded" in call_args[0][0]

    def test_notifies_when_db_not_found(self, tmp_path):
        """Test that notification is shown when db file doesn't exist."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        mock_patch.corpus_dir = corpus_dir
        mock_app.state.patch_a = mock_patch

        open_database_for_patch(mock_app, "A")

        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "No corpus.db found" in call_args[0][0]

    def test_pushes_database_screen_when_db_exists(self, tmp_path):
        """Test that DatabaseScreen is pushed when db exists."""
        mock_app = MagicMock()
        mock_patch = MagicMock()
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()
        db_path = data_dir / "corpus.db"
        db_path.touch()
        mock_patch.corpus_dir = corpus_dir
        mock_app.state.patch_a = mock_patch

        with patch("build_tools.syllable_walk_tui.modules.database.DatabaseScreen") as mock_screen:
            open_database_for_patch(mock_app, "A")

            mock_app.push_screen.assert_called_once()
            mock_screen.assert_called_once_with(db_path=db_path, patch_name="A")
