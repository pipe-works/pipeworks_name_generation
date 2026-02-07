"""Tests for webapp CLI argument parsing and main dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pipeworks_name_generation.webapp.cli import (
    build_settings_from_args,
    create_argument_parser,
    main,
    parse_arguments,
)


def test_argument_parser_basics() -> None:
    """Parser should expose expected CLI flags."""
    parser = create_argument_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "8123", "--quiet"])
    assert args.host == "0.0.0.0"
    assert args.port == 8123
    assert args.quiet is True


def test_build_settings_from_args_uses_ini_and_overrides(tmp_path: Path) -> None:
    """CLI settings builder should merge INI values with command-line overrides."""
    config_path = tmp_path / "server.ini"
    config_path.write_text(
        "[server]\n"
        "host = 127.0.0.1\n"
        "port = 8008\n"
        "db_path = base.sqlite3\n"
        "verbose = true\n",
        encoding="utf-8",
    )

    parsed = parse_arguments(
        [
            "--config",
            str(config_path),
            "--port",
            "8099",
            "--db-path",
            str(tmp_path / "override.sqlite3"),
        ]
    )
    settings = build_settings_from_args(parsed)

    assert settings.host == "127.0.0.1"
    assert settings.port == 8099
    assert settings.db_path == (tmp_path / "override.sqlite3")


def test_main_invokes_run_server() -> None:
    """main() should invoke run_server and return success code."""
    with patch("pipeworks_name_generation.webapp.cli.run_server", return_value=0) as mock_run:
        exit_code = main([])

    assert exit_code == 0
    assert mock_run.call_count == 1


def test_main_returns_error_code_on_exception() -> None:
    """main() should return 1 when startup fails."""
    with patch(
        "pipeworks_name_generation.webapp.cli.run_server",
        side_effect=RuntimeError("boom"),
    ):
        exit_code = main([])

    assert exit_code == 1
