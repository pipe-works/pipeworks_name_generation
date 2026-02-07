"""Tests for web app configuration loading and override behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeworks_name_generation.webapp.config import (
    ServerSettings,
    apply_runtime_overrides,
    load_server_settings,
)


def test_load_server_settings_defaults_when_file_missing(tmp_path: Path) -> None:
    """Missing config file should produce default settings."""
    settings = load_server_settings(tmp_path / "missing.ini")
    assert settings.host == "127.0.0.1"
    assert settings.port is None
    assert settings.db_path == Path("pipeworks_name_generation.sqlite3")
    assert settings.verbose is True


def test_load_server_settings_from_ini(tmp_path: Path) -> None:
    """INI values should be parsed and returned in settings object."""
    config_path = tmp_path / "server.ini"
    config_path.write_text(
        "[server]\n"
        "host = 0.0.0.0\n"
        "port = 8123\n"
        "db_path = /tmp/custom.sqlite3\n"
        "verbose = false\n",
        encoding="utf-8",
    )

    settings = load_server_settings(config_path)

    assert settings.host == "0.0.0.0"
    assert settings.port == 8123
    assert settings.db_path == Path("/tmp/custom.sqlite3")
    assert settings.verbose is False


def test_load_server_settings_invalid_port_raises(tmp_path: Path) -> None:
    """Invalid configured ports should raise a clear ValueError."""
    config_path = tmp_path / "server.ini"
    config_path.write_text("[server]\nport = not-a-port\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid port value"):
        load_server_settings(config_path)


def test_apply_runtime_overrides() -> None:
    """CLI/runtime overrides should take precedence over base settings."""
    base = ServerSettings(host="127.0.0.1", port=None, db_path=Path("db.sqlite3"), verbose=True)

    result = apply_runtime_overrides(
        base,
        host="0.0.0.0",
        port=9001,
        db_path=Path("override.sqlite3"),
        verbose=False,
    )

    assert result.host == "0.0.0.0"
    assert result.port == 9001
    assert result.db_path == Path("override.sqlite3")
    assert result.verbose is False
