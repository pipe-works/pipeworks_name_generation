"""
Tabbed Content Module - Right-Side Multi-View Display

Provides tabbed views for Meta, Output, and Blended content.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Label, Static


class TabbedContentModule(Container):
    """
    Tabbed content widget for displaying Meta/Output/Blended views.

    Three tabs:
    - Meta (M): Corpus normalization metadata
    - Output (O): Generated words and walk details
    - Blended (B): Future blended corpus mode (placeholder)

    Phase 1 (MVP):
    - Keyboard shortcuts (M, O, B) to switch tabs
    - Meta tab shows normalization_meta.txt from active oscillator
    - Output tab shows generated words and walk details
    - Blended tab is placeholder

    Future:
    - Blended mode: generate from mixed corpora
    - Split view options
    - Export functionality per tab
    """

    DEFAULT_ID = "tabbed-content"

    def __init__(self, id: str = DEFAULT_ID):
        super().__init__(id=id)
        self.current_tab = "meta"  # Default to meta tab
        self.outputs: list[str] = []
        self.walks: list[dict] = []
        self.current_meta_path: Path | None = None

        # Store metadata content for both oscillators
        self.osc1_meta_content: str | None = None
        self.osc2_meta_content: str | None = None
        self.active_osc = 1  # Which oscillator metadata is currently displayed

    def compose(self) -> ComposeResult:
        """Create the tabbed content UI."""
        with Vertical():
            # Tab buttons
            with Horizontal(id="tab-buttons"):
                yield Button("Meta (M)", id="tab-meta", variant="primary", classes="tab-button")
                yield Button("Output (O)", id="tab-output", classes="tab-button")
                yield Button("Blended (B)", id="tab-blended", classes="tab-button")

            # Tab content containers (only one visible at a time)
            # Meta tab
            with Vertical(id="meta-content", classes="tab-content"):
                with Container(id="osc-selector"):
                    yield Label("┌──────┬──────┐", classes="osc-selector-header")
                    with Horizontal():
                        yield Button("OSC 1", id="meta-osc1", classes="osc-button active")
                        yield Button("OSC 2", id="meta-osc2", classes="osc-button")
                with VerticalScroll(id="meta-display", classes="meta-display"):
                    yield Label(
                        "Load a corpus in OSC 1 or OSC 2 to view metadata...",
                        classes="placeholder-text",
                    )

            # Output tab
            with Vertical(id="output-content", classes="tab-content"):
                # Generated words section
                yield Label("Generated Words", classes="section-header")
                with VerticalScroll(id="output-display", classes="output-display"):
                    yield Label("Click 'Generate' to create words...", classes="placeholder-text")

                yield Static("", classes="spacer-small")

                # Generation controls
                with Horizontal(classes="button-group"):
                    yield Button("Gen 1", id="gen-1", variant="primary")
                    yield Button("Gen 10", id="gen-10", variant="primary")
                    yield Button("Gen 100", id="gen-100")
                    yield Button("Clear", id="clear-output")

                yield Static("", classes="spacer-small")

                # Walk details section
                yield Label("Walk Details", classes="section-header")
                with VerticalScroll(id="walk-details-display", classes="walk-details-display"):
                    yield Label("Generate words to see walk details...", classes="placeholder-text")

            # Blended tab (placeholder)
            with Vertical(id="blended-content", classes="tab-content"):
                yield Label("BLENDED MODE", classes="module-header")
                yield Static("", classes="spacer")
                yield Label(
                    "Future Feature: Generate names by blending syllables from both oscillators.",
                    classes="placeholder-text",
                )
                yield Static("", classes="spacer")
                yield Label(
                    "This will allow cross-corpus phonetic walks and hybrid name generation.",
                    classes="placeholder-text",
                )
                yield Static("", classes="spacer")
                yield Label("⚠ Not implemented yet", classes="placeholder-warning")

    def on_mount(self) -> None:
        """Initialize tab visibility on mount."""
        self._show_tab("meta")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id

        # Tab switching
        if button_id == "tab-meta":
            self.switch_to_tab("meta")
        elif button_id == "tab-output":
            self.switch_to_tab("output")
        elif button_id == "tab-blended":
            self.switch_to_tab("blended")

        # Meta oscillator selector
        elif button_id == "meta-osc1":
            self._select_meta_osc(1)
        elif button_id == "meta-osc2":
            self._select_meta_osc(2)

        # Output generation
        elif button_id == "gen-1":
            self.post_message(self.GenerateRequest(1))
        elif button_id == "gen-10":
            self.post_message(self.GenerateRequest(10))
        elif button_id == "gen-100":
            self.post_message(self.GenerateRequest(100))
        elif button_id == "clear-output":
            self.clear_outputs()

    def switch_to_tab(self, tab_name: str):
        """Switch to the specified tab."""
        if tab_name not in ["meta", "output", "blended"]:
            return

        self.current_tab = tab_name
        self._show_tab(tab_name)

    def _show_tab(self, tab_name: str):
        """Show the specified tab content and update button styles."""
        # Hide all content
        self.query_one("#meta-content").display = False
        self.query_one("#output-content").display = False
        self.query_one("#blended-content").display = False

        # Show selected content
        if tab_name == "meta":
            self.query_one("#meta-content").display = True
        elif tab_name == "output":
            self.query_one("#output-content").display = True
        elif tab_name == "blended":
            self.query_one("#blended-content").display = True

        # Update button styles
        self.query_one("#tab-meta").variant = "primary" if tab_name == "meta" else "default"  # type: ignore[attr-defined]
        self.query_one("#tab-output").variant = "primary" if tab_name == "output" else "default"  # type: ignore[attr-defined]
        self.query_one("#tab-blended").variant = "primary" if tab_name == "blended" else "default"  # type: ignore[attr-defined]

    def _select_meta_osc(self, osc_num: int):
        """Select which oscillator's metadata to display."""
        # Update button styles
        osc1_btn = self.query_one("#meta-osc1")
        osc2_btn = self.query_one("#meta-osc2")

        if osc_num == 1:
            osc1_btn.add_class("active")
            osc2_btn.remove_class("active")
        else:
            osc2_btn.add_class("active")
            osc1_btn.remove_class("active")

        # Update active oscillator and display its metadata
        self.active_osc = osc_num
        self._display_active_osc_meta()

    # ===== META TAB METHODS =====

    def load_meta_file(self, corpus_directory: str, corpus_type: str, osc_num: int = 1):
        """
        Load and store normalization metadata for an oscillator.

        Args:
            corpus_directory: Directory containing the corpus files
            corpus_type: Type of corpus ("nltk" or "pyphen")
            osc_num: Which oscillator (1 or 2) this metadata belongs to
        """
        directory = Path(corpus_directory)
        meta_filename = f"{corpus_type}_normalization_meta.txt"
        meta_path = directory / meta_filename

        if not meta_path.exists():
            error_msg = f"Meta file not found: {meta_path}"
            if osc_num == 1:
                self.osc1_meta_content = f"⚠️  {error_msg}"
                self.active_osc = 1
            else:
                self.osc2_meta_content = f"⚠️  {error_msg}"
                self.active_osc = osc_num

            # Display the error immediately
            self._show_meta_error(error_msg)
            return

        try:
            with open(meta_path, encoding="utf-8") as f:
                content = f.read()

            # Store content for the appropriate oscillator
            if osc_num == 1:
                self.osc1_meta_content = content
                self.active_osc = 1
            else:
                self.osc2_meta_content = content
                self.active_osc = osc_num

            self.current_meta_path = meta_path

            # Display the metadata immediately
            self._display_meta(content)

        except Exception as e:
            error_msg = f"Error reading meta file: {e}"
            if osc_num == 1:
                self.osc1_meta_content = f"⚠️  {error_msg}"
                self.active_osc = 1
            else:
                self.osc2_meta_content = f"⚠️  {error_msg}"
                self.active_osc = osc_num

            # Display the error immediately
            self._show_meta_error(error_msg)

    def _display_active_osc_meta(self):
        """Display metadata for the currently active oscillator."""
        if self.active_osc == 1:
            if self.osc1_meta_content:
                if self.osc1_meta_content.startswith("⚠️"):
                    self._show_meta_error(self.osc1_meta_content[4:])  # Remove emoji
                else:
                    self._display_meta(self.osc1_meta_content)
            else:
                self._show_meta_error("No corpus loaded in OSC 1")
        else:
            if self.osc2_meta_content:
                if self.osc2_meta_content.startswith("⚠️"):
                    self._show_meta_error(self.osc2_meta_content[4:])  # Remove emoji
                else:
                    self._display_meta(self.osc2_meta_content)
            else:
                self._show_meta_error("No corpus loaded in OSC 2")

    def _display_meta(self, content: str):
        """Display metadata content in the scrollable area."""
        try:
            display = self.query_one("#meta-display", VerticalScroll)
            display.remove_children()

            # Split content into lines and display
            lines = content.splitlines()
            if not lines:
                display.mount(Label("(empty metadata file)", classes="placeholder-text"))
            else:
                for line in lines:
                    display.mount(Label(line, classes="meta-line"))

            # Scroll to top
            display.scroll_home(animate=False)
        except Exception:
            # If we can't find the display, just log the error
            pass

    def _show_meta_error(self, error_message: str):
        """Display an error message in the meta area."""
        try:
            display = self.query_one("#meta-display", VerticalScroll)
            display.remove_children()
            display.mount(Label(f"⚠️  {error_message}", classes="placeholder-warning"))
        except Exception:
            # If we can't find the display, just log the error
            pass

    def clear_meta(self):
        """Clear the metadata display."""
        self.current_meta_path = None
        display = self.query_one("#meta-display", VerticalScroll)
        display.remove_children()
        display.mount(
            Label("Load a corpus in OSC 1 or OSC 2 to view metadata...", classes="placeholder-text")
        )

    # ===== OUTPUT TAB METHODS =====

    def add_outputs(self, words: list[str]):
        """Add generated words to the output display."""
        self.outputs.extend(words)

        display = self.query_one("#output-display", VerticalScroll)

        # Clear placeholder if this is first output
        if len(self.outputs) == len(words):  # First batch
            display.remove_children()

        # Add new words
        for word in words:
            display.mount(Label(word, classes="output-word"))

        # Scroll to bottom
        display.scroll_end(animate=False)

    def clear_outputs(self):
        """Clear all outputs from display."""
        self.outputs = []
        display = self.query_one("#output-display", VerticalScroll)
        display.remove_children()
        display.mount(Label("Click 'Generate' to create words...", classes="placeholder-text"))

        # Also clear walk details
        self.clear_walks()

    def get_last_output(self) -> str | None:
        """Get the most recently generated word."""
        return self.outputs[-1] if self.outputs else None

    def add_walk_details(self, walk_data: dict):
        """
        Add detailed walk information to the display.

        Args:
            walk_data: Dictionary containing:
                - word: The collapsed word
                - steps: List of step dictionaries with syllable, features, distance
                - total_distance: Total phonetic distance traveled
                - seed: Random seed used
        """
        self.walks.append(walk_data)

        display = self.query_one("#walk-details-display", VerticalScroll)

        # Clear placeholder if this is first walk
        if len(self.walks) == 1:
            display.remove_children()

        # Add walk header
        word = walk_data.get("word", "???")
        total_distance = walk_data.get("total_distance", 0)
        seed = walk_data.get("seed", "unknown")

        display.mount(Label("", classes="walk-spacer"))
        display.mount(
            Label(
                f"━━━ {word} ━━━ (distance: {total_distance:.2f}, seed: {seed})",
                classes="walk-header",
            )
        )

        # Add each step
        steps = walk_data.get("steps", [])
        for i, step in enumerate(steps):
            syllable = step.get("syllable", "?")
            distance = step.get("distance", 0.0)
            flipped = step.get("flipped_features", [])

            # Step line
            step_text = f"  {i+1}. {syllable:<10} (d={distance:.2f})"
            display.mount(Label(step_text, classes="walk-step"))

            # Feature flips (if any)
            if flipped:
                flip_text = "     flips: " + ", ".join(flipped)
                display.mount(Label(flip_text, classes="walk-flips"))

        # Scroll to bottom to show latest walk
        display.scroll_end(animate=False)

    def clear_walks(self):
        """Clear all walk details from display."""
        self.walks = []
        display = self.query_one("#walk-details-display", VerticalScroll)
        display.remove_children()
        display.mount(Label("Generate words to see walk details...", classes="placeholder-text"))

    # ===== MESSAGES =====

    class GenerateRequest(Message):
        """Request to generate N words."""

        bubble = True

        def __init__(self, count: int) -> None:
            super().__init__()
            self.count = count
