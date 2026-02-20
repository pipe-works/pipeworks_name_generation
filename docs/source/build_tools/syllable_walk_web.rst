=========================
Syllable Walker Web
=========================

.. currentmodule:: build_tools.syllable_walk_web

Overview
--------

.. automodule:: build_tools.syllable_walk_web
   :no-members:

.. image:: /_static/syllable_walk_web_preview.png
   :alt: Syllable Walk Web — dual-patch Walker interface
   :align: center

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_walk_web.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_walk_web

Output Format
-------------

The web interface is an interactive browser-based tool. It does not produce
file-based outputs directly, but the **Package** feature exports ZIP archives
containing walks, candidates, and selections.

**Interface Components:**

1. **Pipeline tab** — Run the full extraction pipeline from the browser:

   - Filesystem browser for source directory/file selection
   - Extractor selection (Pyphen or NLTK), language, syllable length constraints
   - Live log monitoring with stage progress
   - Toggle normalization and annotation stages

2. **Walker tab** — Dual-patch corpus exploration and name generation:

   - Load corpora into Patch A and Patch B for side-by-side comparison
   - Generate syllable walks with configurable profiles and seeds
   - Combine syllables into name candidates with deduplication stats
   - Select names by policy (first_name, last_name, place_name, etc.)
   - Export selected names as text or build ZIP packages with manifest

Integration Guide
-----------------

The web interface can run the full pipeline internally, so you can start
from raw text without running CLI tools first.

**Quickest path — start from scratch:**

.. code-block:: bash

   # Launch the web interface
   python -m build_tools.syllable_walk_web

   # In the browser:
   # 1. Pipeline tab → browse to your source text → Start Pipeline
   # 2. Walker tab → load the completed run into a patch → Walk / Combine / Select

**Starting from existing pipeline output:**

.. code-block:: bash

   # If you already have pipeline runs in _working/output/
   python -m build_tools.syllable_walk_web

   # The Walker tab discovers runs automatically and lists them for loading

**Custom output directory:**

.. code-block:: bash

   python -m build_tools.syllable_walk_web --output-base /path/to/corpus/output

**When to use this tool:**

- To run the full extraction pipeline without memorizing CLI arguments
- To compare two corpora side-by-side (dual-patch mode)
- To interactively explore syllable walks through a browser
- To generate, filter, and export names in a single session
- To build ZIP packages with manifest metadata for downstream consumption

Advanced Topics
---------------

Architecture
~~~~~~~~~~~~

The module is organised into three layers:

**API handlers** (``api/``):

- ``browse.py`` — Filesystem directory listing
- ``pipeline.py`` — Pipeline start, status, cancel, run discovery
- ``walker.py`` — Corpus loading, walks, combining, selection, export, packaging, analysis

**Service modules** (``services/``):

- ``corpus_loader.py`` — Delegates to ``syllable_walk.db.load_syllables``
- ``combiner_runner.py`` — Delegates to ``name_combiner.combiner``
- ``selector_runner.py`` — Policy caching and delegation to ``name_selector``
- ``walk_generator.py`` — Walk generation with profile routing and seed offsets
- ``metrics.py`` — Corpus shape metrics with length bucketing and terrain scores
- ``packager.py`` — ZIP archive building with manifest and disk persistence
- ``pipeline_runner.py`` — Background subprocess execution with cancellation

**State** (``state.py``):

- ``PatchState`` — Per-patch data (corpus, walker, walks, candidates, selections)
- ``PipelineJobState`` — Pipeline job status, logs, subprocess handle
- ``ServerState`` — Composition of two patches + pipeline job + output path

**Server** (``server.py``):

- stdlib ``http.server.ThreadingHTTPServer`` for concurrent XHR
- Static file serving with directory-traversal guard
- Lazy API imports to avoid circular dependencies

Run Discovery
~~~~~~~~~~~~~

The server scans the output directory for directories matching the pattern
``YYYYMMDD_HHMMSS_{extractor}``. For each run, it reports:

- **Folder name** (e.g., ``20260121_084017_nltk``)
- **Syllable count** from SQLite database or annotated JSON
- **Selection count** (number of selection files)
- **Extractor type** (pyphen, nltk, etc.)

Dual-Patch Comparison
~~~~~~~~~~~~~~~~~~~~~

The Walker tab supports loading two independent corpora into Patch A and
Patch B. Each patch maintains its own:

- Annotated syllable data and frequency map
- Walker instance (with pre-computed neighbor graph)
- Generated walks, candidates, and selections

This enables side-by-side comparison of different extractors, languages,
or source texts.

API Endpoints
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Endpoint
     - Method
     - Description
   * - ``/api/pipeline/runs``
     - GET
     - List discovered run directories with metadata
   * - ``/api/pipeline/status``
     - GET
     - Get pipeline job status, progress, and log lines
   * - ``/api/pipeline/start``
     - POST
     - Start extraction pipeline (source path, extractor, options)
   * - ``/api/pipeline/cancel``
     - POST
     - Cancel a running pipeline job
   * - ``/api/walker/stats``
     - GET
     - Get dual-patch state (loaded corpora, walker readiness)
   * - ``/api/walker/analysis/{patch}``
     - GET
     - Corpus shape metrics for a patch (terrain scores, distributions)
   * - ``/api/walker/name-classes``
     - GET
     - List available name class policies from ``name_classes.yml``
   * - ``/api/walker/load-corpus``
     - POST
     - Load a run's corpus into a patch (builds walker in background)
   * - ``/api/walker/walk``
     - POST
     - Generate syllable walks (count, profile, seed)
   * - ``/api/walker/combine``
     - POST
     - Generate name candidates with deduplication
   * - ``/api/walker/select``
     - POST
     - Select names by policy (name class, mode, count)
   * - ``/api/walker/export``
     - POST
     - Export selected names as a list
   * - ``/api/walker/package``
     - POST
     - Build ZIP archive with manifest (returns binary download)
   * - ``/api/browse-directory``
     - POST
     - Browse a filesystem directory (for source selection)
   * - ``/api/settings``
     - GET
     - Get current server settings (output base path)
   * - ``/api/settings/output-base``
     - POST
     - Update the output base directory

The web server uses Python's standard library ``http.server`` (no Flask dependency).

Notes
-----

**Dependencies:**

- Uses standard library ``http.server`` for the web interface (no Flask)
- Uses ``subprocess`` for pipeline stage execution
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

If no runs are discovered in the Walker tab, ensure you have pipeline output directories
in the configured output base, or use the Pipeline tab to run an extraction first.

.. code-block:: bash

   # Check for existing runs
   ls _working/output/

   # Or run the pipeline from the web UI's Pipeline tab

**Build-time tool:**

This is a build-time analysis tool only - not used during runtime name generation.

**Related Documentation:**

- :doc:`syllable_walk` - Core syllable walker algorithm and CLI
- :doc:`syllable_walk_tui` - Interactive TUI for exploring phonetic space
- :doc:`pipeline_tui` - Interactive TUI for running extraction pipelines
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
