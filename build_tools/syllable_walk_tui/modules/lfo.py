"""
LFO Module - Stochastic Bias and Modulation

Controls probability modulation and bias toward common/rare syllables.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static


class LFOModule(Container):
    """
    LFO widget for stochastic bias.

    Phase 1 (MVP):
    - Placeholder only, not wired

    Future:
    - Frequency bias slider (-2.0 to +2.0)
    - Repeat bias control
    - Drift enable/disable
    - Time-based modulation
    """

    DEFAULT_ID = "lfo"

    def compose(self) -> ComposeResult:
        """Create the LFO module UI."""
        with Vertical(classes="module placeholder-module"):
            yield Label("LFO", classes="module-header")
            yield Label("Stochastic Bias", classes="module-subtitle")
            yield Static("", classes="spacer")

            yield Label("Freq Bias: [+0.0]", classes="info-text placeholder")
            yield Label("[──────○────]", classes="info-text placeholder")
            yield Static("", classes="spacer-small")

            yield Label("Drift:  [ ] Enable", classes="info-text placeholder")
            yield Label("Repeat: [+0.0]", classes="info-text placeholder")
            yield Label("[──────○────]", classes="info-text placeholder")

            yield Static("", classes="spacer")
            yield Label("⚠ Not wired yet", classes="placeholder-warning")
