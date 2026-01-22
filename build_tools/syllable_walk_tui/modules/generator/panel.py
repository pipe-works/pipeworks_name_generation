"""
Combiner panel UI component.

This module provides the CombinerPanel widget for name_combiner controls.
The panel mirrors the exact CLI options from build_tools/name_combiner.

CLI Options → UI Controls:
    --run-dir          → Determined by which patch panel this is in
    --syllables        → Syllables spinner (2-4, default: 2)
    --count            → Count spinner (default: 10000)
    --seed             → Seed input (None = random)
    --frequency-weight → Frequency weight slider (0.0-1.0)
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Button, Label, Static

from build_tools.syllable_walk_tui.controls import FloatSlider, IntSpinner, SeedInput


class CombinerPanel(Static):
    """
    Panel with name_combiner controls for a specific patch.

    Mirrors the CLI options exactly:
    - Syllables: 2, 3, or 4 (--syllables)
    - Count: Number of candidates (--count, default: 10000)
    - Seed: RNG seed (--seed, None = random)
    - Frequency Weight: Sampling bias (--frequency-weight, default: 1.0)

    Args:
        patch_name: Name of the patch ("A" or "B")
    """

    DEFAULT_CSS = """
    CombinerPanel {
        width: 100%;
        height: auto;
        padding: 1;
    }

    CombinerPanel .panel-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    CombinerPanel .control-row {
        height: auto;
        margin-bottom: 1;
    }

    /* Override spinner-value width for count spinner (needs room for 100000) */
    #combiner-count-a .spinner-value,
    #combiner-count-b .spinner-value {
        width: 10;
    }

    CombinerPanel .generate-button {
        margin-top: 1;
        margin-bottom: 1;
    }

    CombinerPanel .output-section {
        margin-top: 1;
        border-top: solid $primary-darken-2;
        padding-top: 1;
    }

    CombinerPanel .output-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    CombinerPanel .meta-line {
        color: $text;
    }

    CombinerPanel .meta-label {
        color: $text-muted;
    }

    CombinerPanel .meta-value {
        color: $success;
    }

    CombinerPanel .meta-path {
        color: $accent;
        text-style: italic;
    }

    CombinerPanel .placeholder {
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self, patch_name: str = "A", **kwargs) -> None:
        """
        Initialize combiner panel.

        Args:
            patch_name: Name of the patch ("A" or "B")
        """
        super().__init__(**kwargs)
        self.patch_name = patch_name

    def compose(self) -> ComposeResult:
        """Create combiner panel layout matching CLI options."""
        yield Label(f"PATCH {self.patch_name} NAME COMBINER", classes="panel-header")

        # --syllables: 2, 3, or 4
        yield IntSpinner(
            "Syllables",
            value=2,
            min_val=2,
            max_val=4,
            step=1,
            id=f"combiner-syllables-{self.patch_name.lower()}",
        )

        # --count: Number of candidates (default: 10000)
        yield IntSpinner(
            "Count",
            value=10000,
            min_val=100,
            max_val=100000,
            step=1000,
            id=f"combiner-count-{self.patch_name.lower()}",
        )

        # --seed: RNG seed (None = random)
        yield SeedInput(value=None, id=f"combiner-seed-{self.patch_name.lower()}")

        # --frequency-weight: 0.0-1.0 (default: 1.0)
        yield FloatSlider(
            "Freq Weight",
            value=1.0,
            min_val=0.0,
            max_val=1.0,
            step=0.1,
            precision=1,
            id=f"combiner-freq-weight-{self.patch_name.lower()}",
        )

        # Generate button
        yield Button(
            "Generate Candidates",
            id=f"generate-candidates-{self.patch_name.lower()}",
            variant="primary",
            classes="generate-button",
        )

        # Output section (metadata display)
        with Static(
            classes="output-section", id=f"combiner-output-section-{self.patch_name.lower()}"
        ):
            yield Label("", id=f"combiner-output-{self.patch_name.lower()}", classes="placeholder")

    def update_output(self, meta: dict | None = None) -> None:
        """
        Update the output display with combiner metadata.

        Args:
            meta: Metadata dict from combiner (matches nltk_combiner_meta.json structure)
                  Keys: tool, version, generated_at, arguments, output
        """
        try:
            output_label = self.query_one(f"#combiner-output-{self.patch_name.lower()}", Label)

            if meta is None:
                output_label.update("(Press Generate to create candidates)")
                output_label.set_classes("placeholder")
                return

            # Build output text from metadata
            lines = []

            # Arguments section
            args = meta.get("arguments", {})
            lines.append(f"Syllables: {args.get('syllables', '?')}")
            lines.append(f"Count: {args.get('count', '?'):,}")
            lines.append(f"Seed: {args.get('seed', '?')}")
            lines.append(f"Freq Weight: {args.get('frequency_weight', '?')}")
            lines.append("")

            # Output section
            out = meta.get("output", {})
            generated = out.get("candidates_generated", 0)
            unique = out.get("unique_names", 0)
            unique_pct = out.get("unique_percentage", 0)
            lines.append(f"Generated: {generated:,} candidates")
            lines.append(f"Unique: {unique:,} ({unique_pct:.1f}%)")

            # Output path (relative)
            candidates_file = out.get("candidates_file", "")
            if candidates_file:
                # Show just the relative part: candidates/xxx.json
                if "/candidates/" in candidates_file:
                    rel_path = "candidates/" + candidates_file.split("/candidates/")[-1]
                else:
                    rel_path = candidates_file
                lines.append(f"→ {rel_path}")

            output_label.update("\n".join(lines))
            output_label.set_classes("meta-line")

        except Exception:  # nosec B110 - Widget may not be mounted yet
            pass

    def clear_output(self) -> None:
        """Clear the output display."""
        self.update_output(None)
