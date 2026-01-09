==================
Syllable Extractor
==================

.. currentmodule:: build_tools.syllable_extractor

Overview
--------

.. automodule:: build_tools.syllable_extractor
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_extractor.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_extractor

Output Format
-------------

Output files are saved to ``_working/output/`` with timestamped names including language codes:

- ``YYYYMMDD_HHMMSS.syllables.LANG.txt`` - Unique syllables (one per line, sorted)
- ``YYYYMMDD_HHMMSS.meta.LANG.txt`` - Extraction metadata and statistics

**Examples:**

::

    20260105_143022.syllables.en_US.txt
    20260105_143022.meta.en_US.txt
    20260105_143045.syllables.de_DE.txt

**Syllables file format:**

Each line contains one unique syllable, sorted alphabetically:

::

    der
    ful
    hel
    lo
    won
    world

**Metadata file format:**

The metadata file records extraction parameters and statistics:

- Source files processed
- Language code used
- Syllable length constraints (min/max)
- Unique syllable count
- Total word count
- Extraction timestamp
- Command-line invocation

Integration Guide
-----------------

The syllable extractor is the first step in the build pipeline:

.. code-block:: bash

   # Step 1: Extract syllables from corpus
   python -m build_tools.syllable_extractor \
     --source data/corpus/ \
     --pattern "*.txt" \
     --lang en_US \
     --output data/raw/

   # Step 2: Normalize extracted syllables
   python -m build_tools.syllable_normaliser \
     --source data/raw/ \
     --output data/normalized/

   # Step 3: Annotate with phonetic features
   python -m build_tools.syllable_feature_annotator

**When to use this tool:**

- To extract syllables from text corpora for the first time
- When adding new language variants to the corpus
- To regenerate syllables after changing extraction parameters (min/max length)
- For exploring syllable patterns in specific text sources

**Extraction modes:**

- **Interactive mode**: No arguments - prompts for file selection
- **Single file**: ``--file input.txt`` - Process one file
- **Multiple files**: ``--files file1.txt file2.txt`` - Process specific files
- **Directory scan**: ``--source /data/ --pattern "*.txt"`` - Scan directory for files
- **Recursive scan**: ``--source /data/ --pattern "*.txt" --recursive`` - Scan subdirectories
- **Auto-detect language**: ``--auto`` - Use automatic language detection (requires ``langdetect``)

Notes
-----

**Supported Languages:**

The extractor supports 40+ languages through pyphen's LibreOffice dictionaries:

- English (US: en_US, UK: en_GB)
- Germanic: German (de_DE), Dutch (nl_NL), Swedish (sv_SE), Danish (da_DK), Norwegian (nb_NO, nn_NO)
- Romance: French (fr_FR), Spanish (es_ES), Italian (it_IT), Portuguese (pt_PT), Romanian (ro_RO)
- Slavic: Russian (ru_RU), Polish (pl_PL), Czech (cs_CZ), Slovak (sk_SK), Ukrainian (uk_UA)
- Other: Greek (el_GR), Turkish (tr_TR), Hungarian (hu_HU), Finnish (fi_FI), Estonian (et_EE)
- And many more...

To list all available languages:

.. code-block:: python

   from build_tools.syllable_extractor import SUPPORTED_LANGUAGES
   print(f"{len(SUPPORTED_LANGUAGES)} languages available")

**Language Auto-Detection:**

The tool includes automatic language detection (requires ``langdetect`` package):

- Use ``--auto`` flag to enable automatic language detection
- Detection is per-file based on text content
- Falls back to English (en_US) if detection fails or is unavailable
- Install with: ``pip install langdetect``

To check if auto-detection is available:

.. code-block:: python

   from build_tools.syllable_extractor import is_detection_available
   if is_detection_available():
       print("Language auto-detection is available")

**Syllable Length Constraints:**

- Default: min=2, max=8 characters
- Adjust with ``--min`` and ``--max`` flags
- Shorter syllables (min=1) include single vowels
- Longer syllables (max=10+) may include compound patterns

**Output Organization:**

- Files are timestamped to preserve extraction history
- Language codes in filenames enable multi-language corpora
- Metadata files provide full provenance tracking
- All extractions are logged to corpus database (if available)

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.syllable_extractor
   :members:
   :undoc-members:
   :show-inheritance:
