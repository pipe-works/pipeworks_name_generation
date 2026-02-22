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

The web interface is an interactive browser-based tool with in-memory working
state (pipeline job status, patch data, walks, candidates, selections).

It produces file outputs in two places:

- Pipeline runs in ``<output_base>/<timestamp>_<extractor>/`` (extract/normalize/annotate/db outputs)
- Package builds from the Walker tab:

  - Browser download: ``<name>-<version>.zip`` (HTTP response from ``/api/walker/package``)
  - Disk persistence (best-effort): ``<output_base>/packages/<name>-<version>_<timestamp>.zip``
    plus ``<name>-<version>_<timestamp>_metadata.json``

**Interface Components:**

1. **Pipeline tab** — Run the full extraction pipeline from the browser:

   - Filesystem browser for source directory/file selection
   - Extractor selection (Pyphen or NLTK), pyphen language selection
   - Live monitor for stage progress and subprocess logs
   - Run history view backed by manifest-discovered run directories
     (refreshes on tab entry and after run completion)

2. **Walker tab** — Dual-patch corpus exploration and name generation:

   - Load corpora into Patch A and Patch B for side-by-side comparison
   - Generate syllable walks with named profiles or custom walk parameters
   - Combine syllables into candidates in flat-sampling or walk-based mode
   - Select names by policy (first_name, last_name, place_name, etc.)
   - Reach deep-dive per profile (top reachable syllables with export)
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

**INI configuration (``--config``):**

The CLI reads ``[build_tools]`` settings from an INI file (default: ``server.ini``).
CLI arguments override INI values.

.. code-block:: ini

   [build_tools]
   output_base = _working/output
   corpus_dir_a = /path/to/patch_a/runs
   corpus_dir_b = /path/to/patch_b/runs
   port = 8000
   verbose = true

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

The module is organised into four layers:

**API handlers** (``api/``):

- ``browse.py`` — Filesystem directory listing
- ``pipeline.py`` — Pipeline start, status, cancel, run discovery
- ``walker.py`` — Corpus loading, walks, reach tables, combining, selection, export, packaging, analysis

**Service modules** (``services/``):

- ``corpus_loader.py`` — Delegates to ``syllable_walk.db.load_syllables``
- ``combiner_runner.py`` — Delegates to ``name_combiner.combiner``
- ``selector_runner.py`` — Policy caching and delegation to ``name_selector``
- ``walk_generator.py`` — Walk generation with profile routing and seed offsets
- ``metrics.py`` — Corpus shape metrics with length bucketing and terrain scores
- ``packager.py`` — ZIP archive building with manifest and disk persistence
- ``pipeline_runner.py`` — Background subprocess execution with cancellation

**Discovery layer**:

- ``run_discovery.py`` — Manifest-driven run discovery, selection discovery,
  and History payload shaping (status, timings, stage state, IPC hashes)

**State** (``state.py``):

- ``PatchState`` — Per-patch data (corpus, walker, walks, candidates, selections)
- ``PipelineJobState`` — Pipeline job status, logs, subprocess handle
- ``ServerState`` — Composition of two patches + pipeline job + output path + optional per-patch run roots

**Server** (``server.py``):

- stdlib ``http.server.ThreadingHTTPServer`` for concurrent XHR
- Static file serving with directory-traversal guard
- Lazy API imports to avoid circular dependencies

Run Discovery
~~~~~~~~~~~~~

The server scans a base directory for run folders matching:
``YYYYMMDD_HHMMSS_{extractor}``.

- ``GET /api/pipeline/runs`` uses ``output_base`` by default.
- ``GET /api/pipeline/runs?patch=a`` and ``?patch=b`` use ``corpus_dir_a`` /
  ``corpus_dir_b`` when configured.

Discovery is strict and manifest-first:

- Run folders must contain ``manifest.json``.
- ``manifest.json`` must include required keys and ``run_id`` must match folder name.
- Missing/corrupt/non-conformant manifests are skipped (no legacy fallback parsing).

For each valid run, discovery reports:

- folder/run id and extractor type
- status and run timestamps
- stage status map (extract/normalize/annotate/database)
- manifest-derived metrics (including syllable count and processed-file count)
- artifact paths (including ``corpus_db_path`` / annotated JSON when present)
- IPC hashes (input/output) from manifest
- selection file map by name class

Pipeline Execution Model
~~~~~~~~~~~~~~~~~~~~~~~~

Pipeline execution runs in a background thread via ``services/pipeline_runner.py``.
Stages are subprocess-backed and logged line-by-line to job state:

1. ``extract`` (always)
2. ``normalize`` (if ``run_normalize=True``)
3. ``annotate`` (if ``run_annotate=True`` and normalize ran)
4. ``database`` (runs after annotate; executes ``build_tools.corpus_sqlite_builder --force``)

Status is polled through ``GET /api/pipeline/status`` and includes:
``status``, ``current_stage``, ``progress_percent``, ``output_path``, and structured log lines.

Corpus Loading and Walker Readiness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``POST /api/walker/load-corpus`` performs two phases:

1. **Synchronous data load**: uses ``services/corpus_loader.load_corpus``, which delegates to
   ``build_tools.syllable_walk.db.load_syllables`` (SQLite preferred, JSON fallback).
2. **Background walker init**: builds ``SyllableWalker`` and resolves profile reaches via
   run-local IPC cache.

Profile reach caching is run-directory local:

- Cache path: ``<run_dir>/ipc/walker_profile_reaches.v1.json``
- Cache schema: ``build_tools/syllable_walk_web/schemas/walker_profile_reaches.v1.schema.json``
- Cache key material:
  - manifest IPC output hash (from ``<run_dir>/manifest.json``)
  - walker graph settings (neighbor distance, inertia, feature costs)
  - reach settings (threshold + named profile parameters)
- On cache hit, precomputed reaches are loaded.
- On miss/invalid cache, reaches are recomputed and cache is rewritten.

The frontend polls ``GET /api/walker/stats`` until ``walker_ready=true``. During load,
``loading_stage`` reports phase progress (e.g., building neighbor graph).
The stats payload also includes ``reach_cache_status`` per patch
(``hit`` | ``miss`` | ``invalid`` | ``error`` | ``none``) to make cache
behavior explicit in diagnostics.

Important readiness guarantees:

- Reach precomputation completes before ``walker_ready`` is set ``true``.
- ``loader_status`` and ``loading_error`` expose terminal failure states explicitly.
- Load concurrency is guarded by per-patch generation tokens, so stale background
  threads cannot overwrite newer corpus loads.

Candidate Generation Modes
~~~~~~~~~~~~~~~~~~~~~~~~~~

``POST /api/walker/combine`` supports two modes:

- **Flat sampling** (default; ``profile`` absent or ``"flat"``):
  delegates to ``name_combiner.combine_syllables`` with ``frequency_weight``.
- **Walk-based sampling** (named profile or ``"custom"``):
  generates walks first, then aggregates features from walked syllables.

The response includes ``generated``, ``unique``, and ``duplicates`` counts.

Dual-Patch Comparison
~~~~~~~~~~~~~~~~~~~~~

The Walker tab supports loading two independent corpora into Patch A and
Patch B. Each patch maintains its own:

- Annotated syllable data and frequency map
- Walker instance (with pre-computed neighbor graph)
- Generated walks, candidates, and selections

This enables side-by-side comparison of different extractors, languages,
or source texts.

API Authority
~~~~~~~~~~~~~

The web frontend is presentation and UX only. The API is the behavioral
authority for validation and execution semantics.

- Frontend checks (for example ``min_length <= max_length``) are UX helpers.
- API handlers enforce the same constraints for all clients (UI and non-UI).
- Requests that fail contract validation return JSON ``{"error": ...}`` with HTTP 400.

Examples of API-authoritative behavior:

- ``POST /api/walker/walk`` validates numeric constraints including
  ``neighbor_limit``, ``min_length``, and ``max_length``.
- ``POST /api/pipeline/start`` validates ``min_syllable_length`` /
  ``max_syllable_length`` ranges server-side.
- ``GET /api/walker/name-classes`` is the source of truth for selector
  class options (UI options are populated from this endpoint).

Walker State Model
~~~~~~~~~~~~~~~~~~

``GET /api/walker/stats`` returns independent status for ``patch_a`` and ``patch_b``.
Each patch reports ``loader_status`` plus readiness/error metadata.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - ``loader_status``
     - Meaning
   * - ``idle``
     - No active load thread. Patch may be empty, or may have prior corpus metadata
       without a currently running initialization.
   * - ``loading``
     - Corpus load generation is in progress. ``loading_stage`` reports the current phase
       (for example ``"Building neighbour graph"``).
   * - ``ready``
     - Walker and pre-computed reaches are available; ``walker_ready=true``.
   * - ``error``
     - Current load generation failed. ``loading_error`` contains terminal error text.

Response fields per patch include:

- ``corpus`` (active ``run_id``)
- ``corpus_type`` (``nltk`` or ``pyphen``)
- ``syllable_count``
- ``walker_ready``, ``loading_stage``, ``loading_error``, ``loader_status``
- ``has_walks``, ``has_candidates``, ``has_selections``
- ``reaches`` (when available; includes reach count and computation timing)

Patch Isolation and Race Safety
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Patch A and Patch B are fully isolated in server state.

- Loading a corpus resets only the target patch state.
- Walks/candidates/selections from one patch never overwrite the other patch.
- Loader concurrency is generation-token guarded:

  - each ``load-corpus`` increments ``load_generation``;
  - background init writes are applied only if generation is still current;
  - stale loader threads exit without mutating patch state.

This prevents rapid corpus switches from producing stale overwrite races.

Determinism and Seed Behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Walk generation is deterministic for fixed request parameters and seed.
- Batched walks use ``seed + i`` per walk to keep outputs deterministic while
  still varying entries within one request.
- Flat combiner and selector paths accept explicit seed values for deterministic
  output ordering/sampling.
- Without a seed, behavior remains valid but non-deterministic between runs.

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
     - List discovered runs; supports ``?patch=a|b`` for per-patch run roots
   * - ``/api/pipeline/status``
     - GET
     - Get pipeline job status, progress, and log lines
   * - ``/api/pipeline/start``
     - POST
     - Start extraction pipeline (source path, extractor, and optional stage/constraint fields)
   * - ``/api/pipeline/cancel``
     - POST
     - Cancel a running pipeline job
   * - ``/api/browse-directory``
     - POST
     - Browse a filesystem directory (for source/output selection)
   * - ``/api/walker/stats``
     - GET
     - Get dual-patch state (loaded corpora, loader/cache status, readiness, reach metadata)
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
     - Generate syllable walks with validated constraints and optional seed
   * - ``/api/walker/combine``
     - POST
     - Generate candidates (flat mode or walk-based mode), returns deduplication stats
   * - ``/api/walker/reach-syllables``
     - POST
     - Return top reachable syllables for one profile/patch (reach deep-dive tables)
   * - ``/api/walker/select``
     - POST
     - Select names by policy (name class, mode, count)
   * - ``/api/walker/export``
     - POST
     - Export selected names as a list
   * - ``/api/walker/package``
     - POST
     - Build ZIP archive with manifest (binary response) and persist package files to disk
   * - ``/api/settings``
     - GET
     - Get current server settings (output base path)
   * - ``/api/settings/output-base``
     - POST
     - Update the output base directory
   * - ``/api/version``
     - GET
     - Return package version for UI header display

The web server uses Python's standard library ``http.server`` (no Flask dependency).

Common Request Fields
~~~~~~~~~~~~~~~~~~~~~

Key request bodies for current API routes:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Endpoint
     - Important request fields
   * - ``POST /api/pipeline/start``
     - ``source_path`` (required), ``output_dir`` (optional), ``extractor`` (default ``pyphen``),
       ``language`` (default ``auto``), ``file_pattern`` (default ``*.txt``),
       ``min_syllable_length``/``max_syllable_length`` (defaults ``2``/``8``),
       ``run_normalize``/``run_annotate`` (default ``true``/``true``)
   * - ``POST /api/walker/load-corpus``
     - ``patch`` (``a``/``b``), ``run_id`` (required non-empty string)
   * - ``POST /api/walker/walk``
     - ``patch``, ``count``, ``steps``, ``seed``, optional ``profile``.
       Custom constraints are always accepted: ``max_flips``, ``temperature``,
       ``frequency_weight``, ``neighbor_limit``, ``min_length``, ``max_length``.
       API validates ranges (for example ``min_length <= max_length``).
   * - ``POST /api/walker/combine``
     - ``patch``, ``count``, ``syllables`` (int or list), ``seed``.
       Flat mode: ``frequency_weight``.
       Walk mode: ``profile`` (named or ``custom``); custom supports
       ``max_flips``, ``temperature``, ``frequency_weight``
   * - ``POST /api/walker/reach-syllables``
     - ``patch`` and ``profile`` (must match one of the precomputed profile keys)
   * - ``POST /api/walker/select``
     - ``patch``, ``name_class``, ``count``, ``mode`` (``hard``/``soft``),
       ``order`` (``alphabetical``/``random``), ``seed``
   * - ``POST /api/walker/package``
     - ``name``, ``version``, include flags:
       ``include_walks_a``, ``include_walks_b``, ``include_candidates``, ``include_selections``

Walker Endpoint Contract Details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 42 30

   * - Endpoint
     - Contract and validation rules
     - Success payload highlights
   * - ``GET /api/walker/stats``
     - No request body. Returns state for both patches, including ``loader_status`` and
       optional ``reaches`` map when available.
     - ``patch_a`` / ``patch_b`` objects with corpus, readiness, loading/error fields,
       and ``has_*`` flags.
   * - ``POST /api/walker/load-corpus``
     - Requires ``patch in {"a","b"}`` and non-empty ``run_id``.
       Errors for invalid patch, missing run, or corpus load failure.
     - ``patch``, ``run_id``, ``corpus_type``, ``syllable_count``, ``source``,
       ``status="loading"``.
   * - ``POST /api/walker/walk``
     - Requires ready walker for target patch. Validates numeric fields:
       ``count >= 1``, ``steps >= 0``, ``max_flips >= 1``, ``neighbor_limit >= 1``,
       ``min_length >= 1``, ``max_length >= 1``, ``min_length <= max_length``,
       ``temperature > 0``, and integer-or-null seed.
     - ``patch`` and ``walks`` (each walk includes ``formatted``, ``syllables``, ``steps``).
   * - ``POST /api/walker/combine``
     - Requires loaded corpus. ``profile`` controls mode:
       absent/``flat`` uses flat combiner; named/custom profile uses walker path and
       requires walker readiness.
     - ``generated``, ``unique``, ``duplicates``, ``syllables``, ``source``.
   * - ``POST /api/walker/reach-syllables``
     - Requires precomputed reaches and valid ``profile`` key for target patch.
       Errors if reach data or walker is not ready.
     - ``profile``, ``reach``, ``total``, ``unique_reachable``, ``syllables`` list.
   * - ``POST /api/walker/select``
     - Requires existing candidates. Validates patch and delegates policy validation to
       selector service (unknown name class returns error).
     - ``name_class``, ``mode``, ``count``, ``requested``, ``names``.
   * - ``POST /api/walker/export``
     - Requires prior selection output for target patch.
     - ``patch``, ``count``, ``names``.
   * - ``POST /api/walker/package``
     - Accepts package metadata and include flags. Builds ZIP from in-memory state.
     - Binary ZIP response with attachment filename ``<name>-<version>.zip``.

Pipeline Configure ↔ API Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Pipeline Configure tab now maps directly to ``POST /api/pipeline/start``:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Configure control
     - Request field / behavior
   * - Source picker (directory or file)
     - ``source_path`` (required)
   * - Output picker
     - ``output_dir`` (optional). If not selected, server default ``output_base`` is used.
   * - Extractor (``pyphen`` / ``nltk``)
     - ``extractor``
   * - Language radios + custom language code
     - ``language``. For ``pyphen``, custom code overrides radio value; for ``nltk``, frontend sends ``"auto"``.
   * - File pattern
     - ``file_pattern``
   * - Min / Max syllable length
     - ``min_syllable_length`` / ``max_syllable_length`` (frontend validates ``min <= max`` and API rejects invalid ranges/types)
   * - Normalize toggle
     - ``run_normalize``
   * - Annotate toggle
     - ``run_annotate`` (frontend enforces annotate requires normalize)

Pipeline Output ↔ API Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Monitor and History views consume pipeline API responses as follows:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - UI output area
     - API field(s) used
   * - Monitor status/progress/log
     - ``GET /api/pipeline/status``: ``status``, ``current_stage``, ``progress_percent``, ``log_lines``
   * - Monitor completion message
     - ``GET /api/pipeline/status``: ``output_path`` (shown when available)
   * - Monitor stage chips
     - ``current_stage`` + requested stage toggles from start payload
   * - History run list
     - ``GET /api/pipeline/runs``:
       ``run_id``, ``path``, ``timestamp``, ``extractor_type``,
       ``syllable_count``, ``status``
   * - History run detail metadata
     - ``source_path``, ``files_processed``, ``processing_time``,
       ``created_at_utc``, ``completed_at_utc`` (from ``manifest.json``)
   * - History output tree
     - ``output_tree_lines`` (manifest artifact list rendered as a deterministic tree)
   * - History database stage chip
     - ``stage_statuses.database``
   * - History stage chips (all stages)
     - ``stage_statuses.extract|normalize|annotate|database``
   * - History IPC hash fields
     - ``ipc_input_hash``, ``ipc_output_hash`` (compact display + full tooltip)

Walker Controls ↔ API Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Walk, Combine, and Select controls map to Walker endpoints as follows.

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Walker control
     - API field
     - Runtime effect
   * - Patch selector (A/B context)
     - ``patch``
     - Routes request to isolated patch state.
   * - Walk count / steps
     - ``count`` / ``steps``
     - Sets number of generated walks and walk length.
   * - Walk profile cards
     - ``profile``
     - Named profile uses tuned walker profile path;
       ``custom`` uses explicit slider/spinner fields.
   * - Walk max flips / temperature / frequency
     - ``max_flips`` / ``temperature`` / ``frequency_weight``
     - Controls walker transition behavior in custom mode.
   * - Walk neighbors
     - ``neighbor_limit``
     - Limits candidate neighbors evaluated per step.
   * - Walk min/max length
     - ``min_length`` / ``max_length``
     - Constrains syllable-length eligibility for starts/transitions.
   * - Walk seed
     - ``seed``
     - Enables deterministic walk batches (internally offset per walk).
   * - Combine profile cards
     - ``profile`` on ``/api/walker/combine``
     - Chooses flat combiner mode vs walk-based generation mode.
   * - Combine count/syllables/seed
     - ``count`` / ``syllables`` / ``seed``
     - Controls candidate volume, name length classes, and deterministic sampling.
   * - Selector class dropdown
     - ``name_class`` on ``/api/walker/select``
     - Applies selected policy from ``name_classes.yml``.
   * - Selector mode/order/count/seed
     - ``mode`` / ``order`` / ``count`` / ``seed``
     - Controls strictness, output ordering, and deterministic random ordering.

History Manifest Contract
~~~~~~~~~~~~~~~~~~~~~~~~~

History discovery is strict manifest-first (no legacy fallback parsing):

- Run directory must contain ``manifest.json``.
- Manifest must include required contract keys:
  ``manifest_version``, ``run_id``, ``status``, ``extractor``,
  ``config``, ``metrics``, ``stages``, ``artifacts``.
- ``run_id`` must match the run directory name.
- Missing/corrupt/non-conformant manifests are skipped by discovery.

This keeps the run directory as the single source of truth and avoids
cross-file drift between legacy metadata files and API payloads.

Pipeline Manifest and IPC
~~~~~~~~~~~~~~~~~~~~~~~~~

Each pipeline run writes ``<run_dir>/manifest.json`` as the canonical run record.

High-value fields used by History and diagnostics:

- ``status`` plus ``created_at_utc`` / ``completed_at_utc``
- ``config`` and ``metrics`` (including ``files_processed`` and unique syllable count)
- ``stages`` (per-stage status and duration)
- ``artifacts`` (deterministic run output inventory)
- ``ipc`` block:

  - ``input_hash`` from canonical run configuration
  - ``output_hash`` from canonical artifact+metric payload
  - library metadata (version/ref) for provenance

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
If patch-specific run roots are configured (``corpus_dir_a`` / ``corpus_dir_b``),
verify those paths contain timestamped run directories with valid ``manifest.json`` files.

.. code-block:: bash

   # Check for existing runs
   ls _working/output/

   # Or run the pipeline from the web UI's Pipeline tab

**Walker Load Fails or Stalls:**

Use ``GET /api/walker/stats`` as the source of truth:

- If ``loader_status="loading"``, inspect ``loading_stage`` for current phase.
- If ``loader_status="error"``, inspect ``loading_error`` and retry load.
- ``walker_ready=true`` means walks/reaches are ready for that patch.

Common causes:

- Run directory missing required artifacts (manifest declares missing files)
- Corrupt/unreadable SQLite/JSON artifacts
- Incompatible or malformed run directory copied into output roots

**Rapid Corpus Switching (Race-Safe Behavior):**

Loading a new run while a previous load is in progress is supported.
The server uses per-patch load generations and accepts writes only from the
current generation. Older background loads are ignored, preventing stale state
from overwriting the newly selected corpus.

If you switch repeatedly:

- trust the latest selected run in the UI;
- use ``/api/walker/stats`` to confirm final ``corpus`` and ``loader_status``.

**Name Class Dropdown Empty or Unexpected:**

Selector classes come from ``GET /api/walker/name-classes``. If the dropdown
is empty or stale:

- verify API route availability and server health;
- verify ``data/name_classes.yml`` exists and is valid YAML;
- reload the page after fixing policy file issues.

**Package Persistence Warnings:**

The package endpoint always returns a ZIP download when package generation succeeds.
Disk persistence to ``<output_base>/packages/`` is best-effort; permission/path issues
are logged as warnings on the server side and do not block the download.

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
