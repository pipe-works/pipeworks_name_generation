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
   * - :doc:`pyphen_syllable_extractor`
     - Dictionary-based syllable extraction using pyphen (LibreOffice dictionaries)
   * - :doc:`nltk_syllable_extractor`
     - Phonetically-guided syllable extraction using NLTK CMUDict with onset/coda principles
   * - :doc:`pyphen_syllable_normaliser`
     - 3-step normalization pipeline for pyphen extractor output
   * - :doc:`nltk_syllable_normaliser`
     - NLTK-specific normalization with fragment cleaning for phonetically coherent syllables
   * - :doc:`syllable_feature_annotator`
     - Phonetic feature detection (onset, nucleus, coda features)
   * - :doc:`name_combiner`
     - Generate N-syllable name candidates with feature aggregation
   * - :doc:`name_selector`
     - Filter and rank candidates against name class policies
   * - :doc:`corpus_sqlite_builder`
     - Convert annotated JSON to SQLite databases for fast TUI loading (optional performance optimization)
   * - :doc:`syllable_walk`
     - Explore phonetic feature space via cost-based random walks (CLI)
   * - :doc:`syllable_walk_web`
     - Browser-based interface for browsing selections and generating walks
   * - :doc:`syllable_walk_tui`
     - Interactive TUI for exploring phonetic space with side-by-side patch configuration
   * - :doc:`corpus_db`
     - Build provenance ledger for tracking extraction runs (inputs, outputs, settings)
   * - :doc:`corpus_db_viewer`
     - Interactive TUI for viewing corpus database provenance records
   * - :doc:`analysis_tools`
     - Post-annotation analysis (feature signatures, t-SNE visualization, random sampling)
   * - :doc:`tui_common`
     - Shared TUI components (controls, browsers, keybinding config) for Textual-based tools
   * - :doc:`pipeline_tui`
     - Interactive TUI for running extraction, normalization, and annotation pipelines

Quick Start
-----------

.. code-block:: bash

   # Extract syllables from text (choose one extractor)

   # Option 1: pyphen extractor (40+ languages, typographic splits)
   python -m build_tools.pyphen_syllable_extractor --file input.txt --auto

   # Option 2: NLTK extractor (English only, phonetic splits)
   python -m build_tools.nltk_syllable_extractor --file input.txt

   # Normalize extracted syllables (both use in-place processing)

   # For pyphen extractor output:
   python -m build_tools.pyphen_syllable_normaliser --run-dir _working/output/20260110_143022_pyphen/

   # For NLTK extractor output:
   python -m build_tools.nltk_syllable_normaliser --run-dir _working/output/20260110_095213_nltk/

   # Annotate syllables with phonetic features
   python -m build_tools.syllable_feature_annotator

   # Generate name candidates
   python -m build_tools.name_combiner \
       --run-dir _working/output/20260110_143022_pyphen/ \
       --syllables 2 --count 10000

   # Select names for a class
   python -m build_tools.name_selector \
       --run-dir _working/output/20260110_143022_pyphen/ \
       --candidates candidates/pyphen_candidates_2syl.json \
       --name-class first_name

   # (Optional) Convert to SQLite for faster TUI loading
   python -m build_tools.corpus_sqlite_builder _working/output/20260110_143022_pyphen/

   # Explore syllable walks (choose one interface)
   python -m build_tools.syllable_walk_web      # Browser-based selections browser
   python -m build_tools.syllable_walk_tui       # Terminal TUI with side-by-side comparison

   # Analyze and visualize
   python -m build_tools.syllable_analysis.tsne_visualizer --interactive

Detailed Documentation
----------------------

.. toctree::
   :maxdepth: 2

   pyphen_syllable_extractor
   nltk_syllable_extractor
   pyphen_syllable_normaliser
   nltk_syllable_normaliser
   syllable_feature_annotator
   name_combiner
   name_selector
   corpus_sqlite_builder
   syllable_walk
   syllable_walk_web
   syllable_walk_tui
   corpus_db
   corpus_db_viewer
   analysis_tools
   tui_common
   pipeline_tui
