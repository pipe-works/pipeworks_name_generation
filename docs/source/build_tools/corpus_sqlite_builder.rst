======================
Corpus SQLite Builder
======================

.. currentmodule:: build_tools.corpus_sqlite_builder

Overview
--------

.. automodule:: build_tools.corpus_sqlite_builder
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.corpus_sqlite_builder.cli
   :func: create_argument_parser
   :prog: python -m build_tools.corpus_sqlite_builder

Output Format
-------------

The corpus SQLite builder creates optimized database files in the ``data/`` subdirectory
of each corpus. The SQLite database is a derived format that coexists with the canonical
JSON files.

**Output structure:**

.. code-block:: text

    _working/output/20260110_115453_pyphen/
    ├── data/
    │   ├── pyphen_syllables_annotated.json  (canonical, 11MB)
    │   └── corpus.db                         (derived, 2.1MB, NEW)
    ├── pyphen_syllables_unique.txt
    ├── pyphen_syllables_frequencies.json
    └── ... (other corpus files)

**SQLite Database Schema:**

The ``corpus.db`` file contains two tables:

1. **syllables table** - Main data storage

   - ``syllable`` (TEXT, PRIMARY KEY): The syllable string
   - ``frequency`` (INTEGER): Occurrence count in source corpus
   - 12 phonetic feature columns (INTEGER 0/1): Boolean feature flags

2. **metadata table** - Database information

   - ``schema_version``: Database schema version (for migrations)
   - ``source_tool``: Tool that created the database
   - ``generated_at``: ISO 8601 timestamp
   - ``total_syllables``: Number of syllables in database
   - ``source_json_path``: Original JSON file name

**Performance characteristics:**

- File size: ~5x smaller than JSON (2-3MB vs 11-16MB)
- Load time: ~20x faster than JSON (100ms vs 2000ms)
- Memory: On-demand loading vs full file in memory
- Query: Indexed, optimized for filtering by features

Integration Guide
-----------------

The corpus SQLite builder is an **optional performance optimization** that runs
after syllable feature annotation. The JSON file remains the canonical source of
truth, while the SQLite database provides a faster query interface for interactive
tools like the TUI.

**Standard build pipeline:**

.. code-block:: bash

    # Step 1: Extract syllables (pyphen or NLTK)
    python -m build_tools.pyphen_syllable_extractor --file input.txt

    # Step 2: Normalize syllables
    python -m build_tools.pyphen_syllable_normaliser --run-dir _working/output/20260110_115453_pyphen/

    # Step 3: Annotate with phonetic features
    python -m build_tools.syllable_feature_annotator \
        --syllables _working/output/20260110_115453_pyphen/pyphen_syllables_unique.txt \
        --frequencies _working/output/20260110_115453_pyphen/pyphen_syllables_frequencies.json

    # Step 4: Convert to SQLite (OPTIONAL, for performance)
    python -m build_tools.corpus_sqlite_builder \
        _working/output/20260110_115453_pyphen/

**When to use this tool:**

- **Required for TUI performance:** If you're using ``syllable_walk_tui`` with large corpora
  (10,000+ syllables), converting to SQLite dramatically improves load times and responsiveness.

- **Optional for other tools:** Command-line analysis tools can work directly with JSON files.
  SQLite is only necessary when interactive performance matters.

- **Batch conversion:** Run with ``--batch`` flag to convert all existing corpora at once.

**Regeneration is safe:**

The SQLite database can be deleted and regenerated at any time from the JSON source:

.. code-block:: bash

    # Delete database
    rm _working/output/20260110_115453_pyphen/data/corpus.db

    # Regenerate from JSON
    python -m build_tools.corpus_sqlite_builder \
        _working/output/20260110_115453_pyphen/

**Idempotent operation:**

Running the converter multiple times is safe. Use ``--force`` to overwrite existing databases:

.. code-block:: bash

    # Regenerate, overwriting existing database
    python -m build_tools.corpus_sqlite_builder \
        _working/output/20260110_115453_pyphen/ --force

Notes
-----

**Design Philosophy:**

The corpus SQLite builder follows the principle that **JSON is the canonical format**
and **SQLite is derived data**. This means:

- JSON files are never deleted or modified by this tool
- SQLite databases can be regenerated at any time
- Both formats coexist peacefully in the ``data/`` subdirectory
- The TUI automatically prefers SQLite when available, falls back to JSON

**Performance considerations:**

- Conversion time: ~5-10 seconds for 30,000 syllables
- Memory usage during conversion: ~50MB peak (batched inserts)
- The ``--batch-size`` parameter controls transaction size (default: 10,000)
- Larger batch sizes are faster but use more memory

**Backwards compatibility:**

The TUI maintains full backwards compatibility with JSON-only corpora. If no ``corpus.db``
file exists, it will load from JSON with no errors. This allows gradual migration to SQLite
without breaking existing workflows.

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.
The SQLite databases are used exclusively by interactive analysis tools.

API Reference
-------------

.. automodule:: build_tools.corpus_sqlite_builder
   :members:
   :undoc-members:
   :show-inheritance:
