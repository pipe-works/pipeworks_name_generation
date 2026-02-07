"""Tests for webapp configuration loading and runtime override behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeworks_name_generation.webapp.config import (
    DEFAULT_DB_PATH,
    DEFAULT_HOST,
    ServerSettings,
    _coerce_port,
    apply_runtime_overrides,
    load_server_settings,
)


def test_coerce_port_handles_blank_and_none() -> None:
    """Blank port values should be treated as auto-port (``None``)."""
    assert _coerce_port(None) is None
    assert _coerce_port("") is None
    assert _coerce_port("   ") is None


def test_coerce_port_rejects_invalid_values() -> None:
    """Invalid textual or out-of-range ports should raise ``ValueError``."""
    with pytest.raises(ValueError):
        _coerce_port("abc")
    with pytest.raises(ValueError):
        _coerce_port("1023")
    with pytest.raises(ValueError):
        _coerce_port("70000")


def test_load_server_settings_defaults_when_file_missing(tmp_path: Path) -> None:
    """Missing config file should return default server settings."""
    missing = tmp_path / "does-not-exist.ini"
    settings = load_server_settings(missing)

    assert settings.host == DEFAULT_HOST
    assert settings.port is None
    assert settings.db_path == DEFAULT_DB_PATH
    assert settings.verbose is True


def test_load_server_settings_reads_server_section(tmp_path: Path) -> None:
    """INI values in ``[server]`` should be parsed into ``ServerSettings``."""
    ini_path = tmp_path / "server.ini"
    ini_path.write_text(
        "\n".join(
            [
                "[server]",
                "host = 0.0.0.0",
                "port = 8111",
                "db_path = ~/pipeworks/test.sqlite3",
                "verbose = false",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_server_settings(ini_path)
    assert settings.host == "0.0.0.0"
    assert settings.port == 8111
    assert settings.db_path == Path("~/pipeworks/test.sqlite3").expanduser()
    assert settings.verbose is False


def test_load_server_settings_ignores_ini_without_server_section(tmp_path: Path) -> None:
    """INI files without ``[server]`` should fall back to defaults."""
    ini_path = tmp_path / "no-server-section.ini"
    ini_path.write_text("[other]\nkey = value\n", encoding="utf-8")
    settings = load_server_settings(ini_path)

    assert settings.host == DEFAULT_HOST
    assert settings.port is None
    assert settings.db_path == DEFAULT_DB_PATH
    assert settings.verbose is True


def test_apply_runtime_overrides_updates_selected_fields(tmp_path: Path) -> None:
    """CLI-style overrides should replace only the values that are provided."""
    base = ServerSettings()
    db_override = tmp_path / "db.sqlite3"

    updated = apply_runtime_overrides(
        base,
        host="127.0.0.2",
        port=8123,
        db_path=db_override,
        verbose=False,
    )

    assert updated.host == "127.0.0.2"
    assert updated.port == 8123
    assert updated.db_path == db_override
    assert updated.verbose is False


def test_apply_runtime_overrides_keeps_defaults_when_none() -> None:
    """``None`` overrides should preserve existing values."""
    base = ServerSettings(host="127.0.0.1", port=8010, db_path=Path("x.sqlite3"), verbose=True)

    updated = apply_runtime_overrides(
        base,
        host=None,
        port=None,
        db_path=None,
        verbose=None,
    )

    assert updated == base
