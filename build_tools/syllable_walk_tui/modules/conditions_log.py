"""
Conditions Log Module - Patch Management and Discovery Journal

Records interesting conditions and manages saved patches.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Label, Static


class ConditionsLogModule(Container):
    """
    Conditions Log widget for patch management.

    Phase 1 (MVP):
    - Displays logged conditions
    - Save/load placeholder buttons

    Future:
    - JSON patch file management
    - Timestamped entries
    - Export log
    - Load patch to restore state
    """

    DEFAULT_ID = "conditions-log"

    def __init__(self, id: str = DEFAULT_ID):
        super().__init__(id=id)
        self.log_entries: list[dict] = []

    def compose(self) -> ComposeResult:
        """Create the conditions log module UI."""
        with Vertical(classes="module log-module"):
            yield Label("CONDITIONS LOG", classes="module-header")
            yield Label("Interesting Moments & Saved Patches", classes="module-subtitle")
            yield Static("", classes="spacer-small")

            # Log display area (scrollable)
            with VerticalScroll(id="log-display", classes="log-display"):
                yield Label("No conditions logged yet...", classes="placeholder-text")

            yield Static("", classes="spacer-small")

            # Action controls
            with Horizontal(classes="button-group"):
                yield Button("Save Patch", id="save-patch", disabled=True)
                yield Button("Load Patch", id="load-patch", disabled=True)

            yield Static("", classes="spacer-small")
            yield Label("⚠ Patch management not wired yet", classes="placeholder-warning")

    def add_log_entry(self, conditions: dict, note: str = ""):
        """Add a conditions entry to the log."""
        import datetime

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "conditions": conditions,
            "note": note,
        }
        self.log_entries.append(entry)

        # Update display
        display = self.query_one("#log-display", VerticalScroll)

        # Clear placeholder if this is first entry
        if len(self.log_entries) == 1:
            display.remove_children()

        # Format and add entry
        timestamp = datetime.datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M:%S")
        entry_text = f"{timestamp} → {note}" if note else f"{timestamp} → conditions logged"
        display.mount(Label(entry_text, classes="log-entry"))

        # Add condition details
        cond_text = ", ".join(f"{k}={v}" for k, v in conditions.items())
        display.mount(Label(f"  {cond_text}", classes="log-details"))

        # Scroll to bottom
        display.scroll_end(animate=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id

        if button_id == "save-patch":
            self.post_message(self.SavePatchRequest())
        elif button_id == "load-patch":
            self.post_message(self.LoadPatchRequest())

    class SavePatchRequest(Message):
        """Request to save current patch."""

        pass

    class LoadPatchRequest(Message):
        """Request to load a patch."""

        pass
