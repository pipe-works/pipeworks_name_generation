=========================
Syllable Walker Web
=========================

.. currentmodule:: build_tools.syllable_walk_web

Overview
--------

.. automodule:: build_tools.syllable_walk_web
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_walk_web.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_walk_web

Output Format
-------------

The web interface is an interactive browser-based tool and does not produce file-based outputs.
Instead, it provides a visual interface for exploring syllable walks and name selections.

**Interface Components:**

1. **Run Selector** - Dropdown to choose from discovered pipeline runs
2. **Selections Browser** - Tabbed view of name selections (first_name, last_name, place_name)
3. **Quick Walk Generator** - Generate walks with preset profiles

Integration Guide
-----------------

The web interface auto-discovers pipeline runs from ``_working/output/`` and provides
a browser for exploring selections and generating walks.

**Recommended Workflow:**

.. code-block:: bash

   # Step 1: Extract and normalize syllables
   python -m build_tools.pyphen_syllable_extractor --file wordlist.txt
   python -m build_tools.pyphen_syllable_normaliser \
     --run-dir _working/output/20260110_115453_pyphen/

   # Step 2: Annotate with phonetic features
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/20260110_115453_pyphen/pyphen_syllables_unique.txt \
     --frequencies _working/output/20260110_115453_pyphen/pyphen_syllables_frequencies.json

   # Step 3: (Optional) Build SQLite database for faster loading
   python -m build_tools.corpus_sqlite_builder \
     --run-dir _working/output/20260110_115453_pyphen/

   # Step 4: Generate name candidates and selections
   python -m build_tools.name_combiner \
     --run-dir _working/output/20260110_115453_pyphen/ \
     --syllables 2 --count 10000

   python -m build_tools.name_selector \
     --run-dir _working/output/20260110_115453_pyphen/ \
     --candidates candidates/pyphen_candidates_2syl.json \
     --name-class first_name

   # Step 5: Start the web interface
   python -m build_tools.syllable_walk_web
   # Auto-discovers port starting at 8000

**When to use this tool:**

- To browse name selections (first_name, last_name, place_name)
- To interactively explore syllable walks through a browser
- To compare different pipeline runs and their selections
- To quickly generate walks without command-line arguments

Advanced Topics
---------------

Run Discovery
~~~~~~~~~~~~~

The server scans ``_working/output/`` for directories matching the pattern
``YYYYMMDD_HHMMSS_{extractor}``. For each run, it displays:

- **Folder name** (e.g., ``20260121_084017_nltk``)
- **Syllable count** from SQLite database or JSON
- **Selection count** (number of selection files)

Example display: ``20260121_084017_nltk (3,135 syllables, 3 selections)``

Selections Browser
~~~~~~~~~~~~~~~~~~

The interface shows tabbed selection categories when a run has selections:

- **First Names** - ``selections/{prefix}_first_name_*.json``
- **Last Names** - ``selections/{prefix}_last_name_*.json``
- **Place Names** - ``selections/{prefix}_place_name_*.json``

Each selection displays:

- Name and syllables
- Admission score
- Sortable table interface

Data Sources
~~~~~~~~~~~~

The walker prefers SQLite ``corpus.db`` for performance, falling back to annotated JSON:

1. ``{run_dir}/data/corpus.db`` - SQLite database (fast, <100ms load)
2. ``{run_dir}/data/{prefix}_syllables_annotated.json`` - JSON fallback

API Endpoints
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Endpoint
     - Method
     - Description
   * - ``/api/runs``
     - GET
     - List all discovered run directories with metadata
   * - ``/api/runs/{id}/selections/{class}``
     - GET
     - Get selection data for a name class
   * - ``/api/select-run``
     - POST
     - Switch to a different run (loads walker)
   * - ``/api/walk``
     - POST
     - Generate a syllable walk
   * - ``/api/stats``
     - GET
     - Get current walker stats (syllable count, etc.)

The web server uses Python's standard library ``http.server`` (no Flask dependency).

Notes
-----

**Dependencies:**

- Uses standard library ``http.server`` for web interface (no Flask)
- Requires NumPy for efficient feature matrix operations (build-time dependency)

**Troubleshooting:**

**Port Already in Use:**

The server auto-discovers available ports starting at 8000. If a specific port is requested
with ``--port`` and is unavailable, the server will fail with an error message.

.. code-block:: bash

   # Auto-discover (tries 8000, 8001, 8002, ...)
   python -m build_tools.syllable_walk_web

   # Specific port (fails if unavailable)
   python -m build_tools.syllable_walk_web --port 9000

**No Runs Found:**

If no runs are discovered, ensure you have pipeline output directories:

.. code-block:: bash

   # Check for existing runs
   ls _working/output/

   # Run the extraction pipeline first
   python -m build_tools.nltk_syllable_extractor --file wordlist.txt
   python -m build_tools.nltk_syllable_normaliser \
     --run-dir _working/output/YYYYMMDD_HHMMSS_nltk/

**No Selections Shown:**

Selection files must be in the ``selections/`` subdirectory with the naming pattern
``{prefix}_{name_class}_{N}syl.json``. Run the name selector to generate them:

.. code-block:: bash

   python -m build_tools.name_selector \
     --run-dir _working/output/YYYYMMDD_HHMMSS_nltk/ \
     --candidates candidates/nltk_candidates_2syl.json \
     --name-class first_name \
     --count 100

**Build-time tool:**

This is a build-time analysis tool only - not used during runtime name generation.

**Related Documentation:**

- :doc:`syllable_walk` - Core syllable walker algorithm and CLI
- :doc:`syllable_walk_tui` - Interactive TUI for exploring phonetic space
- :doc:`syllable_feature_annotator` - Generates input data with phonetic features
- :doc:`corpus_sqlite_builder` - Builds SQLite database for fast loading
- :doc:`name_combiner` - Generates name candidates
- :doc:`name_selector` - Selects names by policy

API Reference
-------------

.. automodule:: build_tools.syllable_walk_web
   :members:
   :undoc-members:
   :show-inheritance:
