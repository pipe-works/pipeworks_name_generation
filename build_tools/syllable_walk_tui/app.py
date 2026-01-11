"""
Syllable Walk TUI - Main Application

Eurorack-inspired terminal interface for phonetic space exploration.
"""

import random
from typing import cast

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, LoadingIndicator, Static

from build_tools.syllable_walk_tui.config import TUIConfig
from build_tools.syllable_walk_tui.modules import OscillatorModule, TabbedContentModule
from build_tools.syllable_walk_tui.walk_controller import WalkController


class LoadingScreen(Screen):
    """Loading screen shown while corpus loads."""

    CSS = """
    LoadingScreen {
        align: center middle;
    }

    #loading-container {
        width: 60;
        height: 11;
        border: solid $primary;
        background: $surface;
        padding: 2;
    }

    #loading-title {
        text-align: center;
        text-style: bold;
        color: $accent;
    }

    #loading-status {
        text-align: center;
        color: $text;
        padding: 1 0;
    }

    #loading-spinner {
        height: 3;
    }

    #loading-note {
        text-align: center;
        color: $text-muted;
        text-style: italic;
        padding: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the loading screen."""
        with Container(id="loading-container"):
            yield Label("SYLLABLE WALK · INITIALIZING", id="loading-title")
            yield Static("", classes="spacer")
            yield Label("Loading phonetic corpus...", id="loading-status")
            yield Static("This may take a few seconds (parsing ~11-15MB JSON)", id="loading-note")
            yield LoadingIndicator(id="loading-spinner")

    def update_status(self, message: str):
        """Update the loading status message."""
        status = self.query_one("#loading-status", Label)
        status.update(message)


class SyllableWalkApp(App):
    """
    Main TUI application for syllable walk exploration.

    This app composes all eurorack-style modules and coordinates
    between the UI and the syllable walk backend.
    """

    CSS = """
    /* Global styles */
    Screen {
        background: $surface;
    }

    /* Header */
    .app-header {
        background: $primary;
        color: $text;
        text-align: center;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }

    /* Main layout: Two columns */
    #main-layout {
        height: 1fr;
        width: 100%;
    }

    #left-column {
        width: 50%;
        height: 1fr;
    }

    #right-column {
        width: 50%;
        height: 1fr;
        border-left: solid $primary;
    }

    /* Module containers */
    .module {
        border: solid $primary;
        padding: 1;
        height: auto;
        margin: 0;
    }

    .placeholder-module {
        border: dashed $secondary;
        padding: 1;
        opacity: 0.6;
    }

    /* Module headers */
    .module-header {
        text-style: bold;
        color: $accent;
    }

    .module-subtitle {
        text-style: italic;
        color: $text-muted;
    }

    /* Spacing */
    .spacer {
        height: 1;
    }

    .spacer-small {
        height: 0;
    }

    /* Text styles */
    .info-text {
        color: $text;
    }

    .placeholder {
        color: $text-muted;
        text-style: italic;
    }

    .placeholder-text {
        color: $text-disabled;
        text-style: italic;
        text-align: center;
        padding: 1;
    }

    .placeholder-warning {
        color: $warning;
        text-style: italic;
        text-align: center;
    }

    .section-header {
        text-style: bold;
        color: $accent;
        padding: 0 0 0 1;
    }

    /* Button groups */
    .button-group {
        height: auto;
        align: center middle;
    }

    .step-button {
        min-width: 8;
    }

    .step-button.active {
        background: $accent;
    }

    /* Tab buttons */
    #tab-buttons {
        height: 3;
        width: 100%;
        padding: 0 1;
    }

    .tab-button {
        min-width: 12;
    }

    .tab-content {
        height: 1fr;
        width: 100%;
        padding: 1;
    }

    #meta-content {
        height: 1fr;
    }

    #output-content {
        height: 1fr;
    }

    #blended-content {
        height: 1fr;
    }

    .osc-button {
        min-width: 8;
    }

    .osc-button.active {
        background: $accent;
    }

    #osc-selector {
        height: 5;
        padding: 0 1 1 1;
    }

    .osc-selector-header {
        color: $text-muted;
        text-align: center;
    }

    /* Output display */
    #output-display {
        border: solid $primary-darken-2;
        height: 20;
        padding: 1;
        overflow-y: auto;
    }

    .output-word {
        color: $text;
        padding: 0;
    }

    /* Corpus browser */
    ListView {
        height: 12;
        max-height: 15;
        border: solid $primary-darken-2;
        background: $surface;
    }

    .help-text {
        color: $text-muted;
        text-style: italic;
    }

    .json-file {
        color: $success;
        text-style: bold;
    }

    /* Meta display */
    #meta-display {
        border: solid $primary-darken-2;
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }

    .meta-line {
        color: $text;
        padding: 0;
    }

    /* Walk details display */
    #walk-details-display {
        border: solid $primary-darken-2;
        height: 15;
        padding: 1;
        overflow-y: auto;
    }

    .walk-spacer {
        height: 1;
    }

    .walk-header {
        color: $accent;
        text-style: bold;
        padding: 0;
    }

    .walk-step {
        color: $text;
        padding: 0;
    }

    .walk-flips {
        color: $text-muted;
        text-style: italic;
        padding: 0;
    }

    /* Footer */
    Footer {
        background: $primary-darken-2;
    }
    """

    SCREENS = {"loading": LoadingScreen}

    def __init__(self):
        super().__init__()
        self.config = TUIConfig()  # Load user config
        self.controller = WalkController()  # Initialize controller (no corpus loaded yet)
        self.current_steps = 5

        # Track both oscillators
        self.osc1_corpus_name: str | None = None
        self.osc1_corpus_info: dict | None = None
        self.osc2_corpus_name: str | None = None
        self.osc2_corpus_info: dict | None = None

        # Track which oscillator is active (1 or 2)
        self.active_oscillator = 1

        # Set up keybindings from config
        self._setup_keybindings()

    def _setup_keybindings(self):
        """Configure keybindings from user config."""
        keybindings = self.config.get_keybindings()

        # Build BINDINGS list dynamically
        binding_definitions = [
            ("quit", "Quit"),
            ("clear_output", "Clear Output"),
            ("generate_quick", "Generate 10"),
            ("switch_tab_meta", "Meta Tab (M)"),
            ("switch_tab_output", "Output Tab (O)"),
            ("switch_tab_blended", "Blended Tab (B)"),
            ("help", "Help"),
        ]

        bindings = []
        for action, description in binding_definitions:
            keys = keybindings.get(action, "")
            if keys:
                # Support multiple keys (comma-separated)
                for key in keys.split(","):
                    key = key.strip()
                    bindings.append((key, action, description))

        # Add default tab switching keys if not configured
        bindings.extend(
            [
                ("m", "switch_tab_meta", "Meta Tab (M)"),
                ("o", "switch_tab_output", "Output Tab (O)"),
                ("b", "switch_tab_blended", "Blended Tab (B)"),
            ]
        )

        self.BINDINGS = bindings  # type: ignore[assignment, misc]

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        # App header
        yield Header(show_clock=False)

        # Main content: Two-column layout
        with Horizontal(id="main-layout"):
            # LEFT COLUMN: Oscillators (~50% width)
            with Vertical(id="left-column"):
                # Oscillator 1
                initial_dir = self.config.get_last_corpus_directory()
                yield OscillatorModule(initial_directory=initial_dir, id="oscillator-1")

                # Oscillator 2
                yield OscillatorModule(initial_directory=initial_dir, id="oscillator-2")

            # RIGHT COLUMN: Tabbed content (~50% width)
            with Container(id="right-column"):
                yield TabbedContentModule()

        # Footer with keybindings
        yield Footer()

    def on_mount(self) -> None:
        """Initialize app state after mounting."""
        # Show welcome message with instructions
        self.notify(
            "Browse to *_syllables_annotated.json files in OSC 1 or OSC 2, then select to load.",
            severity="information",
            timeout=8,
        )

        # Update oscillator titles
        try:
            osc1 = self.query_one("#oscillator-1", OscillatorModule)
            osc1.set_title("Oscillator 1 - Syllable")
            osc2 = self.query_one("#oscillator-2", OscillatorModule)
            osc2.set_title("Oscillator 2 - Syllable")
        except Exception:
            pass  # Modules may not be mounted yet

    def on_oscillator_module_load_corpus(self, message: OscillatorModule.LoadCorpus) -> None:
        """Handle user selecting a corpus to load."""
        # Determine which oscillator is requesting the load
        osc_id = message.oscillator_id or "oscillator-1"
        osc_num = 1 if "1" in osc_id else 2

        # Store corpus info for the appropriate oscillator
        if osc_num == 1:
            self.osc1_corpus_info = message.corpus_info
        else:
            self.osc2_corpus_info = message.corpus_info

        # Show loading screen and load corpus
        self.push_screen("loading")
        self.load_corpus_async(message.corpus_info, osc_num)

    def on_oscillator_module_invalid_selection(
        self, message: OscillatorModule.InvalidSelection
    ) -> None:
        """Handle user selecting an invalid file."""
        self.notify(message.error_message, severity="warning")

    @work(exclusive=True, thread=True)
    async def load_corpus_async(self, corpus_info: dict, osc_num: int):
        """Load the corpus in a background thread."""
        loading_screen = cast(LoadingScreen, self.screen)

        try:
            # Update status
            self.call_from_thread(
                loading_screen.update_status, f"Loading OSC {osc_num}: {corpus_info['name']}..."
            )

            # Load controller (this is the slow part - JSON parsing)
            # For now, we only use the active oscillator's corpus
            # Future: support switching between loaded corpora
            self.controller.load_corpus(
                corpus_path=corpus_info["path"], corpus_type=corpus_info["type"]
            )

            # Update status
            info = self.controller.get_corpus_info()
            syllable_count = info.get("syllable_count", 0)
            self.call_from_thread(
                loading_screen.update_status,
                f"Loaded {syllable_count:,} syllables. Building neighbor graph...",
            )

            # Small delay to show final status
            import time

            time.sleep(0.5)

            # Update UI and dismiss loading screen
            self.call_from_thread(self.finish_loading, corpus_info["name"], syllable_count, osc_num)

        except Exception as e:
            self.call_from_thread(loading_screen.update_status, f"Error: {e}")
            import time

            time.sleep(2)
            self.call_from_thread(self.pop_screen)
            self.call_from_thread(self.notify, f"Failed to load corpus: {e}", severity="error")

    def finish_loading(self, corpus_name: str, syllable_count: int, osc_num: int):
        """Finish loading and update UI (called from main thread)."""
        # Pop loading screen
        self.pop_screen()

        # Save to config
        corpus_info = self.controller.get_corpus_info()
        if corpus_info.get("loaded"):
            self.config.set_last_corpus(
                path=corpus_info["corpus_path"], corpus_type=corpus_info["corpus_type"]
            )

        # Update corpus names
        if osc_num == 1:
            self.osc1_corpus_name = corpus_name
            self.active_oscillator = 1
        else:
            self.osc2_corpus_name = corpus_name
            self.active_oscillator = osc_num

        # Update oscillator with corpus info
        try:
            osc_id = f"oscillator-{osc_num}"
            oscillator = self.query_one(f"#{osc_id}", OscillatorModule)
            oscillator.update_corpus_info(corpus_name, syllable_count)
            self.notify(f"OSC {osc_num} loaded successfully!", severity="information")
        except Exception as e:
            self.notify(f"Warning: Could not update oscillator info: {e}", severity="warning")

        # Load corpus metadata into TabbedContentModule
        corpus_info_data = self.osc1_corpus_info if osc_num == 1 else self.osc2_corpus_info
        if corpus_info_data:
            try:
                tabbed = self.query_one(TabbedContentModule)
                # Switch to meta tab FIRST to ensure it's visible
                tabbed.switch_to_tab("meta")
                # Then load the metadata
                tabbed.load_meta_file(
                    corpus_directory=corpus_info_data["directory"],
                    corpus_type=corpus_info_data["type"],
                    osc_num=osc_num,  # Pass which oscillator this is for
                )
            except Exception as e:
                self.notify(f"Warning: Could not load corpus metadata: {e}", severity="error")

    def on_tabbed_content_module_generate_request(
        self, message: TabbedContentModule.GenerateRequest
    ) -> None:
        """Handle word generation requests from TabbedContentModule."""
        # Check if corpus is loaded
        if not self.controller.walker:
            self.notify(
                "No corpus loaded. Select one from OSC 1 or OSC 2 first.", severity="warning"
            )
            return

        try:
            # Determine step count (handle random)
            steps = self.current_steps
            if steps == -1:  # Random
                steps = random.randint(3, 10)  # noqa: S311

            # Generate words with detailed walk information
            results = self.controller.generate_words_with_details(
                count=message.count,
                steps=steps,
                temperature=1.0,  # Default for now
                frequency_weight=0.0,  # Default for now
                max_flips=2,  # Default for now
            )

            # Extract words for output display
            words = [result["word"] for result in results]

            # Display word outputs in TabbedContentModule
            tabbed = self.query_one(TabbedContentModule)
            tabbed.add_outputs(words)

            # Display walk details (only show last walk to avoid flooding)
            if results:
                # Show only the last walk generated
                tabbed.add_walk_details(results[-1])

            # Switch to output tab to show results
            tabbed.switch_to_tab("output")

        except Exception as e:
            self.notify(f"Error generating words: {e}", severity="error")

    def action_generate_quick(self) -> None:
        """Keybinding: Generate 10 words quickly."""
        if not self.controller.walker:
            self.notify(
                "No corpus loaded. Select one from OSC 1 or OSC 2 first.", severity="warning"
            )
            return
        tabbed = self.query_one(TabbedContentModule)
        tabbed.post_message(TabbedContentModule.GenerateRequest(10))

    def action_clear_output(self) -> None:
        """Keybinding: Clear output display and walk details."""
        tabbed = self.query_one(TabbedContentModule)
        tabbed.clear_outputs()

    def action_switch_tab_meta(self) -> None:
        """Keybinding: Switch to Meta tab."""
        tabbed = self.query_one(TabbedContentModule)
        tabbed.switch_to_tab("meta")

    def action_switch_tab_output(self) -> None:
        """Keybinding: Switch to Output tab."""
        tabbed = self.query_one(TabbedContentModule)
        tabbed.switch_to_tab("output")

    def action_switch_tab_blended(self) -> None:
        """Keybinding: Switch to Blended tab."""
        tabbed = self.query_one(TabbedContentModule)
        tabbed.switch_to_tab("blended")

    def action_help(self) -> None:
        """Keybinding: Show help."""
        self.notify(
            "Keys: [g]enerate 10, [c]lear, [m]eta tab, [o]output tab, [b]lended tab, [q]uit",
            severity="information",
            timeout=5,
        )


def main():
    """Entry point for the TUI application."""
    app = SyllableWalkApp()
    app.run()


if __name__ == "__main__":
    main()
