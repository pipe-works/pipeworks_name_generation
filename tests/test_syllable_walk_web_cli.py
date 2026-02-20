"""Tests for syllable walker web CLI.

This module tests the command-line interface for the web server:
- Argument parsing (create_argument_parser, parse_arguments)
- Main entry point and error handling
- Module entry point (__main__)
"""

from unittest.mock import patch

import pytest

from build_tools.syllable_walk_web.cli import (
    create_argument_parser,
    main,
    parse_arguments,
)

# ============================================================
# Argument Parser Tests
# ============================================================


class TestCreateArgumentParser:
    """Test create_argument_parser function."""

    def test_parser_creation(self):
        """Test parser can be created."""
        parser = create_argument_parser()
        assert parser is not None
        assert parser.description is not None
        assert "syllable" in str(parser.description).lower()

    def test_parser_has_port_argument(self):
        """Test parser has --port argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--port", "9000"])
        assert args.port == 9000

    def test_parser_has_quiet_argument(self):
        """Test parser has --quiet argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--quiet"])
        assert args.quiet is True

    def test_parser_has_output_base_argument(self):
        """Test parser has --output-base argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--output-base", "/tmp/output"])
        assert args.output_base == "/tmp/output"

    def test_parser_default_values(self):
        """Test parser default values."""
        parser = create_argument_parser()
        args = parser.parse_args([])
        assert args.port is None
        assert args.quiet is False
        assert args.output_base is None


class TestParseArguments:
    """Test parse_arguments function."""

    def test_parse_no_args(self):
        """Test parsing with no arguments."""
        args = parse_arguments([])
        assert args.port is None
        assert args.quiet is False
        assert args.output_base is None

    def test_parse_port_arg(self):
        """Test parsing --port argument."""
        args = parse_arguments(["--port", "8080"])
        assert args.port == 8080

    def test_parse_quiet_arg(self):
        """Test parsing --quiet argument."""
        args = parse_arguments(["--quiet"])
        assert args.quiet is True

    def test_parse_output_base_arg(self):
        """Test parsing --output-base argument."""
        args = parse_arguments(["--output-base", "/tmp/test"])
        assert args.output_base == "/tmp/test"

    def test_parse_all_args(self):
        """Test parsing all arguments together."""
        args = parse_arguments(["--port", "9000", "--quiet", "--output-base", "/tmp"])
        assert args.port == 9000
        assert args.quiet is True
        assert args.output_base == "/tmp"

    def test_parse_invalid_port_raises(self):
        """Test that invalid port value raises error."""
        with pytest.raises(SystemExit):
            parse_arguments(["--port", "not-a-number"])


# ============================================================
# Main Function Tests
# ============================================================


class TestMain:
    """Test main entry point function.

    Note: run_server is imported locally inside main(), so the patch target
    is the source module (server), not the cli module.
    """

    def test_main_success(self):
        """Test main returns 0 on success."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            exit_code = main([])
            assert exit_code == 0
            mock_run.assert_called_once_with(port=None, verbose=True, output_base=None)

    def test_main_passes_port_to_server(self):
        """Test main passes port argument to run_server."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--port", "9000"])
            mock_run.assert_called_once_with(port=9000, verbose=True, output_base=None)

    def test_main_passes_quiet_to_server(self):
        """Test main passes quiet argument as verbose=False."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--quiet"])
            mock_run.assert_called_once_with(port=None, verbose=False, output_base=None)

    def test_main_passes_output_base_to_server(self):
        """Test main passes --output-base as a Path to run_server."""
        from pathlib import Path

        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--output-base", "/tmp/output"])
            mock_run.assert_called_once_with(
                port=None, verbose=True, output_base=Path("/tmp/output")
            )

    def test_main_oserror(self, capsys):
        """Test main handles OSError from run_server."""
        with patch(
            "build_tools.syllable_walk_web.server.run_server",
            side_effect=OSError("Address already in use"),
        ):
            exit_code = main(["--port", "5000"])
            assert exit_code == 1

            captured = capsys.readouterr()
            assert "Error:" in captured.err
            assert "Address already in use" in captured.err

    def test_main_keyboard_interrupt(self):
        """Test main handles KeyboardInterrupt with exit code 130."""
        with patch(
            "build_tools.syllable_walk_web.server.run_server",
            side_effect=KeyboardInterrupt(),
        ):
            exit_code = main([])
            assert exit_code == 130

    def test_main_general_exception(self, capsys):
        """Test main handles general exceptions."""
        with patch(
            "build_tools.syllable_walk_web.server.run_server",
            side_effect=RuntimeError("Something went wrong"),
        ):
            exit_code = main([])
            assert exit_code == 1

            captured = capsys.readouterr()
            assert "Error: Something went wrong" in captured.err

    def test_main_returns_server_exit_code(self):
        """Test main propagates the exit code from run_server."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=1):
            exit_code = main([])
            assert exit_code == 1


# ============================================================
# Module Entry Point Tests
# ============================================================


class TestModuleEntryPoint:
    """Test __main__.py module entry point.

    The ``__main__.py`` file calls ``sys.exit(main())`` at module level, so
    importing it directly triggers execution.  Tests must patch run_server
    and catch SystemExit.
    """

    def test_main_module_executes_via_runpy(self):
        """Test running __main__ via runpy calls main() and sys.exit."""
        import runpy

        with (
            patch("build_tools.syllable_walk_web.server.run_server", return_value=0),
            patch("sys.argv", ["__main__"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            runpy.run_module("build_tools.syllable_walk_web", run_name="__main__", alter_sys=True)
        assert exc_info.value.code == 0

    def test_main_module_propagates_nonzero_exit(self):
        """Test __main__ propagates non-zero exit code from main()."""
        import runpy

        with (
            patch("build_tools.syllable_walk_web.server.run_server", return_value=1),
            patch("sys.argv", ["__main__"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            runpy.run_module("build_tools.syllable_walk_web", run_name="__main__", alter_sys=True)
        assert exc_info.value.code == 1
