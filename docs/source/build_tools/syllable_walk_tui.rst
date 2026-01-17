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
- Center panel walk output display with corpus provenance
- Configurable walk count per patch (default 2, "less is more")
- Modal screens for blended walks and analysis (v/a keys)
- Keyboard-first navigation with Tab and arrow keys
- Real-time phonetic exploration with profile selection
- Quick corpus selection with number keys (1/2)
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

**Center Panel Walk Display:**

Generated walks are displayed in the center panel with corpus provenance:

.. code-block:: text

    PATCH A
    20260110_115453_pyphen (Pyphen)
    ────────────────────
    ka → ki → ta → ka → ti → ko
    ma → mi → na → ni → mo → no

    PATCH B
    20260110_115601_nltk (NLTK)
    ────────────────────
    bra → kla → gal → sta → pla → tra
    clem → gism → lents → rovn → pus → cha

**Walk Count:**

Each patch has a configurable walk count (default 2, range 1-20). The "less is more"
approach encourages focused exploration - start with 2 walks to *feel* the phonetic
space before generating more.

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
   * - ``1``
     - Select corpus directory for Patch A
   * - ``2``
     - Select corpus directory for Patch B

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
   * - ``d``
     - Open Database Viewer modal screen
   * - ``Esc``
     - Close current modal screen

**Navigation:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``Tab``
     - Next control
   * - ``Shift+Tab``
     - Previous control
   * - ``hjkl``
     - Vi-style navigation in corpus browser

**Control Actions:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``Enter`` / ``Space``
     - Select profile option
   * - ``+`` / ``=`` / ``j`` / ``↓``
     - Increment spinner/slider value
   * - ``-`` / ``_`` / ``k`` / ``↑``
     - Decrement spinner/slider value
   * - ``r``
     - Generate random seed (when seed input focused)

Keybinding Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

Keybindings are currently defined in the application code. Custom keybinding
configuration via TOML file is planned for a future release.

**Configuration Location (planned):**

``~/.config/pipeworks_tui/keybindings.toml``

**Current Defaults:**

The current keybindings are designed for keyboard efficiency with vi-style
navigation in the corpus browser and intuitive shortcuts for common actions.

**Note:** Keybindings use Textual's priority system, so global shortcuts like
``q`` and ``v`` work even when controls have focus.

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

Database Viewer
~~~~~~~~~~~~~~~

Press ``d`` to open the Database Viewer modal, which provides direct access
to the corpus SQLite database (``corpus.db``). This allows inspection of
syllables and their phonetic features.

**Features:**

- Paginated table view (50 rows per page)
- Column sorting (cycle with ``[``/``]``, toggle order with ``f``)
- Sort indicator shows active column and direction (↑/↓)
- Row details modal (press ``Enter`` on any row)

**Database Viewer Keybindings:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``j`` / ``k``
     - Navigate rows down/up
   * - ``Enter``
     - Show detailed feature breakdown for selected row
   * - ``[`` / ``]``
     - Cycle sort column (previous/next)
   * - ``f``
     - Toggle sort order (ascending/descending)
   * - ``h`` / ``←``
     - Previous page
   * - ``l`` / ``→``
     - Next page
   * - ``Home`` / ``End``
     - First/Last page
   * - ``Esc``
     - Close database viewer

**Row Details Modal:**

Pressing ``Enter`` on a row opens a detail modal showing:

- Syllable text and frequency
- All 12 phonetic features with full readable names
- Features grouped by category (Onset, Body, Coda)
- Visual indicators (● Yes / ○ No)

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

**Walk Steps vs Syllables:**

The "Walk Steps" parameter controls edge traversal, not output count. See
:ref:`Walk Structure <syllable_walk:Walk Structure>` in the Syllable Walker docs for the
invariant: *steps + 1 = syllables produced*. The TUI displays this dynamically
(e.g., ``[5] → 6 syl``).

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
