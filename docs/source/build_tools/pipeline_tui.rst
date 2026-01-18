=========================
Pipeline TUI
=========================

.. currentmodule:: build_tools.pipeline_tui

Overview
--------

.. automodule:: build_tools.pipeline_tui
   :no-members:

The Pipeline TUI is an interactive terminal user interface for running and monitoring
the syllable extraction pipeline. Built with `Textual <https://textual.textualize.io/>`_,
it provides a visual interface for configuring and executing extraction, normalization,
and annotation workflows.

**Key Features:**

- **Source Selection**: Browse and select input text files/directories
- **Extractor Configuration**: Choose pyphen or NLTK extractor with options
- **Pipeline Execution**: Run extraction, normalization, annotation in sequence
- **Job Monitoring**: Watch progress, view logs, inspect outputs
- **Run History**: Browse previous pipeline runs from corpus_db

**Relationship to CLI Tools:**

This TUI wraps the existing CLI tools and does not replace them:

- ``build_tools.pyphen_syllable_extractor`` - Pyphen extraction
- ``build_tools.nltk_syllable_extractor`` - NLTK extraction
- ``build_tools.pyphen_syllable_normaliser`` - Pyphen normalization
- ``build_tools.nltk_syllable_normaliser`` - NLTK normalization
- ``build_tools.syllable_feature_annotator`` - Feature annotation

Command-Line Interface
----------------------

.. code-block:: bash

    # Launch the TUI
    python -m build_tools.pipeline_tui

    # Start with a specific source directory
    python -m build_tools.pipeline_tui --source ~/corpora/english

    # Start with a specific output directory
    python -m build_tools.pipeline_tui --output _working/output

**Options:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``--source PATH``
     - Initial source directory for input files
   * - ``--output PATH``
     - Initial output directory for results (default: ``_working/output``)
   * - ``--theme NAME``
     - Color theme (nord, dracula, monokai, textual-dark, textual-light)

Interface Overview
------------------

The TUI uses a tabbed interface with three main screens:

Configure Tab
~~~~~~~~~~~~~

Set up extraction parameters:

- Source directory selection (``d`` key)
- Individual file selection (``f`` key)
- Output directory selection (``o`` key)
- Extractor type (pyphen/NLTK)
- Language selection (for pyphen)
- Syllable length constraints
- Pipeline stage toggles (normalize, annotate)

Monitor Tab
~~~~~~~~~~~

Watch job progress and logs:

- Job status indicator
- Progress bar
- Current stage display
- Log output area
- Cancel button

History Tab
~~~~~~~~~~~

Browse previous pipeline runs:

- List of runs from corpus_db
- Run details panel
- Output file browser
- Re-run capability

Keyboard Shortcuts
------------------

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
     - Switch to Configure tab
   * - ``2``
     - Switch to Monitor tab
   * - ``3``
     - Switch to History tab
   * - ``d``
     - Select source directory
   * - ``f``
     - Select individual source files
   * - ``o``
     - Select output directory
   * - ``r``
     - Run pipeline
   * - ``c``
     - Cancel running job

**Directory Browser:**

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key(s)
     - Action
   * - ``j`` / ``↓``
     - Move down
   * - ``k`` / ``↑``
     - Move up
   * - ``h`` / ``←``
     - Collapse directory
   * - ``l`` / ``→``
     - Expand directory
   * - ``Space``
     - Toggle expand/collapse
   * - ``Enter``
     - Select directory
   * - ``Esc``
     - Cancel selection

Integration Guide
-----------------

Typical Workflow
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # 1. Launch the TUI
    python -m build_tools.pipeline_tui

    # 2. Select source directory (press 's')
    #    Navigate to directory containing .txt files

    # 3. Select output directory (press 'o')
    #    Choose where results will be saved

    # 4. Configure extraction options
    #    Select extractor type, language, etc.

    # 5. Run pipeline (press 'r')
    #    Monitor progress in Monitor tab

    # 6. View results
    #    Browse output in History tab

When to Use
~~~~~~~~~~~

**Use the Pipeline TUI when:**

- You want a visual interface for pipeline configuration
- You need to monitor job progress in real-time
- You're exploring different extraction options
- You want to browse previous runs and their outputs

**Use the CLI tools when:**

- You're scripting automated pipelines
- You need batch processing
- You want precise control over individual steps
- You're integrating with other tools

Architecture
------------

.. code-block:: text

    pipeline_tui/
    ├── __init__.py           # Package entry point
    ├── __main__.py           # CLI entry point
    ├── core/
    │   ├── app.py            # Main PipelineTuiApp class
    │   └── state.py          # Application state management
    ├── screens/
    │   ├── __init__.py       # Screen exports
    │   └── configure.py      # ConfigurePanel widget
    └── services/
        ├── __init__.py
        └── validators.py     # Directory validation functions

**State Management:**

- ``PipelineState``: Top-level application state
- ``ExtractionConfig``: Extractor settings (type, language, constraints)
- ``JobState``: Current job execution status

**Shared Components:**

Uses ``build_tools.tui_common`` for:

- ``DirectoryBrowserScreen``: File browser modal
- ``IntSpinner``, ``FloatSlider``: Parameter controls
- ``RadioOption``: Selection widgets
- ``KeybindingConfig``: Keybinding management

Notes
-----

**Current Status:**

The Pipeline TUI has a working Configure tab with full settings UI.
Monitor and History tabs are placeholders. Pipeline execution is planned for a future release.

**Dependencies:**

Requires Textual library:

.. code-block:: bash

    pip install -r requirements-dev.txt

**Python Version:**

Requires Python 3.12+.

**Related Documentation:**

- :doc:`tui_common` - Shared TUI components used by this tool
- :doc:`syllable_walk_tui` - Interactive phonetic exploration TUI
- :doc:`pyphen_syllable_extractor` - Pyphen extraction CLI
- :doc:`nltk_syllable_extractor` - NLTK extraction CLI

API Reference
-------------

Core
~~~~

.. automodule:: build_tools.pipeline_tui.core
   :members:
   :undoc-members:
   :show-inheritance:

Services
~~~~~~~~

.. automodule:: build_tools.pipeline_tui.services
   :members:
   :undoc-members:
   :show-inheritance:
