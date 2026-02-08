"""Configuration loading for the end-user name generator web application.

The application supports a small INI file so end users can set runtime values
without changing Python code. The most important setting is ``port``; when it
is omitted the server auto-selects a free port in the 8000 range.
"""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass, replace
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_DB_PATH = Path("pipeworks_name_generation/data/name_packages.sqlite3")


@dataclass(frozen=True)
class ServerSettings:
    """Server runtime settings.

    Attributes:
        host: Interface to bind (default localhost)
        port: Optional explicit port. ``None`` means auto-select.
        db_path: SQLite database file path
        verbose: Print startup/runtime messages when True
        serve_ui: When ``True``, serve UI/static routes in addition to the API.
    """

    host: str = DEFAULT_HOST
    port: int | None = None
    db_path: Path = DEFAULT_DB_PATH
    verbose: bool = True
    serve_ui: bool = True


def _coerce_port(raw_port: str | None) -> int | None:
    """Convert string port to int with validation.

    Args:
        raw_port: Port string from config

    Returns:
        Integer port, or ``None`` if blank

    Raises:
        ValueError: If the port is invalid
    """
    if raw_port is None:
        return None

    stripped = raw_port.strip()
    if not stripped:
        return None

    try:
        port = int(stripped)
    except ValueError as exc:
        raise ValueError(f"Invalid port value: {raw_port!r}") from exc

    if port < 1024 or port > 65535:
        raise ValueError("Port must be between 1024 and 65535")

    return port


def load_server_settings(config_path: Path | None) -> ServerSettings:
    """Load server settings from an INI file.

    The parser reads a ``[server]`` section with the following optional keys:
    ``host``, ``port``, ``db_path``, ``verbose``, and ``serve_ui``. An optional
    ``api_only`` flag can be used to force API-only mode and overrides
    ``serve_ui`` when set.

    Args:
        config_path: Path to INI file. If missing/None, defaults are used.

    Returns:
        Parsed ``ServerSettings`` instance

    Raises:
        ValueError: If a setting is syntactically invalid
    """
    settings = ServerSettings()

    if config_path is None or not config_path.exists():
        return settings

    parser = ConfigParser()
    parser.read(config_path, encoding="utf-8")

    if not parser.has_section("server"):
        return settings

    host = parser.get("server", "host", fallback=settings.host).strip() or settings.host
    port = _coerce_port(parser.get("server", "port", fallback=None))

    db_path_raw = parser.get("server", "db_path", fallback=str(settings.db_path)).strip()
    db_path = Path(db_path_raw).expanduser() if db_path_raw else settings.db_path

    verbose = parser.getboolean("server", "verbose", fallback=settings.verbose)
    serve_ui = parser.getboolean("server", "serve_ui", fallback=settings.serve_ui)
    api_only = parser.getboolean("server", "api_only", fallback=False)

    if api_only:
        serve_ui = False

    return ServerSettings(
        host=host,
        port=port,
        db_path=db_path,
        verbose=verbose,
        serve_ui=serve_ui,
    )


def apply_runtime_overrides(
    settings: ServerSettings,
    host: str | None,
    port: int | None,
    db_path: Path | None,
    verbose: bool | None,
    serve_ui: bool | None,
) -> ServerSettings:
    """Apply command-line overrides over loaded settings.

    Args:
        settings: Base settings (typically from INI)
        host: Optional host override
        port: Optional port override
        db_path: Optional database path override
        verbose: Optional verbose override
        serve_ui: Optional UI routing override

    Returns:
        Updated settings with overrides applied
    """
    result = settings

    if host is not None and host.strip():
        result = replace(result, host=host.strip())
    if port is not None:
        result = replace(result, port=port)
    if db_path is not None:
        result = replace(result, db_path=db_path.expanduser())
    if verbose is not None:
        result = replace(result, verbose=verbose)
    if serve_ui is not None:
        result = replace(result, serve_ui=serve_ui)

    return result
