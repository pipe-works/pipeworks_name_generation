"""
Blended walk screen modal component.

This module provides the BlendedWalkScreen modal for viewing blended
walk results from both patches.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label


class BlendedWalkScreen(Screen):
    """
    Modal screen for viewing blended walk results.

    Displays generated syllable walks from both patches in a full-screen view.
    Provides detailed walk information and comparison.

    Keybindings:
        Esc: Close screen and return to main view
        j/k: Scroll through results
    """

    BINDINGS = [
        ("escape", "close_screen", "Close"),
    ]

    DEFAULT_CSS = """
    BlendedWalkScreen {
        background: $surface;
        border: solid $primary;
    }

    BlendedWalkScreen Label {
        margin: 1;
    }

    .walk-header {
        text-style: bold;
        color: $accent;
        margin-top: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create blended walk screen layout."""
        yield Label("BLENDED WALK RESULTS", classes="walk-header")
        yield Label("")
        yield Label("Patch A Walk:")
        yield Label("  (Generate to see results)")
        yield Label("")
        yield Label("Patch B Walk:")
        yield Label("  (Generate to see results)")
        yield Label("")
        yield Label("Comparison Analysis:")
        yield Label("  (Generate to see analysis)")
        yield Label("")
        yield Label("Press Esc to close")

    def action_close_screen(self) -> None:
        """Close this screen and return to main view."""
        self.app.pop_screen()
