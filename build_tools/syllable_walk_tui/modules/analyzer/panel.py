"""
Statistics panel component.

This module provides the StatsPanel widget for displaying comparison
statistics between patches.
"""

from textual.app import ComposeResult
from textual.widgets import Label, Static


class StatsPanel(Static):
    """
    Panel displaying comparison statistics between patches.

    Shows parameter differences, output metrics, and phonetic analysis.
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for statistics panel."""
        yield Label("COMPARISON STATS", classes="stats-header")
        yield Label("", classes="spacer")
        yield Label("Differences:")
        yield Label("  (generate to compare)")
        yield Label("", classes="spacer")
        yield Label("Outputs:")
        yield Label("  A: 0 generated")
        yield Label("  B: 0 generated")
        yield Label("", classes="spacer")
        yield Label("(More stats as we")
        yield Label(" discover needs)")
