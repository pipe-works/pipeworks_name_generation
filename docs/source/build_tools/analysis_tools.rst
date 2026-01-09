==============
Analysis Tools
==============

.. currentmodule:: build_tools.syllable_analysis

Overview
--------

.. automodule:: build_tools.syllable_analysis
   :no-members:

Random Sampler
--------------

Random sampling utility for QA and inspection of annotated syllables.

Command-Line Interface
~~~~~~~~~~~~~~~~~~~~~~

.. argparse::
   :module: build_tools.syllable_analysis.random_sampler
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_analysis.random_sampler

Integration Guide
~~~~~~~~~~~~~~~~~

Use after annotation to randomly sample syllables for quality assurance:

.. code-block:: bash

   # Step 1: Annotate syllables
   python -m build_tools.syllable_feature_annotator

   # Step 2: Sample for QA inspection
   python -m build_tools.syllable_analysis.random_sampler \
     --input data/annotated/syllables_annotated.json \
     --count 50 \
     --output _working/samples.json \
     --seed 42

Feature Signature Analysis
---------------------------

The feature signature analysis tool examines annotated syllables to identify which feature combinations
actually exist in the data and how frequently each combination appears.

A "feature signature" is the set of all active (True) features for a syllable. For example, a syllable
with only ``starts_with_vowel`` and ``ends_with_vowel`` active would have the signature:
``('ends_with_vowel', 'starts_with_vowel')``.

This analysis answers questions like:

- What feature patterns are most common in natural language?
- Are certain feature combinations rare or impossible?
- How diverse is the feature space in the corpus?

Command-Line Interface
~~~~~~~~~~~~~~~~~~~~~~

.. argparse::
   :module: build_tools.syllable_analysis.feature_signatures
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_analysis.feature_signatures

Output Format
~~~~~~~~~~~~~

The tool generates timestamped plain text reports (``YYYYMMDD_HHMMSS.feature_signatures.txt``) with:

.. code-block:: text

   ================================================================================
   FEATURE SIGNATURE ANALYSIS
   ================================================================================
   Generated: 2026-01-06 13:55:56
   Total syllables analyzed: 23,160
   Unique feature signatures: 361

   SUMMARY STATISTICS
   --------------------------------------------------------------------------------
   Most common signature: 661 syllables (2.9%)
     Features: contains_liquid, contains_plosive, ends_with_vowel, long_vowel

   Feature cardinality distribution:
     1 features: 3 unique signatures
     2 features: 17 unique signatures
     3 features: 54 unique signatures
     4 features: 86 unique signatures
     5 features: 96 unique signatures
     6 features: 70 unique signatures
     7 features: 30 unique signatures
     8 features: 5 unique signatures

   ================================================================================
   SIGNATURE RANKINGS
   --------------------------------------------------------------------------------
   Rank   Count    Pct      Features
   --------------------------------------------------------------------------------
   1      661        2.85%  [4] contains_liquid, contains_plosive, ends_with_vowel, long_vowel
   2      506        2.18%  [3] contains_plosive, ends_with_vowel, long_vowel
   ...

Integration Guide
~~~~~~~~~~~~~~~~~

Use after annotation to understand feature patterns:

.. code-block:: bash

   # Step 1: Annotate syllables
   python -m build_tools.syllable_feature_annotator

   # Step 2: Analyze feature signatures
   python -m build_tools.syllable_analysis.feature_signatures \
     --input data/annotated/syllables_annotated.json \
     --output _working/analysis/feature_signatures/

t-SNE Visualization
-------------------

The t-SNE (t-distributed Stochastic Neighbor Embedding) visualization tool creates 2D visualizations of the
high-dimensional feature signature space. This helps identify clustering patterns, syllable similarity, and
natural groupings in the annotated syllable corpus.

t-SNE is a dimensionality reduction technique that projects 12-dimensional feature vectors into 2D space while
preserving local structure. The visualization uses:

- **Position (x, y)**: t-SNE projection coordinates
- **Size**: Syllable frequency (larger points = more common)
- **Color**: Syllable frequency (warmer colors = more common)

Command-Line Interface
~~~~~~~~~~~~~~~~~~~~~~

.. argparse::
   :module: build_tools.syllable_analysis.tsne_visualizer
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_analysis.tsne_visualizer

Output Format
~~~~~~~~~~~~~

The visualizer generates timestamped files in the output directory:

1. **YYYYMMDD_HHMMSS.tsne_visualization.png** - High-resolution static visualization (PNG, always generated)
2. **YYYYMMDD_HHMMSS.tsne_metadata.txt** - Detailed metadata and interpretation guide
3. **YYYYMMDD_HHMMSS.tsne_mapping.json** - Syllable→features→coordinates mapping (optional, requires ``--save-mapping``)
4. **YYYYMMDD_HHMMSS.tsne_interactive.html** - Interactive Plotly visualization (optional, requires ``--interactive``)

**Output Formats:**

- **Static PNG**: High-resolution matplotlib visualization (always generated, 300 DPI default)
- **Interactive HTML**: Plotly-based interactive visualization with hover tooltips, zoom, pan, and export (optional)

**Static PNG metadata file includes:**

- Algorithm parameters (method, perplexity, random seed, dimensions, distance metric, features)
- Visualization encoding (axis meanings, point size/color)
- Interpretation guide (how to read the visualization)
- Technical details (DPI, generation timestamp)

**Interactive HTML features:**

- Hover tooltips showing syllable text, frequency, and active features
- Interactive zoom, pan, and exploration controls
- Export to high-resolution PNG directly from browser
- Self-contained HTML file with embedded metadata
- Works in any modern web browser without additional dependencies

Integration Guide
~~~~~~~~~~~~~~~~~

Use after annotation to visualize the feature space:

.. code-block:: bash

   # Step 1: Annotate syllables
   python -m build_tools.syllable_feature_annotator

   # Step 2: Generate t-SNE visualization
   python -m build_tools.syllable_analysis.tsne_visualizer \
     --input data/annotated/syllables_annotated.json \
     --output _working/analysis/tsne/ \
     --interactive

Advanced Topics
~~~~~~~~~~~~~~~

**Understanding t-SNE Parameters:**

**Perplexity** (default: 30):

- Balances attention between local and global structure
- Typical range: 5-50
- Lower values: emphasize local clusters
- Higher values: preserve global structure
- Rule of thumb: should be less than number of syllables
- Default of 30 works well for most corpus sizes (100-10,000 syllables)

**Random State** (default: 42):

- Controls random initialization of t-SNE
- Same value = reproducible visualizations
- Different values = different (but valid) layouts
- Use fixed value (e.g., 42) for consistent results

**Distance Metric**:

- Uses Hamming distance (optimal for binary feature vectors)
- Automatically configured for 12-dimensional binary features
- Not configurable via command-line (intentional design choice)

**Interpreting the Visualization:**

**What to look for:**

- **Nearby points**: Syllables with similar phonetic features
- **Clusters**: Natural groupings in the feature space
- **Large/bright points**: High-frequency syllables (common patterns)
- **Small/dark points**: Low-frequency syllables (rare patterns)
- **Isolated points**: Unique or rare feature combinations
- **Dense regions**: Common feature patterns
- **Sparse regions**: Less common feature patterns

**Example insights:**

- Vowel-initial syllables might cluster together
- Heavy consonant clusters might form distinct groups
- Frequency might correlate with certain feature patterns
- Outliers might indicate unusual phonetic combinations

Notes
-----

**Dependencies:**

Required dependencies for t-SNE visualization (install with ``pip install -e ".[build-tools]"``):

- scikit-learn, matplotlib, numpy, pandas (for static PNG generation)
- plotly (for interactive HTML generation, optional)

**Performance:**

- Deterministic analysis with fixed random seeds (same input = same output)
- Fast processing: typically <10 seconds for 1,000-10,000 syllables
- t-SNE processing time scales roughly O(n²) with corpus size
- For very large datasets (>50,000 syllables), consider sampling first

**Output Characteristics:**

- Human-readable plain text reports with formatted tables
- Timestamped output files for historical tracking
- High-resolution visualizations (default 300 DPI)
- Static visualizations saved as PNG files for easy sharing and embedding
- Interactive visualizations saved as self-contained HTML files

**Build-time tool:**

These are build-time analysis tools - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.syllable_analysis
   :members:
   :undoc-members:
   :show-inheritance:
