"""
Pipe-Works Build Tools — Web Application

Combined web interface for the Pipeline and Walker build tools,
providing a browser-based alternative to ``pipeline_tui`` and
``syllable_walk_tui``.

This is a **build-time tool only** — not used during runtime name generation.

Features:
    - Pipeline tool: extraction, normalization, annotation with live monitoring
    - Walker tool: dual-patch syllable walking, name combiner, name selector
    - Corpus analysis with terrain visualization and profile reach deep-dives
    - Name rendering and package export (ZIP with manifest + disk metadata persistence)
    - Dark/light theme support
    - 18 API endpoints across Pipeline, Walker, Browse, Settings, and Version groups

Architecture:
    - ``api/``: Request handlers (``browse``, ``pipeline``, ``walker``)
    - ``services/``: Business logic (``corpus_loader``, ``combiner_runner``,
      ``selector_runner``, ``walk_generator``, ``metrics``, ``packager``,
      ``pipeline_runner``)
    - ``state.py``: Dataclasses (``PatchState``, ``PipelineJobState``,
      ``ServerState``)
    - ``server.py``: stdlib ``http.server`` with routing and static file serving

Usage:
    Launch the web server from the command line::

        python -m build_tools.syllable_walk_web
        python -m build_tools.syllable_walk_web --port 9000
        python -m build_tools.syllable_walk_web --output-base /path/to/output

    Or programmatically::

        >>> from build_tools.syllable_walk_web import run_server
        >>> run_server(port=8000)
"""

from build_tools.syllable_walk_web.server import (
    CorpusBuilderHandler,
    find_available_port,
    run_server,
)

__all__ = [
    "CorpusBuilderHandler",
    "find_available_port",
    "run_server",
]
