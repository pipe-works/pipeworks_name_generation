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
   * - ``Ctrl+Q``
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
   * - ``w``
     - Open Terrain Weights editor (from Analysis screen)
   * - ``e``
     - Export metrics to text file (from Analysis screen)
   * - ``r``
     - Refresh pole exemplars (from Analysis screen)
   * - ``d``
     - Open Database Viewer for Patch A
   * - ``D`` (Shift+d)
     - Open Database Viewer for Patch B
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
   * - ``Space``
     - Toggle expand/collapse in browser
   * - ``Enter``
     - Select directory in browser
   * - ``>`` (Shift+.)
     - Toggle hidden files in browser
   * - ``Esc``
     - Cancel/close browser

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

Corpus Shape Analysis
~~~~~~~~~~~~~~~~~~~~~

Press ``a`` to open the Analysis modal screen, which displays raw corpus shape
metrics for both loaded patches side-by-side. This screen provides objective,
numerical data about corpus structure without interpretation.

**Design Philosophy:**

- Raw numbers only, no value judgments
- Observable facts about corpus structure
- Users draw their own conclusions through observation

**Metrics Displayed:**

*Inventory Metrics:*

- Total syllables, length min/max/mean/median/std
- Length distribution (count per character length)

*Frequency Metrics:*

- Total occurrences, frequency min/max/mean/median/std
- Percentiles (P10, P25, P50, P75, P90, P99)
- Unique frequency count, hapax count (frequency=1)
- Top 5 syllables by frequency

*Feature Saturation (per phonetic feature):*

- Count and percentage of syllables with each feature
- Grouped by category: Onset, Internal, Nucleus, Coda

*Terrain Visualization:*

Displayed alongside Feature Saturation, the Terrain visualization synthesizes
phonetic features into three phonaesthetic axes:

.. code-block:: text

   TERRAIN

     Shape: Round ↔ Jagged (Bouba/Kiki)
       ██████████████████░░░░░░░░░░░░ BALANCED +0.015
       round: mala, luno, anei    jagged: krask, thrix

     Craft: Flowing ↔ Worked (Sung/Forged)
       ███████████████████░░░░░░░░░░░ BALANCED +0.020
       flowing: lira, meno    worked: strunk, grak

     Space: Open ↔ Dense (Valley/Workshop)
       ██████████████░░░░░░░░░░░░░░░░ BALANCED -0.009
       open: aa, io, ele    dense: krist, blent

Each axis displays:

- **Hi-fi bar** (30 characters) showing position on the axis
- **Label** (ROUND, BALANCED, JAGGED, etc.) based on score thresholds
- **Delta** (+0.015, -0.009, etc.) showing deviation from neutral (0.5)
- **Pole exemplars** showing concrete syllables from each end of the axis

The pole exemplars help users understand what each phonaesthetic pole *sounds like*
by showing real syllables from the corpus that score at each extreme. Press ``r``
to refresh and see different exemplars sampled from the corpus.

The three axes represent:

- **Shape** (Round ↔ Jagged): The Bouba/Kiki dimension. Derived from plosives,
  stops, heavy clusters, and fricatives. High scores indicate angular,
  percussive sounds; low scores indicate soft, flowing sounds.

- **Craft** (Flowing ↔ Worked): The Sung/Forged dimension. Derived from liquids,
  nasals, and cluster density. High scores suggest "forged" names (worked,
  effortful); low scores suggest "sung" names (smooth, natural).

- **Space** (Open ↔ Dense): The Valley/Workshop dimension. Derived from vowel
  features and syllable length distribution. High scores indicate dense,
  compact syllables; low scores indicate open, expansive syllables.

Labels are assigned based on score thresholds:

- Score < 0.35: Low-end label (ROUND, FLOWING, OPEN)
- Score 0.35-0.65: BALANCED
- Score > 0.65: High-end label (JAGGED, WORKED, DENSE)

These visualizations help users understand the **phonaesthetic terrain** a
corpus inhabits - not prescribing how to use it, but describing what kind of
acoustic character it naturally supports.

**Terrain Weights Editor:**

Press ``w`` from the Analysis screen to open the Terrain Weights editor. This
modal allows you to adjust the weights used to calculate terrain scores for
each patch independently.

.. code-block:: text

   TERRAIN WEIGHTS
   ─── PATCH A ───
   Shape: liq:-0.8  nas:-0.6  v_end:-0.6  plo:+0.6  stop:+1.0  h_cl:+0.8  fri:+0.3
   Craft: v_end:-1.0  v_sta:-0.8  lg_v:-0.6  clus:+1.0  h_cl:+0.8  sh_v:+0.4
   Space: v_end:-1.0  v_sta:-0.8  lg_v:-0.6  sh_v:+0.6  stop:+0.6  n_end:+0.4

   ─── PATCH B ───
   ...

   [Tab] navigate  [j/k] adjust  [r] reset  [q] close

**Weights Editor Keybindings:**

- ``Tab`` / ``Shift+Tab``: Navigate between weights
- ``j`` / ``k``: Decrease / increase selected weight by 0.1
- ``r``: Reset current patch's weights to defaults
- ``q`` / ``Esc``: Close and apply changes

Each patch maintains independent weights, allowing you to compare how different
weight configurations affect terrain interpretation of the same corpus.

.. caution::
   **On Weight Tuning and "Forcing" Terrain Shape**

   The terrain weights system is designed to **describe** phonaesthetic reality,
   not to be tuned to produce desired results for specific corpora.

   **Why this matters:**

   If Patch A is 65% plosives and Patch B is 12%, the user should *feel* that
   difference. Generating "round" names from Patch A means **fighting upstream**;
   generating "jagged" names means **riding the current**. That tension *is* the
   experience.

   **Do NOT adjust weights to:**

   - Make a jagged corpus appear round
   - Force both patches to show the same terrain
   - Flatten differences between corpora

   **DO adjust weights when:**

   - Testing alternative phonaesthetic models
   - Calibrating for non-English corpora with different feature distributions
   - Exploring how specific features contribute to each axis
   - Validating that weights produce defensible phonaesthetic claims

   **The principle:** Each weight should have a defensible rationale independent
   of test outcomes. If test results seem "wrong", consider whether the
   phonaesthetic claim is actually correct, or whether other features are
   washing out the effect — not whether the weights need adjustment to make
   tests "look right".

   See ``_working/sfa_shapes_terrain_map.md`` for detailed calibration notes
   and the phonaesthetic rationale behind default weights.

**Why Corpus Shape Matters:**

Understanding corpus shape is essential for effective syllable walks:

- **Corpus size** describes how many syllables exist
- **Corpus shape** describes how those syllables are connected

A syllable walk never sees the entire corpus at once - it only sees a local
neighbourhood around the current syllable. Two corpora with different sizes
can behave identically if their local neighbourhoods are similar.

The metrics help you understand why walks feel different across corpora,
even with identical parameters.

Database Viewer
~~~~~~~~~~~~~~~

Press ``d`` to open the Database Viewer for Patch A, or ``D`` (Shift+d) for
Patch B. The modal provides direct access to the corpus SQLite database
(``corpus.db``), allowing inspection of syllables and their phonetic features.

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
the Walk Structure section in :doc:`syllable_walk` for the
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
