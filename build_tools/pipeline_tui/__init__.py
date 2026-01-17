"""
Pipeline Build Tools TUI - Interactive interface for syllable extraction pipelines.

This TUI provides a visual interface for running and monitoring the syllable
extraction, normalization, and annotation pipeline. It complements the
existing CLI tools without replacing them.

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

**Architecture:**

.. code-block:: text

    pipeline_tui/
    ├── __init__.py           # This file
    ├── __main__.py           # Entry point (python -m build_tools.pipeline_tui)
    ├── core/
    │   ├── app.py            # Main PipelineApp class
    │   └── state.py          # Application state management
    ├── screens/
    │   ├── config.py         # Pipeline configuration screen
    │   ├── monitor.py        # Job monitoring screen
    │   └── history.py        # Run history browser
    └── services/
        ├── pipeline.py       # Pipeline execution service
        └── validators.py     # Directory/file validators

**Usage:**

.. code-block:: bash

    # Launch the TUI
    python -m build_tools.pipeline_tui

    # With initial directory
    python -m build_tools.pipeline_tui --source ~/corpora

**Shared Components:**

This TUI uses shared components from ``build_tools.tui_common``:

- :class:`~build_tools.tui_common.controls.DirectoryBrowserScreen` - File browser
- :class:`~build_tools.tui_common.controls.IntSpinner` - Integer parameters
- :class:`~build_tools.tui_common.controls.RadioOption` - Option selection
- :class:`~build_tools.tui_common.services.KeybindingConfig` - Keybindings
"""

__version__ = "0.1.0"
