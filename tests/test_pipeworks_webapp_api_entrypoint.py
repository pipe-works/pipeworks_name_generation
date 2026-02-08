"""Tests for the API-only webapp entrypoint module."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from pipeworks_name_generation.webapp import api as api_module


def test_api_build_settings_forces_api_only(tmp_path: Path) -> None:
    """API entrypoint should disable UI even if config enables it."""
    ini_path = tmp_path / "server.ini"
    ini_path.write_text("[server]\nserve_ui = true\n", encoding="utf-8")

    args = type(
        "Args",
        (),
        {
            "config": str(ini_path),
            "host": None,
            "port": None,
            "favorites_db": None,
            "quiet": False,
            "api_only": False,
        },
    )()

    settings = api_module.build_settings_from_args(args)
    assert settings.serve_ui is False


def test_api_argument_parser_metadata() -> None:
    """API parser should advertise the API-specific program name."""
    parser = api_module.create_argument_parser()
    assert parser.prog == "pipeworks-name-api"
    assert "API server" in (parser.description or "")


def test_api_parse_arguments_reads_config() -> None:
    """Parser should accept config path overrides."""
    args = api_module.parse_arguments(["--config", "server.ini"])
    assert str(args.config).endswith("server.ini")


def test_api_main_delegates_to_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Main entrypoint should delegate to the shared CLI wrapper."""
    calls: dict[str, object] = {}

    def fake_main(
        argv,
        *,
        parse_args,
        build_settings,
        run,
        printer,
    ):
        calls["argv"] = argv
        calls["parse_args"] = parse_args
        calls["build_settings"] = build_settings
        calls["run"] = run
        calls["printer"] = printer
        return 0

    monkeypatch.setattr(api_module.webapp_cli, "main", fake_main)
    result = api_module.main(["--config", "server.ini"])
    assert result == 0
    assert calls["parse_args"] is api_module.parse_arguments
    assert calls["build_settings"] is api_module.build_settings_from_args
    assert calls["run"] is api_module.run_server


def test_api_module_dunder_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the module as __main__ should exit cleanly via SystemExit."""

    def fake_main(
        argv,
        *,
        parse_args,
        build_settings,
        run,
        printer,
    ) -> int:
        return 0

    monkeypatch.setattr(api_module.webapp_cli, "main", fake_main)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("pipeworks_name_generation.webapp.api", run_name="__main__")
    assert exc.value.code == 0
