Corpus Database
===============

.. automodule:: build_tools.corpus_db
   :no-members:

Database Schema
---------------

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

Programmatic Usage
------------------

Basic Workflow
~~~~~~~~~~~~~~

.. code-block:: python

   from build_tools.corpus_db import CorpusLedger
   from pathlib import Path

   # Initialize ledger (creates database if needed)
   with CorpusLedger() as ledger:
       # Start recording a run
       run_id = ledger.start_run(
           extractor_tool="syllable_extractor",
           extractor_version="0.2.0",
           pyphen_lang="en_US",
           min_len=2,
           max_len=8,
           command_line="python -m build_tools.syllable_extractor --file input.txt"
       )

       # Record inputs
       ledger.record_input(run_id, Path("data/corpus/english.txt"))

       # ... extraction happens ...

       # Record outputs
       ledger.record_output(
           run_id,
           output_path=Path("data/raw/en_US/corpus.syllables"),
           unique_syllable_count=1234
       )

       # Mark run complete
       ledger.complete_run(run_id, exit_code=0, status="completed")

Querying Runs
~~~~~~~~~~~~~

.. code-block:: python

   # Find recent runs
   recent = ledger.get_recent_runs(limit=10)
   for run in recent:
       print(f"{run['run_timestamp']}: {run['extractor_tool']}")

   # Find runs by tool
   pyphen_runs = ledger.get_runs_by_tool("syllable_extractor")

   # Reverse lookup: which run produced this file?
   run = ledger.find_run_by_output(Path("data/raw/corpus.syllables"))
   if run:
       print(f"Created by: {run['command_line']}")

   # Get overall statistics
   stats = ledger.get_stats()
   print(f"Total runs: {stats['total_runs']}")
   print(f"Success rate: {stats['completed_runs']/stats['total_runs']*100:.1f}%")

Database Location
-----------------

Default location: ``data/raw/syllable_extractor.db``

Custom location:

.. code-block:: python

   from pathlib import Path
   ledger = CorpusLedger(db_path=Path("_working/test.db"))

Cross-Platform Compatibility
-----------------------------

Paths are stored in POSIX format (forward slashes) for cross-platform consistency.
This ensures the database can be shared between Windows, macOS, and Linux systems
without path separator issues.

Integration with Extractors
----------------------------

When building new syllable extractors, integrate the ledger by:

1. Calling ``start_run()`` at the beginning of extraction
2. Recording all input sources with ``record_input()``
3. Recording all output files with ``record_output()``
4. Marking completion with ``complete_run()`` in a try/finally block

Example integration pattern:

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
