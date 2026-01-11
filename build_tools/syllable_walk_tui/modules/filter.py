"""
Filter Module - Feature-Based Syllable Filtering

Controls which syllables are allowed through based on features.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static


class FilterModule(Container):
    """
    Filter widget for feature selection.

    Phase 1 (MVP):
    - Placeholder only, not wired

    Future:
    - Min/max length filters
    - Feature preset buttons (soft, hard)
    - Clean vs raw toggle
    - Custom feature selection
    """

    DEFAULT_ID = "filter"

    def compose(self) -> ComposeResult:
        """Create the filter module UI."""
        with Vertical(classes="module placeholder-module"):
            yield Label("FILTER", classes="module-header")
            yield Label("Feature Selection", classes="module-subtitle")
            yield Static("", classes="spacer")

            yield Label("Min Length: [2]", classes="info-text placeholder")
            yield Label("Max Length: [∞]", classes="info-text placeholder")
            yield Static("", classes="spacer-small")

            yield Label("[Soft Features]", classes="info-text placeholder")
            yield Label("[Hard Features]", classes="info-text placeholder")
            yield Static("", classes="spacer-small")

            yield Label("[Clean] [Raw]", classes="info-text placeholder")

            yield Static("", classes="spacer")
            yield Label("⚠ Not wired yet", classes="placeholder-warning")
