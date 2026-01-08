Syllable Normaliser
===================

.. automodule:: build_tools.syllable_normaliser
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_normaliser.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_normaliser

Output Files
------------

The pipeline generates 5 output files:

1. **syllables_raw.txt** - Aggregated raw syllables (all occurrences preserved)
2. **syllables_canonicalised.txt** - Normalized canonical syllables
3. **syllables_frequencies.json** - Frequency intelligence (syllable → count)
4. **syllables_unique.txt** - Deduplicated canonical syllable inventory
5. **normalization_meta.txt** - Detailed statistics and metadata report

Pipeline Details
----------------

Step 1 - Aggregation
~~~~~~~~~~~~~~~~~~~~

- Combines all input files into ``syllables_raw.txt``
- Preserves ALL occurrences (no deduplication)
- Maintains raw counts for frequency analysis
- Empty lines filtered during file reading

Step 2 - Canonicalization
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Unicode normalization (NFKD - compatibility decomposition)
- Strip diacritics: café → cafe, résumé → resume
- Lowercase conversion
- Trim whitespace
- Charset validation (reject invalid characters)
- Length constraint enforcement
- Outputs to ``syllables_canonicalised.txt``

Step 3 - Frequency Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Count occurrences of each canonical syllable
- Generate frequency rankings and percentages
- Create deduplicated unique list (alphabetically sorted)
- Outputs:
  - ``syllables_frequencies.json`` - Frequency counts before deduplication
  - ``syllables_unique.txt`` - Authoritative syllable inventory
  - ``normalization_meta.txt`` - Comprehensive statistics report

Programmatic Usage
------------------

Full Pipeline
~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from build_tools.syllable_normaliser import (
       NormalizationConfig,
       run_full_pipeline,
       discover_input_files
   )

   # Discover input files
   files = discover_input_files(
       source_dir=Path("data/corpus/"),
       pattern="*.txt",
       recursive=False
   )

   # Create configuration
   config = NormalizationConfig(
       min_length=2,
       max_length=20,
       allowed_charset="abcdefghijklmnopqrstuvwxyz",
       unicode_form="NFKD"
   )

   # Run full pipeline
   result = run_full_pipeline(
       input_files=files,
       output_dir=Path("_working/normalized"),
       config=config,
       verbose=True
   )

   # Access results
   print(f"Processed {result.stats.raw_count:,} raw syllables")
   print(f"Canonical: {result.stats.after_canonicalization:,}")
   print(f"Unique: {result.stats.unique_canonical:,}")
   print(f"Rejection rate: {result.stats.rejection_rate:.1f}%")

   # Access frequency data
   top_syllable = max(result.frequencies.items(), key=lambda x: x[1])
   print(f"Most frequent: {top_syllable[0]} ({top_syllable[1]} occurrences)")

Individual Pipeline Steps
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from build_tools.syllable_normaliser import (
       FileAggregator,
       SyllableNormalizer,
       FrequencyAnalyzer,
       NormalizationConfig,
       normalize_batch
   )

   # Step 1: Aggregation
   aggregator = FileAggregator()
   raw_syllables = aggregator.aggregate_files([Path("file1.txt"), Path("file2.txt")])
   aggregator.save_raw_syllables(raw_syllables, Path("syllables_raw.txt"))

   # Step 2: Normalization
   config = NormalizationConfig(min_length=2, max_length=8)
   canonical_syllables, rejection_stats = normalize_batch(raw_syllables, config)

   # Save canonicalized syllables
   with open("syllables_canonicalised.txt", "w", encoding="utf-8") as f:
       for syllable in canonical_syllables:
           f.write(f"{syllable}\\n")

   # Step 3: Frequency analysis
   analyzer = FrequencyAnalyzer()
   frequencies = analyzer.calculate_frequencies(canonical_syllables)
   unique_syllables = analyzer.extract_unique_syllables(canonical_syllables)

   # Save outputs
   analyzer.save_frequencies(frequencies, Path("syllables_frequencies.json"))
   analyzer.save_unique_syllables(unique_syllables, Path("syllables_unique.txt"))

Single Syllable Normalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from build_tools.syllable_normaliser import SyllableNormalizer, NormalizationConfig

   config = NormalizationConfig(min_length=2, max_length=20)
   normalizer = SyllableNormalizer(config)

   # Basic normalization
   normalizer.normalize("Café")       # → "cafe"
   normalizer.normalize("  HELLO  ")  # → "hello"
   normalizer.normalize("résumé")     # → "resume"
   normalizer.normalize("Zürich")     # → "zurich"

   # Rejections return None
   normalizer.normalize("x")          # → None (too short)
   normalizer.normalize("hello123")   # → None (invalid characters)
   normalizer.normalize("   ")        # → None (empty after normalization)

Frequency Intelligence
----------------------

The frequency data captures how often each canonical syllable occurs **before** deduplication.
This intelligence is essential for understanding natural language patterns:

.. code-block:: json

   {
     "ka": 187,
     "ra": 162,
     "mi": 145,
     "ta": 98
   }

This shows "ka" appears 187 times in the canonical syllables, providing valuable frequency information
for weighted name generation patterns.

Important Notes
---------------

- This is a **build-time tool only** - not used during runtime name generation
- The normalizer is deterministic (same input always produces same output)
- Empty lines are filtered during aggregation (not counted as rejections)
- Frequency counts capture occurrences BEFORE deduplication
- All syllable processing is case-insensitive (output is lowercase)
- Unicode normalization form NFKD provides maximum compatibility decomposition

API Reference
-------------

.. automodule:: build_tools.syllable_normaliser
   :members:
   :undoc-members:
   :show-inheritance:
