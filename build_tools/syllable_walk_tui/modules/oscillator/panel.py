"""
Oscillator panel UI component.

This module provides the PatchPanel widget for displaying oscillator
configuration controls in the TUI.
"""

from textual.app import ComposeResult
from textual.widgets import Button, Label, Static

from build_tools.syllable_walk_tui.controls import FloatSlider, IntSpinner, ProfileOption, SeedInput


class OscillatorPanel(Static):
    """
    Panel displaying patch configuration controls.

    This widget will contain all the module controls (Oscillator, Filter,
    Envelope, LFO, Attenuator) for a single patch.

    Args:
        patch_name: Name of the patch ("A" or "B")
        initial_seed: Initial seed value to display (optional)
    """

    def __init__(self, patch_name: str, initial_seed: int | None = None, *args, **kwargs):
        """Initialize patch panel with given name and optional seed."""
        super().__init__(*args, **kwargs)
        self.patch_name = patch_name
        self.initial_seed = initial_seed

    def compose(self) -> ComposeResult:
        """Create child widgets for patch panel."""
        yield Label(f"PATCH {self.patch_name}", classes="patch-header")
        yield Label("", classes="spacer")

        # Corpus selection
        yield Button("Select Corpus Directory", id=f"select-corpus-{self.patch_name}")
        yield Label(
            "No corpus selected", id=f"corpus-status-{self.patch_name}", classes="corpus-status"
        )

        yield Label("", classes="spacer")

        # Profile selection (radio button style - focusable with Enter/Space to select)
        yield Label("Profile:", classes="section-header")
        yield ProfileOption(
            "clerical",
            "Conservative, favors common",
            is_selected=False,
            id=f"profile-clerical-{self.patch_name}",
        )
        yield ProfileOption(
            "dialect",
            "Moderate exploration, neutral",
            is_selected=True,
            id=f"profile-dialect-{self.patch_name}",
        )
        yield ProfileOption(
            "goblin",
            "Chaotic, favors rare",
            is_selected=False,
            id=f"profile-goblin-{self.patch_name}",
        )
        yield ProfileOption(
            "ritual",
            "Maximum exploration, strongly rare",
            is_selected=False,
            id=f"profile-ritual-{self.patch_name}",
        )
        yield ProfileOption(
            "custom",
            "Manual parameter configuration",
            is_selected=False,
            id=f"profile-custom-{self.patch_name}",
        )
        yield Label("", classes="spacer")

        # Parameter controls - matching Dialect profile defaults
        # Filter Module - Syllable Length
        yield IntSpinner(
            "Min Length",
            value=2,
            min_val=1,
            max_val=10,
            id=f"min-length-{self.patch_name}",
        )
        yield IntSpinner(
            "Max Length",
            value=5,
            min_val=1,
            max_val=10,
            id=f"max-length-{self.patch_name}",
        )

        # Envelope Module - Walk Length
        yield IntSpinner(
            "Walk Length",
            value=5,
            min_val=2,
            max_val=20,
            id=f"walk-length-{self.patch_name}",
        )

        # Oscillator Module - Max Feature Flips
        yield IntSpinner(
            "Max Flips",
            value=2,
            min_val=1,
            max_val=3,
            id=f"max-flips-{self.patch_name}",
        )

        # LFO Module - Temperature
        yield FloatSlider(
            "Temperature",
            value=0.7,
            min_val=0.1,
            max_val=5.0,
            step=0.1,
            precision=1,
            id=f"temperature-{self.patch_name}",
        )

        # LFO Module - Frequency Weight
        yield FloatSlider(
            "Freq Weight",
            value=0.0,
            min_val=-2.0,
            max_val=2.0,
            step=0.1,
            precision=1,
            id=f"freq-weight-{self.patch_name}",
        )

        # Attenuator Module - Neighbor Limit
        yield IntSpinner(
            "Neighbors",
            value=10,
            min_val=5,
            max_val=50,
            id=f"neighbors-{self.patch_name}",
        )

        yield Label("", classes="spacer")

        # Global - Seed Input with Random Button
        # Use initial_seed if provided, otherwise None (will show "random" placeholder)
        yield SeedInput(value=self.initial_seed, id=f"seed-{self.patch_name}")

        yield Label("", classes="spacer")

        # Generate button - triggers walk generation using current patch parameters
        # Event handled in core/app.py via on_button_generate_a/b methods
        yield Button("Generate Walks", id=f"generate-{self.patch_name}", variant="primary")

        yield Label("", classes="spacer")
        yield Label("OUTPUT (10)", classes="section-header")
        yield Label("────────────────────", classes="divider")
        # Output display - updated by _generate_walks_for_patch() after generation
        # Shows formatted walk sequences: "syl1 → syl2 → syl3 → ..."
        yield Label(
            "(no generations yet)", id=f"output-{self.patch_name}", classes="output-placeholder"
        )
