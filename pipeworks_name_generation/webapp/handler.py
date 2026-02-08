"""HTTP request handler for Pipeworks webapp endpoints.

The handler intentionally focuses on transport concerns:

- request logging policy
- JSON/text response helpers
- one-time schema bootstrap guard
- GET/POST dispatch through route registries

Route-specific behavior lives in ``endpoint_adapters.py`` and ``routes/*``.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from pipeworks_name_generation.webapp import endpoint_adapters
from pipeworks_name_generation.webapp.db import initialize_schema as _initialize_schema
from pipeworks_name_generation.webapp.favorites import (
    initialize_favorites_schema as _initialize_favorites_schema,
)
from pipeworks_name_generation.webapp.http import read_json_body, send_bytes, send_json, send_text
from pipeworks_name_generation.webapp.route_registry import GET_ROUTE_METHODS, POST_ROUTE_METHODS


class WebAppHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the tabbed web UI and JSON API.

    Class attributes ``verbose`` and ``db_path`` are injected at startup by
    :func:`pipeworks_name_generation.webapp.server.create_handler_class`.
    """

    verbose: bool = True
    db_path: Path = Path("pipeworks_name_generation/data/name_packages.sqlite3")
    favorites_db_path: Path = Path("pipeworks_name_generation/data/user_favorites.sqlite3")
    schema_ready: bool = False
    schema_initialized_paths: set[str] = set()
    favorites_schema_ready: bool = False
    favorites_schema_initialized_paths: set[str] = set()
    # Route maps are class attributes so API-only mode can swap them at startup.
    get_routes: dict[str, str] = GET_ROUTE_METHODS
    post_routes: dict[str, str] = POST_ROUTE_METHODS

    def _ensure_schema(self, conn: Any) -> None:
        """Initialize schema once per handler class and DB path.

        The runtime server initializes schema at startup. This method keeps the
        request path resilient for unit-test harnesses and direct handler use,
        without re-running schema DDL for every request.
        """
        handler_type = type(self)
        db_path_key = str(Path(self.db_path).expanduser().resolve())
        if db_path_key in handler_type.schema_initialized_paths:
            handler_type.schema_ready = True
            return
        _initialize_schema(conn)
        handler_type.schema_initialized_paths.add(db_path_key)
        handler_type.schema_ready = True

    def _ensure_favorites_schema(self, conn: Any) -> None:
        """Initialize favorites schema once per handler class and DB path."""
        handler_type = type(self)
        db_path_key = str(Path(self.favorites_db_path).expanduser().resolve())
        if db_path_key in handler_type.favorites_schema_initialized_paths:
            handler_type.favorites_schema_ready = True
            return
        _initialize_favorites_schema(conn)
        handler_type.favorites_schema_initialized_paths.add(db_path_key)
        handler_type.favorites_schema_ready = True

    def log_message(self, format: str, *args: Any) -> None:
        """Emit request logs only when verbose mode is enabled."""
        if self.verbose:
            super().log_message(format, *args)

    def _send_text(self, content: str, status: int = 200, content_type: str = "text/plain") -> None:
        """Send a UTF-8 text response."""
        send_text(self, content, status=status, content_type=content_type)

    def _send_bytes(
        self,
        payload: bytes,
        status: int = 200,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Send a binary response."""
        send_bytes(self, payload, status=status, content_type=content_type)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        """Send a JSON response."""
        send_json(self, payload, status=status)

    def _read_json_body(self) -> dict[str, Any]:
        """Read request JSON body and return object payload."""
        return read_json_body(self)

    def do_GET(self) -> None:  # noqa: N802
        """Handle all supported ``GET`` routes."""
        parsed = urlsplit(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)
        method_name = type(self).get_routes.get(route)
        if method_name is None:
            if route.startswith("/static/fonts/"):
                # Serve bundled font files without listing each one in the route registry.
                endpoint_adapters.get_static_font(self, route)
                return
            self.send_error(404, "Not Found")
            return

        route_handler = getattr(endpoint_adapters, method_name)
        route_handler(self, query)

    def do_POST(self) -> None:  # noqa: N802
        """Handle all supported ``POST`` routes."""
        route = urlsplit(self.path).path
        method_name = type(self).post_routes.get(route)
        if method_name is None:
            self.send_error(404, "Not Found")
            return

        route_handler = getattr(endpoint_adapters, method_name)
        route_handler(self)
