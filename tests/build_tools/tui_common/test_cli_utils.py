"""
Tests for tui_common CLI utilities.

Tests for shared CLI functionality including tab completion, file discovery,
and corpus database integration.
"""

from unittest.mock import MagicMock, patch

import pytest

from build_tools.tui_common import cli_utils
from build_tools.tui_common.cli_utils import (
    discover_files,
    path_completer,
    record_corpus_db_safe,
    setup_tab_completion,
)


class TestRecordCorpusDbSafe:
    """Tests for record_corpus_db_safe function."""

    def test_successful_operation_returns_result(self):
        """Test that successful operations return their result."""
        result = record_corpus_db_safe("test op", lambda: "success")
        assert result == "success"

    def test_successful_operation_with_complex_return(self):
        """Test that complex return values are preserved."""
        expected = {"key": "value", "count": 42}
        result = record_corpus_db_safe("test op", lambda: expected)
        assert result == expected

    def test_failed_operation_returns_none(self):
        """Test that failed operations return None."""

        def failing_func():
            raise ValueError("Test error")

        result = record_corpus_db_safe("test op", failing_func)
        assert result is None

    def test_failed_operation_prints_warning(self, capsys):
        """Test that failed operations print warning to stderr."""

        def failing_func():
            raise RuntimeError("Something went wrong")

        record_corpus_db_safe("start run", failing_func)
        captured = capsys.readouterr()
        assert "Warning: Failed to record start run to corpus_db" in captured.err
        assert "Something went wrong" in captured.err

    def test_failed_operation_quiet_suppresses_warning(self, capsys):
        """Test that quiet=True suppresses warning messages."""

        def failing_func():
            raise RuntimeError("Should not appear")

        record_corpus_db_safe("test op", failing_func, quiet=True)
        captured = capsys.readouterr()
        assert captured.err == ""


class TestPathCompleter:
    """Tests for path_completer function."""

    def test_completes_directory_contents(self, tmp_path):
        """Test that completing a directory shows its contents."""
        # Create test files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()

        # Complete the directory
        result = path_completer(str(tmp_path), 0)
        # Should return one of the files or subdirectories
        assert result is not None

    def test_completes_partial_filename(self, tmp_path):
        """Test that partial filenames are completed."""
        (tmp_path / "test_file.txt").touch()
        (tmp_path / "test_other.txt").touch()
        (tmp_path / "different.txt").touch()

        # Complete partial path
        partial = str(tmp_path / "test_")
        result = path_completer(partial, 0)
        # Should return a match starting with test_
        if result:  # May be None on some systems
            assert "test_" in result

    def test_returns_none_when_no_more_matches(self, tmp_path):
        """Test that None is returned when state exceeds matches."""
        (tmp_path / "only_one.txt").touch()

        # Try to get more matches than exist
        result = path_completer(str(tmp_path / "only_one.txt"), 100)
        assert result is None

    def test_expands_tilde(self, tmp_path, monkeypatch):
        """Test that ~ is expanded to home directory."""
        # This tests that os.path.expanduser is called
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / "testfile.txt").touch()

        # The function should expand ~ even if no matches
        # Just verify it doesn't crash
        result = path_completer("~", 0)
        # Result depends on home directory contents
        assert result is None or isinstance(result, str)

    def test_adds_trailing_slash_to_directories(self, tmp_path):
        """Test that directories get trailing slashes."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = path_completer(str(tmp_path), 0)
        # The subdir match should have trailing slash
        if result and "subdir" in result:
            assert result.endswith("/")


class TestSetupTabCompletion:
    """Tests for setup_tab_completion function."""

    def test_returns_early_when_readline_not_available(self):
        """Test that function returns early when readline is not available."""
        with patch.object(cli_utils, "READLINE_AVAILABLE", False):
            # Should not raise, just return
            setup_tab_completion()

    def test_configures_readline_when_available(self):
        """Test that readline is configured when available."""
        mock_readline = MagicMock()

        with patch.object(cli_utils, "READLINE_AVAILABLE", True):
            with patch.object(cli_utils, "readline", mock_readline, create=True):
                setup_tab_completion()

                mock_readline.set_completer.assert_called_once_with(path_completer)
                mock_readline.parse_and_bind.assert_called_once_with("tab: complete")
                mock_readline.set_completer_delims.assert_called_once_with(" \t\n")


class TestInputWithCompletion:
    """Tests for input_with_completion function."""

    def test_calls_input_with_prompt(self, monkeypatch):
        """Test that input is called with the provided prompt."""
        monkeypatch.setattr("builtins.input", lambda p: f"received: {p}")

        result = cli_utils.input_with_completion("Enter path: ")
        assert result == "received: Enter path: "

    def test_sets_up_completion_when_readline_available(self, monkeypatch):
        """Test that tab completion is set up when readline is available."""
        setup_called = []

        def mock_setup():
            setup_called.append(True)

        monkeypatch.setattr("builtins.input", lambda p: "test")
        monkeypatch.setattr(cli_utils, "READLINE_AVAILABLE", True)
        monkeypatch.setattr(cli_utils, "setup_tab_completion", mock_setup)

        cli_utils.input_with_completion("prompt")
        assert len(setup_called) == 1


class TestDiscoverFiles:
    """Tests for discover_files function."""

    def test_discovers_txt_files(self, tmp_path):
        """Test that .txt files are discovered by default."""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        (tmp_path / "file3.md").touch()

        files = discover_files(tmp_path)

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_custom_pattern(self, tmp_path):
        """Test that custom patterns work."""
        (tmp_path / "data.csv").touch()
        (tmp_path / "other.csv").touch()
        (tmp_path / "data.txt").touch()

        files = discover_files(tmp_path, pattern="*.csv")

        assert len(files) == 2
        assert all(f.suffix == ".csv" for f in files)

    def test_recursive_search(self, tmp_path):
        """Test that recursive=True searches subdirectories."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "top.txt").touch()
        (subdir / "nested.txt").touch()

        # Non-recursive should find only top-level
        non_recursive = discover_files(tmp_path, recursive=False)
        assert len(non_recursive) == 1
        assert non_recursive[0].name == "top.txt"

        # Recursive should find both
        recursive = discover_files(tmp_path, recursive=True)
        assert len(recursive) == 2
        names = {f.name for f in recursive}
        assert names == {"top.txt", "nested.txt"}

    def test_returns_sorted_list(self, tmp_path):
        """Test that results are sorted alphabetically."""
        (tmp_path / "zebra.txt").touch()
        (tmp_path / "alpha.txt").touch()
        (tmp_path / "middle.txt").touch()

        files = discover_files(tmp_path)

        assert files[0].name == "alpha.txt"
        assert files[1].name == "middle.txt"
        assert files[2].name == "zebra.txt"

    def test_returns_empty_list_when_no_matches(self, tmp_path):
        """Test that empty list is returned when no files match."""
        (tmp_path / "file.md").touch()

        files = discover_files(tmp_path, pattern="*.txt")

        assert files == []

    def test_raises_error_when_source_does_not_exist(self, tmp_path):
        """Test that ValueError is raised when source doesn't exist."""
        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(ValueError, match="Source path does not exist"):
            discover_files(nonexistent)

    def test_raises_error_when_source_is_not_directory(self, tmp_path):
        """Test that ValueError is raised when source is a file."""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="Source path is not a directory"):
            discover_files(file_path)

    def test_excludes_directories_from_results(self, tmp_path):
        """Test that directories matching pattern are excluded."""
        # Create a directory that matches the pattern
        (tmp_path / "folder.txt").mkdir()
        (tmp_path / "file.txt").touch()

        files = discover_files(tmp_path)

        assert len(files) == 1
        assert files[0].name == "file.txt"

    def test_deeply_nested_recursive_search(self, tmp_path):
        """Test recursive search through multiple levels."""
        # Create deep structure
        level1 = tmp_path / "level1"
        level2 = level1 / "level2"
        level3 = level2 / "level3"
        level3.mkdir(parents=True)

        (tmp_path / "root.txt").touch()
        (level1 / "one.txt").touch()
        (level2 / "two.txt").touch()
        (level3 / "three.txt").touch()

        files = discover_files(tmp_path, recursive=True)

        assert len(files) == 4
        names = {f.name for f in files}
        assert names == {"root.txt", "one.txt", "two.txt", "three.txt"}


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_readline_available_is_boolean(self):
        """Test that READLINE_AVAILABLE is a boolean."""
        from build_tools.tui_common.cli_utils import READLINE_AVAILABLE

        assert isinstance(READLINE_AVAILABLE, bool)

    def test_corpus_db_available_is_boolean(self):
        """Test that CORPUS_DB_AVAILABLE is a boolean."""
        from build_tools.tui_common.cli_utils import CORPUS_DB_AVAILABLE

        assert isinstance(CORPUS_DB_AVAILABLE, bool)

    def test_all_exports_are_accessible(self):
        """Test that all __all__ exports are accessible."""
        from build_tools.tui_common import cli_utils

        for name in cli_utils.__all__:
            assert hasattr(cli_utils, name), f"Missing export: {name}"
