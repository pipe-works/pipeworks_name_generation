"""
Patch Cable Module - Corpus Routing and Comparison

Controls how corpora are routed and compared.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Static


class PatchCableModule(Container):
    """
    Patch Cable widget for corpus routing.

    Phase 1 (MVP):
    - Placeholder only, not wired

    Future:
    - Switch corpus per step
    - Alternate corpus each generation
    - Mix ratio controls
    - A/B comparison view
    """

    DEFAULT_ID = "patch-cable"

    def compose(self) -> ComposeResult:
        """Create the patch cable module UI."""
        with Vertical(classes="module placeholder-module"):
            yield Label("PATCH CABLE", classes="module-header")
            yield Label("Corpus Routing", classes="module-subtitle")
            yield Static("", classes="spacer")

            yield Label("Active: [Single]", classes="info-text placeholder")
            yield Label("  ○ Switch/Step", classes="info-text placeholder")
            yield Label("  ○ Alternate", classes="info-text placeholder")
            yield Label("  ○ Mix Ratio", classes="info-text placeholder")
            yield Static("", classes="spacer-small")

            yield Label("[A/B Compare]", classes="info-text placeholder")

            yield Static("", classes="spacer")
            yield Label("⚠ Not wired yet", classes="placeholder-warning")
