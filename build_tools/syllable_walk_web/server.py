"""
HTTP server for the Pipe-Works Build Tools web application.

Serves static frontend assets and provides a JSON API for pipeline
and walker operations. Uses Python stdlib only (no frameworks).
"""

from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from build_tools.syllable_walk_web.state import ServerState

# Ensure .woff2 is recognized
mimetypes.add_type("font/woff2", ".woff2")


# ── Paths ────────────────────────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"


# ── Request Handler ──────────────────────────────────────────────────────────


class CorpusBuilderHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Corpus Builder web app.

    Serves static files from the ``static/`` directory and routes
    ``/api/*`` requests to the appropriate handlers.
    """

    server_version = "PipeWorksCorpusBuilder/0.1"
    verbose: bool = True
    state: ServerState = ServerState()

    # ── HTTP method dispatch ─────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Root → index.html
        if path == "/":
            self._serve_static("index.html")
            return

        # Static files
        if path.startswith("/static/"):
            rel_path = path[len("/static/") :]
            self._serve_static(rel_path)
            return

        # API routes
        if path.startswith("/api/"):
            self._route_get(path)
            return

        self._send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self._route_post(path)
            return

        self._send_error(404, "Not found")

    # ── Static file serving ──────────────────────────────────────────────

    def _serve_static(self, rel_path: str) -> None:
        """Serve a file from the static directory."""
        # resolve() canonicalises the path, stripping ".." segments.  The
        # startswith() check below is the actual directory-traversal guard:
        # it ensures the resolved path stays within STATIC_DIR.
        try:
            file_path = (STATIC_DIR / rel_path).resolve()
        except (ValueError, OSError):
            self._send_error(400, "Invalid path")
            return

        if not str(file_path).startswith(str(STATIC_DIR.resolve())):
            self._send_error(403, "Forbidden")
            return

        if not file_path.is_file():
            self._send_error(404, f"Not found: {rel_path}")
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        try:
            data = file_path.read_bytes()
        except OSError:
            self._send_error(500, "Read error")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        # no-cache prevents stale static assets during development.
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # ── API routing ─────────────────────────────────────────────────────

    def _route_get(self, path: str) -> None:
        """Route GET /api/* requests."""
        # Lazy imports avoid circular dependencies: api modules import from
        # state.py, and this module creates ServerState at class level.
        from build_tools.syllable_walk_web.api.pipeline import (
            handle_runs,
            handle_status,
        )
        from build_tools.syllable_walk_web.api.walker import (
            handle_analysis,
            handle_sessions,
            handle_stats,
        )

        # Pipeline
        if path == "/api/pipeline/runs":
            from urllib.parse import parse_qs
            from urllib.parse import urlparse as _urlparse

            qs = parse_qs(_urlparse(self.path).query)
            patch = qs.get("patch", [None])[0]
            self._send_json(handle_runs(self.state, patch=patch))
            return
        if path == "/api/pipeline/status":
            self._send_json(handle_status(self.state))
            return

        # Walker
        if path == "/api/walker/stats":
            self._send_json(handle_stats(self.state))
            return
        if path == "/api/walker/sessions":
            result = handle_sessions(self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path.startswith("/api/walker/analysis/"):
            patch_key = path.split("/")[-1]
            result = handle_analysis(patch_key, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/name-classes":
            from build_tools.syllable_walk_web.services.selector_runner import (
                list_name_classes,
            )

            self._send_json({"classes": list_name_classes()})
            return

        # Settings
        if path == "/api/settings":
            from build_tools.syllable_walk_web.services.session_paths import (
                resolve_sessions_base,
            )

            self._send_json(
                {
                    "output_base": str(self.state.output_base.resolve()),
                    "sessions_base": str(
                        resolve_sessions_base(
                            output_base=self.state.output_base,
                            configured_sessions_base=self.state.sessions_base,
                        )
                    ),
                }
            )
            return

        # Version — reads from pipeworks_name_generation.__version__
        if path == "/api/version":
            from pipeworks_name_generation import __version__

            self._send_json({"version": __version__})
            return

        self._send_error(404, f"Unknown API route: {path}")

    def _route_post(self, path: str) -> None:
        """Route POST /api/* requests."""
        # Lazy imports — see _route_get comment.
        from build_tools.syllable_walk_web.api.browse import handle_browse_directory
        from build_tools.syllable_walk_web.api.pipeline import (
            handle_cancel,
            handle_start,
        )
        from build_tools.syllable_walk_web.api.walker import (
            handle_combine,
            handle_export,
            handle_load_corpus,
            handle_load_session,
            handle_package,
            handle_reach_syllables,
            handle_rebuild_reach_cache,
            handle_save_session,
            handle_select,
            handle_walk,
        )

        # Shared
        if path == "/api/browse-directory":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_browse_directory(body)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return

        # Settings
        if path == "/api/settings/output-base":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            new_path = body.get("path")
            if not new_path:
                self._send_error(400, "Missing path")
                return
            resolved = Path(new_path).expanduser().resolve()
            if not resolved.is_dir():
                self._send_json({"error": f"Not a directory: {new_path}"}, status=400)
                return
            self.state.output_base = resolved
            from build_tools.syllable_walk_web.services.session_paths import (
                resolve_sessions_base,
            )

            self._send_json(
                {
                    "output_base": str(resolved),
                    "sessions_base": str(
                        resolve_sessions_base(
                            output_base=self.state.output_base,
                            configured_sessions_base=self.state.sessions_base,
                        )
                    ),
                }
            )
            return

        # Pipeline
        if path == "/api/pipeline/start":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_start(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/pipeline/cancel":
            result = handle_cancel(self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return

        # Walker
        if path == "/api/walker/load-corpus":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_load_corpus(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/save-session":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_save_session(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/load-session":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_load_session(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/walk":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_walk(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/combine":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_combine(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/reach-syllables":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_reach_syllables(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/rebuild-reach-cache":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_rebuild_reach_cache(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/select":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_select(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/export":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            result = handle_export(body, self.state)
            status = 400 if "error" in result else 200
            self._send_json(result, status=status)
            return
        if path == "/api/walker/package":
            body = self._read_json_body()
            if body is None:
                self._send_error(400, "Invalid JSON")
                return
            zip_bytes, filename, error = handle_package(body, self.state)
            if error:
                self._send_json({"error": error}, status=400)
                return
            self._send_zip(zip_bytes, filename)
            return

        self._send_error(404, f"Unknown API route: {path}")

    # ── Response helpers ─────────────────────────────────────────────────

    def _send_json(self, data: Any, *, status: int = 200) -> None:
        """Send a JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, message: str) -> None:
        """Send a JSON error response."""
        self._send_json({"error": message}, status=status)

    def _send_zip(self, data: bytes, filename: str) -> None:
        """Send a ZIP file as a downloadable attachment."""
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict | None:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            raw = self.rfile.read(content_length)
            result: dict = json.loads(raw)
            return result
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    # ── Logging ──────────────────────────────────────────────────────────

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Override to respect verbose flag."""
        if self.verbose:
            super().log_message(format, *args)  # type: ignore[no-any-return]


# ── Server lifecycle ─────────────────────────────────────────────────────────


def find_available_port(start: int = 8000, max_tries: int = 100) -> int | None:
    """Find an available port starting from *start*.

    Tries ports ``start`` through ``start + max_tries - 1``.
    Returns the first available port, or ``None`` if none found.
    """
    import socket

    for port in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    return None


def run_server(
    port: int | None = None,
    verbose: bool = True,
    output_base: Path | None = None,
    sessions_dir: Path | None = None,
    corpus_dir_a: str | None = None,
    corpus_dir_b: str | None = None,
) -> int:
    """Start the HTTP server.

    Args:
        port: Port to listen on. If ``None``, auto-discovers from 8000.
        verbose: If ``True``, log HTTP requests to stderr.
        output_base: Base path for pipeline run discovery.
            Defaults to ``_working/output``.
        sessions_dir: Optional explicit directory for saved walker sessions.
            Defaults to ``None`` (callers derive ``output_base/sessions``).
        corpus_dir_a: Run discovery directory for Patch A.
        corpus_dir_b: Run discovery directory for Patch B.

    Returns:
        Exit code: 0 for clean shutdown, 1 for error.
    """
    if port is None:
        port = find_available_port()
        if port is None:
            print("Error: could not find an available port (tried 8000-8099)", file=sys.stderr)
            return 1

    # State is stored as class attributes (not instance attributes) because
    # BaseHTTPRequestHandler creates a new handler instance per request.
    # Shared state must therefore live on the class itself.
    CorpusBuilderHandler.verbose = verbose
    if output_base is not None:
        CorpusBuilderHandler.state = ServerState(output_base=output_base)
    else:
        CorpusBuilderHandler.state = ServerState()
    if sessions_dir is not None:
        CorpusBuilderHandler.state.sessions_base = sessions_dir.expanduser().resolve()

    # Per-patch corpus directories from INI config.
    if corpus_dir_a:
        CorpusBuilderHandler.state.corpus_dir_a = Path(corpus_dir_a)
    if corpus_dir_b:
        CorpusBuilderHandler.state.corpus_dir_b = Path(corpus_dir_b)

    # ThreadingHTTPServer (not plain HTTPServer) handles requests
    # concurrently — needed because the browser may have multiple pending
    # XHR requests (e.g. polling pipeline status while loading analysis).
    server = ThreadingHTTPServer(("", port), CorpusBuilderHandler)

    if verbose:
        print(f"Pipe-Works Build Tools — serving on http://localhost:{port}")
        print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if verbose:
            print("\nShutting down.")
        server.shutdown()
    return 0
