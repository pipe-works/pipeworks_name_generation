===============
Corpus Database
===============

.. currentmodule:: build_tools.corpus_db

Overview
--------

.. automodule:: build_tools.corpus_db
   :no-members:

Output Format
-------------

Database Schema
~~~~~~~~~~~~~~~

The corpus database uses a simple three-table schema to track extraction runs:

**runs** - One row per extractor invocation
   Records all configuration parameters, timestamps, command-line invocations,
   and execution outcomes. Each run gets a unique ID for tracking.

**inputs** - Source files/directories processed (many-to-one with runs)
   Tracks which files or directories were used as input for each extraction run.

**outputs** - Generated output files (many-to-one with runs)
   Records the .syllables and .meta files produced, along with syllable counts.

For a detailed schema description:

.. code-block:: python

   from build_tools.corpus_db import get_schema_description
   print(get_schema_description())

Database Location
~~~~~~~~~~~~~~~~~

Default location: ``data/raw/syllable_extractor.db``

Custom location can be specified when initializing the ledger:

.. code-block:: python

   from pathlib import Path
   from build_tools.corpus_db import CorpusLedger

   ledger = CorpusLedger(db_path=Path("_working/test.db"))

Integration Guide
-----------------

When building new syllable extractors, integrate the ledger by:

1. Calling ``start_run()`` at the beginning of extraction
2. Recording all input sources with ``record_input()``
3. Recording all output files with ``record_output()``
4. Marking completion with ``complete_run()`` in a try/finally block

**Example integration pattern:**

.. code-block:: python

   from build_tools.corpus_db import CorpusLedger
   import sys

   ledger = CorpusLedger()
   run_id = ledger.start_run(
       extractor_tool="my_extractor",
       command_line=" ".join(sys.argv),
       # ... other parameters ...
   )

   try:
       # ... extraction logic ...
       ledger.record_output(run_id, output_path, unique_syllable_count=count)
       ledger.complete_run(run_id, exit_code=0, status="completed")
   except Exception as e:
       ledger.complete_run(run_id, exit_code=1, status="failed")
       raise

**When to use this tool:**

- Track provenance of all syllable extraction runs
- Query history to understand what corpus files were generated
- Find which run produced a specific output file
- Monitor extraction success rates across tools

Notes
-----

**Cross-Platform Compatibility:**

Paths are stored in POSIX format (forward slashes) for cross-platform consistency.
This ensures the database can be shared between Windows, macOS, and Linux systems
without path separator issues.

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.corpus_db
   :members:
   :undoc-members:
   :show-inheritance:
