"""
Oscillator Module - Syllable Inventory Selection

Controls the raw phonetic material (timbre) by selecting which corpus to use.
"""

from pathlib import Path

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, ListItem, ListView, LoadingIndicator, Static


class OscillatorModule(Container):
    """
    Oscillator widget for corpus selection.

    Phase 1 (MVP):
    - File browser to navigate to corpus files
    - ".." for parent directory (ranger-style)
    - Shows current corpus info

    Future:
    - Quick bookmarks for common corpus locations
    - Recently used corpus list
    - Corpus metadata preview
    """

    DEFAULT_ID = "oscillator"

    def __init__(self, initial_directory: str, id: str = DEFAULT_ID):
        """
        Initialize the oscillator module.

        Args:
            initial_directory: Starting directory for file browser
            id: Widget ID
        """
        super().__init__(id=id)
        self.current_corpus_name: str | None = None
        self.title = "OSCILLATOR"  # Default title

        # Resolve to absolute path and validate it exists
        initial_path = Path(initial_directory).resolve()

        # If it's a file, use its parent directory
        if initial_path.is_file():
            initial_path = initial_path.parent

        # If the directory doesn't exist, walk up to find the first valid parent
        while not initial_path.exists() and initial_path != initial_path.parent:
            initial_path = initial_path.parent

        self.current_directory = initial_path
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        """Create the oscillator module UI."""
        with Vertical(classes="module"):
            yield Label(self.title, id=f"{self.id}-header", classes="module-header")
            yield Label("Syllable Inventory", classes="module-subtitle")
            yield Static("", classes="spacer-small")

            # Corpus info display (shows current or "none loaded")
            yield Label("Corpus: None loaded", id=f"{self.id}-corpus-info", classes="info-text")
            yield Label("Syllables: ---", id=f"{self.id}-syllable-count", classes="info-text")

            yield Static("", classes="spacer-small")

            # Current directory display
            yield Label(
                f"Path: {self.current_directory}", id=f"{self.id}-current-path", classes="info-text"
            )

            # Instructions
            yield Label("hjkl/arrows=navigate Enter/l=load h=parent", classes="help-text")

            yield Static("", classes="spacer-small")

            # File browser list
            yield ListView(id=f"{self.id}-corpus-browser")
            yield LoadingIndicator(id=f"{self.id}-browser-loading")

            yield Static("", classes="spacer-small")

            # Load button
            with Horizontal(classes="button-group"):
                yield Button("Load", id=f"{self.id}-load-corpus-btn", variant="primary")

    def on_mount(self) -> None:
        """After mounting, populate file browser and hide loading indicator."""
        loading = self.query_one(f"#{self.id}-browser-loading", LoadingIndicator)
        loading.display = False
        self._populate_browser()

    def on_key(self, event: events.Key) -> None:
        """Handle vim-style navigation keys for the file browser."""
        browser = self.query_one(f"#{self.id}-corpus-browser", ListView)

        if event.key == "j":
            # Move down
            browser.action_cursor_down()
            event.prevent_default()
        elif event.key == "k":
            # Move up
            browser.action_cursor_up()
            event.prevent_default()
        elif event.key == "l" or event.key == "enter":
            # Select/enter
            if browser.highlighted_child:
                browser.action_select_cursor()
                event.prevent_default()
        elif event.key == "h":
            # Go to parent directory
            if self.current_directory.parent != self.current_directory:
                self.current_directory = self.current_directory.parent
                self.selected_path = None
                self._populate_browser()
                event.prevent_default()

    def _populate_browser(self):
        """
        Populate the file browser with current directory contents.

        Shows a loading indicator for busy directories.
        """
        browser = self.query_one(f"#{self.id}-corpus-browser", ListView)
        loading = self.query_one(f"#{self.id}-browser-loading", LoadingIndicator)

        # Show loading indicator
        loading.display = True
        browser.display = False

        # Clear and rebuild
        browser.clear()

        # Update path display
        path_label = self.query_one(f"#{self.id}-current-path", Label)
        try:
            rel_path = self.current_directory.relative_to(Path.cwd())
            path_label.update(f"Path: {rel_path if rel_path != Path('.') else '.'}")
        except ValueError:
            path_label.update(f"Path: {self.current_directory}")

        # Add ".." parent directory entry if not at filesystem root
        if self.current_directory.parent != self.current_directory:
            item = ListItem(Label("📁 ../"))
            item.user_data = {"type": "parent", "path": self.current_directory.parent}  # type: ignore[attr-defined]
            browser.append(item)

        # Get directory contents
        try:
            entries = []

            # Separate directories and files
            for path_item in self.current_directory.iterdir():
                if path_item.is_dir():
                    entries.append((path_item.name, path_item, True))
                elif path_item.is_file():
                    entries.append((path_item.name, path_item, False))

            # Sort: directories first, then files, both alphabetically
            entries.sort(key=lambda x: (not x[2], x[0].lower()))

            # Add to list
            for name, path, is_dir in entries:
                if is_dir:
                    list_item = ListItem(Label(f"📁 {name}/"))
                    list_item.user_data = {"type": "dir", "path": path}  # type: ignore[attr-defined]
                    browser.append(list_item)
                else:
                    # Highlight annotated JSON files
                    if name.endswith("_syllables_annotated.json"):
                        list_item = ListItem(Label(f"✓ {name}", classes="json-file"))
                    else:
                        list_item = ListItem(Label(f"  {name}"))
                    list_item.user_data = {"type": "file", "path": path}  # type: ignore[attr-defined]
                    browser.append(list_item)

        except PermissionError:
            browser.append(ListItem(Label("⚠️  Permission denied")))
        except Exception as e:
            browser.append(ListItem(Label(f"⚠️  Error: {e}")))

        # Hide loading indicator and show browser
        loading.display = False
        browser.display = True

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle file/directory selection."""
        if not event.item or not hasattr(event.item, "user_data"):
            return

        data = event.item.user_data
        item_type = data.get("type")
        path = data.get("path")

        if not path:
            return

        # Handle parent directory navigation
        if item_type == "parent":
            self.current_directory = path
            self.selected_path = None
            self._populate_browser()
            return

        # Handle directory navigation
        if item_type == "dir":
            self.current_directory = path
            self.selected_path = None
            self._populate_browser()
            return

        # Handle file selection
        if item_type == "file":
            self.selected_path = path

            # If it's a valid corpus file, automatically trigger load
            if path.is_file() and path.name.endswith("_syllables_annotated.json"):
                self._trigger_load()

    def _trigger_load(self):
        """Trigger the corpus load action (called by button or keyboard)."""
        if not self.selected_path:
            self.post_message(self.InvalidSelection("No file selected"))
            return

        # Check if it's an annotated JSON file
        if self.selected_path.is_file() and self.selected_path.name.endswith(
            "_syllables_annotated.json"
        ):
            # Infer corpus type from filename
            if "pyphen" in self.selected_path.name:
                corpus_type = "pyphen"
            elif "nltk" in self.selected_path.name:
                corpus_type = "nltk"
            else:
                corpus_type = "unknown"

            corpus_info = {
                "name": self.selected_path.name,
                "path": str(self.selected_path),
                "type": corpus_type,
                "directory": str(self.selected_path.parent.parent),  # Run dir, not data/ subdir
            }

            self.post_message(self.LoadCorpus(corpus_info, self.id))
        else:
            self.post_message(
                self.InvalidSelection("Please select a *_syllables_annotated.json file")
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle load button click."""
        if event.button.id == f"{self.id}-load-corpus-btn":
            self._trigger_load()

    def set_title(self, title: str):
        """Set the oscillator title."""
        self.title = title
        try:
            header = self.query_one(f"#{self.id}-header", Label)
            header.update(title)
        except Exception:
            pass  # Header may not be mounted yet

    def update_corpus_info(self, corpus_name: str, syllable_count: int):
        """
        Update the current corpus info display.

        Args:
            corpus_name: Display name of the loaded corpus
            syllable_count: Number of syllables in corpus
        """
        self.current_corpus_name = corpus_name

        info_label = self.query_one(f"#{self.id}-corpus-info", Label)
        info_label.update(f"Corpus: {Path(corpus_name).name}")

        count_label = self.query_one(f"#{self.id}-syllable-count", Label)
        count_label.update(f"Syllables: {syllable_count:,}")

    class LoadCorpus(Message):
        """Message posted when user selects a corpus to load."""

        bubble = True

        def __init__(self, corpus_info: dict, oscillator_id: str | None = None) -> None:
            super().__init__()
            self.corpus_info = corpus_info
            self.oscillator_id = oscillator_id

    class InvalidSelection(Message):
        """Message posted when user selects an invalid file."""

        bubble = True

        def __init__(self, error_message: str) -> None:
            super().__init__()
            self.error_message = error_message
