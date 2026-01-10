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

- ``pyphen_syllables_unique.txt`` or ``nltk_syllables_unique.txt`` - One canonical syllable per line
- ``pyphen_syllables_frequencies.json`` or ``nltk_syllables_frequencies.json`` - ``{"syllable": count}`` mapping

**Output** (auto-detected from input paths):

- ``<run_directory>/data/pyphen_syllables_annotated.json`` - Pyphen extractor output
- ``<run_directory>/data/nltk_syllables_annotated.json`` - NLTK extractor output

**Output path auto-detection:**

The tool automatically detects the extractor type (pyphen or nltk) from the input file paths and places
output in the same run directory. This creates a self-contained workflow where each extraction run
contains all its derived data.

**Example directory structure after annotation:**

.. code-block:: text

    _working/output/20260110_115601_nltk/
    ├── data/
    │   └── nltk_syllables_annotated.json      ← Auto-detected output
    ├── meta/
    ├── syllables/
    ├── nltk_syllables_unique.txt              ← Input
    ├── nltk_syllables_frequencies.json        ← Input
    └── ...

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

The feature annotator sits between the normaliser and pattern development. It automatically
detects the extractor type and places output in the run directory.

**Recommended workflow (with auto-detection):**

.. code-block:: bash

   # Step 1: Extract and normalize syllables
   python -m build_tools.pyphen_syllable_extractor --file input.txt
   python -m build_tools.pyphen_syllable_normaliser \
     --run-dir _working/output/20260110_115453_pyphen/

   # Step 2: Annotate with features (output path auto-detected)
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/20260110_115453_pyphen/pyphen_syllables_unique.txt \
     --frequencies _working/output/20260110_115453_pyphen/pyphen_syllables_frequencies.json
   # Creates: _working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json

   # Step 3: Use annotated syllables for pattern generation (future)

**Alternative: Explicit output path (overrides auto-detection):**

.. code-block:: bash

   python -m build_tools.syllable_feature_annotator \
     --syllables path/to/syllables.txt \
     --frequencies path/to/frequencies.json \
     --output custom/output.json

**When to use this tool:**

- After syllable normalization is complete
- Before developing phonotactic patterns or constraints
- To add structural feature metadata to your syllable corpus
- For analysis tasks requiring feature-based filtering or grouping

**Extractor type detection:**

The tool detects the extractor type by examining:
1. Filename prefix (``pyphen_*`` or ``nltk_*``)
2. Parent directory name (``*_pyphen`` or ``*_nltk``)
3. Falls back to ``data/annotated/syllables_annotated.json`` if detection fails

Notes
-----

**Auto-detection creates self-contained workflows:**

The automatic output path detection ensures each extraction run is self-contained with all
derived data in one directory. This makes it easy to manage multiple extraction runs and
compare results from different extractors (pyphen vs NLTK).

**Features are structural observations:**

Features are structural observations based on phoneme presence, not linguistic
interpretations. This ensures deterministic, language-agnostic detection.

**Processing characteristics:**

- Fast and deterministic (same input = same output)
- All 12 features applied to every syllable (no selective detection)
- Designed to integrate seamlessly with syllable normalizer output
- Output path auto-detection works with both pyphen and NLTK normalizer outputs

**Backward compatibility:**

Explicit ``--output`` paths still work and override auto-detection. This ensures compatibility
with existing workflows and scripts.

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.syllable_feature_annotator
   :members:
   :undoc-members:
   :show-inheritance:
