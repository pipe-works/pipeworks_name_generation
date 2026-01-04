pipeworks_name_generation
==========================

**Phonetically-grounded name generation for games and procedural systems**

A lightweight, deterministic name generator that produces pronounceable names without imposing semantic meaning.

.. note::

   **User Guides and Project Documentation**

   For user guides, build tool documentation, and project guidelines, see the ``_working/guides/`` directory in the project root:

   * ``_working/guides/syllable_extractor_guide.md`` - Complete guide to the syllable extractor
   * ``_working/guides/syllable_extractor_fix_notes.md`` - Technical implementation notes
   * ``_working/guides/tab_completion_guide.md`` - Tab completion usage guide
   * ``_working/guides/README_DOCS.md`` - Documentation system overview
   * ``README.md`` - Main project README
   * ``CLAUDE.md`` - Project guidelines for Claude Code

.. toctree::
   :maxdepth: 2
   :caption: Project Information

   Changelog <changelog>

.. toctree::
   :maxdepth: 3
   :caption: API Reference

   autoapi/index

Key Features
------------

* **Deterministic**: Same seed always produces same name
* **Phonetically plausible**: Uses syllable-based generation
* **Context-free**: No semantic meaning imposed
* **Lightweight**: Zero runtime dependencies
* **Type-safe**: Full type hint support

Quick Start
-----------

Installation:

.. code-block:: bash

   pip install pipeworks-name-generation

Basic usage:

.. code-block:: python

   from pipeworks_name_generation import NameGenerator

   gen = NameGenerator(pattern="simple")
   name = gen.generate(seed=42)
   print(name)  # Always produces same name for seed=42

Batch generation:

.. code-block:: python

   names = gen.generate_batch(count=10, base_seed=1000, unique=True)

Build Tools
-----------

Extract syllables from text corpora:

.. code-block:: bash

   python -m build_tools.syllable_extractor

Features tab completion for paths and supports 50+ languages via pyphen.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
