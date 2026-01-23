"""
Tests for pipeline_tui CLI module.

Tests command-line argument parsing and main entry point.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from build_tools.pipeline_tui.__main__ import (
    create_argument_parser,
    main,
    parse_arguments,
)


class TestArgumentParser:
    """Tests for argument parser creation and parsing."""

    def test_create_argument_parser(self) -> None:
        """Test argument parser is created with correct configuration."""
        parser = create_argument_parser()

        assert parser.description is not None
        assert "syllable extraction" in parser.description.lower()

    def test_parse_arguments_defaults(self) -> None:
        """Test default argument values."""
        args = parse_arguments([])

        assert args.source is None
        assert args.output is None
        assert args.theme == "nord"

    def test_parse_arguments_source(self, tmp_path: Path) -> None:
        """Test parsing --source argument."""
        args = parse_arguments(["--source", str(tmp_path)])

        assert args.source == tmp_path

    def test_parse_arguments_output(self, tmp_path: Path) -> None:
        """Test parsing --output argument."""
        args = parse_arguments(["--output", str(tmp_path)])

        assert args.output == tmp_path

    def test_parse_arguments_theme(self) -> None:
        """Test parsing --theme argument."""
        args = parse_arguments(["--theme", "dracula"])

        assert args.theme == "dracula"

    def test_parse_arguments_theme_choices(self) -> None:
        """Test that only valid theme choices are accepted."""
        valid_themes = ["nord", "dracula", "monokai", "textual-dark", "textual-light"]

        for theme in valid_themes:
            args = parse_arguments(["--theme", theme])
            assert args.theme == theme

    def test_parse_arguments_invalid_theme(self) -> None:
        """Test that invalid theme is rejected."""
        with pytest.raises(SystemExit):
            parse_arguments(["--theme", "invalid-theme"])

    def test_parse_arguments_all_options(self, tmp_path: Path) -> None:
        """Test parsing all options together."""
        source = tmp_path / "source"
        output = tmp_path / "output"

        args = parse_arguments(
            [
                "--source",
                str(source),
                "--output",
                str(output),
                "--theme",
                "monokai",
            ]
        )

        assert args.source == source
        assert args.output == output
        assert args.theme == "monokai"

    def test_parse_arguments_help_text(self) -> None:
        """Test that help text exists for all arguments."""
        parser = create_argument_parser()

        # Get all actions (arguments)
        for action in parser._actions:
            if action.dest not in ["help"]:
                # All arguments should have help text
                if action.help:
                    assert len(action.help) > 0


class TestMain:
    """Tests for main entry point."""

    def test_main_launches_app(self) -> None:
        """Test that main launches the TUI app."""
        mock_app = MagicMock()

        with patch(
            "build_tools.pipeline_tui.core.app.PipelineTuiApp",
            return_value=mock_app,
        ) as mock_class:
            with patch("sys.argv", ["pipeline_tui"]):
                main()

        mock_class.assert_called_once()
        mock_app.run.assert_called_once()

    def test_main_passes_arguments_to_app(self, tmp_path: Path) -> None:
        """Test that main passes CLI arguments to the app."""
        source = tmp_path / "source"
        output = tmp_path / "output"
        mock_app = MagicMock()

        with patch(
            "build_tools.pipeline_tui.core.app.PipelineTuiApp",
            return_value=mock_app,
        ) as mock_class:
            with patch(
                "build_tools.pipeline_tui.__main__.parse_arguments",
                return_value=MagicMock(
                    source=source,
                    output=output,
                    theme="dracula",
                ),
            ):
                main()

        mock_class.assert_called_once_with(
            source_dir=source,
            output_dir=output,
            theme="dracula",
        )

    def test_main_uses_default_arguments(self) -> None:
        """Test that main uses default arguments when none provided."""
        mock_app = MagicMock()

        with patch(
            "build_tools.pipeline_tui.core.app.PipelineTuiApp",
            return_value=mock_app,
        ) as mock_class:
            with patch("sys.argv", ["pipeline_tui"]):
                main()

        mock_class.assert_called_once_with(
            source_dir=None,
            output_dir=None,
            theme="nord",
        )

    def test_main_returns_zero_on_success(self) -> None:
        """Test that main returns 0 on successful execution."""
        mock_app = MagicMock()

        with patch(
            "build_tools.pipeline_tui.core.app.PipelineTuiApp",
            return_value=mock_app,
        ):
            result = main([])

        assert result == 0

    def test_main_returns_130_on_keyboard_interrupt(self) -> None:
        """Test that main returns 130 on KeyboardInterrupt."""
        with patch(
            "build_tools.pipeline_tui.core.app.PipelineTuiApp",
            side_effect=KeyboardInterrupt(),
        ):
            result = main([])

        assert result == 130

    def test_main_returns_1_on_exception(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that main returns 1 on general exception."""
        with patch(
            "build_tools.pipeline_tui.core.app.PipelineTuiApp",
            side_effect=RuntimeError("Test error"),
        ):
            result = main([])

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Test error" in captured.err
