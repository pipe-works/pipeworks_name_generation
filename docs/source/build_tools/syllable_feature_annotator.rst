===========================
Syllable Feature Annotator
===========================

.. currentmodule:: build_tools.syllable_feature_annotator

Overview
--------

.. automodule:: build_tools.syllable_feature_annotator
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.syllable_feature_annotator.cli
   :func: create_argument_parser
   :prog: python -m build_tools.syllable_feature_annotator

Output Format
-------------

Input/Output Contract
~~~~~~~~~~~~~~~~~~~~~

**Inputs** (from syllable normaliser):

- ``syllables_unique.txt`` - One canonical syllable per line
- ``syllables_frequencies.json`` - ``{"syllable": count}`` mapping

**Output**:

- ``syllables_annotated.json`` - Array of syllable records with features

Output Structure
~~~~~~~~~~~~~~~~

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

**Feature set:**

All 12 features are applied to every syllable:
- Onset features (starts_with_vowel, starts_with_cluster, starts_with_heavy_cluster)
- Content features (contains_plosive, contains_fricative, contains_liquid, contains_nasal)
- Vowel features (short_vowel, long_vowel)
- Coda features (ends_with_vowel, ends_with_nasal, ends_with_stop)

Integration Guide
-----------------

The feature annotator sits between the normaliser and pattern development:

.. code-block:: bash

   # Step 1: Normalize syllables from corpus
   python -m build_tools.pyphen_syllable_normaliser \
     --source data/corpus/ \
     --output data/normalized/

   # Step 2: Annotate normalized syllables with features
   python -m build_tools.syllable_feature_annotator \
     --syllables data/normalized/syllables_unique.txt \
     --frequencies data/normalized/syllables_frequencies.json \
     --output data/annotated/syllables_annotated.json

   # Step 3: Use annotated syllables for pattern generation (future)

**When to use this tool:**

- After syllable normalization is complete
- Before developing phonotactic patterns or constraints
- To add structural feature metadata to your syllable corpus
- For analysis tasks requiring feature-based filtering or grouping

Notes
-----

**Features are structural observations:**

Features are structural observations based on phoneme presence, not linguistic
interpretations. This ensures deterministic, language-agnostic detection.

**Processing characteristics:**

- Fast and deterministic (same input = same output)
- All 12 features applied to every syllable (no selective detection)
- Designed to integrate seamlessly with syllable normalizer output

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.syllable_feature_annotator
   :members:
   :undoc-members:
   :show-inheritance:
