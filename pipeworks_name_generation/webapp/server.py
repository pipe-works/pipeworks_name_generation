"""HTTP server and browser UI for importing name package pairs.

This server intentionally uses the Python standard library so deployment stays
simple. On startup it either uses a configured manual port or selects the
first free port between 8000 and 8999.
"""

from __future__ import annotations

import json
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from pipeworks_name_generation.webapp.config import ServerSettings
from pipeworks_name_generation.webapp.db import (
    connect_database,
    initialize_schema,
    list_imported_packages,
)
from pipeworks_name_generation.webapp.importer import import_package_pair

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pipeworks Name Generator Importer</title>
  <style>
    :root {
      --bg: #111827;
      --surface: #1f2937;
      --text: #f9fafb;
      --muted: #9ca3af;
      --accent: #22d3ee;
      --ok: #34d399;
      --err: #f87171;
      --border: #374151;
    }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: radial-gradient(circle at top right, #1e3a8a 0%, var(--bg) 45%);
      color: var(--text);
    }
    .wrap {
      max-width: 1100px;
      margin: 2rem auto;
      padding: 0 1rem;
    }
    .card {
      background: color-mix(in srgb, var(--surface) 92%, black 8%);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      margin-bottom: 1rem;
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.22);
    }
    h1 {
      margin-top: 0;
      letter-spacing: 0.03em;
    }
    .muted {
      color: var(--muted);
    }
    .row {
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 0.75rem;
      margin-bottom: 0.75rem;
      align-items: center;
    }
    input {
      width: 100%;
      box-sizing: border-box;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #0f172a;
      color: var(--text);
      padding: 0.6rem 0.7rem;
      font-family: "JetBrains Mono", monospace;
      font-size: 0.9rem;
    }
    button {
      border-radius: 8px;
      border: 1px solid color-mix(in srgb, var(--accent) 80%, white 20%);
      background: color-mix(in srgb, var(--accent) 25%, black 75%);
      color: white;
      padding: 0.6rem 1rem;
      cursor: pointer;
      font-weight: 600;
    }
    button:hover {
      filter: brightness(1.1);
    }
    #status.ok { color: var(--ok); }
    #status.err { color: var(--err); }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }
    th, td {
      border-bottom: 1px solid var(--border);
      text-align: left;
      padding: 0.5rem;
      vertical-align: top;
    }
    @media (max-width: 800px) {
      .row { grid-template-columns: 1fr; }
      th:nth-child(4), td:nth-child(4), th:nth-child(5), td:nth-child(5) { display: none; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Package Importer</h1>
      <p class="muted">Import a metadata JSON and package ZIP pair into SQLite.</p>
      <form id="import-form">
        <div class="row">
          <label for="metadata">Metadata JSON Path</label>
          <input id="metadata" name="metadata_json_path" type="text" required />
        </div>
        <div class="row">
          <label for="zip">Package ZIP Path</label>
          <input id="zip" name="package_zip_path" type="text" required />
        </div>
        <button type="submit">Import Pair</button>
      </form>
      <p id="status" class="muted">Idle.</p>
    </div>

    <div class="card">
      <h2>Imported Packages</h2>
      <button id="refresh" type="button">Refresh</button>
      <div style="overflow-x:auto; margin-top:0.75rem;">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Common Name</th>
              <th>Imported At</th>
              <th>Source Run</th>
              <th>ZIP Entries</th>
            </tr>
          </thead>
          <tbody id="imports-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    async function loadImports() {
      const res = await fetch('/api/imports');
      const data = await res.json();
      const body = document.getElementById('imports-body');
      body.innerHTML = '';

      for (const row of data.imports) {
        const tr = document.createElement('tr');
        tr.innerHTML =
          `<td>${row.id}</td>` +
          `<td>${row.common_name || ''}</td>` +
          `<td>${row.imported_at || ''}</td>` +
          `<td>${row.source_run || ''}</td>` +
          `<td>${row.zip_entry_count}</td>`;
        body.appendChild(tr);
      }
    }

    async function submitImport(event) {
      event.preventDefault();
      const status = document.getElementById('status');
      status.className = 'muted';
      status.textContent = 'Importing...';

      const payload = {
        metadata_json_path: document.getElementById('metadata').value,
        package_zip_path: document.getElementById('zip').value,
      };

      const res = await fetch('/api/import', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (res.ok && data.success) {
        status.className = 'ok';
        status.textContent = data.message;
        await loadImports();
      } else {
        status.className = 'err';
        status.textContent = data.error || 'Import failed.';
      }
    }

    document.getElementById('import-form').addEventListener('submit', submitImport);
    document.getElementById('refresh').addEventListener('click', loadImports);
    loadImports();
  </script>
</body>
</html>
"""


class WebAppHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the package importer UI/API."""

    db_path: Path = Path("pipeworks_name_generation.sqlite3")
    verbose: bool = True

    def log_message(self, format: str, *args: Any) -> None:
        """Keep request logging quiet by default to reduce console noise."""
        if self.verbose:
            super().log_message(format, *args)

    def _send_text(self, content: str, status: int = 200, content_type: str = "text/plain") -> None:
        """Send text response with content length precomputed."""
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        """Send JSON response."""
        self._send_text(json.dumps(payload), status=status, content_type="application/json")

    def do_GET(self) -> None:  # noqa: N802
        """Handle UI and API GET routes."""
        if self.path == "/":
            self._send_text(HTML_TEMPLATE, content_type="text/html")
            return

        if self.path == "/api/health":
            self._send_json({"ok": True})
            return

        if self.path == "/api/imports":
            try:
                with connect_database(self.db_path) as conn:
                    initialize_schema(conn)
                    imports = list_imported_packages(conn)
                self._send_json({"imports": imports})
            except Exception as exc:  # nosec B110 - return controlled API error
                self._send_json({"error": f"Failed to list imports: {exc}"}, status=500)
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        """Handle API POST routes."""
        if self.path != "/api/import":
            self.send_error(404, "Not Found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "Invalid Content-Length header."}, status=400)
            return

        if content_length <= 0:
            self._send_json({"error": "Request body is required."}, status=400)
            return

        raw_body = self.rfile.read(content_length)
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Request body must be valid JSON."}, status=400)
            return

        metadata_raw = str(body.get("metadata_json_path", "")).strip()
        zip_raw = str(body.get("package_zip_path", "")).strip()
        if not metadata_raw or not zip_raw:
            self._send_json(
                {"error": ("Both 'metadata_json_path' and 'package_zip_path' are required.")},
                status=400,
            )
            return

        metadata_path = Path(metadata_raw)
        zip_path = Path(zip_raw)

        try:
            with connect_database(self.db_path) as conn:
                initialize_schema(conn)
                result = import_package_pair(conn, metadata_path, zip_path)
            self._send_json(
                {
                    "success": True,
                    "package_id": result.package_id,
                    "message": result.message,
                }
            )
        except (
            FileNotFoundError,
            ValueError,
            json.JSONDecodeError,
            OSError,
            PermissionError,
        ) as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:  # nosec B110 - unexpected error converted to API response
            self._send_json({"error": f"Import failed: {exc}"}, status=500)


def _port_is_available(host: str, port: int) -> bool:
    """Return True if a host/port can be bound by this process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_available_port(host: str = "127.0.0.1", start: int = 8000, end: int = 8999) -> int:
    """Find the first available TCP port in the requested range.

    Args:
        host: Host/interface for bind checks
        start: Range start (inclusive)
        end: Range end (inclusive)

    Returns:
        First available port

    Raises:
        OSError: If no free port exists in range
    """
    for port in range(start, end + 1):
        if _port_is_available(host, port):
            return port
    raise OSError(f"No free ports available in range {start}-{end}.")


def resolve_server_port(host: str, configured_port: int | None) -> int:
    """Resolve runtime port using manual config or auto-discovery.

    Args:
        host: Host/interface for bind checks
        configured_port: Port from config/CLI, or None for auto mode

    Returns:
        Port selected for server startup

    Raises:
        OSError: If configured port is occupied or no 8000-range port is free
    """
    if configured_port is not None:
        if not _port_is_available(host, configured_port):
            raise OSError(f"Configured port {configured_port} is already in use.")
        return configured_port

    return find_available_port(host=host, start=8000, end=8999)


def create_handler_class(db_path: Path, verbose: bool) -> type[WebAppHandler]:
    """Create a handler class bound to runtime DB path and verbosity."""

    class BoundHandler(WebAppHandler):
        pass

    BoundHandler.db_path = db_path
    BoundHandler.verbose = verbose
    return BoundHandler


def start_http_server(settings: ServerSettings) -> tuple[HTTPServer, int]:
    """Create and return a configured ``HTTPServer`` instance.

    Args:
        settings: Effective server settings

    Returns:
        Tuple of (server, selected_port)
    """
    with connect_database(settings.db_path) as conn:
        initialize_schema(conn)

    port = resolve_server_port(settings.host, settings.port)
    handler_class = create_handler_class(settings.db_path, settings.verbose)
    server = HTTPServer((settings.host, port), handler_class)
    return server, port


def run_server(settings: ServerSettings) -> int:
    """Run server forever until interrupted.

    Args:
        settings: Effective server settings

    Returns:
        Exit code (0 on clean stop)
    """
    server, port = start_http_server(settings)

    if settings.verbose:
        print(f"Serving Pipeworks Name Generator UI at http://{settings.host}:{port}")
        print(f"SQLite DB: {settings.db_path}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if settings.verbose:
            print("\nStopping server...")
    finally:
        server.server_close()

    return 0
