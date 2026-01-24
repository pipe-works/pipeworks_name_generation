"""
Database viewer screen modal component.

This module provides the DatabaseScreen modal for browsing corpus SQLite
database contents with pagination and sorting.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Label

from build_tools.corpus_db_viewer import queries


class SyllableDetailModal(ModalScreen):
    """Modal showing detailed feature breakdown for a syllable."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("enter", "close", "Close"),
    ]

    DEFAULT_CSS = """
    SyllableDetailModal {
        align: center middle;
    }

    SyllableDetailModal > Vertical {
        width: 50;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    SyllableDetailModal .detail-header {
        text-style: bold;
        color: $accent;
        text-align: center;
        margin-bottom: 1;
    }

    SyllableDetailModal .detail-freq {
        text-align: center;
        margin-bottom: 1;
    }

    SyllableDetailModal .detail-section {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
    }

    SyllableDetailModal .detail-feature {
        padding-left: 2;
    }

    SyllableDetailModal .detail-help {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, syllable_data: dict, feature_details: dict, *args, **kwargs):
        """Initialize with syllable data and feature mapping."""
        super().__init__(*args, **kwargs)
        self.syllable_data = syllable_data
        self.feature_details = feature_details

    def compose(self) -> ComposeResult:
        """Create detail modal layout."""
        with Vertical():
            yield Label(f'"{self.syllable_data["syllable"]}"', classes="detail-header")
            yield Label(f'Frequency: {self.syllable_data["frequency"]:,}', classes="detail-freq")

            # Group features by category
            current_category = None
            for feature_key, (category, feature_name) in self.feature_details.items():
                if feature_key in self.syllable_data:
                    if category != current_category:
                        yield Label(f"{category}:", classes="detail-section")
                        current_category = category

                    value = self.syllable_data[feature_key]
                    indicator = "●" if value else "○"
                    yes_no = "Yes" if value else "No"
                    yield Label(f"{indicator} {feature_name}: {yes_no}", classes="detail-feature")

            yield Label("Press Esc or Enter to close", classes="detail-help")

    def action_close(self) -> None:
        """Close the modal."""
        self.app.pop_screen()


class DatabaseScreen(Screen):
    """
    Modal screen for viewing corpus database contents.

    Displays the syllables table from the corpus.db SQLite database
    with pagination and sorting by frequency.

    Args:
        db_path: Path to the corpus.db SQLite database
        patch_name: Name of the patch (A or B) for display

    Keybindings:
        Esc: Close screen and return to main view
        j/k: Navigate rows down/up
        Enter: Show row details
        n/l/Right: Next page
        p/h/Left: Previous page
        [/]: Cycle sort column (prev/next)
        f: Toggle sort order (asc/desc)
        Home: Go to first page
        End: Go to last page
    """

    # Feature names for detail view (maps db column to readable name)
    FEATURE_DETAILS = {
        "starts_with_vowel": ("Onset", "Starts with vowel"),
        "starts_with_cluster": ("Onset", "Starts with cluster"),
        "starts_with_heavy_cluster": ("Onset", "Heavy cluster"),
        "contains_plosive": ("Body", "Contains plosive"),
        "contains_fricative": ("Body", "Contains fricative"),
        "contains_liquid": ("Body", "Contains liquid"),
        "contains_nasal": ("Body", "Contains nasal"),
        "short_vowel": ("Body", "Short vowel"),
        "long_vowel": ("Body", "Long vowel"),
        "ends_with_vowel": ("Coda", "Ends with vowel"),
        "ends_with_nasal": ("Coda", "Ends with nasal"),
        "ends_with_stop": ("Coda", "Ends with stop"),
    }

    # Sortable columns with display names
    SORTABLE_COLUMNS = [
        ("syllable", "Syllable"),
        ("frequency", "Freq"),
        ("starts_with_vowel", "V→"),
        ("starts_with_cluster", "Cl→"),
        ("contains_plosive", "Pls"),
        ("contains_fricative", "Frc"),
        ("contains_liquid", "Liq"),
        ("contains_nasal", "Nas"),
        ("ends_with_vowel", "→V"),
        ("ends_with_nasal", "→N"),
        ("ends_with_stop", "→St"),
    ]

    BINDINGS = [
        ("escape", "close_screen", "Close"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("enter", "show_details", "Details"),
        ("n", "next_page", "Next"),
        ("l", "next_page", "Next"),
        ("right", "next_page", "Next"),
        ("p", "prev_page", "Prev"),
        ("h", "prev_page", "Prev"),
        ("left", "prev_page", "Prev"),
        ("left_square_bracket", "prev_column", "Prev Col"),
        ("right_square_bracket", "next_column", "Next Col"),
        ("f", "toggle_sort", "Sort"),
        ("home", "first_page", "First"),
        ("end", "last_page", "Last"),
    ]

    DEFAULT_CSS = """
    DatabaseScreen {
        background: $surface;
        padding: 1;
    }

    DatabaseScreen .db-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    DatabaseScreen .db-meta {
        color: $text-muted;
        margin-bottom: 1;
    }

    DatabaseScreen .db-status {
        dock: bottom;
        height: 1;
        background: $boost;
        padding: 0 1;
    }

    DatabaseScreen .db-help {
        dock: bottom;
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }

    DatabaseScreen DataTable {
        height: 1fr;
    }
    """

    def __init__(
        self,
        db_path: Path | None = None,
        patch_name: str = "",
        *args,
        **kwargs,
    ):
        """
        Initialize database screen.

        Args:
            db_path: Path to corpus.db file
            patch_name: Patch identifier for display (A or B)
        """
        super().__init__(*args, **kwargs)
        self.db_path = db_path
        self.patch_name = patch_name
        self.current_page = 1
        self.total_pages = 1
        self.total_rows = 0
        self.page_size = 50
        self.sort_column_index = 1  # Default to frequency (index 1)
        self.sort_by = self.SORTABLE_COLUMNS[self.sort_column_index][0]
        self.sort_direction: str = "DESC"
        self.metadata: dict[str, str] = {}
        self.current_rows: list[dict] = []  # Store current page data for detail view

    def compose(self) -> ComposeResult:
        """Create database screen layout."""
        title = (
            f"CORPUS DATABASE - PATCH {self.patch_name}" if self.patch_name else "CORPUS DATABASE"
        )
        yield Label(title, classes="db-header")
        yield Label("", id="db-meta", classes="db-meta")
        yield DataTable(id="db-table")
        yield Label("", id="db-status", classes="db-status")
        yield Label(
            r"j/k:Row  Enter:Details  \[/]:Col  f:Order  h/l:Page  Esc:Close",
            classes="db-help",
        )

    def on_mount(self) -> None:
        """Load data when screen is mounted."""
        table = self.query_one("#db-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        if self.db_path and self.db_path.exists():
            self._load_metadata()
            self._setup_columns()
            self._load_data()
        else:
            self._show_no_database()

    def _load_metadata(self) -> None:
        """Load and display database metadata."""
        if not self.db_path:
            return

        try:
            # Get metadata from database
            import sqlite3

            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM metadata")
            self.metadata = dict(cursor.fetchall())
            conn.close()

            # Get total syllable count
            self.total_rows = queries.get_row_count(self.db_path, "syllables")
            self.total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)

            # Update meta display
            meta_label = self.query_one("#db-meta", Label)
            source_tool = self.metadata.get("source_tool", "unknown")
            generated_at = self.metadata.get("generated_at", "unknown")[:19]  # Trim to datetime
            meta_label.update(
                f"Source: {source_tool} | Generated: {generated_at} | "
                f"Syllables: {self.total_rows:,}"
            )
        except Exception as e:
            meta_label = self.query_one("#db-meta", Label)
            meta_label.update(f"Error loading metadata: {e}")

    def _setup_columns(self) -> None:
        """Set up DataTable columns with sort indicator on active column."""
        table = self.query_one("#db-table", DataTable)
        table.clear(columns=True)

        # Add columns with sort indicator on the active sort column
        sort_indicator = "↓" if self.sort_direction == "DESC" else "↑"

        for i, (col_key, col_name) in enumerate(self.SORTABLE_COLUMNS):
            # Add sort indicator to the active column
            if i == self.sort_column_index:
                label = f"{col_name}{sort_indicator}"
            else:
                label = col_name

            # First two columns are wider
            width = 12 if col_key == "syllable" else (8 if col_key == "frequency" else 4)
            table.add_column(label, key=col_key, width=width)

    def _load_data(self) -> None:
        """Load current page of data into the table."""
        if not self.db_path:
            return

        table = self.query_one("#db-table", DataTable)
        table.clear()

        try:
            data = queries.get_table_data(
                self.db_path,
                "syllables",
                page=self.current_page,
                limit=self.page_size,
                sort_by=self.sort_by,
                sort_order=self.sort_direction,
            )

            # Store rows for detail view lookup
            self.current_rows = data["rows"]

            for row in data["rows"]:
                # Convert binary features to visual indicators
                table.add_row(
                    row["syllable"],
                    str(row["frequency"]),
                    "●" if row["starts_with_vowel"] else "○",
                    "●" if row["starts_with_cluster"] else "○",
                    "●" if row["contains_plosive"] else "○",
                    "●" if row["contains_fricative"] else "○",
                    "●" if row["contains_liquid"] else "○",
                    "●" if row["contains_nasal"] else "○",
                    "●" if row["ends_with_vowel"] else "○",
                    "●" if row["ends_with_nasal"] else "○",
                    "●" if row["ends_with_stop"] else "○",
                )

            self._update_status()

        except Exception as e:
            status = self.query_one("#db-status", Label)
            status.update(f"Error: {e}")

    def _update_status(self) -> None:
        """Update the status bar with pagination info."""
        status = self.query_one("#db-status", Label)
        sort_indicator = "↓" if self.sort_direction == "DESC" else "↑"
        col_name = self.SORTABLE_COLUMNS[self.sort_column_index][1]
        # Escape brackets to avoid Textual markup interpretation
        status.update(
            f"Page {self.current_page}/{self.total_pages} | "
            f"Sort: {col_name} {sort_indicator} | "
            r"\[]/f:change"
        )

    def _show_no_database(self) -> None:
        """Display message when no database is available."""
        meta_label = self.query_one("#db-meta", Label)
        meta_label.update("No corpus database found. Select a corpus directory first.")

        status = self.query_one("#db-status", Label)
        status.update("Press Esc to close")

    def action_close_screen(self) -> None:
        """Close this screen and return to main view."""
        self.app.pop_screen()

    def action_cursor_down(self) -> None:
        """Move cursor down one row."""
        table = self.query_one("#db-table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up one row."""
        table = self.query_one("#db-table", DataTable)
        table.action_cursor_up()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key) to show details."""
        # Get row index from the event
        row_index = event.cursor_row
        if 0 <= row_index < len(self.current_rows):
            row_data = self.current_rows[row_index]
            self.app.push_screen(SyllableDetailModal(row_data, self.FEATURE_DETAILS))

    def action_show_details(self) -> None:
        """Show detailed feature breakdown for the selected row (fallback)."""
        table = self.query_one("#db-table", DataTable)

        # Get current cursor row
        row_index = table.cursor_row
        if row_index is not None and 0 <= row_index < len(self.current_rows):
            row_data = self.current_rows[row_index]
            self.app.push_screen(SyllableDetailModal(row_data, self.FEATURE_DETAILS))

    def action_next_page(self) -> None:
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_data()

    def action_prev_page(self) -> None:
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self._load_data()

    def action_first_page(self) -> None:
        """Go to first page."""
        if self.current_page != 1:
            self.current_page = 1
            self._load_data()

    def action_last_page(self) -> None:
        """Go to last page."""
        if self.current_page != self.total_pages:
            self.current_page = self.total_pages
            self._load_data()

    def action_prev_column(self) -> None:
        """Cycle to previous sortable column."""
        self.sort_column_index = (self.sort_column_index - 1) % len(self.SORTABLE_COLUMNS)
        self.sort_by = self.SORTABLE_COLUMNS[self.sort_column_index][0]
        self.current_page = 1  # Reset to first page when column changes
        self._setup_columns()  # Rebuild columns to update sort indicator
        self._load_data()

    def action_next_column(self) -> None:
        """Cycle to next sortable column."""
        self.sort_column_index = (self.sort_column_index + 1) % len(self.SORTABLE_COLUMNS)
        self.sort_by = self.SORTABLE_COLUMNS[self.sort_column_index][0]
        self.current_page = 1  # Reset to first page when column changes
        self._setup_columns()  # Rebuild columns to update sort indicator
        self._load_data()

    def action_toggle_sort(self) -> None:
        """Toggle sort order (ascending/descending)."""
        if self.sort_direction == "DESC":
            self.sort_direction = "ASC"
        else:
            self.sort_direction = "DESC"
        self.current_page = 1  # Reset to first page when sorting changes
        self._setup_columns()  # Rebuild columns to update sort indicator
        self._load_data()
