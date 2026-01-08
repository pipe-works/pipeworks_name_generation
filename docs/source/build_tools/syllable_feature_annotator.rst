Syllable Feature Annotator
==========================

.. automodule:: build_tools.syllable_feature_annotator
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_feature_annotator.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_feature_annotator

Input/Output Contract
---------------------

**Inputs** (from syllable normaliser):

- ``syllables_unique.txt`` - One canonical syllable per line
- ``syllables_frequencies.json`` - ``{"syllable": count}`` mapping

**Output**:

- ``syllables_annotated.json`` - Array of syllable records with features

Output Structure
----------------

The annotator produces JSON with this structure:

.. code-block:: json

   [
     {
       "syllable": "kran",
       "frequency": 7,
       "features": {
         "starts_with_vowel": false,
         "starts_with_cluster": true,
         "starts_with_heavy_cluster": false,
         "contains_plosive": true,
         "contains_fricative": false,
         "contains_liquid": true,
         "contains_nasal": true,
         "short_vowel": true,
         "long_vowel": false,
         "ends_with_vowel": false,
         "ends_with_nasal": true,
         "ends_with_stop": false
       }
     }
   ]

Programmatic Usage
------------------

Full Pipeline
~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from build_tools.syllable_feature_annotator import run_annotation_pipeline

   # Run complete annotation pipeline
   result = run_annotation_pipeline(
       syllables_path=Path("data/normalized/syllables_unique.txt"),
       frequencies_path=Path("data/normalized/syllables_frequencies.json"),
       output_path=Path("data/annotated/syllables_annotated.json"),
       verbose=True
   )

   # Access results
   print(f"Annotated {result.statistics.syllable_count} syllables")
   print(f"Processing time: {result.statistics.processing_time:.2f}s")

Annotate Syllables in Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from build_tools.syllable_feature_annotator import (
       annotate_corpus,
       annotate_syllable,
       FEATURE_DETECTORS
   )

   # Annotate a corpus
   syllables = ["ka", "kran", "spla"]
   frequencies = {"ka": 187, "kran": 7, "spla": 2}
   result = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)

   # Annotate a single syllable
   record = annotate_syllable("kran", 7, FEATURE_DETECTORS)
   print(f"{record.syllable}: {sum(record.features.values())} features active")

   # Access feature detection results
   print(f"Starts with cluster: {record.features['starts_with_cluster']}")
   print(f"Contains plosive: {record.features['contains_plosive']}")

Import Individual Components
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from build_tools.syllable_feature_annotator import (
       # Core functions
       run_annotation_pipeline,
       annotate_corpus,
       annotate_syllable,
       # Data models
       AnnotatedSyllable,
       AnnotationStatistics,
       AnnotationResult,
       # Feature detection
       FEATURE_DETECTORS,
       starts_with_vowel,
       contains_plosive,
       # Phoneme sets
       VOWELS,
       PLOSIVES,
       FRICATIVES,
       # File I/O
       load_syllables,
       load_frequencies,
       save_annotated_syllables
   )

Pipeline Integration
--------------------

The feature annotator sits between the normaliser and pattern development:

.. code-block:: bash

   # Step 1: Normalize syllables from corpus
   python -m build_tools.syllable_normaliser \\
     --source data/corpus/ \\
     --output data/normalized/

   # Step 2: Annotate normalized syllables with features
   python -m build_tools.syllable_feature_annotator \\
     --syllables data/normalized/syllables_unique.txt \\
     --frequencies data/normalized/syllables_frequencies.json \\
     --output data/annotated/syllables_annotated.json

   # Step 3: Use annotated syllables for pattern generation (future)

Notes
-----

- This is a **build-time tool only** - not used during runtime name generation
- Features are structural observations, not linguistic interpretations
- All 12 features are applied to every syllable (no selective detection)
- Processing is fast and deterministic (same input = same output)
- Designed to integrate seamlessly with syllable normalizer output

API Reference
-------------

.. automodule:: build_tools.syllable_feature_annotator
   :members:
   :undoc-members:
   :show-inheritance:
