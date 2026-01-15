=========================
Syllable Walker TUI
=========================

.. currentmodule:: build_tools.syllable_walk_tui

Overview
--------

.. automodule:: build_tools.syllable_walk_tui
   :no-members:

The Syllable Walker TUI is an interactive terminal user interface for exploring phonetic space
through the Syllable Walker system. Built with `Textual <https://textual.textualize.io/>`_,
it provides a keyboard-driven interface for interactive phonetic exploration with side-by-side
patch comparison.

**Design Philosophy:**

Based on the eurorack modular synthesizer analogy - we patch conditions, not outputs.
The focus is on exploring phonetic climates through interactive parameter tweaking
rather than generating specific outputs.

**Key Features:**

- Side-by-side patch configuration (dual oscillator comparison)
- Modal screens for blended walks and analysis (v/a keys)
- Keyboard-first navigation (HJKL + arrow keys)
- Real-time phonetic exploration with profile selection
- Configurable keybindings (TOML-based)
- Corpus directory selection and browsing
- Live syllable walk generation

Core Concepts
-------------

Eurorack Modular Synthesizer Analogy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The TUI is inspired by eurorack modular synthesizers, where you patch together modules
to create complex sonic textures. Instead of sound, we're exploring phonetic space:

**Patches:** Each patch (A and B) represents a configuration of phonetic parameters
that define how syllable walks are generated.

**Modules:** Controls for oscillators, filters, envelopes, LFOs, and attenuators
that shape the phonetic exploration behavior.

**Patching:** Rather than directly specifying outputs, you configure conditions
and constraints that guide phonetic exploration through the syllable space.

**Dual Oscillators:** Side-by-side patches allow comparison of different phonetic
configurations, similar to comparing two oscillator settings in a synthesizer.

Side-by-Side Patch Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The TUI displays two patches (A and B) simultaneously, enabling direct comparison
of different phonetic exploration strategies:

- Configure Patch A with conservative parameters (e.g., "clerical" profile)
- Configure Patch B with chaotic parameters (e.g., "goblin" profile)
- Generate walks for both to compare phonetic behaviors
- Swap configurations between patches for rapid experimentation

Keyboard-First Navigation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The TUI is designed for keyboard-driven efficiency:

**Navigation:**

- ``hjkl`` or arrow keys for movement (vi-style)
- ``Tab`` / ``Shift+Tab`` for panel switching
- Single-key commands for common actions

**Configuration:**

All keybindings are configurable via TOML file at:
``~/.config/pipeworks_tui/keybindings.toml``

Command-Line Interface
----------------------

**Launching the TUI:**

.. code-block:: bash

   python -m build_tools.syllable_walk_tui

The TUI takes no command-line arguments and launches directly into the interactive interface.

**Requirements:**

- Python 3.12+
- Textual library (install via ``pip install -r requirements-dev.txt``)
- Annotated syllable corpus (from ``syllable_feature_annotator``)

Output Format
-------------

Interactive Exploration
~~~~~~~~~~~~~~~~~~~~~~~

The Syllable Walker TUI is an interactive exploration tool and does not produce
file-based outputs. Instead, it enables real-time phonetic exploration through
the terminal interface.

**Live Walk Display:**

Generated walks are displayed in the TUI interface with:

- Syllable sequence (visual representation of the walk)
- Phonetic features for each syllable
- Frequency information
- Step-by-step progression details

**Future Enhancement:**

Export functionality for walks may be added in future versions, allowing users
to save interesting walk sequences for later analysis or use in name generation patterns.

Integration Guide
-----------------

Use the Syllable Walker TUI to interactively explore phonetic space after
annotating your syllable corpus:

.. code-block:: bash

   # Step 1: Extract and normalize syllables
   python -m build_tools.pyphen_syllable_extractor --file wordlist.txt
   python -m build_tools.pyphen_syllable_normaliser \
     --run-dir _working/output/20260110_115453_pyphen/

   # Step 2: Annotate with phonetic features
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/20260110_115453_pyphen/pyphen_syllables_unique.txt \
     --frequencies _working/output/20260110_115453_pyphen/pyphen_syllables_frequencies.json

   # Step 3: Launch interactive TUI for exploration
   python -m build_tools.syllable_walk_tui

**When to use this tool:**

- To interactively explore phonetic space with real-time parameter adjustment
- To compare different walk profiles side-by-side (clerical vs goblin, etc.)
- To experiment with phonetic constraints before finalizing pattern designs
- To discover interesting syllable sequences through guided exploration
- To understand how different parameters affect phonetic walk behavior
- To test corpus coverage and phonetic connectivity interactively

**Common workflows:**

1. **Compare Extractors:** Load pyphen and NLTK corpora side-by-side to see
   phonetic connectivity differences between extraction methods

2. **Profile Exploration:** Test all four walk profiles (clerical, dialect,
   goblin, ritual) with the same starting syllable to understand their behaviors

3. **Parameter Tuning:** Adjust temperature, frequency weight, and max flips
   in real-time to discover optimal settings for your use case

4. **Corpus Discovery:** Browse corpus directories to explore available
   annotated datasets and their characteristics

Advanced Topics
---------------

Keyboard Shortcuts
~~~~~~~~~~~~~~~~~~

**Global Actions:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``q`` / ``Ctrl+Q``
     - Quit application
   * - ``?`` / ``F1``
     - Show help

**Modal Screens:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key
     - Action
   * - ``v``
     - Open Blended Walk modal screen
   * - ``a``
     - Open Analysis modal screen
   * - ``Esc``
     - Close current modal screen

**Navigation:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``k`` / ``↑``
     - Move up
   * - ``j`` / ``↓``
     - Move down
   * - ``h`` / ``←``
     - Move left
   * - ``l`` / ``→``
     - Move right
   * - ``Tab`` / ``Ctrl+N``
     - Next panel
   * - ``Shift+Tab`` / ``Ctrl+P``
     - Previous panel

**Control Actions:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``Enter`` / ``Space``
     - Activate control
   * - ``+`` / ``=`` / ``]``
     - Increment value
   * - ``-`` / ``[``
     - Decrement value

**Patch Operations:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``g`` / ``F5``
     - Generate walk
   * - ``y`` / ``Ctrl+C``
     - Copy patch configuration
   * - ``p`` / ``Ctrl+V``
     - Paste patch configuration
   * - ``r``
     - Reset patch to defaults
   * - ``x``
     - Swap patches A and B

Keybinding Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

All keyboard shortcuts can be customized via TOML configuration file.

**Configuration Location:**

``~/.config/pipeworks_tui/keybindings.toml``

**Example Configuration:**

.. code-block:: toml

   [keybindings.global]
   quit = ["q", "ctrl+q"]
   help = ["question_mark", "f1"]

   [keybindings.modals]
   blended_walk = ["v"]
   analysis = ["a"]
   close_modal = ["escape"]

   [keybindings.navigation]
   up = ["k", "up"]
   down = ["j", "down"]
   left = ["h", "left"]
   right = ["l", "right"]
   next_panel = ["tab", "ctrl+n"]
   prev_panel = ["shift+tab", "ctrl+p"]

   [keybindings.controls]
   activate = ["enter", "space"]
   increment = ["plus", "equal", "right_square_bracket"]
   decrement = ["minus", "left_square_bracket"]

   [keybindings.patch]
   generate = ["g", "f5"]
   copy = ["y", "ctrl+c"]
   paste = ["p", "ctrl+v"]
   reset = ["r"]
   swap = ["x"]

**Keybinding Conflicts:**

The TUI automatically detects keybinding conflicts within each context and
displays warnings on startup. If conflicts are detected, the first binding
in the list takes precedence.

**Fallback to Defaults:**

If the configuration file doesn't exist or has errors, the TUI falls back
to sensible defaults (shown above).

Corpus Directory Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The TUI allows browsing and selecting corpus directories containing annotated
syllable data:

**Corpus Browser:**

1. Press the "Select Corpus Directory" button in either patch
2. Browse available corpus directories in ``_working/output/``
3. View metadata (extractor type, timestamp, syllable count)
4. Select directory to load annotated corpus data

**Auto-Discovery:**

The TUI automatically scans for annotated datasets in:

- ``_working/output/*/data/*_syllables_annotated.json``
- ``data/annotated/syllables_annotated.json`` (legacy location)

**Background Loading:**

Corpus data loads asynchronously in the background, preventing UI freezing
for large datasets. A loading indicator shows progress during data loading.

Design Philosophy
~~~~~~~~~~~~~~~~~

**Patching Conditions, Not Outputs:**

Like a modular synthesizer, the TUI focuses on configuring exploration
parameters (conditions) rather than specifying exact outputs. This enables
creative discovery of phonetic sequences through guided experimentation.

**Keyboard-First Efficiency:**

The TUI is designed for keyboard power users, with vi-style navigation
(``hjkl``) and single-key commands for all actions. Mouse support is
secondary.

**Side-by-Side Comparison:**

Dual patch configuration enables rapid comparison of different phonetic
strategies, helping users understand parameter effects through direct
visual comparison.

**Real-Time Exploration:**

Parameter changes take effect immediately, enabling rapid iteration and
experimentation with phonetic walk configurations.

Notes
-----

**Dependencies:**

Requires Textual library for TUI functionality. Install with:

.. code-block:: bash

   pip install -r requirements-dev.txt

**Python Version:**

Requires Python 3.12+ for modern type hints and dataclass features used
in configuration management.

**Troubleshooting:**

**Textual Not Installed:**

.. code-block:: text

   Error: Textual library not found

**Solution:** Install development dependencies:

.. code-block:: bash

   pip install -r requirements-dev.txt

**Terminal Too Small:**

If the layout looks broken, resize your terminal. Minimum recommended:
100 columns × 30 rows for proper side-by-side patch display.

**No Annotated Corpus Found:**

If the corpus browser shows no datasets, ensure you've run the feature
annotator:

.. code-block:: bash

   # Run feature annotator first
   python -m build_tools.syllable_feature_annotator \
     --syllables _working/output/.../pyphen_syllables_unique.txt \
     --frequencies _working/output/.../pyphen_syllables_frequencies.json

   # Then launch TUI
   python -m build_tools.syllable_walk_tui

**Keybinding Configuration Errors:**

If you see keybinding conflict warnings on startup, review your TOML
configuration file for duplicate key assignments within the same context.

**Performance:**

- The TUI uses async loading for large corpus datasets (500k+ syllables)
- UI remains responsive during corpus loading and walk generation
- Memory usage depends on corpus size (typically 50-300 MB)

**Build-time tool:**

This is a build-time exploration tool - not used during runtime name generation.

**Related Documentation:**

- :doc:`syllable_walk` - Command-line syllable walker (batch generation)
- :doc:`syllable_feature_annotator` - Generates input data with phonetic features
- :doc:`corpus_db_viewer` - Interactive TUI for viewing corpus database records
- :doc:`pyphen_syllable_normaliser` - Prepares pyphen syllable corpus
- :doc:`nltk_syllable_normaliser` - Prepares NLTK syllable corpus

API Reference
-------------

.. automodule:: build_tools.syllable_walk_tui
   :members:
   :undoc-members:
   :show-inheritance:
