"""
Syllable Walker Web Interface - Browser-Based Selection Browser and Walk Generator

The syllable walker web interface provides a browser-based tool for browsing name selections
and exploring syllable walks interactively. This is a **build-time analysis tool only** - not
used during runtime name generation.

The web interface auto-discovers pipeline runs from _working/output/ and provides:

- **Run Selection** - Browse and select from available pipeline runs
- **Selections Browser** - View name selections with tabs for each name class
- **Walk Generator** - Generate syllable walks with profile presets
- **Lazy Loading** - Walker initialization happens when user selects a run

This module is separate from the core `syllable_walk` module to maintain clean separation
between the walk algorithm and the web presentation layer.

Main Components:

- run_server: Start the HTTP server for the web interface
- SimplifiedWalkerHandler: HTTP request handler for API endpoints
- discover_runs: Find pipeline runs with selections
- find_available_port: Auto-discover available network ports

Usage:
    >>> from build_tools.syllable_walk_web import run_server
    >>>
    >>> # Start web server with auto-discovered port
    >>> run_server()  # Opens at http://localhost:8000 (or next available)
    >>>
    >>> # Start on specific port
    >>> run_server(port=9000)

CLI Usage:

    .. code-block:: bash

       # Start web interface (auto-discovers port starting at 8000)
       python -m build_tools.syllable_walk_web

       # Start on specific port
       python -m build_tools.syllable_walk_web --port 9000

       # Quiet mode (suppress startup messages)
       python -m build_tools.syllable_walk_web --quiet
"""

from build_tools.syllable_walk_web.run_discovery import (
    RunInfo,
    discover_runs,
    get_run_by_id,
    get_selection_data,
)
from build_tools.syllable_walk_web.server import (
    SimplifiedWalkerHandler,
    find_available_port,
    run_server,
)

# Public API
__all__ = [
    "run_server",
    "find_available_port",
    "SimplifiedWalkerHandler",
    "discover_runs",
    "get_run_by_id",
    "get_selection_data",
    "RunInfo",
]
