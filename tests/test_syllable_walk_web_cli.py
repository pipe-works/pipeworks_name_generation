"""Tests for syllable walker web CLI.

This module tests the command-line interface for the web server:
- Argument parsing (create_argument_parser, parse_arguments)
- Main entry point and error handling
- Module entry point (__main__)
- INI config loading (load_build_tools_settings)
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from build_tools.syllable_walk_web.cli import (
    BuildToolsSettings,
    create_argument_parser,
    load_build_tools_settings,
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

    def test_parser_has_config_argument(self):
        """Test parser has --config argument with default."""
        parser = create_argument_parser()
        args = parser.parse_args([])
        assert args.config == "server.ini"

    def test_parser_has_sessions_dir_argument(self):
        """Test parser has --sessions-dir argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--sessions-dir", "/tmp/sessions"])
        assert args.sessions_dir == "/tmp/sessions"

    def test_parser_config_custom_path(self):
        """Test parser accepts custom --config path."""
        parser = create_argument_parser()
        args = parser.parse_args(["--config", "my_config.ini"])
        assert args.config == "my_config.ini"

    def test_parser_default_values(self):
        """Test parser default values."""
        parser = create_argument_parser()
        args = parser.parse_args([])
        assert args.port is None
        assert args.quiet is False
        assert args.output_base is None
        assert args.sessions_dir is None
        assert args.config == "server.ini"


class TestParseArguments:
    """Test parse_arguments function."""

    def test_parse_no_args(self):
        """Test parsing with no arguments."""
        args = parse_arguments([])
        assert args.port is None
        assert args.quiet is False
        assert args.output_base is None
        assert args.sessions_dir is None
        assert args.config == "server.ini"

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

    def test_parse_config_arg(self):
        """Test parsing --config argument."""
        args = parse_arguments(["--config", "/etc/app.ini"])
        assert args.config == "/etc/app.ini"

    def test_parse_sessions_dir_arg(self):
        """Test parsing --sessions-dir argument."""
        args = parse_arguments(["--sessions-dir", "/tmp/sessions"])
        assert args.sessions_dir == "/tmp/sessions"

    def test_parse_all_args(self):
        """Test parsing all arguments together."""
        args = parse_arguments(
            [
                "--port",
                "9000",
                "--quiet",
                "--output-base",
                "/tmp",
                "--sessions-dir",
                "/tmp/sessions",
                "--config",
                "custom.ini",
            ]
        )
        assert args.port == 9000
        assert args.quiet is True
        assert args.output_base == "/tmp"
        assert args.sessions_dir == "/tmp/sessions"
        assert args.config == "custom.ini"

    def test_parse_invalid_port_raises(self):
        """Test that invalid port value raises error."""
        with pytest.raises(SystemExit):
            parse_arguments(["--port", "not-a-number"])


# ============================================================
# INI Config Loading Tests
# ============================================================


class TestLoadBuildToolsSettings:
    """Test load_build_tools_settings function."""

    def test_defaults_when_no_file(self, tmp_path: Path):
        """Missing config file should return default settings."""
        missing = tmp_path / "does-not-exist.ini"
        settings = load_build_tools_settings(missing)

        assert settings.output_base is None
        assert settings.corpus_dir_a is None
        assert settings.corpus_dir_b is None
        assert settings.sessions_dir is None
        assert settings.port is None
        assert settings.verbose is True

    def test_defaults_when_none(self):
        """None config path should return default settings."""
        settings = load_build_tools_settings(None)

        assert settings.output_base is None
        assert settings.corpus_dir_a is None
        assert settings.corpus_dir_b is None
        assert settings.sessions_dir is None
        assert settings.port is None
        assert settings.verbose is True

    def test_defaults_when_no_build_tools_section(self, tmp_path: Path):
        """INI without [build_tools] section should return defaults."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text("[webapp]\nhost = 127.0.0.1\n", encoding="utf-8")
        settings = load_build_tools_settings(ini_path)

        assert settings.output_base is None
        assert settings.corpus_dir_a is None
        assert settings.corpus_dir_b is None
        assert settings.sessions_dir is None
        assert settings.port is None
        assert settings.verbose is True

    def test_reads_all_values(self, tmp_path: Path):
        """All [build_tools] values should be parsed correctly."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "output_base = _working/output",
                    "sessions_dir = _working/sessions",
                    "corpus_dir_a = 20260121_084017_nltk",
                    "corpus_dir_b = 20260122_091500_pyphen",
                    "port = 9000",
                    "verbose = false",
                ]
            ),
            encoding="utf-8",
        )
        settings = load_build_tools_settings(ini_path)

        assert settings.output_base == Path("_working/output")
        assert settings.sessions_dir == Path("_working/sessions")
        assert settings.corpus_dir_a == "20260121_084017_nltk"
        assert settings.corpus_dir_b == "20260122_091500_pyphen"
        assert settings.port == 9000
        assert settings.verbose is False

    def test_blank_output_base_returns_none(self, tmp_path: Path):
        """Blank output_base should resolve to None."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "output_base =   ",
                    "port =",
                ]
            ),
            encoding="utf-8",
        )
        settings = load_build_tools_settings(ini_path)

        assert settings.output_base is None
        assert settings.port is None

    def test_blank_corpus_dirs_return_none(self, tmp_path: Path):
        """Blank corpus_dir_a and corpus_dir_b should resolve to None."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "corpus_dir_a =   ",
                    "corpus_dir_b =",
                ]
            ),
            encoding="utf-8",
        )
        settings = load_build_tools_settings(ini_path)

        assert settings.corpus_dir_a is None
        assert settings.corpus_dir_b is None

    def test_blank_sessions_dir_returns_none(self, tmp_path: Path):
        """Blank sessions_dir should resolve to None."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "sessions_dir =   ",
                ]
            ),
            encoding="utf-8",
        )
        settings = load_build_tools_settings(ini_path)

        assert settings.sessions_dir is None

    def test_corpus_dir_a_only(self, tmp_path: Path):
        """Setting only corpus_dir_a should leave corpus_dir_b as None."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "corpus_dir_a = 20260121_084017_nltk",
                ]
            ),
            encoding="utf-8",
        )
        settings = load_build_tools_settings(ini_path)

        assert settings.corpus_dir_a == "20260121_084017_nltk"
        assert settings.corpus_dir_b is None

    def test_expands_user_in_output_base(self, tmp_path: Path):
        """Tilde in output_base should be expanded."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "output_base = ~/my_output",
                ]
            ),
            encoding="utf-8",
        )
        settings = load_build_tools_settings(ini_path)

        assert settings.output_base == Path("~/my_output").expanduser()

    def test_expands_user_in_sessions_dir(self, tmp_path: Path):
        """Tilde in sessions_dir should be expanded."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "sessions_dir = ~/my_sessions",
                ]
            ),
            encoding="utf-8",
        )
        settings = load_build_tools_settings(ini_path)

        assert settings.sessions_dir == Path("~/my_sessions").expanduser()

    def test_returns_frozen_dataclass(self, tmp_path: Path):
        """Returned settings should be a frozen BuildToolsSettings instance."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text("[build_tools]\nverbose = true\n", encoding="utf-8")
        settings = load_build_tools_settings(ini_path)

        assert isinstance(settings, BuildToolsSettings)
        with pytest.raises(AttributeError):
            settings.verbose = False  # type: ignore[misc]


# ============================================================
# Main Function Tests (CLI overrides INI)
# ============================================================


class TestMain:
    """Test main entry point function.

    Note: run_server is imported locally inside main(), so the patch target
    is the source module (server), not the cli module.
    """

    def test_main_success(self):
        """Test main returns 0 on success."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            exit_code = main(["--config", "nonexistent.ini"])
            assert exit_code == 0
            mock_run.assert_called_once_with(
                port=None,
                verbose=True,
                output_base=None,
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_passes_port_to_server(self):
        """Test main passes port argument to run_server."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--port", "9000", "--config", "nonexistent.ini"])
            mock_run.assert_called_once_with(
                port=9000,
                verbose=True,
                output_base=None,
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_passes_quiet_to_server(self):
        """Test main passes quiet argument as verbose=False."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--quiet", "--config", "nonexistent.ini"])
            mock_run.assert_called_once_with(
                port=None,
                verbose=False,
                output_base=None,
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_passes_output_base_to_server(self):
        """Test main passes --output-base as a Path to run_server."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--output-base", "/tmp/output", "--config", "nonexistent.ini"])
            mock_run.assert_called_once_with(
                port=None,
                verbose=True,
                output_base=Path("/tmp/output"),
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_ini_provides_defaults(self, tmp_path: Path):
        """INI values should be used when CLI args are not provided."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "output_base = _working/output",
                    "port = 9500",
                    "verbose = false",
                ]
            ),
            encoding="utf-8",
        )

        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--config", str(ini_path)])
            mock_run.assert_called_once_with(
                port=9500,
                verbose=False,
                output_base=Path("_working/output"),
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_ini_passes_corpus_dirs(self, tmp_path: Path):
        """INI corpus_dir_a and corpus_dir_b should be passed to run_server."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "corpus_dir_a = 20260121_084017_nltk",
                    "corpus_dir_b = 20260122_091500_pyphen",
                ]
            ),
            encoding="utf-8",
        )

        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--config", str(ini_path)])
            mock_run.assert_called_once_with(
                port=None,
                verbose=True,
                output_base=None,
                sessions_dir=None,
                corpus_dir_a="20260121_084017_nltk",
                corpus_dir_b="20260122_091500_pyphen",
            )

    def test_main_cli_overrides_ini_port(self, tmp_path: Path):
        """CLI --port should override INI port value."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "port = 9500",
                ]
            ),
            encoding="utf-8",
        )

        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--port", "7000", "--config", str(ini_path)])
            mock_run.assert_called_once_with(
                port=7000,
                verbose=True,
                output_base=None,
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_cli_overrides_ini_output_base(self, tmp_path: Path):
        """CLI --output-base should override INI output_base value."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "output_base = _working/output",
                ]
            ),
            encoding="utf-8",
        )

        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--output-base", "/custom/path", "--config", str(ini_path)])
            mock_run.assert_called_once_with(
                port=None,
                verbose=True,
                output_base=Path("/custom/path"),
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_cli_quiet_overrides_ini_verbose(self, tmp_path: Path):
        """CLI --quiet should override INI verbose=true."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "verbose = true",
                ]
            ),
            encoding="utf-8",
        )

        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--quiet", "--config", str(ini_path)])
            mock_run.assert_called_once_with(
                port=None,
                verbose=False,
                output_base=None,
                sessions_dir=None,
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_passes_sessions_dir_to_server(self, tmp_path: Path):
        """CLI --sessions-dir should be forwarded to run_server as a Path."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--sessions-dir", str(tmp_path / "sessions"), "--config", "nonexistent.ini"])
            mock_run.assert_called_once_with(
                port=None,
                verbose=True,
                output_base=None,
                sessions_dir=tmp_path / "sessions",
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_ini_passes_sessions_dir(self, tmp_path: Path):
        """INI sessions_dir should be forwarded when CLI override is absent."""
        ini_path = tmp_path / "server.ini"
        ini_path.write_text(
            "\n".join(
                [
                    "[build_tools]",
                    "sessions_dir = /tmp/ini-sessions",
                ]
            ),
            encoding="utf-8",
        )
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=0) as mock_run:
            main(["--config", str(ini_path)])
            mock_run.assert_called_once_with(
                port=None,
                verbose=True,
                output_base=None,
                sessions_dir=Path("/tmp/ini-sessions"),
                corpus_dir_a=None,
                corpus_dir_b=None,
            )

    def test_main_oserror(self, capsys):
        """Test main handles OSError from run_server."""
        with patch(
            "build_tools.syllable_walk_web.server.run_server",
            side_effect=OSError("Address already in use"),
        ):
            exit_code = main(["--port", "5000", "--config", "nonexistent.ini"])
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
            exit_code = main(["--config", "nonexistent.ini"])
            assert exit_code == 130

    def test_main_general_exception(self, capsys):
        """Test main handles general exceptions."""
        with patch(
            "build_tools.syllable_walk_web.server.run_server",
            side_effect=RuntimeError("Something went wrong"),
        ):
            exit_code = main(["--config", "nonexistent.ini"])
            assert exit_code == 1

            captured = capsys.readouterr()
            assert "Error: Something went wrong" in captured.err

    def test_main_returns_server_exit_code(self):
        """Test main propagates the exit code from run_server."""
        with patch("build_tools.syllable_walk_web.server.run_server", return_value=1):
            exit_code = main(["--config", "nonexistent.ini"])
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
            patch("sys.argv", ["__main__", "--config", "nonexistent.ini"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            runpy.run_module("build_tools.syllable_walk_web", run_name="__main__", alter_sys=True)
        assert exc_info.value.code == 0

    def test_main_module_propagates_nonzero_exit(self):
        """Test __main__ propagates non-zero exit code from main()."""
        import runpy

        with (
            patch("build_tools.syllable_walk_web.server.run_server", return_value=1),
            patch("sys.argv", ["__main__", "--config", "nonexistent.ini"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            runpy.run_module("build_tools.syllable_walk_web", run_name="__main__", alter_sys=True)
        assert exc_info.value.code == 1
