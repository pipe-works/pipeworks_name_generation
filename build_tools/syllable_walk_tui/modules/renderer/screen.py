"""
Render Screen for Syllable Walker TUI.

Modal screen for viewing selected names with proper rendering.
Displays Patch A and Patch B selections side-by-side with styling.

This screen consumes the name_renderer module to transform raw
lowercase names into properly styled, human-readable formats.

Design Philosophy:
    - Presentation only - does not modify underlying data
    - Shows names in context for human evaluation
    - "orma" in a list is data; "Orma" in context is a name
"""

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from build_tools.name_renderer import (
    get_available_styles,
    get_style_description,
    render,
    render_full_name,
)


class RenderScreen(Screen):
    """
    Modal screen for rendered name display.

    Shows selected names from both patches with:
    - Title case rendering (default)
    - Full name combination (A first + B last)
    - Style toggle (title/upper/lower)

    Keybindings:
        Esc/q: Close screen and return to main view
        s: Cycle through rendering styles
        c: Toggle combined name view
    """

    BINDINGS = [
        ("escape", "close_screen", "Close"),
        ("q", "close_screen", "Close"),
        ("s", "cycle_style", "Style"),
        ("c", "toggle_combine", "Combine"),
    ]

    DEFAULT_CSS = """
    RenderScreen {
        background: $surface;
        padding: 1;
    }

    /* Header styling */
    .render-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        padding: 1;
        border-bottom: solid $primary;
    }

    .render-subtitle {
        color: $text-muted;
        text-align: center;
        padding-bottom: 1;
    }

    /* Main layout - side by side columns */
    .render-columns {
        width: 100%;
        height: 1fr;
    }

    .render-column {
        width: 1fr;
        height: 100%;
        padding: 1;
        border: solid $primary;
        margin: 0 1;
    }

    .column-header {
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
        border-bottom: dashed $primary;
    }

    .name-class-label {
        color: $text-muted;
        padding-bottom: 1;
    }

    /* Name list styling */
    .names-scroll {
        height: 1fr;
    }

    .rendered-name {
        padding: 0 1;
    }

    .no-names {
        color: $text-muted;
        text-style: italic;
    }

    /* Combined names panel */
    .combined-panel {
        width: 100%;
        height: auto;
        max-height: 30%;
        padding: 1;
        border: solid $accent;
        margin-top: 1;
    }

    .combined-header {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }

    .combined-scroll {
        height: 1fr;
        max-height: 20;
    }

    .combined-name {
        padding: 0 1;
        color: $success;
    }

    /* Footer */
    .render-footer {
        text-align: center;
        color: $text-muted;
        padding-top: 1;
        border-top: solid $primary;
    }
    """

    def __init__(
        self,
        names_a: list[str],
        names_b: list[str],
        name_class_a: str,
        name_class_b: str,
        selections_dir_a: Path | None = None,
        selections_dir_b: Path | None = None,
    ) -> None:
        """
        Initialize with selected names from both patches.

        Args:
            names_a: Selected names from Patch A (SelectorState.outputs)
            names_b: Selected names from Patch B (SelectorState.outputs)
            name_class_a: Name class used for Patch A selection
            name_class_b: Name class used for Patch B selection
            selections_dir_a: Selections directory for Patch A (for exports)
            selections_dir_b: Selections directory for Patch B (for exports)
        """
        super().__init__()

        # Store input data
        self.names_a = names_a
        self.names_b = names_b
        self.name_class_a = name_class_a
        self.name_class_b = name_class_b
        self.selections_dir_a = selections_dir_a
        self.selections_dir_b = selections_dir_b

        # Display state
        self.available_styles = get_available_styles()
        self.current_style_index = 0  # Start with "title"
        self.show_combined = False

    @property
    def current_style(self) -> str:
        """Get the current rendering style."""
        return self.available_styles[self.current_style_index]

    def compose(self) -> ComposeResult:
        """Create the render screen layout."""
        # Header
        yield Label("NAME RENDERER", classes="render-title")
        yield Label(
            f"Style: {get_style_description(self.current_style)} | "
            f"Press 's' to change, 'c' to combine",
            id="style-label",
            classes="render-subtitle",
        )

        # Main content - two columns
        with Horizontal(classes="render-columns"):
            # Patch A column
            with Vertical(classes="render-column"):
                yield Label("PATCH A", classes="column-header")
                yield Label(
                    f"Name Class: {self.name_class_a}",
                    classes="name-class-label",
                )
                yield Button(
                    "Export Sample",
                    id="export-sample-a",
                    variant="primary",
                )
                with VerticalScroll(classes="names-scroll"):
                    yield Static(
                        self._render_names_list(self.names_a, self.name_class_a),
                        id="names-a",
                    )

            # Patch B column
            with Vertical(classes="render-column"):
                yield Label("PATCH B", classes="column-header")
                yield Label(
                    f"Name Class: {self.name_class_b}",
                    classes="name-class-label",
                )
                yield Button(
                    "Export Sample",
                    id="export-sample-b",
                    variant="primary",
                )
                with VerticalScroll(classes="names-scroll"):
                    yield Static(
                        self._render_names_list(self.names_b, self.name_class_b),
                        id="names-b",
                    )

        # Combined names panel (hidden by default)
        with Vertical(id="combined-panel", classes="combined-panel"):
            yield Label("COMBINED NAMES (A + B)", classes="combined-header")
            with VerticalScroll(classes="combined-scroll"):
                yield Static(
                    self._render_combined_names(),
                    id="combined-names",
                )

        # Footer
        yield Label(
            "Esc/q: Close | s: Cycle Style | c: Toggle Combine",
            classes="render-footer",
        )

    def on_mount(self) -> None:
        """Handle screen mount - hide combined panel initially."""
        self._update_combined_visibility()

    def _render_names_list(self, names: list[str], name_class: str) -> str:
        """
        Render a list of names with current style.

        Args:
            names: List of raw names
            name_class: Name class for rendering

        Returns:
            Rendered names as newline-separated string
        """
        if not names:
            return "(no names selected)"

        rendered = [render(name, name_class, style=self.current_style) for name in names]
        return "\n".join(rendered)

    def _render_combined_names(self) -> str:
        """
        Render combined full names (Patch A first + Patch B last).

        Pairs names from both patches. If lists are different lengths,
        only pairs up to the shorter length.

        Returns:
            Combined names as newline-separated string
        """
        if not self.names_a or not self.names_b:
            return "(need names in both patches to combine)"

        # Pair names from both patches
        combined = []
        pair_count = min(len(self.names_a), len(self.names_b))

        for i in range(pair_count):
            full_name = render_full_name(
                self.names_a[i],
                self.names_b[i],
                style=self.current_style,
            )
            combined.append(full_name)

        return "\n".join(combined)

    def _refresh_names_display(self) -> None:
        """Refresh all name displays with current style."""
        try:
            # Update Patch A names
            names_a_widget = self.query_one("#names-a", Static)
            names_a_widget.update(self._render_names_list(self.names_a, self.name_class_a))

            # Update Patch B names
            names_b_widget = self.query_one("#names-b", Static)
            names_b_widget.update(self._render_names_list(self.names_b, self.name_class_b))

            # Update combined names
            combined_widget = self.query_one("#combined-names", Static)
            combined_widget.update(self._render_combined_names())

            # Update style label
            style_label = self.query_one("#style-label", Label)
            style_label.update(
                f"Style: {get_style_description(self.current_style)} | "
                f"Press 's' to change, 'c' to combine"
            )
        except Exception:  # nosec B110 - Widget query may fail during transitions
            pass

    def _update_combined_visibility(self) -> None:
        """Show or hide the combined names panel."""
        try:
            combined_panel = self.query_one("#combined-panel")
            if self.show_combined:
                combined_panel.display = True
            else:
                combined_panel.display = False
        except Exception:  # nosec B110 - Widget may not be mounted yet
            pass

    def action_close_screen(self) -> None:
        """Close this screen and return to main view."""
        self.app.pop_screen()

    def action_cycle_style(self) -> None:
        """Cycle through available rendering styles."""
        # Move to next style (wrapping around)
        self.current_style_index = (self.current_style_index + 1) % len(self.available_styles)

        # Refresh display with new style
        self._refresh_names_display()

        # Notify user
        self.notify(f"Style: {get_style_description(self.current_style)}")

    def action_toggle_combine(self) -> None:
        """Toggle the combined names panel visibility."""
        self.show_combined = not self.show_combined
        self._update_combined_visibility()

        # Notify user
        if self.show_combined:
            self.notify("Combined names: ON")
        else:
            self.notify("Combined names: OFF")

    @on(Button.Pressed, "#export-sample-a")
    def on_export_sample_a(self) -> None:
        """Export a sample JSON for Patch A."""
        self._export_sample(
            names=self.names_a,
            name_class=self.name_class_a,
            selections_dir=self.selections_dir_a,
            patch_label="A",
        )

    @on(Button.Pressed, "#export-sample-b")
    def on_export_sample_b(self) -> None:
        """Export a sample JSON for Patch B."""
        self._export_sample(
            names=self.names_b,
            name_class=self.name_class_b,
            selections_dir=self.selections_dir_b,
            patch_label="B",
        )

    def _export_sample(
        self,
        names: list[str],
        name_class: str,
        selections_dir: Path | None,
        patch_label: str,
    ) -> None:
        """
        Export a random sample JSON file for the specified patch.

        Args:
            names: Selected names for the patch
            name_class: Name class for file naming
            selections_dir: Directory to write the sample JSON into
            patch_label: Patch label for user messaging
        """
        from build_tools.syllable_walk_tui.services.exporter import export_sample_json

        # Validate there are names to sample
        if not names:
            self.notify(f"Patch {patch_label}: No names to sample.", severity="warning")
            return

        # Ensure the selections directory is available
        if selections_dir is None:
            self.notify(
                f"Patch {patch_label}: No selections directory available.",
                severity="warning",
            )
            return

        # Write the sample JSON file
        output_path, error = export_sample_json(
            names=names,
            name_class=name_class,
            selections_dir=selections_dir,
        )

        if error:
            self.notify(f"Patch {patch_label}: {error}", severity="error")
            return

        # Tell the user where the sample landed for packaging workflows
        self.notify(
            f"Patch {patch_label}: Sample exported → {output_path.name}",
            severity="information",
        )
