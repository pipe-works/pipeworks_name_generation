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

The syllable walker uses output from the feature annotator:

.. code-block:: bash

   # Step 1: Extract syllables from dictionary
   python -m build_tools.pyphen_syllable_extractor --file wordlist.txt --auto

   # Step 2: Normalize syllables
   python -m build_tools.pyphen_syllable_normaliser \
     --source data/corpus/ \
     --output data/normalized/

   # Step 3: Annotate with phonetic features
   python -m build_tools.syllable_feature_annotator \
     --syllables data/normalized/syllables_unique.txt \
     --frequencies data/normalized/syllables_frequencies.json \
     --output data/annotated/syllables_annotated.json

   # Step 4: Explore with syllable walker
   python -m build_tools.syllable_walk data/annotated/syllables_annotated.json --web

**When to use this tool:**

- To explore phonetic connectivity in your syllable corpus
- To test if desired phonetic transitions exist before creating patterns
- To discover interesting phonetic progressions for name generation
- To analyze corpus structure and syllable relationships
- To generate datasets for statistical analysis of phonetic patterns

**Common Use Cases:**

**Understanding Corpus Structure:**

Generate many walks to see how syllables connect:

.. code-block:: bash

   # Generate 100 walks for corpus analysis
   python -m build_tools.syllable_walk data.json --batch 100 --output corpus_walks.json

Analyze the JSON output to understand syllable connectivity, central hubs, and phonetic pathways.

**Testing Pattern Viability:**

Explore if desired phonetic transitions exist before creating new patterns:

.. code-block:: bash

   # Test phonetic transitions with ritual profile
   python -m build_tools.syllable_walk data.json --start the --profile ritual

**Finding Interesting Sequences:**

Discover unusual but valid phonetic progressions:

.. code-block:: bash

   # Explore unusual sequences with goblin profile
   python -m build_tools.syllable_walk data.json --profile goblin --steps 10

**Statistical Analysis:**

Generate large datasets for analysis:

.. code-block:: bash

   # Generate 1000 walks with dialect profile
   python -m build_tools.syllable_walk data.json --batch 1000 \
     --profile dialect --output dialect_walks.json

   # Generate 1000 walks with goblin profile
   python -m build_tools.syllable_walk data.json --batch 1000 \
     --profile goblin --output goblin_walks.json

Then analyze frequency distributions, transition patterns, etc.

Advanced Topics
---------------

Web Interface
~~~~~~~~~~~~~

The web interface provides an intuitive way to explore syllable walks without command-line complexity.

**Starting the Server:**

.. code-block:: bash

   # Default port (5000)
   python -m build_tools.syllable_walk data/annotated/syllables_annotated.json --web

   # Custom port
   python -m build_tools.syllable_walk data/annotated/syllables_annotated.json \
     --web --port 8000

   # Quiet mode (suppress initialization messages)
   python -m build_tools.syllable_walk data/annotated/syllables_annotated.json \
     --web --quiet

**Features:**

- **Profile selection** - Choose from four profiles or use custom parameters
- **Starting syllable** - Specify start or use random
- **Real-time generation** - Instant walk generation with visual feedback
- **Walk display** - See full path and syllable details with frequencies
- **Statistics tracking** - Total syllables and walks generated
- **Reproducible** - Optional seed for deterministic walks

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

.. code-block:: bash

   # Use a different port if 5000 is occupied
   python -m build_tools.syllable_walk data.json --web --port 8000

**Build-time tool:**

This is a build-time analysis tool only - not used during runtime name generation.

**Related Documentation:**

- :doc:`syllable_feature_annotator` - Generates input data with phonetic features
- :doc:`syllable_normaliser` - Prepares syllable corpus before annotation
- :doc:`syllable_extractor` - Extracts raw syllables from dictionary
- :doc:`analysis_tools` - Additional analysis tools for syllable data

For detailed usage guide, see: ``claude/build_tools/syllable_walk.md``

API Reference
-------------

.. automodule:: build_tools.syllable_walk
   :members:
   :undoc-members:
   :show-inheritance:
