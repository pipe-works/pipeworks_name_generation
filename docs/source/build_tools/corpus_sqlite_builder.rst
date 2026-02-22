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
    │   └── corpus.db                         (derived, size varies by corpus)
    ├── pyphen_syllables_unique.txt
    ├── pyphen_syllables_frequencies.json
    └── ... (other corpus files)

**SQLite Database Schema:**

The ``corpus.db`` file contains two application tables:

1. **syllables table** - Main data storage

   - ``syllable`` (TEXT, PRIMARY KEY): The syllable string
   - ``frequency`` (INTEGER): Occurrence count in source corpus
   - 12 phonetic feature columns (INTEGER 0/1):

     - ``starts_with_vowel``
     - ``starts_with_cluster``
     - ``starts_with_heavy_cluster``
     - ``contains_plosive``
     - ``contains_fricative``
     - ``contains_liquid``
     - ``contains_nasal``
     - ``short_vowel``
     - ``long_vowel``
     - ``ends_with_vowel``
     - ``ends_with_nasal``
     - ``ends_with_stop``

2. **metadata table** - Database information

   - ``schema_version``: Database schema version (for migrations)
   - ``source_tool``: Tool that created the database
   - ``source_version``: Version of the converter tool
   - ``generated_at``: ISO 8601 timestamp
   - ``total_syllables``: Number of syllables in database
   - ``source_json_path``: Original JSON file name

SQLite may also include internal statistics tables (for example ``sqlite_stat1``)
after optimization runs (``ANALYZE``). These are SQLite-managed and not part of
the application data model.

**Indexes created:**

- ``idx_starts_with_vowel`` on ``syllables(starts_with_vowel)``
- ``idx_ends_with_vowel`` on ``syllables(ends_with_vowel)``
- ``idx_frequency`` on ``syllables(frequency DESC)``
- ``idx_vowel_boundaries`` on ``syllables(starts_with_vowel, ends_with_vowel)``
- ``idx_starts_with_cluster`` on ``syllables(starts_with_cluster)``
- ``idx_ends_with_stop`` on ``syllables(ends_with_stop)``

**Performance characteristics:**

- File size: typically much smaller than canonical JSON (exact ratio depends on corpus size/content)
- Load time: significantly faster than JSON loading for interactive tools
- Memory: On-demand loading vs full file in memory
- Query: Indexed, optimized for filtering by features

Integration Guide
-----------------

The corpus SQLite builder is an **optional performance optimization** that runs
after syllable feature annotation. The JSON file remains the canonical source of
truth, while the SQLite database provides a faster query interface for interactive
tools like the TUI.

Syllable Walk Web Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``build_tools.syllable_walk_web`` integrates with ``corpus.db`` at four points:

1. **Pipeline execution (database creation)**

   - In the web pipeline runner, the database stage runs after annotation and executes:

     .. code-block:: bash

        python -m build_tools.corpus_sqlite_builder <run_directory> --force

   - Output location is the standard path:
     ``<run_directory>/data/corpus.db``.
   - If normalization/annotation stages are skipped, this database stage does not run.

2. **Run discovery and listing**

   - The web run discovery scans output runs and checks for
     ``data/corpus.db``.
   - When present, syllable counts are read from SQLite via
     ``SELECT COUNT(*) FROM syllables``.
   - If no database exists, run discovery falls back to the annotated JSON file.

3. **Corpus loading for Walker API**

   - ``/api/walker/load-corpus`` calls the corpus loader, which delegates to
     ``build_tools.syllable_walk.db.load_syllables``.
   - Loading behavior is:

     - Prefer SQLite when ``corpus.db`` exists and is readable.
     - Fall back to ``*_syllables_annotated.json`` if SQLite is missing or read fails.
     - Return source info to the UI (for example ``"SQLite (2,088 syllables)"`` or
       ``"JSON (... syllables)"``).

4. **Read-only runtime queries**

   - SQLite access in the walker data layer uses read-only URI mode
     (``file:<path>?mode=ro``).
   - The web stack reads from ``syllables`` (for full corpus load and counts) and
     does not mutate ``corpus.db`` during browsing/walking.

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
