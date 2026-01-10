pipeworks_name_generation
==========================

**Phonetically-grounded name generation for games and procedural systems**

A lightweight, deterministic name generator that produces pronounceable names without imposing semantic meaning.

.. toctree::
   :maxdepth: 2
   :caption: Project Information

   Changelog <changelog>

.. toctree::
   :maxdepth: 2
   :caption: Build Tools

   build_tools/index

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

   # Install from PyPI
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

   # Run syllable extractor in interactive mode
   python -m build_tools.pyphen_syllable_extractor

Features tab completion for paths and supports 50+ languages via pyphen.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
