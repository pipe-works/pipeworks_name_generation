=========================
NLTK Syllable Extractor
=========================

.. currentmodule:: build_tools.nltk_syllable_extractor

Overview
--------

.. automodule:: build_tools.nltk_syllable_extractor
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.nltk_syllable_extractor.cli
   :func: create_argument_parser
   :prog: python -m build_tools.nltk_syllable_extractor

Output Format
-------------

Output files are organized in a run-based subdirectory structure under ``_working/output/``. Each extraction run creates a timestamped directory containing ``syllables/`` and ``meta/`` subdirectories:

**Directory structure:**

::

    _working/output/
      └── YYYYMMDD_HHMMSS_nltk/     # Run directory (one per batch)
          ├── syllables/
          │   ├── file1.txt          # Input filename preserved
          │   ├── file2.txt
          │   └── ...
          └── meta/
              ├── file1.txt          # Matching metadata
              ├── file2.txt
              └── ...

**Interactive mode (single file):**

::

    _working/output/
      └── 20260110_143022_nltk/
          ├── syllables/
          │   └── en_US.txt
          └── meta/
              └── en_US.txt

**Batch mode (multiple files):**

::

    _working/output/
      └── 20260110_143022_nltk/     # All files share one run directory
          ├── syllables/
          │   ├── alice.txt
          │   ├── middlemarch.txt
          │   └── don_quijote.txt
          └── meta/
              ├── alice.txt
              ├── middlemarch.txt
              └── don_quijote.txt

**Benefits of run-based organization:**

- Each extraction run is self-contained in a timestamped directory
- Easy to archive, move, or delete entire runs as atomic units
- Input filenames are preserved for easy identification
- Clean separation between syllables and metadata
- All outputs from a batch operation are grouped together

**Syllables file format:**

Each line contains one syllable, preserving duplicates in the order extracted. This preserves natural syllable frequency for downstream processing:

::

    hel
    lo
    won
    der
    ful
    world
    hel
    lo
    world

**Note:** Duplicates are intentionally preserved. The extractor's job is to extract, not to filter. Use ``build_tools.pyphen_syllable_normaliser`` for deduplication and frequency analysis.

**Metadata file format:**

The metadata file records extraction parameters and statistics:

- Source files processed
- Language code (always ``en_US`` for NLTK extractor)
- Extractor type (``nltk_syllable_extractor (CMUDict + onset/coda)``)
- Syllable length constraints (min/max)
- Total syllables (with duplicates)
- Unique syllable count (for reference)
- Total word count
- Processing statistics (processed words, fallback count, rejected syllables)
- Extraction timestamp
- Command-line invocation

**Metadata distinguishes extractor source:**

The NLTK extractor clearly labels its output to distinguish from pyphen-based extraction:

::

    ======================================================================
    NLTK SYLLABLE EXTRACTION METADATA
    ======================================================================
    Extraction Date:    2026-01-09 22:43:28
    Extractor:          nltk_syllable_extractor (CMUDict + onset/coda)
    Language Code:      en_US
    Syllable Length:    1-999 characters
    Total Syllables:    911
    Unique Syllables:   401

    Processing Statistics:
      Total Words:        503
      Processed Words:    503
      Fallback Used:      17 (not in CMUDict)
      Rejected Syllables: 0 (length filter)
    ...

Integration Guide
-----------------

The NLTK syllable extractor is an alternative first step in the build pipeline, complementing the pyphen-based extractor:

**Standard workflow (using NLTK extractor):**

.. code-block:: bash

   # Step 1: Extract syllables using NLTK/CMUDict
   python -m build_tools.nltk_syllable_extractor \
     --source data/corpus/ \
     --pattern "*.txt" \
     --output data/raw/nltk/

   # Step 2: Normalize extracted syllables (source-agnostic)
   python -m build_tools.pyphen_syllable_normaliser \
     --source data/raw/nltk/ \
     --output data/normalized/

   # Step 3: Annotate with phonetic features (source-agnostic)
   python -m build_tools.syllable_feature_annotator

**Parallel workflow (comparing both extractors):**

.. code-block:: bash

   # Extract with pyphen (typographic)
   python -m build_tools.pyphen_syllable_extractor \
     --source data/corpus/ \
     --lang en_US \
     --output data/raw/pyphen/

   # Extract with NLTK (phonetic)
   python -m build_tools.nltk_syllable_extractor \
     --source data/corpus/ \
     --output data/raw/nltk/

   # Compare outputs or merge for hybrid corpus
   # Both feed into the same downstream tools

**When to use NLTK extractor vs pyphen:**

**Use NLTK extractor when:**

- You want phonetically-guided syllable boundaries
- You prefer consonant cluster integrity (e.g., "An-drew" not "And-rew")
- You want syllables that feel more like spoken language
- You're working with English text (CMUDict limitation)
- You want to explore phonetic texture differences

**Use pyphen extractor when:**

- You need multi-language support (40+ languages)
- You prefer typographic hyphenation rules
- You want formal, dictionary-based splits
- You're working with non-English text

**Combining both extractors:**

The two extractors produce complementary textures. You can:

1. Extract with both, compare outputs, choose one
2. Merge outputs for richer syllable inventory
3. Use different extractors for different name generation profiles

**Extraction modes:**

- **Interactive mode**: No arguments - prompts for file selection
- **Single file**: ``--file input.txt`` - Process one file
- **Multiple files**: ``--files file1.txt file2.txt`` - Process specific files
- **Directory scan**: ``--source /data/ --pattern "*.txt"`` - Scan directory for files
- **Recursive scan**: ``--source /data/ --pattern "*.txt" --recursive`` - Scan subdirectories

Notes
-----

**Language Limitation:**

The NLTK extractor is **English-only** due to CMUDict constraints:

- CMU Pronouncing Dictionary covers North American English pronunciation
- No support for other languages (use pyphen for multi-language needs)
- This is a fundamental limitation of the phonetic dictionary approach

**CMUDict Package:**

The tool uses the ``cmudict`` pip package (python-cmudict) which includes the
CMU Pronouncing Dictionary data. No separate corpus download is required - simply
install via pip and you're ready to go.

**Phonetic vs Typographic Splitting:**

The NLTK extractor produces different splits than pyphen:

+------------+-------------------+-------------------+
| Word       | pyphen (typo)     | NLTK (phonetic)   |
+============+===================+===================+
| Andrew     | And-rew           | An-drew           |
+------------+-------------------+-------------------+
| structure  | struc-ture        | stru-cture        |
+------------+-------------------+-------------------+
| beautiful  | beau-ti-ful       | beau-ti-ful       |
+------------+-------------------+-------------------+
| program    | pro-gram          | pro-gram          |
+------------+-------------------+-------------------+

These differences create distinct **phonetic textures**:

- **pyphen**: Conservative, formal, typographic breaks
- **NLTK**: Natural, phonetic, respects consonant clustering

**Deterministic Pronunciation Selection:**

When words have multiple pronunciations in CMUDict (e.g., "read" as present vs past tense), the extractor:

- Always selects the **first pronunciation** listed
- This ensures deterministic results (same input → same output)
- Pronunciation selection cannot be configured

**Fallback for Unknown Words:**

Words not in CMUDict use a heuristic fallback:

1. Identifies vowel groups as syllable nuclei
2. Applies onset/coda principles to consonant clusters
3. Maintains phonetic character even for out-of-vocabulary words

Fallback usage is tracked in metadata as "Fallback Used: N (not in CMUDict)" to clearly distinguish from CMUDict-based extraction.

**Extraction Philosophy - Preserving Duplicates:**

The extractor preserves all syllables including duplicates, following separation-of-concerns design:

- **Extractor's job**: Extract syllables (preserves frequency information)
- **Normaliser's job**: Deduplicate, filter, aggregate (``syllable_normaliser``)
- **Annotator's job**: Add phonetic features (``syllable_feature_annotator``)

This design allows downstream tools to:

- Perform frequency analysis on natural corpus distribution
- Make informed filtering decisions based on occurrence counts
- Apply different normalization strategies for different use cases

**Syllable Length Constraints:**

- Default: min=1, max=999 (no practical filtering by default)
- Adjust with ``--min`` and ``--max`` flags to filter if needed
- Default behavior preserves all syllables for downstream processing
- Examples:

  - ``--min 2 --max 8`` - Filter to 2-8 character syllables (like old default)
  - ``--min 1 --max 1`` - Extract only single-character syllables
  - ``--min 3`` - Extract syllables of 3+ characters (no upper limit)

**Output Organization:**

- Each extraction run creates a timestamped directory with nltk identifier (``YYYYMMDD_HHMMSS_nltk/``)
- Run directory contains ``syllables/`` and ``meta/`` subdirectories
- Batch processing groups all files into a single run directory
- Input filenames are preserved in output (e.g., ``alice.txt``)
- Interactive mode uses ``en_US.txt`` as the filename
- Metadata clearly labels extractor source for provenance
- All extractions logged to corpus database (if available)

**Performance Considerations:**

- CMUDict lookup is fast (dictionary-based)
- Fallback heuristics are efficient
- Processing speed comparable to pyphen for English text
- NLTK initial import may take 1-2 seconds

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.nltk_syllable_extractor
   :members:
   :undoc-members:
   :show-inheritance:
