"""
Selector panel UI component.

This module provides the SelectorPanel widget for name_selector controls.
The panel mirrors the exact CLI options from build_tools/name_selector.

CLI Options → UI Controls:
    --run-dir       → Determined by which patch panel this is in
    --candidates    → Determined by combiner output (auto-detected)
    --name-class    → Name class dropdown
    --count         → Count spinner (default: 100)
    --mode          → Mode radio (hard/soft, default: hard)
    --order         → Order radio (random/alphabetical, default: random)
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Button, Label, Static

from build_tools.syllable_walk_tui.controls import IntSpinner, JKSelect, RadioOption
from build_tools.syllable_walk_tui.modules.generator.state import NAME_CLASSES


class SelectorPanel(Static):
    """
    Panel with name_selector controls for a specific patch.

    Mirrors the CLI options exactly:
    - Name Class: Policy to use for selection (--name-class)
    - Count: Maximum names to output (--count, default: 100)
    - Mode: Evaluation mode (--mode, hard/soft, default: hard)
    - Order: Ordering for names with equal scores (random/alphabetical)

    Args:
        patch_name: Name of the patch ("A" or "B")
    """

    DEFAULT_CSS = """
    SelectorPanel {
        width: 100%;
        height: auto;
        padding: 1;
        border-top: solid $primary-darken-2;
        margin-top: 1;
    }

    SelectorPanel .panel-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    SelectorPanel .control-row {
        height: auto;
        margin-bottom: 1;
    }

    SelectorPanel .select-button {
        margin-top: 1;
        margin-bottom: 1;
    }

    SelectorPanel .export-button {
        margin-bottom: 1;
    }

    SelectorPanel .output-section {
        margin-top: 1;
        border-top: solid $primary-darken-2;
        padding-top: 1;
    }

    SelectorPanel .output-content {
        layout: horizontal;
        height: auto;
    }

    SelectorPanel .output-meta {
        width: 1fr;
        height: auto;
    }

    SelectorPanel .output-names {
        width: 1fr;
        height: auto;
        margin-left: 2;
        padding-left: 2;
        border-left: solid $primary-darken-2;
    }

    SelectorPanel .names-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    SelectorPanel .names-list {
        color: $text;
    }

    SelectorPanel .output-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    SelectorPanel .meta-line {
        color: $text;
    }

    SelectorPanel .placeholder {
        color: $text-muted;
        text-style: italic;
    }

    SelectorPanel .mode-label {
        margin-top: 1;
        margin-bottom: 0;
    }

    SelectorPanel .mode-options {
        layout: horizontal;
        height: auto;
    }

    SelectorPanel .order-label {
        margin-top: 1;
        margin-bottom: 0;
    }

    SelectorPanel .order-options {
        layout: horizontal;
        height: auto;
    }

    SelectorPanel .names-scroll {
        height: 15;
        border: solid $primary-darken-2;
        padding: 1;
    }

    SelectorPanel JKSelect {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def __init__(self, patch_name: str = "A", **kwargs) -> None:
        """
        Initialize selector panel.

        Args:
            patch_name: Name of the patch ("A" or "B")
        """
        super().__init__(**kwargs)
        self.patch_name = patch_name

    def compose(self) -> ComposeResult:
        """Create selector panel layout matching CLI options."""
        yield Label(f"PATCH {self.patch_name} NAME SELECTOR", classes="panel-header")

        # --name-class: Policy to use
        yield Label("Name Class:", classes="control-label")
        yield JKSelect(
            [(nc.replace("_", " ").title(), nc) for nc in NAME_CLASSES],
            value="first_name",
            id=f"selector-name-class-{self.patch_name.lower()}",
            allow_blank=False,
        )

        # --count: Maximum names to output (default: 100)
        yield IntSpinner(
            "Count",
            value=100,
            min_val=10,
            max_val=1000,
            step=10,
            id=f"selector-count-{self.patch_name.lower()}",
        )

        # --mode: Evaluation mode (hard/soft)
        yield Label("Mode:", classes="mode-label")
        with Static(classes="mode-options"):
            yield RadioOption(
                "hard",
                "Reject discouraged",
                is_selected=True,
                id=f"selector-mode-hard-{self.patch_name.lower()}",
            )
            yield RadioOption(
                "soft",
                "Penalize discouraged",
                is_selected=False,
                id=f"selector-mode-soft-{self.patch_name.lower()}",
            )

        # Order: Ordering for names with equal scores
        yield Label("Order:", classes="order-label")
        with Static(classes="order-options"):
            yield RadioOption(
                "random",
                "Random (shuffled)",
                is_selected=True,
                id=f"selector-order-random-{self.patch_name.lower()}",
            )
            yield RadioOption(
                "alphabetical",
                "Alphabetical",
                is_selected=False,
                id=f"selector-order-alphabetical-{self.patch_name.lower()}",
            )

        # Select button
        yield Button(
            "Select Names",
            id=f"select-names-{self.patch_name.lower()}",
            variant="primary",
            classes="select-button",
        )

        # Export to TXT button
        yield Button(
            "Export TXT",
            id=f"export-txt-{self.patch_name.lower()}",
            variant="default",
            classes="export-button",
        )

        # Output section (metadata and names display)
        with Static(
            classes="output-section", id=f"selector-output-section-{self.patch_name.lower()}"
        ):
            with Static(classes="output-content"):
                # Left side: metadata
                with Static(classes="output-meta"):
                    yield Label(
                        "(Generate candidates first, then select)",
                        id=f"selector-output-{self.patch_name.lower()}",
                        classes="placeholder",
                    )
                # Right side: names list (scrollable)
                with Static(classes="output-names"):
                    yield Label("Selected Names:", classes="names-header")
                    with VerticalScroll(classes="names-scroll"):
                        yield Label(
                            "",
                            id=f"selector-names-{self.patch_name.lower()}",
                            classes="names-list",
                        )

    def update_output(self, meta: dict | None = None, names: list[str] | None = None) -> None:
        """
        Update the output display with selector metadata and selected names.

        Args:
            meta: Metadata dict from selector (matches selector_meta.json structure)
            names: List of selected names to display (typically top N)
        """
        try:
            output_label = self.query_one(f"#selector-output-{self.patch_name.lower()}", Label)
            names_label = self.query_one(f"#selector-names-{self.patch_name.lower()}", Label)

            if meta is None:
                output_label.update("(Generate candidates first, then select)")
                output_label.set_classes("placeholder")
                names_label.update("")
                return

            # Build output text from metadata
            lines = []

            # Arguments section
            args = meta.get("arguments", {})
            lines.append(f"Name Class: {args.get('name_class', '?')}")
            lines.append(f"Count: {args.get('count', '?')}")
            lines.append(f"Mode: {args.get('mode', '?')}")
            lines.append(f"Order: {args.get('order', '?')}")
            lines.append("")

            # Statistics section
            stats = meta.get("statistics", {})
            total = stats.get("total_evaluated", 0)
            admitted = stats.get("admitted", 0)
            admitted_pct = stats.get("admitted_percentage", 0)
            rejected = stats.get("rejected", 0)
            lines.append(f"Evaluated: {total:,} candidates")
            lines.append(f"Admitted: {admitted:,} ({admitted_pct:.1f}%)")
            lines.append(f"Rejected: {rejected:,}")

            # Output section
            output = meta.get("output", {})
            selections_count = output.get("selections_count", 0)
            lines.append("")
            lines.append(f"Selected: {selections_count:,} names")

            # Output path (relative)
            selections_file = output.get("selections_file", "")
            if selections_file:
                if "/selections/" in selections_file:
                    rel_path = "selections/" + selections_file.split("/selections/")[-1]
                else:
                    rel_path = selections_file
                lines.append(f"→ {rel_path}")

            output_label.update("\n".join(lines))
            output_label.set_classes("meta-line")

            # Update names display
            if names:
                names_label.update("\n".join(names))
            else:
                names_label.update("")

        except Exception:  # nosec B110 - Widget may not be mounted yet
            pass

    def clear_output(self) -> None:
        """Clear the output display and names list."""
        self.update_output(None, None)

    def set_mode(self, mode: str) -> None:
        """
        Set the mode selection.

        Args:
            mode: "hard" or "soft"
        """
        try:
            hard_option = self.query_one(
                f"#selector-mode-hard-{self.patch_name.lower()}", RadioOption
            )
            soft_option = self.query_one(
                f"#selector-mode-soft-{self.patch_name.lower()}", RadioOption
            )

            if mode == "hard":
                hard_option.set_selected(True)
                soft_option.set_selected(False)
            else:
                hard_option.set_selected(False)
                soft_option.set_selected(True)
        except Exception:  # nosec B110 - Widget may not be mounted yet
            pass

    def set_order(self, order: str) -> None:
        """
        Set the order selection.

        Args:
            order: "random" or "alphabetical"
        """
        try:
            random_option = self.query_one(
                f"#selector-order-random-{self.patch_name.lower()}", RadioOption
            )
            alpha_option = self.query_one(
                f"#selector-order-alphabetical-{self.patch_name.lower()}", RadioOption
            )

            if order == "random":
                random_option.set_selected(True)
                alpha_option.set_selected(False)
            else:
                random_option.set_selected(False)
                alpha_option.set_selected(True)
        except Exception:  # nosec B110 - Widget may not be mounted yet
            pass
