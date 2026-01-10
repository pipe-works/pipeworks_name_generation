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

Output Format
-------------

Single Walk
~~~~~~~~~~~

.. code-block:: json

   {
     "walk": [
       {
         "syllable": "ka",
         "frequency": 20,
         "features": [0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0]
       },
       {
         "syllable": "pai",
         "frequency": 9,
         "features": [0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0]
       }
     ],
     "profile": "dialect",
     "start": "ka",
     "seed": 42
   }

Batch Output
~~~~~~~~~~~~

.. code-block:: json

   {
     "walks": [
       {
         "walk": [
           {"syllable": "ka", "frequency": 20, "features": [0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0]},
           {"syllable": "ki", "frequency": 15, "features": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0]}
         ],
         "start": "ka",
         "seed": 42
       },
       {
         "walk": [
           {"syllable": "bak", "frequency": 8, "features": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]},
           {"syllable": "pak", "frequency": 5, "features": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]}
         ],
         "start": "bak",
         "seed": 43
       }
     ],
     "profile": "dialect",
     "parameters": {
       "steps": 5,
       "max_flips": 2,
       "temperature": 0.7,
       "frequency_weight": 0.0
     }
   }

Integration Guide
-----------------

The syllable walker uses output from the feature annotator. With Phase 1 enhancements, the walker automatically
discovers annotated datasets from your ``_working/output/`` directories.

**Recommended Workflow (with auto-discovery):**

.. code-block:: bash

   # Step 1: Extract and normalize syllables
   python -m build_tools.pyphen_syllable_extractor --file wordlist.txt
   python -m build_tools.pyphen_syllable_normaliser \
     --run-dir _working/output/20260110_115453_pyphen/

   # Step 2: Annotate with phonetic features (output auto-detected)
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/20260110_115453_pyphen/pyphen_syllables_unique.txt \
     --frequencies _working/output/20260110_115453_pyphen/pyphen_syllables_frequencies.json
   # Creates: _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json

   # Step 3: Explore with syllable walker (auto-discovers datasets)
   python -m build_tools.syllable_walk --web
   # Web interface shows dropdown with all available datasets

**Alternative (explicit path):**

.. code-block:: bash

   # Specify dataset explicitly
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json --web

**When to use this tool:**

- To explore phonetic connectivity in your syllable corpus
- To compare different extractors (pyphen vs NLTK) and their phonetic behaviors
- To test if desired phonetic transitions exist before creating patterns
- To discover interesting phonetic progressions for name generation
- To analyze corpus structure and syllable relationships
- To generate datasets for statistical analysis of phonetic patterns
- To evaluate the impact of different normalization pipelines on syllable connectivity

**Common Use Cases:**

**Comparing Pyphen vs NLTK Extractors:**

Use the web interface to compare different extraction methods:

.. code-block:: bash

   # Start walker with auto-discovery
   python -m build_tools.syllable_walk --web

Then use the dataset dropdown to switch between pyphen and NLTK datasets. Generate walks with the same
seed to see how different extraction methods affect phonetic connectivity.

**Understanding Corpus Structure:**

Generate many walks to see how syllables connect:

.. code-block:: bash

   # Generate 100 walks for corpus analysis (CLI mode requires explicit path)
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json \
     --batch 100 --output corpus_walks.json

Analyze the JSON output to understand syllable connectivity, central hubs, and phonetic pathways.

**Testing Pattern Viability:**

Explore if desired phonetic transitions exist before creating new patterns:

.. code-block:: bash

   # Test phonetic transitions with ritual profile
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json \
     --start the --profile ritual

**Finding Interesting Sequences:**

Discover unusual but valid phonetic progressions:

.. code-block:: bash

   # Explore unusual sequences with goblin profile
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json \
     --profile goblin --steps 10

**Statistical Analysis:**

Generate large datasets for analysis:

.. code-block:: bash

   # Generate 1000 walks with dialect profile
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json \
     --batch 1000 --profile dialect --output dialect_walks.json

   # Generate 1000 walks with goblin profile
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json \
     --batch 1000 --profile goblin --output goblin_walks.json

Then analyze frequency distributions, transition patterns, etc.

Advanced Topics
---------------

Web Interface
~~~~~~~~~~~~~

The web interface provides an intuitive way to explore syllable walks without command-line complexity.
With Phase 1 enhancements, the interface includes smart dataset discovery and dynamic switching.

**Starting the Server (Zero-Configuration):**

.. code-block:: bash

   # Auto-discover and load most recent dataset
   python -m build_tools.syllable_walk --web
   # Discovers datasets from _working/output/*/data/*_syllables_annotated.json
   # Opens at http://localhost:5000 (or next available port)

**Starting the Server (Explicit Dataset):**

.. code-block:: bash

   # Load specific dataset
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json --web

   # Custom port (with smart port selection)
   python -m build_tools.syllable_walk --web --port 8000
   # If port 8000 is in use, automatically tries 8001, 8002, etc.

   # Quiet mode (suppress initialization messages)
   python -m build_tools.syllable_walk --web --quiet

**Interface Features:**

- **Dataset selector** - Dropdown showing all available datasets with metadata

  - Displays: "NLTK - 2026-01-10 11:56 (33,640 syllables)"
  - Switch datasets without server restart
  - Auto-loads most recent dataset on startup

- **Profile selection** - Choose from four profiles or use custom parameters
- **Starting syllable** - Specify start or use random
- **Real-time generation** - Instant walk generation with visual feedback
- **Walk display** - See full path and syllable details with frequencies
- **Statistics tracking** - Total syllables and walks generated per dataset
- **Reproducible** - Optional seed for deterministic walks
- **Smart port selection** - Automatically finds available port if requested port is in use

**Dataset Discovery:**

The walker automatically scans these locations:

- ``_working/output/*/data/*_syllables_annotated.json`` - Normalizer output directories
- ``data/annotated/syllables_annotated.json`` - Legacy location (if exists)

Each dataset displays:

- **Extractor type** (pyphen or NLTK)
- **Timestamp** (when the extraction was run)
- **Syllable count** (corpus size)

**Comparing Extractors:**

Use the dataset selector to easily compare pyphen vs NLTK outputs:

1. Start the web interface: ``python -m build_tools.syllable_walk --web``
2. Select "PYPHEN - 2026-01-10 11:54 (24,220 syllables)" from dropdown
3. Generate a walk with seed=42
4. Switch to "NLTK - 2026-01-10 11:56 (33,640 syllables)"
5. Generate same walk with seed=42 to compare behavior

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

**Initialization Time (500k syllables):**

.. list-table::
   :header-rows: 1

   * - Max Neighbor Distance
     - Time
     - Memory
     - Max Flips Supported
   * - 1
     - ~30 seconds
     - ~50 MB
     - 1
   * - 2
     - ~1 minute
     - ~150 MB
     - 1-2
   * - 3
     - ~3 minutes
     - ~300 MB
     - 1-3

**Walk Generation:**

- **After initialization**: <10ms per walk (instant)
- **Deterministic**: Same seed always produces same walk
- **Scalable**: Speed independent of corpus size

Notes
-----

**Dependencies:**

- Requires NumPy for efficient feature matrix operations (build-time dependency)
- Uses standard library ``http.server`` for web interface (no Flask)

**Performance Characteristics:**

- Initialization is one-time cost (30 sec - 3 min depending on distance)
- Walk generation is instant after initialization (<10ms per walk)
- Designed for large corpus analysis (500k+ syllables)
- Determinism guaranteed via isolated RNG instances

**Troubleshooting:**

**Initialization Takes Too Long:**

- Reduce ``--max-neighbor-distance`` (default 3 → try 2)
- Use smaller corpus for testing
- Initialization is one-time cost, walk generation is instant

**Getting Stuck at One Syllable:**

- Increase ``--max-flips`` (allow bigger phonetic jumps)
- Increase ``--temperature`` (more randomness)
- Check if starting syllable is isolated with ``--search``

**Walks Too Random:**

- Decrease ``--temperature`` (less randomness)
- Adjust ``--frequency-weight`` (try -0.5 for rare syllables)
- Try different profiles (clerical for conservative)

**Port Already in Use (Web Mode):**

The server now automatically finds an available port if the requested port is in use:

.. code-block:: text

   Port 5000 in use, trying 5001...
   Port 5001 in use, trying 5002...
   ✓ Found available port: 5002

   Starting web server on port 5002...
   Open your browser and navigate to: http://localhost:5002

The server tries up to 10 ports (e.g., 5000-5009) before giving up. You can also manually specify a different starting port:

.. code-block:: bash

   # Start from port 8000
   python -m build_tools.syllable_walk --web --port 8000

**No Datasets Found:**

If you see "No annotated datasets found", ensure you've run the feature annotator:

.. code-block:: bash

   # Run feature annotator first
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/.../pyphen_syllables_unique.txt \
     --frequencies _working/output/.../pyphen_syllables_frequencies.json

   # Then start walker
   python -m build_tools.syllable_walk --web

**Build-time tool:**

This is a build-time analysis tool only - not used during runtime name generation.

**Related Documentation:**

- :doc:`syllable_feature_annotator` - Generates input data with phonetic features
- :doc:`pyphen_syllable_normaliser` - Prepares pyphen syllable corpus before annotation
- :doc:`nltk_syllable_normaliser` - Prepares NLTK syllable corpus before annotation
- :doc:`pyphen_syllable_extractor` - Extracts raw syllables using pyphen
- :doc:`nltk_syllable_extractor` - Extracts raw syllables using NLTK
- :doc:`analysis_tools` - Additional analysis tools for syllable data

For detailed usage guide, see: ``claude/build_tools/syllable_walk.md``

API Reference
-------------

.. automodule:: build_tools.syllable_walk
   :members:
   :undoc-members:
   :show-inheritance:
