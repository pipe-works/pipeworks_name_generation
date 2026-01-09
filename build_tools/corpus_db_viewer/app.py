"""
Textual TUI application for corpus database viewer.

Provides an interactive terminal interface for browsing database tables.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from . import formatters, queries


class SchemaModal(ModalScreen[None]):
    """Modal screen for displaying table schema information."""

    DEFAULT_CSS = """
    SchemaModal {
        align: center middle;
    }

    SchemaModal > Container {
        width: 90%;
        height: 85%;
        border: thick $background 80%;
        background: $surface;
    }

    #schema-content {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
    }

    .schema-section {
        margin: 1;
        padding: 1;
        border: solid $primary;
    }

    .schema-title {
        text-style: bold;
        color: $accent;
    }
    """

    def __init__(self, schema_data: dict[str, Any], table_name: str) -> None:
        """
        Initialize schema modal.

        Parameters
        ----------
        schema_data : dict[str, Any]
            Schema information from queries.get_table_schema()
        table_name : str
            Name of the table
        """
        super().__init__()
        self.schema_data = schema_data
        self.table_name = table_name

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container():
            yield Static(f"Schema: {self.table_name}", classes="schema-title")

            with VerticalScroll(id="schema-content"):
                # Columns section
                cols_text = "\n[bold]Columns:[/bold]\n"
                for col in self.schema_data["columns"]:
                    pk = " [PRIMARY KEY]" if col["pk"] else ""
                    notnull = " NOT NULL" if col["notnull"] else ""
                    dflt = f" DEFAULT {col['dflt_value']}" if col["dflt_value"] else ""
                    cols_text += f"  • {col['name']}: {col['type']}{pk}{notnull}{dflt}\n"
                yield Static(cols_text, classes="schema-section")

                # Indexes section
                if self.schema_data["indexes"]:
                    idx_text = "\n[bold]Indexes:[/bold]\n"
                    for idx in self.schema_data["indexes"]:
                        idx_cols = ", ".join([c["name"] for c in idx["columns"]])
                        unique = "[UNIQUE] " if idx.get("unique") else ""
                        idx_text += f"  • {unique}{idx['name']} ({idx_cols})\n"
                    yield Static(idx_text, classes="schema-section")

                # CREATE TABLE SQL
                if self.schema_data["create_sql"]:
                    yield Static(
                        f"\n[bold]CREATE TABLE Statement:[/bold]\n\n{self.schema_data['create_sql']}",
                        classes="schema-section",
                    )

            yield Button("Close", id="close-schema")

    @on(Button.Pressed, "#close-schema")
    def close_modal(self) -> None:
        """Close the schema modal."""
        self.app.pop_screen()


class ExportModal(ModalScreen[dict[str, str]]):
    """Modal screen for export options."""

    DEFAULT_CSS = """
    ExportModal {
        align: center middle;
    }

    ExportModal > Container {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    ExportModal Input {
        margin: 1 0;
    }

    ExportModal Horizontal {
        height: auto;
        align: center middle;
        margin: 1 0;
    }
    """

    def __init__(self, default_filename: str) -> None:
        """
        Initialize export modal.

        Parameters
        ----------
        default_filename : str
            Default filename (without extension)
        """
        super().__init__()
        self.default_filename = default_filename

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container():
            yield Label("Export Data")
            yield Label("Filename (without extension):")
            yield Input(value=self.default_filename, id="filename-input")

            with Horizontal():
                yield Button("Export CSV", id="export-csv", variant="primary")
                yield Button("Export JSON", id="export-json", variant="primary")
                yield Button("Cancel", id="export-cancel")

    @on(Button.Pressed, "#export-csv")
    def export_csv(self) -> None:
        """Export as CSV."""
        filename_input = self.query_one("#filename-input", Input)
        filename = filename_input.value.strip()
        if filename:
            self.dismiss({"format": "csv", "filename": filename})

    @on(Button.Pressed, "#export-json")
    def export_json(self) -> None:
        """Export as JSON."""
        filename_input = self.query_one("#filename-input", Input)
        filename = filename_input.value.strip()
        if filename:
            self.dismiss({"format": "json", "filename": filename})

    @on(Button.Pressed, "#export-cancel")
    def cancel_export(self) -> None:
        """Cancel export."""
        self.dismiss(None)


class HelpModal(ModalScreen[None]):
    """Modal screen showing keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }

    HelpModal > Container {
        width: 70;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        help_text = """
[bold cyan]Corpus Database Viewer - Keyboard Shortcuts[/bold cyan]

[bold]Navigation:[/bold]
  ↑/↓             Navigate rows
  ←/→             Previous/Next page
  PageUp/PageDn   Jump multiple pages
  Home/End        First/Last page

[bold]Actions:[/bold]
  t               Switch table (table selector)
  i               Show schema information
  e               Export current view
  r               Refresh data

[bold]Application:[/bold]
  q               Quit application
  ?               Show this help screen

[bold]In Table Selector:[/bold]
  ↑/↓             Navigate tables
  Enter           Select table
  Escape          Cancel

Press any key to close this help screen.
"""
        with Container():
            yield Static(help_text)
            yield Button("Close", id="close-help")

    @on(Button.Pressed, "#close-help")
    def close_help(self) -> None:
        """Close help modal."""
        self.app.pop_screen()

    def on_key(self, event) -> None:
        """Close on any key press."""
        if event.key != "question_mark":  # Don't close on the key that opened it
            self.app.pop_screen()


class CorpusDBViewerApp(App[None]):
    """
    A Textual app for viewing corpus database provenance records.

    This interactive TUI provides table browsing, schema viewing, and export
    functionality for SQLite databases.
    """

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 30;
        height: 100%;
        border-right: solid $primary;
        background: $boost;
    }

    #main-content {
        width: 1fr;
        height: 100%;
    }

    #table-info {
        height: 3;
        background: $boost;
        padding: 0 1;
    }

    #data-table-container {
        height: 1fr;
    }

    DataTable {
        height: 100%;
    }

    ListView {
        height: 100%;
    }

    ListItem {
        padding: 0 1;
    }

    .sidebar-title {
        text-style: bold;
        padding: 1;
        background: $primary;
        color: $text;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "show_help", "Help", show=True, key_display="?"),
        Binding("t", "switch_table", "Switch Table", show=False),
        Binding("i", "show_schema", "Schema", show=True),
        Binding("e", "export_data", "Export", show=True),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("left", "prev_page", "Prev Page", show=False),
        Binding("right", "next_page", "Next Page", show=False),
        Binding("pageup", "jump_back", "Jump Back", show=False),
        Binding("pagedown", "jump_forward", "Jump Forward", show=False),
        Binding("home", "first_page", "First Page", show=False),
        Binding("end", "last_page", "Last Page", show=False),
    ]

    def __init__(self, db_path: Path, export_dir: Path, page_size: int = 50) -> None:
        """
        Initialize the app.

        Parameters
        ----------
        db_path : Path
            Path to SQLite database
        export_dir : Path
            Directory for exported files
        page_size : int, optional
            Number of rows per page, by default 50
        """
        super().__init__()
        self.db_path = db_path
        self.export_dir = export_dir
        self.page_size = page_size

        self.current_table: str | None = None
        self.current_page: int = 1
        self.total_pages: int = 1
        self.total_rows: int = 0
        self.current_data: list[dict[str, Any]] = []
        self.tables: list[dict[str, str]] = []  # Store table list for lookup

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Horizontal():
            # Sidebar with table list
            with Vertical(id="sidebar"):
                yield Static("Tables", classes="sidebar-title")
                yield ListView(id="table-list")

            # Main content area
            with Vertical(id="main-content"):
                yield Static(id="table-info")
                with Container(id="data-table-container"):
                    yield DataTable(id="data-table", zebra_stripes=True)

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        # Load tables
        try:
            self.tables = queries.get_tables_list(self.db_path)
            table_list = self.query_one("#table-list", ListView)

            if not self.tables:
                self.notify("No tables found in database", severity="warning")
                return

            for table in self.tables:
                table_list.append(ListItem(Label(table["name"]), id=table["name"]))

            # Select first table automatically
            if self.tables:
                self.current_table = self.tables[0]["name"]
                self.load_table_data()

        except Exception as e:
            self.notify(f"Error loading tables: {e}", severity="error")

    def load_table_data(self) -> None:
        """Load data for the current table."""
        if not self.current_table:
            return

        try:
            # Get data
            data = queries.get_table_data(
                self.db_path,
                self.current_table,
                page=self.current_page,
                limit=self.page_size,
            )

            self.total_rows = data["total"]
            self.total_pages = data["total_pages"]
            self.current_data = data["rows"]

            # Update table info
            table_info = self.query_one("#table-info", Static)
            table_info.update(
                f"Table: [bold]{self.current_table}[/bold] | "
                f"Page {self.current_page}/{self.total_pages} | "
                f"Total rows: {formatters.format_row_count(self.total_rows)}"
            )

            # Update data table
            data_table = self.query_one("#data-table", DataTable)
            data_table.clear(columns=True)

            if self.current_data:
                # Add columns
                columns = list(self.current_data[0].keys())
                for col in columns:
                    data_table.add_column(col, key=col)

                # Add rows
                for row in self.current_data:
                    data_table.add_row(*[str(row[col]) for col in columns])

        except Exception as e:
            self.notify(f"Error loading table data: {e}", severity="error")

    @on(ListView.Selected, "#table-list")
    def on_table_selected(self, event: ListView.Selected) -> None:
        """Handle table selection from sidebar."""
        if event.item and event.item.id:
            # Use the ListItem's id which we set to the table name
            self.current_table = str(event.item.id)
            self.current_page = 1
            self.load_table_data()

    def action_switch_table(self) -> None:
        """Focus the table list for switching tables."""
        table_list = self.query_one("#table-list", ListView)
        table_list.focus()

    def action_show_schema(self) -> None:
        """Show schema information for current table."""
        if not self.current_table:
            self.notify("No table selected", severity="warning")
            return

        try:
            schema_data = queries.get_table_schema(self.db_path, self.current_table)
            self.push_screen(SchemaModal(schema_data, self.current_table))
        except Exception as e:
            self.notify(f"Error loading schema: {e}", severity="error")

    def action_export_data(self) -> None:
        """Export current table data."""
        if not self.current_table or not self.current_data:
            self.notify("No data to export", severity="warning")
            return

        # Capture current_table in local variable for type narrowing
        current_table = self.current_table
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{current_table}_{timestamp}"

        def handle_export(result: dict[str, str] | None) -> None:
            """Handle export modal result."""
            if result is None:
                return

            format_type = result["format"]
            filename = result["filename"]

            # Get all data (not just current page)
            try:
                all_data = queries.get_table_data(
                    self.db_path,
                    current_table,
                    page=1,
                    limit=self.total_rows if self.total_rows > 0 else 1000000,
                )

                output_path = self.export_dir / f"{filename}.{format_type}"

                if format_type == "csv":
                    formatters.export_to_csv(all_data["rows"], output_path)
                else:  # json
                    formatters.export_to_json(all_data["rows"], output_path)

                self.notify(f"Exported to {output_path}", severity="information")

            except Exception as e:
                self.notify(f"Export failed: {e}", severity="error")

        self.push_screen(ExportModal(default_filename), handle_export)

    def action_refresh(self) -> None:
        """Refresh current table data."""
        if self.current_table:
            self.load_table_data()
            self.notify("Data refreshed", severity="information")

    def action_show_help(self) -> None:
        """Show help modal with keyboard shortcuts."""
        self.push_screen(HelpModal())

    def action_prev_page(self) -> None:
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_table_data()

    def action_next_page(self) -> None:
        """Go to next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_table_data()

    def action_jump_back(self) -> None:
        """Jump back 10 pages."""
        self.current_page = max(1, self.current_page - 10)
        self.load_table_data()

    def action_jump_forward(self) -> None:
        """Jump forward 10 pages."""
        self.current_page = min(self.total_pages, self.current_page + 10)
        self.load_table_data()

    def action_first_page(self) -> None:
        """Go to first page."""
        self.current_page = 1
        self.load_table_data()

    def action_last_page(self) -> None:
        """Go to last page."""
        self.current_page = self.total_pages
        self.load_table_data()
