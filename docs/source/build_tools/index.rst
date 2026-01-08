Build Tools
===========

The pipeworks_name_generation project includes build-time tools for analyzing and extracting
phonetic patterns from text. These tools are used to prepare syllable data for the name generator.

**Important**: These are build-time tools only - they are not used during runtime name generation.

Tool Overview
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Tool
     - Description
   * - :doc:`syllable_extractor`
     - Dictionary-based syllable extraction using pyphen (LibreOffice dictionaries)
   * - :doc:`syllable_normaliser`
     - 3-step normalization pipeline (aggregation, canonicalization, frequency analysis)
   * - :doc:`syllable_feature_annotator`
     - Phonetic feature detection (onset, nucleus, coda features)
   * - :doc:`syllable_walk`
     - Explore phonetic feature space via cost-based random walks
   * - :doc:`corpus_db`
     - Build provenance ledger for tracking extraction runs (inputs, outputs, settings)
   * - :doc:`analysis_tools`
     - Post-annotation analysis (feature signatures, t-SNE visualization, random sampling)

Quick Start
-----------

Extract syllables from text:

.. code-block:: bash

   python -m build_tools.syllable_extractor --file input.txt --auto

Normalize extracted syllables:

.. code-block:: bash

   python -m build_tools.syllable_normaliser --source data/corpus/ --output results/

Annotate syllables with phonetic features:

.. code-block:: bash

   python -m build_tools.syllable_feature_annotator

Explore syllable walks (interactive):

.. code-block:: bash

   python -m build_tools.syllable_walk data/annotated/syllables_annotated.json --web

Analyze and visualize:

.. code-block:: bash

   python -m build_tools.syllable_analysis.tsne_visualizer --interactive

Detailed Documentation
----------------------

.. toctree::
   :maxdepth: 2

   syllable_extractor
   syllable_normaliser
   syllable_feature_annotator
   syllable_walk
   corpus_db
   analysis_tools
