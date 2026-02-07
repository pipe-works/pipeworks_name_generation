"""Web application for importing and browsing packaged name datasets.

This package provides:
- INI-based server configuration
- Auto port selection in the 8000 range
- SQLite persistence for imported package pairs
- HTTP API and simple browser UI for import operations
"""

from pipeworks_name_generation.webapp.config import ServerSettings, load_server_settings
from pipeworks_name_generation.webapp.server import (
    find_available_port,
    run_server,
    start_http_server,
)

__all__ = [
    "ServerSettings",
    "load_server_settings",
    "find_available_port",
    "start_http_server",
    "run_server",
]
