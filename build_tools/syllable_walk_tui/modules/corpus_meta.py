"""
Corpus Meta Module - Static Corpus Metadata Display

Displays normalization metadata from the corpus source files.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Label, Static


class CorpusMetaModule(Container):
    """
    Widget for displaying static corpus metadata.

    Displays the contents of *_normalization_meta.txt files that correspond
    to loaded corpus files. This provides provenance and statistics about
    the syllable extraction and normalization process.

    Phase 1 (MVP):
    - Display normalization metadata when corpus is loaded
    - Scrollable text area for long metadata files
    - Clear display when no corpus is loaded

    Future:
    - Syntax highlighting for metadata sections
    - Collapsible sections
    - Export metadata
    """

    DEFAULT_ID = "corpus-meta"

    def __init__(self, id: str = DEFAULT_ID):
        super().__init__(id=id)
        self.current_meta_path: Path | None = None

    def compose(self) -> ComposeResult:
        """Create the corpus meta module UI."""
        with Vertical(classes="module meta-module"):
            yield Label("CORPUS META", classes="module-header")
            yield Label("Source Provenance", classes="module-subtitle")
            yield Static("", classes="spacer-small")

            # Meta display area (scrollable)
            with VerticalScroll(id="meta-display", classes="meta-display"):
                yield Label("Load a corpus to view metadata...", classes="placeholder-text")

    def load_meta_file(self, corpus_directory: str, corpus_type: str):
        """
        Load and display the normalization metadata file.

        Args:
            corpus_directory: Directory containing the corpus files
            corpus_type: Type of corpus ("nltk" or "pyphen")
        """
        directory = Path(corpus_directory)

        # Construct meta file name based on corpus type
        meta_filename = f"{corpus_type}_normalization_meta.txt"
        meta_path = directory / meta_filename

        if not meta_path.exists():
            self._show_error(f"Meta file not found: {meta_filename}")
            return

        try:
            # Read the meta file
            with open(meta_path, encoding="utf-8") as f:
                content = f.read()

            # Update display
            self._display_meta(content)
            self.current_meta_path = meta_path

        except Exception as e:
            self._show_error(f"Error reading meta file: {e}")

    def _display_meta(self, content: str):
        """Display metadata content in the scrollable area."""
        display = self.query_one("#meta-display", VerticalScroll)
        display.remove_children()

        # Split content into lines and display
        for line in content.splitlines():
            display.mount(Label(line, classes="meta-line"))

        # Scroll to top
        display.scroll_home(animate=False)

    def _show_error(self, error_message: str):
        """Display an error message in the meta area."""
        display = self.query_one("#meta-display", VerticalScroll)
        display.remove_children()
        display.mount(Label(f"⚠️  {error_message}", classes="placeholder-warning"))

    def clear_meta(self):
        """Clear the metadata display."""
        self.current_meta_path = None
        display = self.query_one("#meta-display", VerticalScroll)
        display.remove_children()
        display.mount(Label("Load a corpus to view metadata...", classes="placeholder-text"))
