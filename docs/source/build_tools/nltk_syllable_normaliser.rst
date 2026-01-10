============================
NLTK Syllable Normaliser
============================

.. currentmodule:: build_tools.nltk_syllable_normaliser

Overview
--------

.. automodule:: build_tools.nltk_syllable_normaliser
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.nltk_syllable_normaliser.cli
   :func: create_argument_parser
   :prog: python -m build_tools.nltk_syllable_normaliser

Output Format
-------------

The pipeline generates 5 output files in the NLTK run directory with ``nltk_`` prefix for provenance:

1. **nltk_syllables_raw.txt** - Aggregated raw syllables (all occurrences preserved)
2. **nltk_syllables_canonicalised.txt** - After fragment cleaning + normalization
3. **nltk_syllables_frequencies.json** - Frequency intelligence (syllable → count mapping)
4. **nltk_syllables_unique.txt** - Deduplicated canonical syllable inventory
5. **nltk_normalization_meta.txt** - Detailed statistics and metadata report

**In-Place Processing:**

Unlike the pyphen normaliser which writes to a separate output directory, the NLTK normaliser processes run directories in-place, writing output files directly into the run directory:

::

    _working/output/20260110_095213_nltk/
    ├── syllables/                          # Input (from NLTK extractor)
    │   ├── en_US_alice.txt
    │   ├── en_US_middlemarch.txt
    │   └── ...
    ├── meta/                               # Metadata (from extractor)
    │   └── ...
    ├── nltk_syllables_raw.txt              # Output: Aggregated
    ├── nltk_syllables_canonicalised.txt    # Output: After cleaning + normalization
    ├── nltk_syllables_frequencies.json     # Output: Frequency intelligence
    ├── nltk_syllables_unique.txt           # Output: Deduplicated
    └── nltk_normalization_meta.txt         # Output: Statistics

**File structure examples:**

``nltk_syllables_raw.txt`` (before fragment cleaning):

::

    cha
    pter
    i
    down
    the
    r
    a
    bbit

``nltk_syllables_canonicalised.txt`` (after fragment cleaning + normalization):

::

    cha
    pter
    idown
    the
    rabbit

``nltk_syllables_frequencies.json`` (counts after cleaning):

.. code-block:: json

   {
     "cha": 1,
     "pter": 1,
     "idown": 1,
     "the": 1,
     "rabbit": 1
   }

``nltk_syllables_unique.txt`` (deduplicated, sorted):

::

    cha
    idown
    pter
    rabbit
    the

Integration Guide
-----------------

The NLTK syllable normaliser is the second step after NLTK extraction, complementing the NLTK extractor:

**Standard workflow (using NLTK extractor + normaliser):**

.. code-block:: bash

   # Step 1: Extract syllables using NLTK/CMUDict
   python -m build_tools.nltk_syllable_extractor \
     --source data/corpus/ \
     --pattern "*.txt" \
     --output _working/output/

   # Step 2: Normalize extracted syllables (in-place)
   python -m build_tools.nltk_syllable_normaliser \
     --run-dir _working/output/20260110_095213_nltk/

   # Alternative: Auto-detect all NLTK run directories
   python -m build_tools.nltk_syllable_normaliser \
     --source _working/output/

   # Step 3: Annotate with phonetic features (source-agnostic)
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/20260110_095213_nltk/nltk_syllables_unique.txt \
     --frequencies _working/output/20260110_095213_nltk/nltk_syllables_frequencies.json

**Parallel workflow (comparing both extractors):**

.. code-block:: bash

   # Extract and normalize with pyphen (typographic)
   python -m build_tools.pyphen_syllable_extractor \
     --source data/corpus/ \
     --lang en_US \
     --output _working/output/

   python -m build_tools.pyphen_syllable_normaliser \
     --source _working/output/20260110_143022_pyphen/syllables/ \
     --output _working/output/20260110_143022_pyphen/

   # Extract and normalize with NLTK (phonetic)
   python -m build_tools.nltk_syllable_extractor \
     --source data/corpus/ \
     --output _working/output/

   python -m build_tools.nltk_syllable_normaliser \
     --run-dir _working/output/20260110_095213_nltk/

   # Compare outputs - both use different prefixes (pyphen_* vs nltk_*)
   diff _working/output/20260110_143022_pyphen/pyphen_syllables_unique.txt \
        _working/output/20260110_095213_nltk/nltk_syllables_unique.txt

**When to use NLTK normaliser vs pyphen normaliser:**

**Use NLTK normaliser when:**

- You used the NLTK syllable extractor
- Your syllables contain many single-letter fragments
- You want phonetically coherent syllables reconstructed
- You're working with NLTK's onset/coda-based splits
- You want in-place processing within run directories

**Use pyphen normaliser when:**

- You used the pyphen syllable extractor
- Your syllables are already well-formed (typographic hyphenation)
- You want to aggregate multiple extraction runs
- You prefer explicit output directory specification
- You're working with multi-language pyphen extractions

**Fragment Cleaning:**

The key differentiator of the NLTK normaliser is fragment cleaning. This step reconstructs phonetically coherent syllables from NLTK's over-segmented output:

+-------------------+-------------------------+---------------------------+
| Original Fragments| After Fragment Cleaning | Reason                    |
+===================+=========================+===========================+
| i, down           | idown                   | Single vowel merged       |
+-------------------+-------------------------+---------------------------+
| r, a, bbit        | ra, bbit                | Single letters merged     |
+-------------------+-------------------------+---------------------------+
| h, o, le          | ho, le                  | Single letters merged     |
+-------------------+-------------------------+---------------------------+
| cha, pter         | cha, pter               | Multi-char preserved      |
+-------------------+-------------------------+---------------------------+

**Merging Rules:**

1. Single vowels (a, e, i, o, u, y) merge with next fragment
2. Single consonants merge with next fragment
3. Multi-character fragments remain unchanged
4. Processing is left-to-right, deterministic

**Processing Modes:**

- **Specific run directory**: ``--run-dir /path/to/run/`` - Process one NLTK run
- **Auto-detection**: ``--source /path/to/output/`` - Find and process all NLTK runs
- **Skip fragment cleaning**: ``--no-fragment-cleaning`` - For comparison with pyphen

Notes
-----

**In-Place Processing Philosophy:**

The NLTK normaliser writes outputs directly into the run directory (not a separate location) because:

- **Convention**: Each NLTK run is self-contained (extractor + normaliser outputs together)
- **Simplicity**: No confusion about where normalized files live
- **Provenance**: Run directory name (``*_nltk``) and file prefix (``nltk_*``) both indicate source

**Fragment Cleaning Statistics:**

Real-world performance on multi-language corpus (21 files, 2.98M syllables):

- **Before cleaning**: 2,977,447 syllables
- **After cleaning**: 2,709,503 syllables
- **Fragments merged**: 267,944 (9% reduction)
- **Processing time**: 6.07 seconds
- **Unique syllables**: 33,640

**When Fragment Cleaning Matters:**

Fragment cleaning has the most impact on:

- Short function words ("i", "a", "the")
- Consonant clusters split by onset/coda ("r" + "a" → "ra")
- Single-character prefixes/suffixes
- Phonetically over-segmented words

For well-formed multi-syllable words, fragment cleaning has minimal effect.

**Comparing with Pyphen Normaliser:**

+--------------------------------+---------------------------+---------------------------+
| Feature                        | Pyphen Normaliser         | NLTK Normaliser           |
+================================+===========================+===========================+
| **Input Source**               | Any directory             | NLTK run directories      |
+--------------------------------+---------------------------+---------------------------+
| **Preprocessing**              | None                      | Fragment cleaning         |
+--------------------------------+---------------------------+---------------------------+
| **Output Location**            | User-specified directory  | In-place (run directory)  |
+--------------------------------+---------------------------+---------------------------+
| **Output Prefix**              | pyphen_*                  | nltk_*                    |
+--------------------------------+---------------------------+---------------------------+
| **Run Detection**              | Manual file discovery     | Auto-detect *_nltk dirs   |
+--------------------------------+---------------------------+---------------------------+
| **Normalization Steps**        | 3 (aggregate, canon, freq)| 4 (clean, aggregate, ...) |
+--------------------------------+---------------------------+---------------------------+
| **Typical Use Case**           | Pyphen extractor output   | NLTK extractor output     |
+--------------------------------+---------------------------+---------------------------+

**Auto-Detection Criteria:**

The auto-detection feature (``--source``) finds NLTK run directories by:

1. Scanning for directories ending with ``_nltk``
2. Verifying existence of ``syllables/`` subdirectory
3. Sorting chronologically by directory name

This allows batch processing:

.. code-block:: bash

   # Process all NLTK runs at once
   python -m build_tools.nltk_syllable_normaliser --source _working/output/

   # Output:
   # Found 3 NLTK run directories:
   #   - 20260110_095213_nltk
   #   - 20260110_143022_nltk
   #   - 20260110_153045_nltk
   # Processing...

**Deterministic Processing:**

The NLTK normaliser is fully deterministic:

- Same input → same output (always)
- Fragment cleaning uses left-to-right greedy algorithm
- Unicode normalization is deterministic (NFKD)
- Frequency analysis preserves insertion order (Python 3.7+)

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

**Output File Prefixes:**

Both normalisers now use prefixed output files:

- Pyphen normaliser: ``pyphen_*`` prefix
- NLTK normaliser: ``nltk_*`` prefix

This ensures clear provenance when files are shared individually.

API Reference
-------------

.. automodule:: build_tools.nltk_syllable_normaliser
   :members:
   :undoc-members:
   :show-inheritance:
