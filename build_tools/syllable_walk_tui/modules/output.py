"""
Output Module - Live Word Generation Display

Displays generated words and provides generation controls.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Label, Static


class OutputModule(Container):
    """
    Output widget for displaying generated words.

    Phase 1 (MVP):
    - Displays generated words in a scrollable list
    - Generate 1, 10, or 100 words
    - Clear output
    - Mark interesting (logs conditions)

    Future:
    - Copy to clipboard
    - Export list
    - Filter/search outputs
    """

    DEFAULT_ID = "output"

    def __init__(self, id: str = DEFAULT_ID):
        super().__init__(id=id)
        self.outputs: list[str] = []

    def compose(self) -> ComposeResult:
        """Create the output module UI."""
        with Vertical(classes="module output-module"):
            yield Label("OUTPUT", classes="module-header")
            yield Label("Collapsed Words / Names", classes="module-subtitle")
            yield Static("", classes="spacer-small")

            # Output display area (scrollable)
            with VerticalScroll(id="output-display", classes="output-display"):
                yield Label("Click 'Generate' to create words...", classes="placeholder-text")

            yield Static("", classes="spacer-small")

            # Generation controls
            with Horizontal(classes="button-group"):
                yield Button("Generate 1", id="gen-1", variant="primary")
                yield Button("Generate 10", id="gen-10", variant="primary")
                yield Button("Generate 100", id="gen-100")

            yield Static("", classes="spacer-small")

            # Action controls
            with Horizontal(classes="button-group"):
                yield Button("→ Interesting!", id="mark-interesting", variant="success")
                yield Button("Clear", id="clear-output")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id

        if button_id == "gen-1":
            self.post_message(self.GenerateRequest(1))
        elif button_id == "gen-10":
            self.post_message(self.GenerateRequest(10))
        elif button_id == "gen-100":
            self.post_message(self.GenerateRequest(100))
        elif button_id == "clear-output":
            self.clear_outputs()
        elif button_id == "mark-interesting":
            self.post_message(self.MarkInteresting())

    def add_outputs(self, words: list[str]):
        """Add generated words to the output display."""
        self.outputs.extend(words)

        # Update display
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

    def get_last_output(self) -> str | None:
        """Get the most recently generated word."""
        return self.outputs[-1] if self.outputs else None

    class GenerateRequest(Message):
        """Request to generate N words."""

        bubble = True  # Allow message to bubble up to app

        def __init__(self, count: int) -> None:
            super().__init__()
            self.count = count

    class MarkInteresting(Message):
        """Mark current conditions as interesting."""

        bubble = True  # Allow message to bubble up to app
