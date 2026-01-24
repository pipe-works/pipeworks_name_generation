"""HTTP server for the simplified syllable walker web interface.

This module provides a web-based interface for browsing name selections and
exploring syllable walks using the standard library's http.server module.

The server handles:
- Serving the HTML interface (/)
- Serving CSS styles (/styles.css)
- Listing available pipeline runs (/api/runs)
- Loading selection data (/api/runs/{id}/selections/{name_class})
- Generating syllable walks (/api/walk)

Usage::

    from build_tools.syllable_walk_web.server import run_server
    run_server(port=8000)
"""

from __future__ import annotations

import json
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from build_tools.syllable_walk.db import load_syllables
from build_tools.syllable_walk.walker import SyllableWalker
from build_tools.syllable_walk_web.run_discovery import (
    RunInfo,
    discover_runs,
    get_run_by_id,
    get_selection_data,
)
from build_tools.syllable_walk_web.web_assets import CSS_CONTENT, HTML_TEMPLATE


class SimplifiedWalkerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the simplified syllable walker web interface.

    This handler processes HTTP requests and serves the web interface,
    including run discovery, selection browsing, and walk generation.

    Class Attributes:
        walker: SyllableWalker instance (lazily initialized)
        current_run: Currently active RunInfo
        verbose: Whether to print progress messages
    """

    walker: SyllableWalker | None = None
    current_run: RunInfo | None = None
    verbose: bool = True

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default request logging to keep console clean."""
        pass

    def _send_response(
        self, content: str, content_type: str = "text/html", status: int = 200
    ) -> None:
        """Send HTTP response with specified content and headers."""
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _send_json_response(self, data: dict[str, Any], status: int = 200) -> None:
        """Send JSON response with appropriate headers."""
        content = json.dumps(data)
        self._send_response(content, content_type="application/json", status=status)

    def _send_error_response(self, message: str, status: int = 400) -> None:
        """Send JSON error response."""
        self._send_json_response({"error": message}, status=status)

    def _parse_path(self) -> tuple[str, dict[str, str]]:
        """Parse URL path and query parameters.

        Returns:
            Tuple of (path string, query params dict)
        """
        parsed = urlparse(self.path)
        query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        return parsed.path, query_params

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests for HTML, CSS, and API endpoints.

        Routes:
            /: Serve main HTML interface
            /styles.css: Serve CSS stylesheet
            /api/runs: List all available pipeline runs
            /api/runs/{id}/selections/{name_class}: Get selection data
        """
        path, query = self._parse_path()

        if path == "/":
            self._send_response(HTML_TEMPLATE, content_type="text/html")

        elif path == "/styles.css":
            self._send_response(CSS_CONTENT, content_type="text/css")

        elif path == "/api/runs":
            self._handle_list_runs()

        elif path.startswith("/api/runs/") and "/selections/" in path:
            self._handle_get_selection(path)

        elif path == "/api/stats":
            self._handle_get_stats()

        else:
            try:
                self.send_error(404, "Not Found")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests for walk generation and run selection.

        Routes:
            /api/walk: Generate a syllable walk
            /api/select-run: Select active run for walking
        """
        path, _ = self._parse_path()

        if path == "/api/walk":
            self._handle_walk()

        elif path == "/api/select-run":
            self._handle_select_run()

        else:
            try:
                self.send_error(404, "Not Found")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    def _handle_list_runs(self) -> None:
        """Handle GET /api/runs - list all available pipeline runs."""
        try:
            runs = discover_runs()
            response = {
                "runs": [r.to_dict() for r in runs],
                "current_run": (
                    SimplifiedWalkerHandler.current_run.path.name
                    if SimplifiedWalkerHandler.current_run
                    else None
                ),
            }
            self._send_json_response(response)
        except Exception as e:
            self._send_error_response(f"Error discovering runs: {e}", status=500)

    def _handle_get_selection(self, path: str) -> None:
        """Handle GET /api/runs/{id}/selections/{name_class}."""
        try:
            # Parse: /api/runs/20260121_084017_nltk/selections/first_name
            parts = path.split("/")
            if len(parts) < 6:
                self._send_error_response("Invalid path format")
                return

            run_id = parts[3]
            name_class = parts[5]

            # Find the run
            run = get_run_by_id(run_id)
            if run is None:
                self._send_error_response(f"Run not found: {run_id}", status=404)
                return

            # Check if selection exists
            if name_class not in run.selections:
                self._send_error_response(f"Selection not found: {name_class}", status=404)
                return

            # Load selection data
            selection_path = run.selections[name_class]
            data = get_selection_data(selection_path)
            self._send_json_response(data)

        except Exception as e:
            self._send_error_response(f"Error loading selection: {e}", status=500)

    def _handle_get_stats(self) -> None:
        """Handle GET /api/stats - get current walker stats."""
        run = SimplifiedWalkerHandler.current_run
        walker = SimplifiedWalkerHandler.walker

        response = {
            "current_run": run.path.name if run else None,
            "syllable_count": len(walker.syllables) if walker else 0,
            "has_walker": walker is not None,
        }
        self._send_json_response(response)

    def _handle_select_run(self) -> None:
        """Handle POST /api/select-run - select active run for walking."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_error_response("Empty request body")
                return

            body = self.rfile.read(content_length)
            params = json.loads(body.decode("utf-8"))

            run_id = params.get("run_id")
            if not run_id:
                self._send_error_response("Missing 'run_id' parameter")
                return

            # Find the run
            run = get_run_by_id(run_id)
            if run is None:
                self._send_error_response(f"Run not found: {run_id}", status=404)
                return

            # Check if already selected
            if (
                SimplifiedWalkerHandler.current_run
                and SimplifiedWalkerHandler.current_run.path.name == run_id
            ):
                self._send_json_response(
                    {
                        "success": True,
                        "message": "Run already selected",
                        "syllable_count": (
                            len(SimplifiedWalkerHandler.walker.syllables)
                            if SimplifiedWalkerHandler.walker
                            else 0
                        ),
                    }
                )
                return

            # Load syllables for this run
            if self.verbose:
                print(f"\nLoading run: {run_id}")

            syllables, source = load_syllables(
                db_path=run.corpus_db_path, json_path=run.annotated_json_path
            )

            if self.verbose:
                print(f"  Loaded from {source}")
                print("  Building neighbor graph...")

            # Initialize walker with loaded data
            walker = SyllableWalker.from_data(syllables, max_neighbor_distance=3)

            SimplifiedWalkerHandler.current_run = run
            SimplifiedWalkerHandler.walker = walker

            if self.verbose:
                print(f"  Done! ({len(walker.syllables):,} syllables)")

            self._send_json_response(
                {
                    "success": True,
                    "run_id": run_id,
                    "syllable_count": len(walker.syllables),
                    "source": source,
                }
            )

        except json.JSONDecodeError as e:
            self._send_error_response(f"Invalid JSON: {e}")
        except Exception as e:
            self._send_error_response(f"Error selecting run: {e}", status=500)

    def _handle_walk(self) -> None:
        """Handle POST /api/walk - generate a syllable walk."""
        walker = SimplifiedWalkerHandler.walker
        if walker is None:
            self._send_error_response("No run selected. Select a run first.", status=400)
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_error_response("Empty request body")
                return

            body = self.rfile.read(content_length)
            params = json.loads(body.decode("utf-8"))

            # Extract parameters with defaults
            start = params.get("start") or walker.get_random_syllable()
            profile = params.get("profile", "dialect")
            steps = params.get("steps", 5)
            seed = params.get("seed")

            # Validate start syllable
            if start and start not in walker.syllable_to_idx:
                self._send_error_response(f"Unknown syllable: {start}")
                return

            # Generate walk using profile
            walk = walker.walk_from_profile(start=start, profile=profile, steps=steps, seed=seed)

            response = {"walk": walk, "profile": profile, "start": start}
            self._send_json_response(response)

        except json.JSONDecodeError as e:
            self._send_error_response(f"Invalid JSON: {e}")
        except ValueError as e:
            self._send_error_response(str(e))
        except Exception as e:
            self._send_error_response(f"Server error: {e}", status=500)


def find_available_port(start: int = 8000, max_attempts: int = 100) -> int:
    """Find the first available port starting from `start`.

    Args:
        start: Port number to start searching from
        max_attempts: Maximum number of ports to try

    Returns:
        First available port number

    Raises:
        OSError: If no available ports found in range
    """
    for port in range(start, start + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))  # nosec B104
                return port
        except OSError:
            continue

    raise OSError(f"No available ports in range {start}-{start + max_attempts}")


def run_server(
    port: int | None = None,
    verbose: bool = True,
) -> None:
    """Start the web server.

    If no port is specified, automatically discovers an available port
    starting from 8000. If a specific port is given, uses that port
    (fails if unavailable).

    Args:
        port: Port number to use. If None, auto-discovers starting at 8000.
        verbose: Whether to print startup messages. Default: True

    Raises:
        OSError: If specified port is unavailable or no ports found
    """
    if verbose:
        print("=" * 60)
        print("Syllable Walker - Simplified Web Interface")
        print("=" * 60)

    # Discover runs
    runs = discover_runs()
    if verbose:
        print(f"\nFound {len(runs)} pipeline run(s)")
        for run in runs[:3]:  # Show top 3
            sel_count = len(run.selections)
            print(f"  - {run.display_name} ({sel_count} selection files)")
        if len(runs) > 3:
            print(f"  ... and {len(runs) - 3} more")

    # Find port
    if port is None:
        port = find_available_port(start=8000)
        if verbose:
            print(f"\nAuto-selected port: {port}")
    else:
        # Test if specified port is available
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))  # nosec B104
        except OSError as e:
            raise OSError(f"Port {port} is not available: {e}") from e

    # Set handler configuration
    SimplifiedWalkerHandler.verbose = verbose
    SimplifiedWalkerHandler.walker = None
    SimplifiedWalkerHandler.current_run = None

    # Create and start server
    server = HTTPServer(("0.0.0.0", port), SimplifiedWalkerHandler)  # nosec B104

    if verbose:
        print(f"\nServer running at http://localhost:{port}")
        print("Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if verbose:
            print("\n\nShutting down server...")
        server.shutdown()
        if verbose:
            print("Server stopped.")
