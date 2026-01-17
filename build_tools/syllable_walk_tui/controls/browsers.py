"""
Corpus browser modal widget for Syllable Walker TUI.

This module provides the CorpusBrowserScreen modal for selecting corpus
directories. It wraps the shared DirectoryBrowserScreen from tui_common
with corpus-specific validation.

**Migration Note:**

This module now uses the shared DirectoryBrowserScreen from tui_common.
The CorpusBrowserScreen is a convenience wrapper that pre-configures
the browser with corpus validation.

For custom directory browsers, use DirectoryBrowserScreen directly:

.. code-block:: python

    from build_tools.tui_common.controls import DirectoryBrowserScreen

    result = await app.push_screen_wait(
        DirectoryBrowserScreen(
            title="Select Directory",
            validator=my_validator,
        )
    )
"""

from __future__ import annotations

from pathlib import Path

from build_tools.syllable_walk_tui.services.corpus import validate_corpus_directory
from build_tools.tui_common.controls import DirectoryBrowserScreen


class CorpusBrowserScreen(DirectoryBrowserScreen):
    """
    Modal screen for browsing and selecting a corpus directory.

    This is a convenience wrapper around DirectoryBrowserScreen that
    pre-configures it for corpus selection with appropriate validation.

    A valid corpus directory contains either NLTK or pyphen normalized output:

    - NLTK corpus: ``nltk_syllables_unique.txt`` + ``nltk_syllables_frequencies.json``
    - Pyphen corpus: ``pyphen_syllables_unique.txt`` + ``pyphen_syllables_frequencies.json``

    Returns:
        Selected Path when "Select" is pressed, or None if cancelled

    Example:
        .. code-block:: python

            result = await self.app.push_screen_wait(
                CorpusBrowserScreen(initial_dir=Path.home() / "corpora")
            )
            if result:
                self.load_corpus(result)
    """

    # CSS must be redeclared for subclass - Textual CSS selectors are class-name specific
    CSS = """
    CorpusBrowserScreen {
        align: center middle;
    }

    #browser-container {
        width: 80;
        height: 30;
        background: $panel;
        border: thick $primary;
        padding: 1;
    }

    #browser-header {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #directory-tree {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }

    #help-text {
        height: 2;
        width: 100%;
        color: $text-muted;
        text-align: center;
        margin-bottom: 1;
    }

    #validation-status {
        height: 3;
        width: 100%;
        border: solid $primary;
        padding: 0 1;
        margin-bottom: 1;
    }

    .status-valid {
        color: $success;
    }

    .status-invalid {
        color: $error;
    }

    .status-none {
        color: $text-muted;
    }

    #button-bar {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #button-bar Button {
        margin: 0 1;
    }
    """

    def __init__(self, initial_dir: Path | None = None) -> None:
        """
        Initialize corpus browser with corpus validation.

        Args:
            initial_dir: Starting directory for browser (defaults to home directory)
        """
        super().__init__(
            title="Select Corpus Directory",
            validator=validate_corpus_directory,
            initial_dir=initial_dir,
            help_text="Navigate with hjkl/arrows. Select the DIRECTORY (not files inside it).",
        )
