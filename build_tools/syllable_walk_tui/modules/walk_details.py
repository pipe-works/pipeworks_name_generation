"""
Walk Details Module - Dynamic Walk Results Display

Displays detailed step-by-step information about syllable walks.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Label, Static


class WalkDetailsModule(Container):
    """
    Widget for displaying detailed walk results.

    Shows the step-by-step syllable path, features flipped at each step,
    and phonetic distances traveled. This provides transparency into how
    the walk algorithm explores phonetic space.

    Phase 1 (MVP):
    - Display last walk with syllable sequence
    - Show feature flips per step
    - Show phonetic distance per step
    - Scrollable display for long walks

    Future:
    - History of multiple walks
    - Collapsible walk entries
    - Export walk details
    - Visualization of feature changes
    """

    DEFAULT_ID = "walk-details"

    def __init__(self, id: str = DEFAULT_ID):
        super().__init__(id=id)
        self.walks: list[dict] = []

    def compose(self) -> ComposeResult:
        """Create the walk details module UI."""
        with Vertical(classes="module walk-details-module"):
            yield Label("WALK DETAILS", classes="module-header")
            yield Label("Phonetic Path Trace", classes="module-subtitle")
            yield Static("", classes="spacer-small")

            # Walk details display area (scrollable)
            with VerticalScroll(id="walk-details-display", classes="walk-details-display"):
                yield Label("Generate words to see walk details...", classes="placeholder-text")

    def add_walk_details(self, walk_data: dict):
        """
        Add detailed walk information to the display.

        Args:
            walk_data: Dictionary containing:
                - word: The collapsed word
                - steps: List of step dictionaries with syllable, features, distance
                - total_distance: Total phonetic distance traveled
                - seed: Random seed used
        """
        self.walks.append(walk_data)

        # Update display
        display = self.query_one("#walk-details-display", VerticalScroll)

        # Clear placeholder if this is first walk
        if len(self.walks) == 1:
            display.remove_children()

        # Add walk header
        word = walk_data.get("word", "???")
        total_distance = walk_data.get("total_distance", 0)
        seed = walk_data.get("seed", "unknown")

        display.mount(Label("", classes="walk-spacer"))
        display.mount(
            Label(
                f"━━━ {word} ━━━ (distance: {total_distance:.2f}, seed: {seed})",
                classes="walk-header",
            )
        )

        # Add each step
        steps = walk_data.get("steps", [])
        for i, step in enumerate(steps):
            syllable = step.get("syllable", "?")
            distance = step.get("distance", 0.0)
            flipped = step.get("flipped_features", [])

            # Step line
            step_text = f"  {i+1}. {syllable:<10} (d={distance:.2f})"
            display.mount(Label(step_text, classes="walk-step"))

            # Feature flips (if any)
            if flipped:
                flip_text = "     flips: " + ", ".join(flipped)
                display.mount(Label(flip_text, classes="walk-flips"))

        # Scroll to bottom to show latest walk
        display.scroll_end(animate=False)

    def clear_walks(self):
        """Clear all walk details from display."""
        self.walks = []
        display = self.query_one("#walk-details-display", VerticalScroll)
        display.remove_children()
        display.mount(Label("Generate words to see walk details...", classes="placeholder-text"))
