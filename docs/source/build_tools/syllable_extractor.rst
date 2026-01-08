Syllable Extractor
==================

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

Examples::

    20260105_143022.syllables.en_US.txt
    20260105_143022.meta.en_US.txt
    20260105_143045.syllables.de_DE.txt

Programmatic Usage
------------------

Single-File Extraction
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from build_tools.syllable_extractor import SyllableExtractor

   # Initialize extractor for English (US)
   extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)

   # Extract syllables from text
   syllables = extractor.extract_syllables_from_text("Hello wonderful world")
   print(sorted(syllables))
   # ['der', 'ful', 'hel', 'lo', 'won', 'world']

   # Extract from a file
   syllables = extractor.extract_syllables_from_file(Path('input.txt'))

   # Save results
   extractor.save_syllables(syllables, Path('output.txt'))

Automatic Language Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from build_tools.syllable_extractor import SyllableExtractor

   # Automatic language detection from text
   text = "Bonjour le monde, comment allez-vous?"
   syllables, stats, detected_lang = SyllableExtractor.extract_with_auto_language(text)
   print(f"Detected language: {detected_lang}")  # "fr"
   print(f"Extracted {len(syllables)} syllables")

Batch Processing
~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from build_tools.syllable_extractor import discover_files, process_batch

   # Discover files in a directory
   files = discover_files(
       source=Path("~/documents"),
       pattern="*.txt",
       recursive=True
   )

   # Process batch with automatic language detection
   result = process_batch(
       files=files,
       language_code="auto",  # or specific code like "en_US"
       min_len=2,
       max_len=8,
       output_dir=Path("_working/output"),
       quiet=False,
       verbose=False
   )

   # Check results
   print(f"Processed {result.total_files} files")
   print(f"Successful: {result.successful}")
   print(f"Failed: {result.failed}")
   print(result.format_summary())  # Detailed summary report

Supported Languages
-------------------

The extractor supports 40+ languages through pyphen's LibreOffice dictionaries.

.. code-block:: python

   from build_tools.syllable_extractor import SUPPORTED_LANGUAGES

   print(f"{len(SUPPORTED_LANGUAGES)} languages available")
   # English (US/UK), German, French, Spanish, Russian, and many more...

Language Auto-Detection
~~~~~~~~~~~~~~~~~~~~~~~

The tool includes automatic language detection (requires ``langdetect``):

.. code-block:: python

   from build_tools.syllable_extractor import (
       detect_language_code,
       is_detection_available,
       list_supported_languages
   )

   # Check if detection is available
   if is_detection_available():
       # Detect language from text
       lang_code = detect_language_code("Hello world, this is a test")
       print(lang_code)  # "en_US"

       # List all supported languages with detection
       languages = list_supported_languages()
       print(f"{len(languages)} languages available")

API Reference
-------------

.. automodule:: build_tools.syllable_extractor
   :members:
   :undoc-members:
   :show-inheritance:
