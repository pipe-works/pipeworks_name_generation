"""HTTP server for the syllable walker web interface.

This module provides a web-based interface for exploring syllable walks using the
standard library's http.server module (no Flask dependency). The server handles:
- Serving the HTML interface (/)
- Serving CSS styles (/styles.css)
- Providing walker statistics (/api/stats)
- Generating syllable walks (/api/walk)
- Listing available datasets (/api/datasets)
- Loading datasets dynamically (/api/load-dataset)

Usage::

    from build_tools.syllable_walk.server import run_server
    run_server(data_path, max_neighbor_distance=3, port=5000)
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

from build_tools.syllable_walk.dataset_discovery import discover_datasets, get_default_dataset
from build_tools.syllable_walk.walker import SyllableWalker
from build_tools.syllable_walk.web_assets import CSS_CONTENT, HTML_TEMPLATE


class WalkerHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the syllable walker web interface.

    This handler processes HTTP requests and serves the web interface. It maintains
    a cache of SyllableWalker instances (one per dataset) for fast switching between
    datasets without reloading.

    Class Attributes:
        walker_cache: Dictionary mapping dataset paths to SyllableWalker instances
        max_neighbor_distance: Configuration for walker initialization
        current_dataset_path: Path to currently active dataset
        verbose: Whether to print progress messages
    """

    # Class attributes (shared across all request handlers)
    walker_cache: dict[str, SyllableWalker] = {}
    max_neighbor_distance: int = 3
    current_dataset_path: Optional[Path] = None
    verbose: bool = True

    def log_message(self, format: str, *args: Any) -> None:
        """Override to suppress default request logging to keep console clean.

        Args:
            format: Log message format string
            *args: Arguments to format into the message
        """
        # Suppress default logging (we'll log errors only)
        pass

    def _send_response(
        self, content: str, content_type: str = "text/html", status: int = 200
    ) -> None:
        """Send HTTP response with specified content and headers.

        Args:
            content: Response body content
            content_type: MIME type for Content-Type header. Default: text/html
            status: HTTP status code. Default: 200

        Note:
            Gracefully handles connection errors (BrokenPipeError, ConnectionResetError)
            when the client closes the connection before receiving the response.
        """
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client closed connection before receiving response - this is normal
            # for cancelled requests or timeouts. Nothing we can do, so silently ignore.
            pass

    def _send_json_response(self, data: dict[str, Any], status: int = 200) -> None:
        """Send JSON response with appropriate headers.

        Args:
            data: Dictionary to serialize as JSON
            status: HTTP status code. Default: 200
        """
        content = json.dumps(data)
        self._send_response(content, content_type="application/json", status=status)

    def _send_error_response(self, message: str, status: int = 400) -> None:
        """Send JSON error response.

        Args:
            message: Error message to include in response
            status: HTTP status code. Default: 400 (Bad Request)
        """
        self._send_json_response({"error": message}, status=status)

    def _get_current_walker(self) -> Optional[SyllableWalker]:
        """Get the walker for the currently active dataset.

        Returns:
            SyllableWalker instance for current dataset, or None if no dataset active
        """
        if self.current_dataset_path is None:
            return None
        path_key = str(self.current_dataset_path)
        return self.walker_cache.get(path_key)

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests for HTML, CSS, and stats API endpoint.

        Routes:
            /: Serve main HTML interface
            /styles.css: Serve CSS stylesheet
            /api/stats: Return walker statistics as JSON
            *: 404 for all other paths
        """
        if self.path == "/":
            # Serve main HTML page
            self._send_response(HTML_TEMPLATE, content_type="text/html")

        elif self.path == "/styles.css":
            # Serve CSS stylesheet
            self._send_response(CSS_CONTENT, content_type="text/css")

        elif self.path == "/api/stats":
            # Return walker statistics
            walker = self._get_current_walker()
            if walker is None:
                self._send_error_response("No dataset loaded", status=500)
                return

            stats = {
                "total_syllables": len(walker.syllables),
                "max_neighbor_distance": walker.max_neighbor_distance,
                "current_dataset": (
                    str(self.current_dataset_path) if self.current_dataset_path else None
                ),
            }
            self._send_json_response(stats)

        elif self.path == "/api/datasets":
            # Return list of available datasets
            try:
                datasets = discover_datasets()
                response = {
                    "datasets": [ds.to_dict() for ds in datasets],
                    "current": (
                        str(self.current_dataset_path) if self.current_dataset_path else None
                    ),
                }
                self._send_json_response(response)
            except Exception as e:
                self._send_error_response(f"Error discovering datasets: {e}", status=500)

        else:
            # 404 for unknown paths
            try:
                self.send_error(404, "Not Found")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Client closed connection - ignore
                pass

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests for walk generation API endpoint.

        Routes:
            /api/walk: Generate a syllable walk based on JSON parameters

        Request JSON format:
            {
                "start": str | null,              # Starting syllable (null = random)
                "profile": str,                   # Walk profile name or "custom"
                "steps": int,                     # Number of steps in walk
                "max_flips": int,                 # Max feature flips (for custom)
                "temperature": float,             # Temperature (for custom)
                "frequency_weight": float,        # Frequency weight (for custom)
                "seed": int | null                # Random seed (null = random)
            }

        Response JSON format:
            {
                "walk": list[dict],               # List of syllable dicts
                "profile": str,                   # Profile name used
                "start": str                      # Starting syllable used
            }
        """
        if self.path == "/api/walk":
            walker = self._get_current_walker()
            if walker is None:
                self._send_error_response("No dataset loaded", status=500)
                return

            try:
                # Parse JSON request body
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

                # Generate walk based on profile
                if profile == "custom":
                    # Use custom parameters
                    walk = walker.walk(
                        start=start,
                        steps=steps,
                        max_flips=params.get("max_flips", 2),
                        temperature=params.get("temperature", 0.7),
                        frequency_weight=params.get("frequency_weight", 0.0),
                        seed=seed,
                    )
                else:
                    # Use named profile
                    walk = walker.walk_from_profile(
                        start=start, profile=profile, steps=steps, seed=seed
                    )

                # Return walk results
                response = {"walk": walk, "profile": profile, "start": start}
                self._send_json_response(response)

            except json.JSONDecodeError as e:
                self._send_error_response(f"Invalid JSON: {e}")
            except ValueError as e:
                self._send_error_response(str(e))
            except Exception as e:
                self._send_error_response(f"Server error: {e}", status=500)

        elif self.path == "/api/load-dataset":
            # Load a different dataset dynamically (with caching)
            try:
                # Parse JSON request body
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self._send_error_response("Empty request body")
                    return

                body = self.rfile.read(content_length)
                params = json.loads(body.decode("utf-8"))

                dataset_path = params.get("path")
                if not dataset_path:
                    self._send_error_response("Missing 'path' parameter")
                    return

                dataset_path = Path(dataset_path)
                if not dataset_path.exists():
                    self._send_error_response(f"Dataset file not found: {dataset_path}")
                    return

                path_key = str(dataset_path)

                # Check if walker is already cached
                if path_key in WalkerHTTPHandler.walker_cache:
                    # Walker already loaded - instant switch!
                    if self.verbose:
                        walker = WalkerHTTPHandler.walker_cache[path_key]
                        print(
                            f"✓ Dataset already cached, instant switch! ({len(walker.syllables):,} syllables)"
                        )
                    WalkerHTTPHandler.current_dataset_path = dataset_path
                    walker = WalkerHTTPHandler.walker_cache[path_key]
                else:
                    # Walker not cached - load it
                    if self.verbose:
                        print(f"\nLoading new dataset: {dataset_path}")
                        print("This may take a minute for large datasets...")

                    walker = SyllableWalker(
                        dataset_path,
                        max_neighbor_distance=self.max_neighbor_distance,
                        verbose=self.verbose,
                    )

                    # Cache the walker
                    WalkerHTTPHandler.walker_cache[path_key] = walker
                    WalkerHTTPHandler.current_dataset_path = dataset_path

                    if self.verbose:
                        print(f"✓ Dataset loaded and cached! ({len(walker.syllables):,} syllables)")

                # Return success response with stats
                response = {
                    "success": True,
                    "dataset": str(dataset_path),
                    "total_syllables": len(walker.syllables),
                }
                self._send_json_response(response)

            except json.JSONDecodeError as e:
                self._send_error_response(f"Invalid JSON: {e}")
            except Exception as e:
                self._send_error_response(f"Error loading dataset: {e}", status=500)
                if self.verbose:
                    import traceback

                    traceback.print_exc()

        else:
            # 404 for unknown POST paths
            try:
                self.send_error(404, "Not Found")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Client closed connection - ignore
                pass


def run_server(
    data_path: Optional[Path | str] = None,
    max_neighbor_distance: int = 3,
    port: int = 5000,
    verbose: bool = True,
) -> None:
    """Initialize syllable walker and start the web server.

    This function loads the syllable data, initializes the walker with neighbor
    graph construction, and starts the HTTP server on the specified port. The
    server runs until interrupted with Ctrl+C.

    If no data_path is specified, automatically discovers and loads the most
    recent dataset from _working/output/ directories.

    Args:
        data_path: Path to syllables_annotated.json file. If None, auto-discovers
            the most recent dataset from _working/output/. Default: None
        max_neighbor_distance: Maximum Hamming distance for neighbor graph (1-3).
            Higher values allow more diverse walks but slower initialization. Default: 3
        port: Port number for HTTP server. If the specified port is in use, automatically
            increments to find an available port (tries up to 10 ports). Default: 5000
        verbose: Whether to print initialization progress. Default: True

    Raises:
        FileNotFoundError: If data_path does not exist or no datasets found
        ValueError: If max_neighbor_distance is invalid
        OSError: If no available ports found in range (port to port+10)

    Examples:
        >>> # Auto-discover and load most recent dataset
        >>> run_server(port=8000)
        # Server starts on http://localhost:8000

        >>> # Load specific dataset
        >>> run_server("data/annotated/syllables_annotated.json", port=8000)
        # Server starts with specified dataset
    """
    if verbose:
        print("=" * 60)
        print("Syllable Walker - Web Interface")
        print("=" * 60)

    # Auto-discover dataset if not specified
    if data_path is None:
        if verbose:
            print("\nDiscovering available datasets...")

        datasets = discover_datasets()
        if not datasets:
            raise FileNotFoundError(
                "No annotated datasets found. Please run syllable_feature_annotator first:\n"
                "  python -m build_tools.syllable_feature_annotator --syllables <file> "
                "--frequencies <file>"
            )

        default_dataset = get_default_dataset(datasets)
        if default_dataset is None:
            raise FileNotFoundError("No valid datasets found")

        data_path = default_dataset.path

        if verbose:
            print(f"✓ Found {len(datasets)} dataset(s)")
            print(f"  Loading: {default_dataset.name}")
            print(f"  Path: {data_path}")

    # Convert to Path object
    data_path = Path(data_path)

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    if verbose:
        print(f"\nLoading data from: {data_path}")
        print("This may take a minute for large datasets...\n")

    # Initialize walker (this builds the neighbor graph)
    walker = SyllableWalker(data_path, max_neighbor_distance=max_neighbor_distance, verbose=verbose)

    # Store configuration in class attributes (shared across all request handlers)
    path_key = str(data_path)
    WalkerHTTPHandler.walker_cache = {path_key: walker}  # Initialize cache with first walker
    WalkerHTTPHandler.max_neighbor_distance = max_neighbor_distance
    WalkerHTTPHandler.current_dataset_path = data_path
    WalkerHTTPHandler.verbose = verbose

    if verbose:
        print("\n" + "=" * 60)
        print("✓ Walker initialized successfully!")
        print("=" * 60)

    # Try to find an available port
    max_port_attempts = 10
    original_port = port
    server = None

    for attempt in range(max_port_attempts):
        try:
            if verbose and attempt > 0:
                print(f"Port {port - 1} in use, trying {port}...")

            # Create HTTP server
            server = HTTPServer(("0.0.0.0", port), WalkerHTTPHandler)  # nosec B104

            # Success! Port is available
            if verbose:
                if port != original_port:
                    print(f"✓ Found available port: {port}")
                print(f"\nStarting web server on port {port}...")
                print(f"Open your browser and navigate to: http://localhost:{port}")
                print("\nPress Ctrl+C to stop the server\n")
            break

        except OSError as e:
            if e.errno == 48 or "Address already in use" in str(e):
                # Port is in use, try next one
                port += 1
                if attempt == max_port_attempts - 1:
                    # Exhausted all attempts
                    raise OSError(
                        f"Could not find available port in range {original_port}-{port}. "
                        f"Please specify a different port with --port option."
                    ) from e
            else:
                # Different error, re-raise
                raise

    if server is None:
        raise OSError("Failed to create server")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if verbose:
            print("\n\nShutting down server...")
        server.shutdown()
        if verbose:
            print("Server stopped.")
