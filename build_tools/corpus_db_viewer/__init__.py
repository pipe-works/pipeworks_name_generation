"""
Corpus Database Viewer - Interactive TUI for Build Provenance

Interactive terminal user interface for viewing corpus database provenance records.
This is a **build-time tool only** - for inspecting extraction run history and outputs.

**This tool provides:**
- Interactive table browsing with pagination
- Schema inspection (columns, types, indexes)
- Data export to CSV and JSON formats
- Keyboard-driven navigation

**Replaces:** Flask-based web viewer (archived in _working/)

Features:
- Browse all database tables interactively
- Paginated data display (50 rows per page)
- View table schemas and CREATE TABLE statements
- Export data to CSV or JSON
- Read-only database access (safe inspection)
- Keyboard shortcuts for efficient navigation

Main Components:
- CorpusDBViewerApp: Main Textual TUI application class
- queries: Database query functions (table lists, schema, data)
- formatters: Export functions for CSV and JSON
- main: CLI entry point with argument parsing

Usage:
    # Launch interactive TUI with default database
    python -m build_tools.corpus_db_viewer

    # Specify custom database path
    python -m build_tools.corpus_db_viewer --db /path/to/database.db

    # Set custom export directory
    python -m build_tools.corpus_db_viewer --export-dir _working/my_exports/

Keyboard Shortcuts (in TUI):
    ↑/↓         Navigate rows
    ←/→         Previous/Next page
    t           Switch table
    i           Show schema info
    e           Export data
    q           Quit
    ?           Show help

Python API Usage:
    >>> from build_tools.corpus_db_viewer import queries
    >>> from pathlib import Path
    >>>
    >>> # Get list of tables
    >>> db_path = Path("data/raw/syllable_extractor.db")
    >>> tables = queries.get_tables_list(db_path)
    >>>
    >>> # Get schema for a table
    >>> schema = queries.get_table_schema(db_path, "runs")
    >>> print(schema['columns'])
    >>>
    >>> # Get paginated data
    >>> data = queries.get_table_data(db_path, "runs", page=1, limit=50)
    >>> print(f"Total rows: {data['total']}")
"""

from . import formatters, queries
from .cli import main

__all__ = [
    "main",
    "queries",
    "formatters",
]

__version__ = "0.1.0"
