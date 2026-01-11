"""
Syllable Walk TUI - Main Application

Eurorack-inspired terminal interface for phonetic space exploration.
"""

import random

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, LoadingIndicator, Static

from build_tools.syllable_walk_tui.config import TUIConfig
from build_tools.syllable_walk_tui.modules import (
    AttenuatorModule,
    ConditionsLogModule,
    EnvelopeModule,
    FilterModule,
    LFOModule,
    OscillatorModule,
    OutputModule,
    PatchCableModule,
)
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

    /* Module containers */
    .module {
        border: solid $primary;
        padding: 1 2;
        height: auto;
        min-height: 12;
    }

    .placeholder-module {
        border: dashed $secondary;
        padding: 1 2;
        opacity: 0.6;
    }

    .output-module {
        height: 20;
    }

    .log-module {
        height: 15;
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
        padding: 2;
    }

    .placeholder-warning {
        color: $warning;
        text-style: italic;
        text-align: center;
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

    /* Output display */
    .output-display {
        border: solid $primary-darken-2;
        height: 10;
        padding: 1;
    }

    .output-word {
        color: $text;
        padding: 0 1;
    }

    /* Log display */
    .log-display {
        border: solid $primary-darken-2;
        height: 8;
        padding: 1;
    }

    .log-entry {
        color: $accent;
        padding: 0;
    }

    .log-details {
        color: $text-muted;
        padding: 0 2;
    }

    /* Corpus browser */
    #corpus-browser {
        height: 18;
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

    #current-path {
        color: $accent;
    }

    /* Layout containers */
    .row-container {
        height: auto;
        padding: 0 1;
    }

    .col-third {
        width: 1fr;
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
        self.current_corpus_name: str | None = None

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

        self.BINDINGS = bindings

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        # App header
        yield Header(show_clock=False)
        yield Label("SYLLABLE WALK · PHONETIC RACK", classes="app-header")

        # Main content
        with Vertical():
            # Top row: Oscillator, Filter, Envelope
            with Horizontal(classes="row-container"):
                with Container(classes="col-third"):
                    # Pass initial directory from config
                    initial_dir = self.config.get_last_corpus_directory()
                    yield OscillatorModule(initial_directory=initial_dir)
                with Container(classes="col-third"):
                    yield FilterModule()
                with Container(classes="col-third"):
                    yield EnvelopeModule()

            # Middle row: LFO, Attenuator, Patch Cable
            with Horizontal(classes="row-container"):
                with Container(classes="col-third"):
                    yield LFOModule()
                with Container(classes="col-third"):
                    yield AttenuatorModule()
                with Container(classes="col-third"):
                    yield PatchCableModule()

            # Output section (full width)
            with Container(classes="row-container"):
                yield OutputModule()

            # Conditions log (full width)
            with Container(classes="row-container"):
                yield ConditionsLogModule()

        # Footer with keybindings
        yield Footer()

    def on_mount(self) -> None:
        """Initialize app state after mounting."""
        # Show welcome message with instructions
        self.notify(
            "Browse to a *_syllables_annotated.json file in the Oscillator, then click 'Load Selected'.",
            severity="information",
            timeout=8,
        )

    def on_oscillator_module_load_corpus(self, message: OscillatorModule.LoadCorpus) -> None:
        """Handle user selecting a corpus to load."""
        # Show loading screen and load corpus
        self.push_screen("loading")
        self.load_corpus_async(message.corpus_info)

    def on_oscillator_module_invalid_selection(
        self, message: OscillatorModule.InvalidSelection
    ) -> None:
        """Handle user selecting an invalid file."""
        self.notify(message.error_message, severity="warning")

    @work(exclusive=True, thread=True)
    async def load_corpus_async(self, corpus_info: dict):
        """Load the corpus in a background thread."""
        loading_screen = self.screen

        try:
            # Update status
            self.call_from_thread(loading_screen.update_status, f"Loading {corpus_info['name']}...")

            # Load controller (this is the slow part - JSON parsing)
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
            self.call_from_thread(self.finish_loading, corpus_info["name"], syllable_count)

        except Exception as e:
            self.call_from_thread(loading_screen.update_status, f"Error: {e}")
            import time

            time.sleep(2)
            self.call_from_thread(self.pop_screen)
            self.call_from_thread(self.notify, f"Failed to load corpus: {e}", severity="error")

    def finish_loading(self, corpus_name: str, syllable_count: int):
        """Finish loading and update UI (called from main thread)."""
        # Pop loading screen
        self.pop_screen()

        # Save to config
        corpus_info = self.controller.get_corpus_info()
        if corpus_info.get("loaded"):
            self.config.set_last_corpus(
                path=corpus_info["corpus_path"], corpus_type=corpus_info["corpus_type"]
            )

        # Update oscillator with corpus info
        self.current_corpus_name = corpus_name
        try:
            oscillator = self.query_one(OscillatorModule)
            oscillator.update_corpus_info(corpus_name, syllable_count)
            self.notify("Loaded successfully!", severity="information")
        except Exception as e:
            self.notify(f"Warning: Could not update oscillator info: {e}", severity="warning")

    def on_envelope_module_steps_changed(self, message: EnvelopeModule.StepsChanged) -> None:
        """Handle step count changes."""
        self.current_steps = message.steps

    def on_output_module_generate_request(self, message: OutputModule.GenerateRequest) -> None:
        """Handle word generation requests."""
        # Check if corpus is loaded
        if not self.controller.walker:
            self.notify(
                "No corpus loaded. Select one from the Oscillator first.", severity="warning"
            )
            return

        try:
            # Determine step count (handle random)
            steps = self.current_steps
            if steps == -1:  # Random
                steps = random.randint(3, 10)  # noqa: S311

            # Generate words
            words = self.controller.generate_words(
                count=message.count,
                steps=steps,
                temperature=1.0,  # Default for now
                frequency_weight=0.0,  # Default for now
                max_flips=2,  # Default for now
            )

            # Display outputs
            output = self.query_one(OutputModule)
            output.add_outputs(words)

        except Exception as e:
            self.notify(f"Error generating words: {e}", severity="error")

    def on_output_module_mark_interesting(self, message: OutputModule.MarkInteresting) -> None:
        """Handle marking current conditions as interesting."""
        # Check if corpus loaded
        if not self.controller.walker:
            self.notify("No corpus loaded yet!", severity="warning")
            return

        # Get last output
        output = self.query_one(OutputModule)
        last_word = output.get_last_output()

        # Log current conditions
        conditions = {
            "corpus": self.current_corpus_name or "unknown",
            "steps": self.current_steps,
            "temperature": 1.0,  # Will be dynamic later
            "frequency_weight": 0.0,  # Will be dynamic later
        }

        log = self.query_one(ConditionsLogModule)
        note = f'"{last_word}"' if last_word else "interesting conditions"
        log.add_log_entry(conditions, note)

        self.notify("Conditions logged!", severity="information")

    def action_generate_quick(self) -> None:
        """Keybinding: Generate 10 words quickly."""
        if not self.controller.walker:
            self.notify(
                "No corpus loaded. Select one from the Oscillator first.", severity="warning"
            )
            return
        output = self.query_one(OutputModule)
        output.post_message(OutputModule.GenerateRequest(10))

    def action_clear_output(self) -> None:
        """Keybinding: Clear output display."""
        output = self.query_one(OutputModule)
        output.clear_outputs()

    def action_help(self) -> None:
        """Keybinding: Show help."""
        self.notify(
            "Keybindings: [g]enerate 10, [c]lear, [q]uit | "
            "Philosophy: We patch conditions, not outputs.",
            severity="information",
            timeout=5,
        )


def main():
    """Entry point for the TUI application."""
    app = SyllableWalkApp()
    app.run()


if __name__ == "__main__":
    main()
