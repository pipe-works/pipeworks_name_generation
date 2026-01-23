"""
Tests for syllable_walk_tui.core.ui_updates module.

Tests the UI status update helper functions that display corpus loading progress.
"""

from unittest.mock import MagicMock

import pytest

from build_tools.syllable_walk_tui.core import ui_updates


class TestGetCorpusPrefix:
    """Tests for _get_corpus_prefix helper."""

    def test_returns_lowercase_when_corpus_type_provided(self):
        """Test that corpus type is lowercased."""
        assert ui_updates._get_corpus_prefix("PYPHEN") == "pyphen"
        assert ui_updates._get_corpus_prefix("NLTK") == "nltk"

    def test_returns_nltk_default_when_corpus_type_none(self):
        """Test that None defaults to nltk."""
        assert ui_updates._get_corpus_prefix(None) == "nltk"

    def test_handles_mixed_case(self):
        """Test mixed case input."""
        assert ui_updates._get_corpus_prefix("Pyphen") == "pyphen"


class TestUpdateCorpusStatusQuickLoad:
    """Tests for update_corpus_status_quick_load function."""

    def test_updates_status_label_with_file_list(self):
        """Test that status label is updated with correct file list."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_quick_load(
            mock_app,
            patch_name="A",
            corpus_info="20260110_143022_pyphen",
            corpus_type="pyphen",
        )

        mock_app.query_one.assert_called_once_with(
            "#corpus-status-A", pytest.importorskip("textual.widgets").Label
        )
        mock_label.update.assert_called_once()
        call_arg = mock_label.update.call_args[0][0]

        assert "20260110_143022_pyphen" in call_arg
        assert "pyphen_syllables_unique.txt" in call_arg
        assert "pyphen_syllables_frequencies.json" in call_arg
        assert "pyphen_syllables_annotated.json" in call_arg

    def test_updates_css_classes(self):
        """Test that CSS classes are updated correctly."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_quick_load(mock_app, "A", "corpus_info", "pyphen")

        mock_label.remove_class.assert_called_once_with("corpus-status")
        mock_label.add_class.assert_called_once_with("corpus-status-valid")

    def test_handles_query_exception_gracefully(self, capsys):
        """Test that exceptions are caught and logged."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise
        ui_updates.update_corpus_status_quick_load(mock_app, "A", "corpus_info", "pyphen")

        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestUpdateCorpusStatusLoading:
    """Tests for update_corpus_status_loading function."""

    def test_shows_loading_indicator(self):
        """Test that loading indicator is shown."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_loading(
            mock_app,
            patch_name="B",
            corpus_info="20260110_143022_nltk",
            corpus_type="nltk",
        )

        call_arg = mock_label.update.call_args[0][0]
        assert "(loading...)" in call_arg

    def test_uses_correct_prefix_for_nltk(self):
        """Test that nltk prefix is used for nltk corpus."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_loading(mock_app, "A", "corpus_info", "nltk")

        call_arg = mock_label.update.call_args[0][0]
        assert "nltk_syllables" in call_arg

    def test_handles_query_exception_gracefully(self, capsys):
        """Test that exceptions are caught and logged."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise
        ui_updates.update_corpus_status_loading(mock_app, "A", "corpus_info", "pyphen")

        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestUpdateCorpusStatusReady:
    """Tests for update_corpus_status_ready function."""

    def test_shows_sqlite_source(self):
        """Test SQLite source is displayed correctly."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_ready(
            mock_app,
            patch_name="A",
            corpus_info="corpus_info",
            corpus_type="pyphen",
            syllable_count=1000,
            source="sqlite",
            load_time=150,
        )

        call_arg = mock_label.update.call_args[0][0]
        assert "corpus.db" in call_arg
        assert "SQLite" in call_arg
        assert "150ms" in call_arg
        assert "1,000 syllables" in call_arg

    def test_shows_json_source(self):
        """Test JSON source is displayed correctly."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_ready(
            mock_app,
            patch_name="A",
            corpus_info="corpus_info",
            corpus_type="pyphen",
            syllable_count=500,
            source="json",
            load_time=250,
            file_name="pyphen_syllables_annotated.json",
        )

        call_arg = mock_label.update.call_args[0][0]
        assert "pyphen_syllables_annotated.json" in call_arg
        assert "JSON" in call_arg
        assert "250ms" in call_arg

    def test_uses_default_file_name_when_not_provided(self):
        """Test that default file name is used when not provided."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_ready(
            mock_app,
            patch_name="A",
            corpus_info="corpus_info",
            corpus_type="pyphen",
            syllable_count=500,
            source="json",
            load_time=250,
            file_name=None,
        )

        call_arg = mock_label.update.call_args[0][0]
        assert "annotated.json" in call_arg

    def test_handles_query_exception_gracefully(self, capsys):
        """Test that exceptions are caught and logged."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise
        ui_updates.update_corpus_status_ready(
            mock_app, "A", "corpus_info", "pyphen", 500, "sqlite", 150
        )

        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestUpdateCorpusStatusError:
    """Tests for update_corpus_status_error function."""

    def test_shows_error_message(self):
        """Test that error message is displayed."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_error(
            mock_app,
            patch_name="A",
            corpus_info="corpus_info",
            corpus_type="pyphen",
            error_msg="File not found",
        )

        call_arg = mock_label.update.call_args[0][0]
        assert "Error:" in call_arg
        assert "File not found" in call_arg

    def test_truncates_long_error_messages(self):
        """Test that long error messages are truncated."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        long_error = "This is a very long error message that should be truncated"
        ui_updates.update_corpus_status_error(mock_app, "A", "corpus_info", "pyphen", long_error)

        call_arg = mock_label.update.call_args[0][0]
        assert "..." in call_arg
        # Should be truncated to 30 chars
        assert "that should be truncated" not in call_arg

    def test_switches_to_error_css_class(self):
        """Test that CSS classes indicate error state."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_error(mock_app, "A", "corpus_info", "pyphen", "error")

        mock_label.remove_class.assert_called_once_with("corpus-status-valid")
        mock_label.add_class.assert_called_once_with("corpus-status")

    def test_handles_query_exception_silently(self):
        """Test that exceptions are caught silently."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise - exception is silently ignored
        ui_updates.update_corpus_status_error(mock_app, "A", "corpus_info", "pyphen", "error")

        # No assertions needed - just verifying no exception is raised


class TestUpdateCorpusStatusNotAnnotated:
    """Tests for update_corpus_status_not_annotated function."""

    def test_shows_annotator_instruction(self):
        """Test that instruction to run annotator is shown."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_corpus_status_not_annotated(
            mock_app,
            patch_name="A",
            corpus_info="corpus_info",
            corpus_type="pyphen",
        )

        call_arg = mock_label.update.call_args[0][0]
        assert "Run syllable_feature_annotator" in call_arg

    def test_handles_query_exception_silently(self):
        """Test that exceptions are caught silently."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise - exception is silently ignored
        ui_updates.update_corpus_status_not_annotated(mock_app, "A", "corpus_info", "pyphen")

        # No assertions needed - just verifying no exception is raised


class TestUpdateCenterCorpusLabel:
    """Tests for update_center_corpus_label function."""

    def test_updates_label_with_dir_name_and_type(self):
        """Test that label shows directory name and corpus type."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_center_corpus_label(
            mock_app,
            patch_name="A",
            dir_name="20260110_115601_nltk",
            corpus_type="nltk",
        )

        mock_label.update.assert_called_once_with("20260110_115601_nltk (nltk)")

    def test_removes_placeholder_class(self):
        """Test that placeholder class is removed."""
        mock_app = MagicMock()
        mock_label = MagicMock()
        mock_app.query_one.return_value = mock_label

        ui_updates.update_center_corpus_label(mock_app, "A", "dir_name", "pyphen")

        mock_label.remove_class.assert_called_once_with("output-placeholder")

    def test_handles_query_exception_gracefully(self, capsys):
        """Test that exceptions are caught and logged."""
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Widget not found")

        # Should not raise
        ui_updates.update_center_corpus_label(mock_app, "A", "dir_name", "pyphen")

        captured = capsys.readouterr()
        assert "Warning" in captured.out
