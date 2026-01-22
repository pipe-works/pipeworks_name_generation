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

   # Step 4: Explore syllable walks (choose one interface)

   # CLI-based exploration
   python -m build_tools.syllable_walk \
     _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json \
     --start ka --profile dialect --steps 10

   # Web interface (separate module)
   python -m build_tools.syllable_walk_web
   # Auto-discovers port starting at 8000
   # Shows all available run directories with selection counts

**When to use this tool:**

- To explore phonetic connectivity in your syllable corpus
- To compare different extractors (pyphen vs NLTK) and their phonetic behaviors
- To test if desired phonetic transitions exist before creating patterns
- To discover interesting phonetic progressions for name generation
- To batch-generate walks for analysis

For browsing name selections and interactive web-based exploration, see :doc:`syllable_walk_web`.

Advanced Topics
---------------

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

**Walk Generation:**

- **After initialization**: <10ms per walk (instant)
- **Deterministic**: Same seed always produces same walk
- **Scalable**: Speed independent of corpus size

**Initialization:**

The neighbor graph must be built on startup, which takes time depending on
``max_neighbor_distance``:

- **Distance 1**: ~30 sec initialization
- **Distance 2**: ~1 min initialization
- **Distance 3**: ~3 min initialization (recommended for large corpora)

Notes
-----

**Dependencies:**

- Requires NumPy for efficient feature matrix operations (build-time dependency)

**Troubleshooting:**

**Invalid Start Syllable:**

If you get an error about an unknown syllable, use ``--search`` to find valid syllables:

.. code-block:: bash

   # Search for syllables containing "th"
   python -m build_tools.syllable_walk data.json --search "th"

**Build-time tool:**

This is a build-time analysis tool only - not used during runtime name generation.

**Related Documentation:**

- :doc:`syllable_walk_web` - Web interface for browsing selections and generating walks
- :doc:`syllable_walk_tui` - Interactive TUI for exploring phonetic space
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
