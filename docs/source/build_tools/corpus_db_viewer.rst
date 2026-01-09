Corpus Database Viewer
======================

.. automodule:: build_tools.corpus_db_viewer
   :no-members:

The Corpus Database Viewer is an interactive terminal user interface (TUI) for inspecting
corpus database provenance records. Built with `Textual <https://textual.textualize.io/>`_,
it provides a keyboard-driven interface for browsing extraction run history.

**Replaces:** Flask-based web viewer (archived in ``_working/_archived/pipeworks_db_viewer_flask/``)

Key Features
------------

- Browse all database tables interactively
- Paginated data display (50 rows per page)
- View table schemas and CREATE TABLE statements
- Export data to CSV or JSON
- Read-only database access (safe inspection)
- Keyboard shortcuts for efficient navigation

Command-Line Interface
----------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   # Launch interactive TUI with default database
   python -m build_tools.corpus_db_viewer

   # Specify custom database path
   python -m build_tools.corpus_db_viewer --db /path/to/database.db

   # Set custom export directory
   python -m build_tools.corpus_db_viewer --export-dir _working/my_exports/

   # Adjust page size
   python -m build_tools.corpus_db_viewer --page-size 100

CLI Options
~~~~~~~~~~~

.. argparse::
   :module: build_tools.corpus_db_viewer.cli
   :func: create_argument_parser
   :prog: corpus_db_viewer

Keyboard Shortcuts (in TUI)
----------------------------

Navigation
~~~~~~~~~~

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

Actions
~~~~~~~

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
--------------

Browsing Tables
~~~~~~~~~~~~~~~

Launch the viewer and it automatically loads the first table. Navigate using:

1. Press ``t`` to focus the table list
2. Use ``↑`` / ``↓`` to navigate tables
3. Press ``Enter`` to select

Or click directly on table names in the sidebar.

Viewing Schema
~~~~~~~~~~~~~~

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

Exporting Data
~~~~~~~~~~~~~~

Press ``e`` to export the current table:

1. Edit filename (optional)
2. Choose CSV or JSON format
3. File saved to export directory (default: ``_working/exports/``)

**Note:** Export includes ALL rows, not just current page.

Output files::

   _working/exports/
   ├── runs_20240109_143022.csv
   ├── runs_20240109_143022.json
   └── outputs_20240109_143145.csv

Programmatic Usage
------------------

Query Functions
~~~~~~~~~~~~~~~

.. code-block:: python

   from build_tools.corpus_db_viewer import queries
   from pathlib import Path

   db_path = Path("data/raw/syllable_extractor.db")

   # Get list of tables
   tables = queries.get_tables_list(db_path)
   for table in tables:
       print(table['name'])

   # Get schema
   schema = queries.get_table_schema(db_path, "runs")
   print(f"Columns: {len(schema['columns'])}")

   # Get paginated data
   data = queries.get_table_data(
       db_path,
       "runs",
       page=1,
       limit=10,
       sort_by="run_timestamp",
       sort_order="DESC"
   )
   print(f"Total: {data['total']} rows")

Export Functions
~~~~~~~~~~~~~~~~

.. code-block:: python

   from build_tools.corpus_db_viewer import formatters
   from pathlib import Path

   rows = [
       {'id': 1, 'name': 'Alice', 'age': 30},
       {'id': 2, 'name': 'Bob', 'age': 25}
   ]

   # Export to CSV
   formatters.export_to_csv(rows, Path("_working/data.csv"))

   # Export to JSON
   formatters.export_to_json(rows, Path("_working/data.json"))

   # Format helpers
   print(formatters.format_row_count(1234))      # "1,234 rows"
   print(formatters.format_file_size(1048576))   # "1.0 MB"

Database Structure
------------------

The corpus database tracks syllable extraction runs:

**runs** - Extraction run metadata
   Tool name, version, status, timestamps, command-line arguments

**inputs** - Source files processed
   Input files or directories used for each run

**outputs** - Generated files
   Output .syllables and .meta files with syllable counts

Troubleshooting
---------------

Database Not Found
~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Error: Database not found: data/raw/syllable_extractor.db

**Solution:** Ensure the database exists or specify a different path:

.. code-block:: bash

   python -m build_tools.corpus_db_viewer --db /path/to/database.db

Textual Not Installed
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Error: Textual library not found

**Solution:** Install development dependencies:

.. code-block:: bash

   pip install -r requirements-dev.txt

Terminal Too Small
~~~~~~~~~~~~~~~~~~

If the layout looks broken, resize your terminal. Minimum recommended: 80 columns × 24 rows.

Design Philosophy
-----------------

Read-Only Access
~~~~~~~~~~~~~~~~

The viewer opens databases in read-only mode (``?mode=ro``) to prevent accidental modifications.

Observational Tool
~~~~~~~~~~~~~~~~~~

Like the corpus_db ledger, this viewer is observational only - it displays run history
but doesn't control or modify build processes.

Benefits Over Flask Version
----------------------------

**Textual TUI advantages:**

- No web server overhead (terminal-native)
- Better build tools integration
- Reduced dependencies (no Flask, pandas, Werkzeug)
- Single-language codebase (Python only)
- Native keyboard navigation

**Trade-offs:**

- No SQL query interface (may be added later)
- No cross-table search (may be added later)
- Terminal-only (no browser UI)

Related Documentation
---------------------

- :doc:`corpus_db` - Build provenance ledger that this tool reads
- :doc:`syllable_extractor` - Main tool that populates the database
