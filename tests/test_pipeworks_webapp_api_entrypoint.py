"""Tests for the API-only webapp entrypoint module."""

from __future__ import annotations

from pathlib import Path

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
            "quiet": False,
            "api_only": False,
        },
    )()

    settings = api_module.build_settings_from_args(args)
    assert settings.serve_ui is False
