"""
Tests for syllable_walk_tui entry point.

Tests the main() function and exception handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from build_tools.syllable_walk_tui.__main__ import main


class TestMain:
    """Tests for main() entry point."""

    def test_main_returns_zero_on_success(self) -> None:
        """Test that main returns 0 on successful execution."""
        mock_app = MagicMock()

        with patch(
            "build_tools.syllable_walk_tui.__main__.SyllableWalkerApp",
            return_value=mock_app,
        ):
            result = main()

        assert result == 0
        mock_app.run.assert_called_once()

    def test_main_returns_130_on_keyboard_interrupt(self) -> None:
        """Test that main returns 130 on KeyboardInterrupt."""
        with patch(
            "build_tools.syllable_walk_tui.__main__.SyllableWalkerApp",
            side_effect=KeyboardInterrupt(),
        ):
            result = main()

        assert result == 130

    def test_main_returns_1_on_exception(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that main returns 1 on general exception."""
        with patch(
            "build_tools.syllable_walk_tui.__main__.SyllableWalkerApp",
            side_effect=RuntimeError("Test error"),
        ):
            result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Test error" in captured.err

    def test_main_accepts_args_parameter(self) -> None:
        """Test that main accepts args parameter (for CLI consistency)."""
        mock_app = MagicMock()

        with patch(
            "build_tools.syllable_walk_tui.__main__.SyllableWalkerApp",
            return_value=mock_app,
        ):
            # args are currently unused but should be accepted
            result = main(args=["--some-arg"])

        assert result == 0

    def test_main_app_run_raises_keyboard_interrupt(self) -> None:
        """Test KeyboardInterrupt during app.run() is handled."""
        mock_app = MagicMock()
        mock_app.run.side_effect = KeyboardInterrupt()

        with patch(
            "build_tools.syllable_walk_tui.__main__.SyllableWalkerApp",
            return_value=mock_app,
        ):
            result = main()

        assert result == 130

    def test_main_app_run_raises_exception(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test exception during app.run() is handled."""
        mock_app = MagicMock()
        mock_app.run.side_effect = RuntimeError("Runtime failure")

        with patch(
            "build_tools.syllable_walk_tui.__main__.SyllableWalkerApp",
            return_value=mock_app,
        ):
            result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Runtime failure" in captured.err
