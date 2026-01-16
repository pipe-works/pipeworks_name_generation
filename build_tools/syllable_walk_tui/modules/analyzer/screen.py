"""
Analysis screen modal component.

This module provides the AnalysisScreen modal for viewing statistical analysis
of generated syllables.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label


class AnalysisScreen(Screen):
    """
    Modal screen for viewing statistical analysis.

    Displays detailed phonetic analysis, frequency distributions,
    and comparative statistics between patches.

    Keybindings:
        Esc: Close screen and return to main view
        j/k: Scroll through results
    """

    BINDINGS = [
        ("escape", "close_screen", "Close"),
    ]

    DEFAULT_CSS = """
    AnalysisScreen {
        background: $surface;
        border: solid $primary;
    }

    AnalysisScreen Label {
        margin: 1;
    }

    .analysis-header {
        text-style: bold;
        color: $accent;
        margin-top: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create analysis screen layout."""
        yield Label("STATISTICAL ANALYSIS", classes="analysis-header")
        yield Label("")
        yield Label("Phonetic Feature Distribution:")
        yield Label("  (Generate to see analysis)")
        yield Label("")
        yield Label("Frequency Analysis:")
        yield Label("  (Generate to see analysis)")
        yield Label("")
        yield Label("Walk Characteristics:")
        yield Label("  (Generate to see analysis)")
        yield Label("")
        yield Label("Press Esc to close")

    def action_close_screen(self) -> None:
        """Close this screen and return to main view."""
        self.app.pop_screen()
