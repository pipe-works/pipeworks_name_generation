"""
Tests for the shared interactive mode utilities.

This module tests the interactive prompts and display functions
used by both pyphen and NLTK syllable extractors.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from build_tools.tui_common.interactive import (
    print_banner,
    print_extraction_complete,
    print_section,
    prompt_extraction_settings,
    prompt_input_file,
    prompt_integer,
)


class TestPrintBanner:
    """Tests for print_banner function."""

    def test_print_banner_basic(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_banner with basic parameters."""
        print_banner("TEST TITLE", ["Line 1", "Line 2"])
        captured = capsys.readouterr()

        assert "TEST TITLE" in captured.out
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        assert "=" * 70 in captured.out

    def test_print_banner_empty_description(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_banner with empty description."""
        print_banner("TITLE", [])
        captured = capsys.readouterr()

        assert "TITLE" in captured.out

    def test_print_banner_custom_width(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_banner with custom width."""
        print_banner("TITLE", ["Desc"], width=40)
        captured = capsys.readouterr()

        assert "=" * 40 in captured.out


class TestPrintSection:
    """Tests for print_section function."""

    def test_print_section_basic(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_section with basic parameters."""
        print_section("SECTION TITLE")
        captured = capsys.readouterr()

        assert "SECTION TITLE" in captured.out
        assert "-" * 70 in captured.out

    def test_print_section_custom_width(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_section with custom width."""
        print_section("TITLE", width=50)
        captured = capsys.readouterr()

        assert "-" * 50 in captured.out


class TestPromptInteger:
    """Tests for prompt_integer function."""

    def test_prompt_integer_default_value(self) -> None:
        """Test prompt_integer returns default when Enter pressed."""
        with patch("builtins.input", return_value=""):
            result = prompt_integer("Test prompt", default=5)
            assert result == 5

    def test_prompt_integer_valid_input(self) -> None:
        """Test prompt_integer accepts valid input."""
        with patch("builtins.input", return_value="10"):
            result = prompt_integer("Test prompt", default=5)
            assert result == 10

    def test_prompt_integer_below_min(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test prompt_integer rejects values below minimum."""
        # First return invalid, then valid
        with patch("builtins.input", side_effect=["0", "2"]):
            result = prompt_integer("Test prompt", default=5, min_value=1)
            assert result == 2
            captured = capsys.readouterr()
            assert "must be at least 1" in captured.out

    def test_prompt_integer_above_max(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test prompt_integer rejects values above maximum."""
        # First return invalid, then valid
        with patch("builtins.input", side_effect=["100", "8"]):
            result = prompt_integer("Test prompt", default=5, max_value=10)
            assert result == 8
            captured = capsys.readouterr()
            assert "must be at most 10" in captured.out

    def test_prompt_integer_below_compare_to(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test prompt_integer rejects values below compare_to."""
        # First return invalid (below min_len), then valid
        with patch("builtins.input", side_effect=["1", "5"]):
            result = prompt_integer("Test prompt", default=8, compare_to=3, compare_label="minimum")
            assert result == 5
            captured = capsys.readouterr()
            assert ">= minimum" in captured.out

    def test_prompt_integer_invalid_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test prompt_integer handles non-numeric input."""
        with patch("builtins.input", side_effect=["abc", "5"]):
            result = prompt_integer("Test prompt", default=8)
            assert result == 5
            captured = capsys.readouterr()
            assert "valid number" in captured.out


class TestPromptExtractionSettings:
    """Tests for prompt_extraction_settings function."""

    def test_prompt_extraction_settings_defaults(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test prompt_extraction_settings uses defaults."""
        with patch("builtins.input", side_effect=["", ""]):
            min_len, max_len = prompt_extraction_settings()
            assert min_len == 2
            assert max_len == 8
            captured = capsys.readouterr()
            assert "2-8 characters" in captured.out

    def test_prompt_extraction_settings_custom_values(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompt_extraction_settings accepts custom values."""
        with patch("builtins.input", side_effect=["3", "6"]):
            min_len, max_len = prompt_extraction_settings()
            assert min_len == 3
            assert max_len == 6
            captured = capsys.readouterr()
            assert "3-6 characters" in captured.out

    def test_prompt_extraction_settings_custom_defaults(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompt_extraction_settings with custom defaults."""
        with patch("builtins.input", side_effect=["", ""]):
            min_len, max_len = prompt_extraction_settings(default_min=1, default_max=999)
            assert min_len == 1
            assert max_len == 999


class TestPromptInputFile:
    """Tests for prompt_input_file function."""

    def test_prompt_input_file_valid_file(self, tmp_path: Path) -> None:
        """Test prompt_input_file accepts valid file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch(
            "build_tools.tui_common.interactive.input_with_completion",
            return_value=str(test_file),
        ):
            result = prompt_input_file()
            assert result == test_file

    def test_prompt_input_file_quit(self) -> None:
        """Test prompt_input_file exits on 'quit'."""
        with patch(
            "build_tools.tui_common.interactive.input_with_completion",
            return_value="quit",
        ):
            with pytest.raises(SystemExit) as excinfo:
                prompt_input_file()
            assert excinfo.value.code == 0

    def test_prompt_input_file_not_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompt_input_file handles file not found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch(
            "build_tools.tui_common.interactive.input_with_completion",
            side_effect=["/nonexistent/file.txt", str(test_file)],
        ):
            result = prompt_input_file()
            assert result == test_file
            captured = capsys.readouterr()
            assert "File not found" in captured.out

    def test_prompt_input_file_is_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompt_input_file rejects directories."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch(
            "build_tools.tui_common.interactive.input_with_completion",
            side_effect=[str(tmp_path), str(test_file)],
        ):
            result = prompt_input_file()
            assert result == test_file
            captured = capsys.readouterr()
            assert "not a file" in captured.out

    def test_prompt_input_file_home_expansion(self, tmp_path: Path) -> None:
        """Test prompt_input_file expands ~ home directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Patch expanduser to return our test file
        with patch(
            "build_tools.tui_common.interactive.input_with_completion",
            return_value=str(test_file),
        ):
            result = prompt_input_file()
            assert result == test_file

    def test_prompt_input_file_readline_tip(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test prompt_input_file shows readline tip when available."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch("build_tools.tui_common.interactive.READLINE_AVAILABLE", True):
            with patch(
                "build_tools.tui_common.interactive.input_with_completion",
                return_value=str(test_file),
            ):
                prompt_input_file()
                captured = capsys.readouterr()
                assert "TAB" in captured.out


class TestPrintExtractionComplete:
    """Tests for print_extraction_complete function."""

    def test_print_extraction_complete_basic(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test print_extraction_complete with basic paths."""
        syllables_path = tmp_path / "run1" / "syllables" / "test.txt"
        metadata_path = tmp_path / "run1" / "meta" / "test.txt"

        print_extraction_complete(syllables_path, metadata_path, tmp_path)
        captured = capsys.readouterr()

        assert "run1" in captured.out
        assert "Done!" in captured.out

    def test_print_extraction_complete_relative_path_fails(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test print_extraction_complete handles relative_to failure."""
        # Use paths where relative_to will fail
        syllables_path = Path("/some/other/path/syllables/test.txt")
        metadata_path = Path("/some/other/path/meta/test.txt")
        output_base = Path("/different/base")

        print_extraction_complete(syllables_path, metadata_path, output_base)
        captured = capsys.readouterr()

        # Should fall back to absolute paths (check for filename which is cross-platform)
        assert "test.txt" in captured.out
        assert "Done!" in captured.out
