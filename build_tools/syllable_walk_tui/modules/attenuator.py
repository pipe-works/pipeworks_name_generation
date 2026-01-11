"""
Attenuator Module - Sampling Limits and Restraint

Controls how much of the phonetic space influences each step.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static


class AttenuatorModule(Container):
    """
    Attenuator widget for sampling limits.

    Phase 1 (MVP):
    - Placeholder only, not wired

    Future:
    - Top-N neighbor limits
    - Fan-out restrictions
    - Decay over time
    - Progressive attenuation curves
    """

    DEFAULT_ID = "attenuator"

    def compose(self) -> ComposeResult:
        """Create the attenuator module UI."""
        with Vertical(classes="module placeholder-module"):
            yield Label("ATTENUATOR", classes="module-header")
            yield Label("Sampling Limits", classes="module-subtitle")
            yield Static("", classes="spacer")

            yield Label("Top-N: [∞]", classes="info-text placeholder")
            yield Label("[10][20][50]", classes="info-text placeholder")
            yield Static("", classes="spacer-small")

            yield Label("Fan-out: [∞]", classes="info-text placeholder")
            yield Label("[5][10][20]", classes="info-text placeholder")
            yield Static("", classes="spacer-small")

            yield Label("[Decay Over Time]", classes="info-text placeholder")

            yield Static("", classes="spacer")
            yield Label("⚠ Not wired yet", classes="placeholder-warning")
