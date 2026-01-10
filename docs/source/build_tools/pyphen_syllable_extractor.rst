==================
Syllable Extractor
==================

.. currentmodule:: build_tools.pyphen_syllable_extractor

Overview
--------

.. automodule:: build_tools.pyphen_syllable_extractor
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.pyphen_syllable_extractor.cli
   :func: create_argument_parser
   :prog: python -m build_tools.pyphen_syllable_extractor

Output Format
-------------

Output files are organized in a run-based subdirectory structure under ``_working/output/``. Each extraction run creates a timestamped directory containing ``syllables/`` and ``meta/`` subdirectories:

**Directory structure:**

::

    _working/output/
      └── YYYYMMDD_HHMMSS_pyphen/   # Run directory (one per batch)
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
      └── 20260110_143022_pyphen/
          ├── syllables/
          │   └── en_US.txt
          └── meta/
              └── en_US.txt

**Batch mode (multiple files):**

::

    _working/output/
      └── 20260110_143022_pyphen/   # All files share one run directory
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

   # Step 1: Extract syllables from corpus (language auto-detected or defaults to en_US)
   python -m build_tools.pyphen_syllable_extractor \
     --source data/corpus/ \
     --pattern "*.txt" \
     --output data/raw/

   # Step 2: Normalize extracted syllables
   python -m build_tools.pyphen_syllable_normaliser \
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

**Language selection (optional):**

- **Intelligent defaults**: If no language is specified, the tool automatically:

  - Uses ``--auto`` (automatic detection) if ``langdetect`` is installed
  - Falls back to ``en_US`` if ``langdetect`` is not available
  - Displays which default was chosen at runtime

- **Explicit language**: ``--lang en_US`` - Specify a specific language code
- **Force auto-detect**: ``--auto`` - Explicitly request automatic language detection (requires ``langdetect``)

**Examples:**

.. code-block:: bash

   # Simple usage (language auto-selected)
   python -m build_tools.pyphen_syllable_extractor --file input.txt

   # Explicit language selection
   python -m build_tools.pyphen_syllable_extractor --file input.txt --lang de_DE

   # Force automatic detection
   python -m build_tools.pyphen_syllable_extractor --file input.txt --auto

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

   from build_tools.pyphen_syllable_extractor import SUPPORTED_LANGUAGES
   print(f"{len(SUPPORTED_LANGUAGES)} languages available")

**Language Auto-Detection:**

The tool includes automatic language detection (requires ``langdetect`` package):

- Use ``--auto`` flag to enable automatic language detection
- Detection is per-file based on text content
- Falls back to English (en_US) if detection fails or is unavailable
- Install with: ``pip install langdetect``

To check if auto-detection is available:

.. code-block:: python

   from build_tools.pyphen_syllable_extractor import is_detection_available
   if is_detection_available():
       print("Language auto-detection is available")

**Syllable Length Constraints:**

- Default: min=2, max=8 characters
- Adjust with ``--min`` and ``--max`` flags
- Shorter syllables (min=1) include single vowels
- Longer syllables (max=10+) may include compound patterns

**Output Organization:**

- Each extraction run creates a timestamped directory with pyphen identifier (``YYYYMMDD_HHMMSS_pyphen/``)
- Run directory contains ``syllables/`` and ``meta/`` subdirectories
- Batch processing groups all files into a single run directory
- Input filenames are preserved in output (e.g., ``alice.txt``)
- Interactive mode uses language code as filename (e.g., ``en_US.txt``)
- Metadata files provide full provenance tracking
- All extractions are logged to corpus database (if available)

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.pyphen_syllable_extractor
   :members:
   :undoc-members:
   :show-inheritance:
