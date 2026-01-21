===============
Syllable Walker
===============

.. currentmodule:: build_tools.syllable_walk

Overview
--------

.. automodule:: build_tools.syllable_walk
   :no-members:

Core Concepts
-------------

Phonetic Distance
~~~~~~~~~~~~~~~~~

Each syllable has 12 binary phonetic features (from ``syllable_feature_annotator``). The distance between
two syllables is the number of features that differ (Hamming distance). The ``max_flips`` parameter limits
how many features can change in a single step.

Neighbor Graph
~~~~~~~~~~~~~~

During initialization, the walker pre-computes which syllables are "neighbors" (within the specified
Hamming distance). This enables fast walk generation:

- **Distance 1**: ~30 sec initialization, conservative walks
- **Distance 2**: ~1 min initialization, moderate walks
- **Distance 3**: ~3 min initialization, maximum flexibility

For 500k+ syllable datasets, distance 3 is recommended.

Determinism
~~~~~~~~~~~

The same seed always produces the same walk. This is essential for reproducible experiments, testing,
and debugging. Each walk uses an isolated RNG instance to avoid global state contamination.

Walk Structure
~~~~~~~~~~~~~~

**Invariant:** A syllable walk always produces one more syllable than the number of steps,
as each step represents a transition (edge) between syllables (vertices).

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Steps
     - Syllables Produced
     - Example
   * - 0
     - 1
     - Starting syllable only (no transitions)
   * - 1
     - 2
     - Start → one neighbor
   * - 5
     - 6
     - Start → 5 transitions
   * - 10
     - 11
     - Start → 10 transitions

This follows from graph theory: a path with *n* edges connects *n+1* vertices.

Walk Profiles
~~~~~~~~~~~~~

The walker includes four pre-configured profiles:

.. list-table::
   :header-rows: 1
   :widths: 15 30 10 10 10 10 15

   * - Profile
     - Description
     - Steps
     - Max Flips
     - Temperature
     - Freq Weight
     - Use Case
   * - clerical
     - Conservative, minimal change
     - 5
     - 1
     - 0.3
     - 1.0
     - Formal names
   * - dialect
     - Balanced exploration
     - 5
     - 2
     - 0.7
     - 0.0
     - General use
   * - goblin
     - Chaotic, high variation
     - 5
     - 2
     - 1.5
     - -0.5
     - Exotic names
   * - ritual
     - Maximum exploration
     - 5
     - 3
     - 2.5
     - -1.0
     - Extreme variation

**Frequency Weight** controls syllable selection:

- Positive values (e.g. 1.0) favor common syllables
- Zero (0.0) is neutral
- Negative values (e.g. -1.0) favor rare syllables

**Temperature** controls randomness:

- Low (0.3) = more deterministic, prefer lowest-cost moves
- High (2.5) = more random, explore high-cost moves

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_walk.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_walk

Integration Guide
-----------------

The syllable walker uses output from the feature annotator and/or the corpus database builder.
It automatically discovers pipeline run directories from ``_working/output/``.

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

   # Step 4: Start the web interface
   python -m build_tools.syllable_walk --web
   # Auto-discovers port starting at 8000
   # Shows all available run directories with selection counts

**When to use this tool:**

- To explore phonetic connectivity in your syllable corpus
- To browse name selections (first_name, last_name, place_name)
- To compare different extractors (pyphen vs NLTK) and their phonetic behaviors
- To test if desired phonetic transitions exist before creating patterns
- To discover interesting phonetic progressions for name generation

Advanced Topics
---------------

Web Interface
~~~~~~~~~~~~~

The simplified web interface provides three main features:

1. **Run Selector** - Choose from discovered pipeline runs
2. **Selections Browser** - Browse generated name selections
3. **Quick Walk** - Generate syllable walks with preset profiles

**Starting the Server:**

.. code-block:: bash

   # Auto-discover port starting at 8000
   python -m build_tools.syllable_walk --web

   # Specify exact port (fails if unavailable)
   python -m build_tools.syllable_walk --web --port 9000

   # Verbose mode for debugging
   python -m build_tools.syllable_walk --web --verbose

**Run Discovery:**

The server scans ``_working/output/`` for directories matching the pattern
``YYYYMMDD_HHMMSS_{extractor}``. For each run, it displays:

- **Folder name** (e.g., ``20260121_084017_nltk``)
- **Syllable count** from SQLite database or JSON
- **Selection count** (number of selection files)

Example display: ``20260121_084017_nltk (3,135 syllables, 3 selections)``

**Selections Browser:**

The interface shows tabbed selection categories when a run has selections:

- **First Names** - ``selections/{prefix}_first_name_*.json``
- **Last Names** - ``selections/{prefix}_last_name_*.json``
- **Place Names** - ``selections/{prefix}_place_name_*.json``

Each selection displays:

- Name and syllables
- Admission score
- Sortable table interface

**Data Sources:**

The walker prefers SQLite ``corpus.db`` for performance, falling back to annotated JSON:

1. ``{run_dir}/data/corpus.db`` - SQLite database (fast, <100ms load)
2. ``{run_dir}/data/{prefix}_syllables_annotated.json`` - JSON fallback

**API Endpoints:**

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

The web server uses Python's standard library ``http.server`` (no Flask dependency).

Algorithm Details
~~~~~~~~~~~~~~~~~

**Cost Function:**

Each potential step has a cost based on:

1. **Hamming distance** - Number of features that change
2. **Feature-specific costs** - Some features cost more to change
3. **Frequency weight** - Bias toward common or rare syllables
4. **Inertia** - Tendency to stay at current syllable

The walker uses softmax selection with temperature to probabilistically choose the next syllable:

.. code-block:: text

   For each neighbor n:
     hamming_cost = sum(feature_costs[i] for i where features differ)
     freq_cost = frequency_weight × log(frequency[n])
     total_cost = hamming_cost + freq_cost + inertia_cost

   Probability of selecting n:
     P(n) = exp(-cost(n) / temperature) / sum(exp(-cost(k) / temperature))

Higher temperature = more random selection (flattens probability distribution)

Lower temperature = more deterministic (strongly favors lowest cost)

Performance
~~~~~~~~~~~

**SQLite vs JSON Loading:**

.. list-table::
   :header-rows: 1

   * - Data Source
     - Load Time
     - Notes
   * - SQLite corpus.db
     - <100ms
     - Preferred, indexed queries
   * - Annotated JSON
     - 2-3 minutes
     - Fallback, loads entire file

**Walk Generation:**

- **After initialization**: <10ms per walk (instant)
- **Deterministic**: Same seed always produces same walk
- **Scalable**: Speed independent of corpus size

Notes
-----

**Dependencies:**

- Requires NumPy for efficient feature matrix operations (build-time dependency)
- Uses standard library ``http.server`` for web interface (no Flask)

**Troubleshooting:**

**Port Already in Use:**

The server auto-discovers available ports starting at 8000. If a specific port is requested
with ``--port`` and is unavailable, the server will fail with an error message.

.. code-block:: bash

   # Auto-discover (tries 8000, 8001, 8002, ...)
   python -m build_tools.syllable_walk --web

   # Specific port (fails if unavailable)
   python -m build_tools.syllable_walk --web --port 9000

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

- :doc:`syllable_feature_annotator` - Generates input data with phonetic features
- :doc:`corpus_sqlite_builder` - Builds SQLite database for fast loading
- :doc:`name_combiner` - Generates name candidates
- :doc:`name_selector` - Selects names by policy

For detailed usage guide, see: ``claude/build_tools/syllable_walk.md``

API Reference
-------------

.. automodule:: build_tools.syllable_walk
   :members:
   :undoc-members:
   :show-inheritance:
