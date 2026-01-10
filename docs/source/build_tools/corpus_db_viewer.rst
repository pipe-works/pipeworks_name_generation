======================
Corpus Database Viewer
======================

.. currentmodule:: build_tools.corpus_db_viewer

Overview
--------

.. automodule:: build_tools.corpus_db_viewer
   :no-members:

The Corpus Database Viewer is an interactive terminal user interface (TUI) for inspecting
corpus database provenance records. Built with `Textual <https://textual.textualize.io/>`_,
it provides a keyboard-driven interface for browsing extraction run history.

**Replaces:** Flask-based web viewer (archived in ``_working/_archived/pipeworks_db_viewer_flask/``)

**Key Features:**

- Browse all database tables interactively
- Paginated data display (50 rows per page)
- View table schemas and CREATE TABLE statements
- Export data to CSV or JSON
- Read-only database access (safe inspection)
- Keyboard shortcuts for efficient navigation

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.corpus_db_viewer.cli
   :func: create_argument_parser
   :prog: corpus_db_viewer

Output Format
-------------

Export Files
~~~~~~~~~~~~

The viewer can export table data to two formats:

**CSV Format:**

Comma-separated values with header row:

::

    id,run_timestamp,extractor_tool,status
    1,2026-01-09T14:30:22,syllable_extractor,completed
    2,2026-01-09T15:12:45,syllable_extractor,completed

**JSON Format:**

Array of objects with full type preservation:

.. code-block:: json

   [
     {
       "id": 1,
       "run_timestamp": "2026-01-09T14:30:22",
       "extractor_tool": "syllable_extractor",
       "status": "completed"
     }
   ]

**Export file naming:**

Files are timestamped and named by table:

::

    _working/exports/
    ├── runs_20260109_143022.csv
    ├── runs_20260109_143022.json
    └── outputs_20260109_143145.csv

**Important:** Exports include ALL rows, not just the current page.

Database Structure
~~~~~~~~~~~~~~~~~~

The corpus database tracks syllable extraction runs:

**runs** - Extraction run metadata
   Tool name, version, status, timestamps, command-line arguments

**inputs** - Source files processed
   Input files or directories used for each run

**outputs** - Generated files
   Output .syllables and .meta files with syllable counts

Integration Guide
-----------------

Use the viewer to inspect corpus database provenance after extraction runs:

.. code-block:: bash

   # Step 1: Extract syllables (populates database)
   python -m build_tools.pyphen_syllable_extractor \
     --source data/corpus/ \
     --lang en_US

   # Step 2: Inspect extraction history with TUI viewer
   python -m build_tools.corpus_db_viewer

**When to use this tool:**

- To verify extraction runs completed successfully
- To inspect which corpus files were processed
- To track provenance of generated syllable files
- To export extraction history for reporting or analysis
- To debug failed extraction runs by examining status and error messages

**Common workflows:**

1. **Browse recent runs:** Launch viewer → select "runs" table → sort by timestamp
2. **Find run details:** Press ``i`` to view schema → browse rows for run metadata
3. **Export history:** Press ``e`` → select format (CSV/JSON) → save to export directory
4. **Track file provenance:** Switch to "outputs" table → identify which run created specific files

Advanced Topics
---------------

Keyboard Shortcuts
~~~~~~~~~~~~~~~~~~

**Navigation:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``↑`` / ``↓``
     - Navigate rows
   * - ``←`` / ``→``
     - Previous/Next page
   * - ``PageUp`` / ``PageDn``
     - Jump 10 pages
   * - ``Home`` / ``End``
     - First/Last page

**Actions:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key
     - Action
   * - ``t``
     - Switch table
   * - ``i``
     - Show schema info
   * - ``e``
     - Export data
   * - ``r``
     - Refresh
   * - ``?``
     - Show help
   * - ``q``
     - Quit

Usage Examples
~~~~~~~~~~~~~~

**Browsing Tables:**

Launch the viewer and it automatically loads the first table. Navigate using:

1. Press ``t`` to focus the table list
2. Use ``↑`` / ``↓`` to navigate tables
3. Press ``Enter`` to select

Or click directly on table names in the sidebar.

**Viewing Schema:**

Press ``i`` to view detailed schema information:

- Column definitions (name, type, constraints)
- Indexes (name, columns, UNIQUE flags)
- CREATE TABLE statement (original SQL)

Example output::

   Schema: runs

   Columns:
     • id: INTEGER [PRIMARY KEY]
     • run_timestamp: TEXT NOT NULL
     • extractor_tool: TEXT NOT NULL
     • status: TEXT

   Indexes:
     • idx_status (status)

**Exporting Data:**

Press ``e`` to export the current table:

1. Edit filename (optional)
2. Choose CSV or JSON format
3. File saved to export directory (default: ``_working/exports/``)

Design Philosophy
~~~~~~~~~~~~~~~~~

**Read-Only Access:**

The viewer opens databases in read-only mode (``?mode=ro``) to prevent accidental modifications.

**Observational Tool:**

Like the corpus_db ledger, this viewer is observational only - it displays run history
but doesn't control or modify build processes.

**Benefits Over Flask Version:**

The Textual TUI offers advantages over the previous Flask-based web viewer:

- No web server overhead (terminal-native)
- Better build tools integration
- Reduced dependencies (no Flask, pandas, Werkzeug)
- Single-language codebase (Python only)
- Native keyboard navigation

**Trade-offs:**

- No SQL query interface (may be added later)
- No cross-table search (may be added later)
- Terminal-only (no browser UI)

Notes
-----

**Dependencies:**

Requires Textual library for TUI functionality. Install with:

.. code-block:: bash

   pip install -r requirements-dev.txt

**Troubleshooting:**

**Database Not Found:**

.. code-block:: text

   Error: Database not found: data/raw/syllable_extractor.db

**Solution:** Ensure the database exists or specify a different path:

.. code-block:: bash

   python -m build_tools.corpus_db_viewer --db /path/to/database.db

**Textual Not Installed:**

.. code-block:: text

   Error: Textual library not found

**Solution:** Install development dependencies:

.. code-block:: bash

   pip install -r requirements-dev.txt

**Terminal Too Small:**

If the layout looks broken, resize your terminal. Minimum recommended: 80 columns × 24 rows.

**Database Access:**

- Database opened in read-only mode for safety
- No modification operations available
- Safe to run while extraction tools are active

**Build-time tool:**

This is a build-time inspection tool - not used during runtime name generation.

**Related Documentation:**

- :doc:`corpus_db` - Build provenance ledger that this tool reads
- :doc:`syllable_extractor` - Main tool that populates the database

API Reference
-------------

.. automodule:: build_tools.corpus_db_viewer
   :members:
   :undoc-members:
   :show-inheritance:
