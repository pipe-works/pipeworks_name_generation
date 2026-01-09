===================
Syllable Normaliser
===================

.. currentmodule:: build_tools.syllable_normaliser

Overview
--------

.. automodule:: build_tools.syllable_normaliser
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_normaliser.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_normaliser

Output Format
-------------

The pipeline generates 5 output files in the specified output directory:

1. **syllables_raw.txt** - Aggregated raw syllables (all occurrences preserved)
2. **syllables_canonicalised.txt** - Normalized canonical syllables
3. **syllables_frequencies.json** - Frequency intelligence (syllable → count mapping)
4. **syllables_unique.txt** - Deduplicated canonical syllable inventory
5. **normalization_meta.txt** - Detailed statistics and metadata report

**File structure examples:**

``syllables_raw.txt`` (preserves all occurrences):

::

    café
    Café
    hello
    hello
    world

``syllables_canonicalised.txt`` (normalized, duplicates preserved):

::

    cafe
    cafe
    hello
    hello
    world

``syllables_frequencies.json`` (counts before deduplication):

.. code-block:: json

   {
     "cafe": 2,
     "hello": 2,
     "world": 1
   }

``syllables_unique.txt`` (deduplicated, sorted):

::

    cafe
    hello
    world

Integration Guide
-----------------

The syllable normaliser sits between extraction and annotation in the pipeline:

.. code-block:: bash

   # Step 1: Extract syllables from corpus
   python -m build_tools.syllable_extractor \
     --source data/corpus/ \
     --lang en_US

   # Step 2: Normalize extracted syllables
   python -m build_tools.syllable_normaliser \
     --source data/raw/ \
     --output data/normalized/

   # Step 3: Annotate with phonetic features
   python -m build_tools.syllable_feature_annotator \
     --syllables data/normalized/syllables_unique.txt \
     --frequencies data/normalized/syllables_frequencies.json

**When to use this tool:**

- After extracting raw syllables from corpus files
- Before feature annotation or pattern development
- To normalize syllables from multiple extraction runs
- To regenerate frequency distributions after combining corpora

**3-Step Normalization Pipeline:**

**Step 1 - Aggregation:**

- Combines all input files into ``syllables_raw.txt``
- Preserves ALL occurrences (no deduplication)
- Maintains raw counts for frequency analysis
- Empty lines filtered during file reading

**Step 2 - Canonicalization:**

- Unicode normalization (NFKD - compatibility decomposition)
- Strip diacritics: café → cafe, résumé → resume
- Lowercase conversion
- Trim whitespace
- Charset validation (reject invalid characters)
- Length constraint enforcement (default: min=2, max=20)
- Outputs to ``syllables_canonicalised.txt``

**Step 3 - Frequency Analysis:**

- Count occurrences of each canonical syllable
- Generate frequency rankings and percentages
- Create deduplicated unique list (alphabetically sorted)
- Outputs:
  - ``syllables_frequencies.json`` - Frequency counts before deduplication
  - ``syllables_unique.txt`` - Authoritative syllable inventory
  - ``normalization_meta.txt`` - Comprehensive statistics report

**Pipeline characteristics:**

- Deterministic: same input always produces same output
- Fast: processes thousands of syllables per second
- Configurable: adjust length constraints, charset, unicode form
- Comprehensive: detailed rejection statistics and metadata

Notes
-----

**Frequency Intelligence:**

The frequency data captures how often each canonical syllable occurs **before** deduplication.
This intelligence is essential for understanding natural language patterns and can inform
weighted name generation:

.. code-block:: json

   {
     "ka": 187,
     "ra": 162,
     "mi": 145,
     "ta": 98
   }

This shows "ka" appears 187 times in the canonical syllables, indicating it's a high-frequency
pattern that may be desirable for common or natural-sounding names.

**Normalization Behavior:**

- All syllable processing is case-insensitive (output is lowercase)
- Unicode normalization form NFKD provides maximum compatibility decomposition
- Empty lines are filtered during aggregation (not counted as rejections)
- Frequency counts capture occurrences BEFORE deduplication
- Invalid syllables (wrong charset, wrong length) are rejected and counted in metadata

**Default Constraints:**

- Min length: 2 characters
- Max length: 20 characters
- Allowed charset: a-z (lowercase ASCII letters)
- Unicode form: NFKD (compatibility decomposition)

**Use Cases:**

- Combining syllables from multiple language extractions
- Normalizing variations in corpus encoding (UTF-8, Latin-1, etc.)
- Filtering syllables by length for specific pattern requirements
- Building frequency-aware name generation systems

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.syllable_normaliser
   :members:
   :undoc-members:
   :show-inheritance:
