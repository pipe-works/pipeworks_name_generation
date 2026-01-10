===================
Syllable Normaliser
===================

.. currentmodule:: build_tools.pyphen_syllable_normaliser

Overview
--------

.. automodule:: build_tools.pyphen_syllable_normaliser
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.pyphen_syllable_normaliser.cli
   :func: create_argument_parser
   :prog: python -m build_tools.pyphen_syllable_normaliser

Output Format
-------------

The pipeline generates 5 output files in the pyphen run directory with ``pyphen_`` prefix for provenance:

1. **pyphen_syllables_raw.txt** - Aggregated raw syllables (all occurrences preserved)
2. **pyphen_syllables_canonicalised.txt** - Normalized canonical syllables
3. **pyphen_syllables_frequencies.json** - Frequency intelligence (syllable → count mapping)
4. **pyphen_syllables_unique.txt** - Deduplicated canonical syllable inventory
5. **pyphen_normalization_meta.txt** - Detailed statistics and metadata report

**In-Place Processing:**

Unlike older versions which wrote to a separate output directory, the pyphen normaliser now processes run directories in-place, writing output files directly into the run directory:

::

    _working/output/20260110_143022_pyphen/
    ├── syllables/                          # Input (from pyphen extractor)
    │   ├── en_US_alice.txt
    │   ├── en_US_middlemarch.txt
    │   └── ...
    ├── meta/                               # Metadata (from extractor)
    │   └── ...
    ├── pyphen_syllables_raw.txt            # Output: Aggregated
    ├── pyphen_syllables_canonicalised.txt  # Output: Normalized
    ├── pyphen_syllables_frequencies.json   # Output: Frequency intelligence
    ├── pyphen_syllables_unique.txt         # Output: Deduplicated
    └── pyphen_normalization_meta.txt       # Output: Statistics

**File structure examples:**

``pyphen_syllables_raw.txt`` (preserves all occurrences):

::

    café
    Café
    hello
    hello
    world

``pyphen_syllables_canonicalised.txt`` (normalized, duplicates preserved):

::

    cafe
    cafe
    hello
    hello
    world

``pyphen_syllables_frequencies.json`` (counts before deduplication):

.. code-block:: json

   {
     "cafe": 2,
     "hello": 2,
     "world": 1
   }

``pyphen_syllables_unique.txt`` (deduplicated, sorted):

::

    cafe
    hello
    world

Integration Guide
-----------------

The pyphen syllable normaliser is the second step after pyphen extraction, processing syllables within their run directories:

**Standard workflow:**

.. code-block:: bash

   # Step 1: Extract syllables using pyphen
   python -m build_tools.pyphen_syllable_extractor \
     --source data/corpus/ \
     --pattern "*.txt" \
     --output _working/output/ \
     --lang en_US

   # Step 2: Normalize extracted syllables (in-place)
   python -m build_tools.pyphen_syllable_normaliser \
     --run-dir _working/output/20260110_143022_pyphen/

   # Alternative: Auto-detect all pyphen run directories
   python -m build_tools.pyphen_syllable_normaliser \
     --source _working/output/

   # Step 3: Annotate with phonetic features (source-agnostic)
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/20260110_143022_pyphen/pyphen_syllables_unique.txt \
     --frequencies _working/output/20260110_143022_pyphen/pyphen_syllables_frequencies.json

**Comparing with NLTK normaliser:**

.. code-block:: bash

   # Pyphen pipeline (typographic hyphenation)
   python -m build_tools.pyphen_syllable_extractor \
     --source data/corpus/ \
     --lang en_US \
     --output _working/output/

   python -m build_tools.pyphen_syllable_normaliser \
     --run-dir _working/output/20260110_143022_pyphen/

   # NLTK pipeline (phonetic splitting)
   python -m build_tools.nltk_syllable_extractor \
     --source data/corpus/ \
     --output _working/output/

   python -m build_tools.nltk_syllable_normaliser \
     --run-dir _working/output/20260110_095213_nltk/

   # Compare outputs - both use different prefixes (pyphen_* vs nltk_*)
   diff _working/output/20260110_143022_pyphen/pyphen_syllables_unique.txt \
        _working/output/20260110_095213_nltk/nltk_syllables_unique.txt

**When to use pyphen normaliser vs NLTK normaliser:**

**Use pyphen normaliser when:**

- You used the pyphen syllable extractor
- Your syllables are well-formed from typographic hyphenation
- You want multi-language support (40+ languages)
- You want in-place processing within run directories
- You're working with pyphen's dictionary-based splits

**Use NLTK normaliser when:**

- You used the NLTK syllable extractor
- Your syllables contain many single-letter fragments
- You want phonetically coherent syllables reconstructed
- You're working with NLTK's onset/coda-based splits (English only)
- You want fragment cleaning preprocessing

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

**In-Place Processing Philosophy:**

The pyphen normaliser writes outputs directly into the run directory (not a separate location) because:

- **Convention**: Each pyphen run is self-contained (extractor + normaliser outputs together)
- **Simplicity**: No confusion about where normalized files live
- **Provenance**: Run directory name (``*_pyphen``) and file prefix (``pyphen_*``) both indicate source

**Processing Modes:**

- **Specific run directory**: ``--run-dir /path/to/run/`` - Process one pyphen run
- **Auto-detection**: ``--source /path/to/output/`` - Find and process all pyphen runs

**Auto-Detection Criteria:**

The auto-detection feature (``--source``) finds pyphen run directories by:

1. Scanning for directories ending with ``_pyphen``
2. Verifying existence of ``syllables/`` subdirectory
3. Sorting chronologically by directory name

This allows batch processing:

.. code-block:: bash

   # Process all pyphen runs at once
   python -m build_tools.pyphen_syllable_normaliser --source _working/output/

   # Output:
   # Found 3 pyphen run directories:
   #   - 20260110_143022_pyphen
   #   - 20260110_153045_pyphen
   #   - 20260110_163010_pyphen
   # Processing...

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.pyphen_syllable_normaliser
   :members:
   :undoc-members:
   :show-inheritance:
