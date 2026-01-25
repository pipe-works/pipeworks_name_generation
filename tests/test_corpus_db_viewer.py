"""
Tests for corpus_db_viewer module.

Tests for database query functions, export formatters, and TUI application.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from build_tools.corpus_db_viewer import formatters, queries


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    """
    Create a test SQLite database.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary directory

    Returns
    -------
    Path
        Path to test database
    """
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)

    # Create test table with some data
    conn.execute("""
        CREATE TABLE test_runs (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT,
            count INTEGER,
            timestamp TEXT
        )
    """)

    # Create another test table
    conn.execute("""
        CREATE TABLE test_outputs (
            id INTEGER PRIMARY KEY,
            run_id INTEGER,
            filename TEXT,
            size INTEGER,
            FOREIGN KEY (run_id) REFERENCES test_runs(id)
        )
    """)

    # Create an index
    conn.execute("CREATE INDEX idx_status ON test_runs(status)")

    # Insert test data
    test_data = [
        (1, "run_alpha", "completed", 100, "2024-01-01 10:00:00"),
        (2, "run_beta", "completed", 200, "2024-01-02 10:00:00"),
        (3, "run_gamma", "failed", 50, "2024-01-03 10:00:00"),
        (4, "run_delta", "completed", 150, "2024-01-04 10:00:00"),
        (5, "run_epsilon", "completed", 175, "2024-01-05 10:00:00"),
    ]
    conn.executemany(
        "INSERT INTO test_runs VALUES (?, ?, ?, ?, ?)",
        test_data,
    )

    # Insert output data
    output_data = [
        (1, 1, "output1.txt", 1024),
        (2, 1, "output2.txt", 2048),
        (3, 2, "output3.txt", 1536),
    ]
    conn.executemany(
        "INSERT INTO test_outputs VALUES (?, ?, ?, ?)",
        output_data,
    )

    conn.commit()
    conn.close()

    return db_path


class TestQueries:
    """Tests for queries module."""

    def test_get_tables_list(self, test_db: Path):
        """Test getting list of tables."""
        tables = queries.get_tables_list(test_db)

        assert len(tables) == 2
        assert tables[0]["name"] == "test_outputs"
        assert tables[0]["type"] == "table"
        assert tables[1]["name"] == "test_runs"
        assert tables[1]["type"] == "table"

    def test_get_tables_list_nonexistent_db(self, tmp_path: Path):
        """Test error handling for nonexistent database."""
        nonexistent = tmp_path / "does_not_exist.db"
        with pytest.raises(FileNotFoundError):
            queries.get_tables_list(nonexistent)

    def test_get_table_schema(self, test_db: Path):
        """Test getting table schema."""
        schema = queries.get_table_schema(test_db, "test_runs")

        # Check columns
        assert len(schema["columns"]) == 5
        col_names = [col["name"] for col in schema["columns"]]
        assert "id" in col_names
        assert "name" in col_names
        assert "status" in col_names

        # Check primary key
        id_col = next(c for c in schema["columns"] if c["name"] == "id")
        assert id_col["pk"] == 1

        # Check NOT NULL constraint
        name_col = next(c for c in schema["columns"] if c["name"] == "name")
        assert name_col["notnull"] == 1

        # Check indexes
        assert len(schema["indexes"]) >= 1
        idx_names = [idx["name"] for idx in schema["indexes"]]
        assert "idx_status" in idx_names

        # Check CREATE TABLE SQL
        assert "CREATE TABLE" in schema["create_sql"]
        assert "test_runs" in schema["create_sql"]

    def test_get_table_data_basic(self, test_db: Path):
        """Test getting table data."""
        data = queries.get_table_data(test_db, "test_runs", page=1, limit=10)

        assert data["total"] == 5
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["total_pages"] == 1
        assert len(data["rows"]) == 5

        # Check first row
        first_row = data["rows"][0]
        assert first_row["id"] == 1
        assert first_row["name"] == "run_alpha"
        assert first_row["status"] == "completed"

    def test_get_table_data_pagination(self, test_db: Path):
        """Test pagination."""
        # Page 1 (2 rows)
        page1 = queries.get_table_data(test_db, "test_runs", page=1, limit=2)
        assert len(page1["rows"]) == 2
        assert page1["total_pages"] == 3
        assert page1["rows"][0]["id"] == 1
        assert page1["rows"][1]["id"] == 2

        # Page 2 (2 rows)
        page2 = queries.get_table_data(test_db, "test_runs", page=2, limit=2)
        assert len(page2["rows"]) == 2
        assert page2["rows"][0]["id"] == 3
        assert page2["rows"][1]["id"] == 4

        # Page 3 (1 row)
        page3 = queries.get_table_data(test_db, "test_runs", page=3, limit=2)
        assert len(page3["rows"]) == 1
        assert page3["rows"][0]["id"] == 5

    def test_get_table_data_sorting(self, test_db: Path):
        """Test sorting."""
        # Sort by count ascending
        data_asc = queries.get_table_data(
            test_db, "test_runs", page=1, limit=10, sort_by="count", sort_order="ASC"
        )
        counts_asc = [row["count"] for row in data_asc["rows"]]
        assert counts_asc == [50, 100, 150, 175, 200]

        # Sort by count descending
        data_desc = queries.get_table_data(
            test_db, "test_runs", page=1, limit=10, sort_by="count", sort_order="DESC"
        )
        counts_desc = [row["count"] for row in data_desc["rows"]]
        assert counts_desc == [200, 175, 150, 100, 50]

    def test_get_table_data_invalid_sort_column(self, test_db: Path):
        """Test that invalid sort column is ignored."""
        # Should not raise error, just ignore invalid column
        data = queries.get_table_data(
            test_db,
            "test_runs",
            page=1,
            limit=10,
            sort_by="nonexistent_column",
            sort_order="ASC",
        )
        assert len(data["rows"]) == 5

    def test_get_row_count(self, test_db: Path):
        """Test getting row count."""
        count = queries.get_row_count(test_db, "test_runs")
        assert count == 5

        count_outputs = queries.get_row_count(test_db, "test_outputs")
        assert count_outputs == 3


class TestFormatters:
    """Tests for formatters module."""

    def test_export_to_csv(self, tmp_path: Path):
        """Test CSV export."""
        rows = [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
            {"id": 3, "name": "Charlie", "age": 35},
        ]
        output = tmp_path / "exports" / "test.csv"

        formatters.export_to_csv(rows, output)

        assert output.exists()
        content = output.read_text()

        # Check header
        assert "id,name,age" in content

        # Check data
        assert "Alice" in content
        assert "Bob" in content
        assert "Charlie" in content
        assert "30" in content
        assert "25" in content

    def test_export_to_csv_empty_raises_error(self, tmp_path: Path):
        """Test that exporting empty data raises error."""
        output = tmp_path / "empty.csv"
        with pytest.raises(ValueError, match="Cannot export empty data"):
            formatters.export_to_csv([], output)

    def test_export_to_json(self, tmp_path: Path):
        """Test JSON export."""
        rows = [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
        ]
        output = tmp_path / "exports" / "test.json"

        formatters.export_to_json(rows, output)

        assert output.exists()

        # Parse and verify JSON
        with output.open() as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["name"] == "Alice"
        assert data[0]["age"] == 30
        assert data[1]["name"] == "Bob"
        assert data[1]["age"] == 25

    def test_export_to_json_empty_raises_error(self, tmp_path: Path):
        """Test that exporting empty data raises error."""
        output = tmp_path / "empty.json"
        with pytest.raises(ValueError, match="Cannot export empty data"):
            formatters.export_to_json([], output)

    def test_format_row_count(self):
        """Test row count formatting."""
        assert formatters.format_row_count(0) == "0 rows"
        assert formatters.format_row_count(1) == "1 row"
        assert formatters.format_row_count(2) == "2 rows"
        assert formatters.format_row_count(1000) == "1,000 rows"
        assert formatters.format_row_count(1234567) == "1,234,567 rows"

    def test_format_file_size(self):
        """Test file size formatting."""
        assert formatters.format_file_size(0) == "0.0 B"
        assert formatters.format_file_size(100) == "100.0 B"
        assert formatters.format_file_size(1024) == "1.0 KB"
        assert formatters.format_file_size(1024 * 1024) == "1.0 MB"
        assert formatters.format_file_size(1536) == "1.5 KB"
        assert formatters.format_file_size(1234567) == "1.2 MB"


class TestCLI:
    """Tests for CLI module."""

    def test_create_argument_parser(self):
        """Test argument parser creation."""
        from build_tools.corpus_db_viewer.cli import create_argument_parser

        parser = create_argument_parser()
        assert parser.prog == "corpus_db_viewer"

        # Test with default arguments
        args = parser.parse_args([])
        assert args.db_path == Path("data/raw/syllable_extractor.db")
        assert args.export_dir == Path("_working/exports/")
        assert args.page_size == 50

    def test_parse_arguments_with_custom_db(self):
        """Test parsing custom database path."""
        from build_tools.corpus_db_viewer.cli import parse_arguments

        args = parse_arguments(["--db", "/tmp/test.db"])
        assert args.db_path == Path("/tmp/test.db")

    def test_parse_arguments_with_custom_export_dir(self):
        """Test parsing custom export directory."""
        from build_tools.corpus_db_viewer.cli import parse_arguments

        args = parse_arguments(["--export-dir", "/tmp/exports/"])
        assert args.export_dir == Path("/tmp/exports/")

    def test_parse_arguments_with_custom_page_size(self):
        """Test parsing custom page size."""
        from build_tools.corpus_db_viewer.cli import parse_arguments

        args = parse_arguments(["--page-size", "100"])
        assert args.page_size == 100

    def test_main_with_nonexistent_db(self, tmp_path: Path):
        """Test main function with nonexistent database."""
        from build_tools.corpus_db_viewer.cli import main

        nonexistent = tmp_path / "does_not_exist.db"
        exit_code = main(["--db", str(nonexistent)])

        assert exit_code == 1  # Error exit code


# ============================================================================
# Additional Edge Case Tests
# ============================================================================


@pytest.fixture
def empty_table_db(tmp_path: Path) -> Path:
    """
    Create a database with an empty table.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary directory

    Returns
    -------
    Path
        Path to test database
    """
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE empty_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value INTEGER
        )
    """)

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def null_values_db(tmp_path: Path) -> Path:
    """
    Create a database with NULL values.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary directory

    Returns
    -------
    Path
        Path to test database
    """
    db_path = tmp_path / "nulls.db"
    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            count INTEGER
        )
    """)

    # Insert rows with NULL values
    conn.executemany(
        "INSERT INTO items VALUES (?, ?, ?, ?)",
        [
            (1, "Item A", "Has description", 10),
            (2, "Item B", None, 20),  # NULL description
            (3, None, "No name", None),  # NULL name and count
            (4, "Item D", None, None),  # Multiple NULLs
        ],
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def unicode_db(tmp_path: Path) -> Path:
    """
    Create a database with unicode data.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary directory

    Returns
    -------
    Path
        Path to test database
    """
    db_path = tmp_path / "unicode.db"
    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE languages (
            id INTEGER PRIMARY KEY,
            language TEXT,
            greeting TEXT,
            script TEXT
        )
    """)

    # Insert unicode data
    conn.executemany(
        "INSERT INTO languages VALUES (?, ?, ?, ?)",
        [
            (1, "English", "Hello", "Latin"),
            (2, "Japanese", "こんにちは", "Hiragana"),
            (3, "Chinese", "你好", "Han"),
            (4, "Arabic", "مرحبا", "Arabic"),
            (5, "Russian", "Привет", "Cyrillic"),
            (6, "Greek", "Γειά σου", "Greek"),
            (7, "Emoji", "👋🌍", "Emoji"),
        ],
    )

    conn.commit()
    conn.close()

    return db_path


class TestQueriesEdgeCases:
    """Edge case tests for queries module."""

    def test_get_table_data_empty_table(self, empty_table_db: Path):
        """Test getting data from an empty table."""
        data = queries.get_table_data(empty_table_db, "empty_table", page=1, limit=10)

        assert data["total"] == 0
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["total_pages"] == 1  # At least 1 page even when empty
        assert len(data["rows"]) == 0

    def test_get_table_data_with_null_values(self, null_values_db: Path):
        """Test that NULL values are properly returned."""
        data = queries.get_table_data(null_values_db, "items", page=1, limit=10)

        assert data["total"] == 4
        assert len(data["rows"]) == 4

        # Check NULL values are preserved
        row_2 = next(r for r in data["rows"] if r["id"] == 2)
        assert row_2["description"] is None

        row_3 = next(r for r in data["rows"] if r["id"] == 3)
        assert row_3["name"] is None
        assert row_3["count"] is None

    def test_get_table_data_invalid_sort_order(self, test_db: Path):
        """Test that invalid sort_order defaults to ASC."""
        # Invalid sort order should default to ASC
        data = queries.get_table_data(
            test_db,
            "test_runs",
            page=1,
            limit=10,
            sort_by="count",
            sort_order="INVALID",
        )

        counts = [row["count"] for row in data["rows"]]
        assert counts == [50, 100, 150, 175, 200]  # ASC order

    def test_get_table_data_sort_order_case_insensitive(self, test_db: Path):
        """Test that sort_order is case-insensitive."""
        # Lowercase should work
        data_lower = queries.get_table_data(
            test_db, "test_runs", page=1, limit=10, sort_by="count", sort_order="desc"
        )
        counts_lower = [row["count"] for row in data_lower["rows"]]
        assert counts_lower == [200, 175, 150, 100, 50]  # DESC order

    def test_get_table_data_page_beyond_total(self, test_db: Path):
        """Test requesting a page beyond total pages returns empty rows."""
        data = queries.get_table_data(test_db, "test_runs", page=100, limit=2)

        assert data["total"] == 5
        assert data["page"] == 100
        assert data["total_pages"] == 3
        assert len(data["rows"]) == 0  # No rows on page 100

    def test_get_table_data_with_unicode(self, unicode_db: Path):
        """Test that unicode data is properly handled."""
        data = queries.get_table_data(unicode_db, "languages", page=1, limit=10)

        assert data["total"] == 7
        assert len(data["rows"]) == 7

        # Verify unicode data is intact
        japanese = next(r for r in data["rows"] if r["language"] == "Japanese")
        assert japanese["greeting"] == "こんにちは"

        chinese = next(r for r in data["rows"] if r["language"] == "Chinese")
        assert chinese["greeting"] == "你好"

        emoji = next(r for r in data["rows"] if r["language"] == "Emoji")
        assert emoji["greeting"] == "👋🌍"

    def test_get_row_count_empty_table(self, empty_table_db: Path):
        """Test row count for empty table."""
        count = queries.get_row_count(empty_table_db, "empty_table")
        assert count == 0

    def test_get_table_schema_no_indexes(self, empty_table_db: Path):
        """Test schema for table with no indexes."""
        schema = queries.get_table_schema(empty_table_db, "empty_table")

        assert len(schema["columns"]) == 3
        assert schema["indexes"] == []
        assert "CREATE TABLE" in schema["create_sql"]


class TestFormattersEdgeCases:
    """Edge case tests for formatters module."""

    def test_export_to_csv_with_special_characters(self, tmp_path: Path):
        """Test CSV export with commas, quotes, and newlines."""
        rows = [
            {"id": 1, "name": "O'Brien", "note": "Has apostrophe"},
            {"id": 2, "name": "Smith, Jr.", "note": "Has comma"},
            {"id": 3, "name": '"Quoted"', "note": "Has quotes"},
        ]
        output = tmp_path / "special.csv"

        formatters.export_to_csv(rows, output)

        assert output.exists()
        content = output.read_text()

        # CSV should properly escape special characters
        assert "O'Brien" in content
        # Comma in value should be quoted (CSV wraps in quotes)
        assert '"Smith, Jr."' in content
        # Quotes should be escaped (doubled)
        assert '"""Quoted"""' in content
        lines = content.strip().split("\n")
        assert len(lines) == 4  # Header + 3 data rows

    def test_export_to_csv_with_unicode(self, tmp_path: Path):
        """Test CSV export with unicode characters."""
        rows = [
            {"id": 1, "greeting": "こんにちは", "lang": "Japanese"},
            {"id": 2, "greeting": "你好", "lang": "Chinese"},
            {"id": 3, "greeting": "👋🌍", "lang": "Emoji"},
        ]
        output = tmp_path / "unicode.csv"

        formatters.export_to_csv(rows, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8")

        assert "こんにちは" in content
        assert "你好" in content
        assert "👋🌍" in content

    def test_export_to_csv_creates_parent_directories(self, tmp_path: Path):
        """Test that CSV export creates nested parent directories."""
        rows = [{"id": 1, "name": "Test"}]
        output = tmp_path / "deep" / "nested" / "path" / "data.csv"

        formatters.export_to_csv(rows, output)

        assert output.exists()
        assert output.parent.exists()

    def test_export_to_json_with_datetime(self, tmp_path: Path):
        """Test JSON export handles datetime objects via default=str."""
        now = datetime.now()
        rows = [
            {"id": 1, "name": "Event A", "timestamp": now},
            {"id": 2, "name": "Event B", "timestamp": now},
        ]
        output = tmp_path / "datetime.json"

        formatters.export_to_json(rows, output)

        assert output.exists()

        with output.open() as f:
            data = json.load(f)

        assert len(data) == 2
        # datetime should be serialized as string
        assert str(now) in data[0]["timestamp"]

    def test_export_to_json_with_unicode(self, tmp_path: Path):
        """Test JSON export preserves unicode without escaping."""
        rows = [
            {"id": 1, "text": "こんにちは"},
            {"id": 2, "text": "emoji: 👋🌍"},
        ]
        output = tmp_path / "unicode.json"

        formatters.export_to_json(rows, output)

        content = output.read_text(encoding="utf-8")

        # ensure_ascii=False should preserve unicode
        assert "こんにちは" in content
        assert "👋🌍" in content

    def test_export_to_json_creates_parent_directories(self, tmp_path: Path):
        """Test that JSON export creates nested parent directories."""
        rows = [{"id": 1, "name": "Test"}]
        output = tmp_path / "deep" / "nested" / "path" / "data.json"

        formatters.export_to_json(rows, output)

        assert output.exists()
        assert output.parent.exists()

    def test_format_file_size_large_values(self):
        """Test file size formatting for GB and TB scale."""
        # GB scale
        assert formatters.format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert formatters.format_file_size(int(1024 * 1024 * 1024 * 2.5)) == "2.5 GB"

        # TB scale
        assert formatters.format_file_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"
        assert formatters.format_file_size(1024 * 1024 * 1024 * 1024 * 5) == "5.0 TB"

    def test_format_row_count_large_values(self):
        """Test row count formatting for very large values."""
        assert formatters.format_row_count(1_000_000_000) == "1,000,000,000 rows"
        assert formatters.format_row_count(999_999_999) == "999,999,999 rows"


class TestCLIEdgeCases:
    """Edge case tests for CLI module."""

    def test_main_creates_export_directory(self, test_db: Path, tmp_path: Path):
        """Test that main creates export directory if it doesn't exist."""
        from build_tools.corpus_db_viewer.cli import main

        export_dir = tmp_path / "new_exports"
        assert not export_dir.exists()

        # Mock the app.run() to avoid launching TUI
        with patch("build_tools.corpus_db_viewer.app.CorpusDBViewerApp.run"):
            exit_code = main(["--db", str(test_db), "--export-dir", str(export_dir)])

        assert exit_code == 0
        assert export_dir.exists()

    def test_main_handles_keyboard_interrupt(self, test_db: Path, tmp_path: Path):
        """Test that main handles KeyboardInterrupt gracefully."""
        from build_tools.corpus_db_viewer.cli import main

        with patch(
            "build_tools.corpus_db_viewer.app.CorpusDBViewerApp.run",
            side_effect=KeyboardInterrupt(),
        ):
            exit_code = main(["--db", str(test_db)])

        assert exit_code == 1

    def test_main_handles_runtime_error(self, test_db: Path, tmp_path: Path):
        """Test that main handles runtime errors gracefully."""
        from build_tools.corpus_db_viewer.cli import main

        with patch(
            "build_tools.corpus_db_viewer.app.CorpusDBViewerApp.run",
            side_effect=RuntimeError("Simulated error"),
        ):
            exit_code = main(["--db", str(test_db)])

        assert exit_code == 1

    def test_main_with_export_dir_creation_error(self, test_db: Path, tmp_path: Path):
        """Test main when export directory creation fails."""
        from build_tools.corpus_db_viewer.cli import main

        # Create a file where we want a directory (will cause mkdir to fail)
        blocking_file = tmp_path / "blocking"
        blocking_file.write_text("I'm a file, not a directory")

        exit_code = main(["--db", str(test_db), "--export-dir", str(blocking_file / "subdir")])

        assert exit_code == 1


# ============================================================================
# TUI Application Tests (using Textual's async testing)
# ============================================================================


class TestCorpusDBViewerApp:
    """Tests for the TUI application using Textual's async pilot."""

    @pytest.fixture
    def app(self, test_db: Path, tmp_path: Path):
        """Create a CorpusDBViewerApp instance for testing."""
        from build_tools.corpus_db_viewer.app import CorpusDBViewerApp

        return CorpusDBViewerApp(
            db_path=test_db,
            export_dir=tmp_path / "exports",
            page_size=2,  # Small page size for testing pagination
        )

    @pytest.mark.asyncio
    async def test_app_initialization(self, app):
        """Test app initializes with correct values."""
        assert app.page_size == 2
        assert app.current_table is None
        assert app.current_page == 1
        assert app.total_pages == 1

    @pytest.mark.asyncio
    async def test_app_loads_tables_on_mount(self, app):
        """Test that app loads tables when mounted."""
        async with app.run_test():
            # App should load tables and select first one
            assert app.tables is not None
            assert len(app.tables) == 2
            assert app.current_table == "test_outputs"  # First table alphabetically

    @pytest.mark.asyncio
    async def test_app_pagination_next_page(self, app):
        """Test pagination - next page action."""
        async with app.run_test() as pilot:
            # Switch to test_runs (5 rows, 2 per page = 3 pages)
            app.current_table = "test_runs"
            app.load_table_data()

            assert app.total_pages == 3
            assert app.current_page == 1

            # Go to next page
            await pilot.press("right")

            assert app.current_page == 2

    @pytest.mark.asyncio
    async def test_app_pagination_prev_page(self, app):
        """Test pagination - previous page action."""
        async with app.run_test() as pilot:
            app.current_table = "test_runs"
            app.current_page = 2
            app.load_table_data()

            await pilot.press("left")

            assert app.current_page == 1

    @pytest.mark.asyncio
    async def test_app_pagination_at_boundary(self, app):
        """Test pagination doesn't go below 1 or above total."""
        async with app.run_test() as pilot:
            app.current_table = "test_runs"
            app.load_table_data()

            # Try to go before first page
            assert app.current_page == 1
            await pilot.press("left")
            assert app.current_page == 1  # Still 1

            # Go to last page
            app.current_page = app.total_pages
            app.load_table_data()

            # Try to go past last page
            await pilot.press("right")
            assert app.current_page == app.total_pages  # Still at last

    @pytest.mark.asyncio
    async def test_app_first_page_action(self, app):
        """Test home key goes to first page."""
        async with app.run_test() as pilot:
            app.current_table = "test_runs"
            app.current_page = 3
            app.load_table_data()

            await pilot.press("home")

            assert app.current_page == 1

    @pytest.mark.asyncio
    async def test_app_last_page_action(self, app):
        """Test end key goes to last page."""
        async with app.run_test() as pilot:
            app.current_table = "test_runs"
            app.load_table_data()

            await pilot.press("end")

            assert app.current_page == app.total_pages

    @pytest.mark.asyncio
    async def test_app_refresh_action(self, app):
        """Test refresh reloads data."""
        async with app.run_test() as pilot:
            app.current_table = "test_runs"
            app.load_table_data()

            initial_data = app.current_data.copy()

            await pilot.press("r")

            # Data should still be the same (no changes)
            assert app.current_data == initial_data

    @pytest.mark.asyncio
    async def test_app_show_help(self, app):
        """Test help modal is shown."""
        from build_tools.corpus_db_viewer.app import HelpModal

        async with app.run_test() as pilot:
            await pilot.press("question_mark")

            # Check that HelpModal is on the screen stack
            assert any(isinstance(s, HelpModal) for s in app.screen_stack)

    @pytest.mark.asyncio
    async def test_app_show_schema(self, app):
        """Test schema modal is shown."""
        from build_tools.corpus_db_viewer.app import SchemaModal

        async with app.run_test() as pilot:
            # Need to wait for table to load
            app.current_table = "test_runs"
            app.load_table_data()

            await pilot.press("i")

            # Check that SchemaModal is on the screen stack
            assert any(isinstance(s, SchemaModal) for s in app.screen_stack)


class TestSchemaModal:
    """Tests for SchemaModal."""

    @pytest.mark.asyncio
    async def test_schema_modal_displays_columns(self, test_db: Path, tmp_path: Path):
        """Test that schema modal displays column information."""
        from build_tools.corpus_db_viewer.app import CorpusDBViewerApp, SchemaModal

        app = CorpusDBViewerApp(
            db_path=test_db,
            export_dir=tmp_path / "exports",
            page_size=50,
        )

        async with app.run_test():
            app.current_table = "test_runs"
            app.load_table_data()

            # Push schema modal
            schema_data = queries.get_table_schema(test_db, "test_runs")
            app.push_screen(SchemaModal(schema_data, "test_runs"))

            # Modal should be on screen
            assert any(isinstance(s, SchemaModal) for s in app.screen_stack)

    @pytest.mark.asyncio
    async def test_schema_modal_closes_on_button(self, test_db: Path, tmp_path: Path):
        """Test that schema modal closes when button is pressed."""
        from build_tools.corpus_db_viewer.app import CorpusDBViewerApp, SchemaModal

        app = CorpusDBViewerApp(
            db_path=test_db,
            export_dir=tmp_path / "exports",
            page_size=50,
        )

        async with app.run_test() as pilot:
            schema_data = queries.get_table_schema(test_db, "test_runs")
            app.push_screen(SchemaModal(schema_data, "test_runs"))

            # Wait for the screen to be mounted and rendered
            await pilot.pause()

            # Click the close button
            await pilot.click("#close-schema")

            # Modal should be gone
            assert not any(isinstance(s, SchemaModal) for s in app.screen_stack)


class TestHelpModal:
    """Tests for HelpModal."""

    @pytest.mark.asyncio
    async def test_help_modal_closes_on_keypress(self, test_db: Path, tmp_path: Path):
        """Test that help modal closes on any key press."""
        from build_tools.corpus_db_viewer.app import CorpusDBViewerApp, HelpModal

        app = CorpusDBViewerApp(
            db_path=test_db,
            export_dir=tmp_path / "exports",
            page_size=50,
        )

        async with app.run_test() as pilot:
            app.push_screen(HelpModal())

            assert any(isinstance(s, HelpModal) for s in app.screen_stack)

            # Press any key to close
            await pilot.press("escape")
            await pilot.pause()  # Allow Textual to process the event (fixes Windows flakiness)

            assert not any(isinstance(s, HelpModal) for s in app.screen_stack)


class TestExportModal:
    """Tests for ExportModal."""

    @pytest.mark.asyncio
    async def test_export_modal_cancel(self, test_db: Path, tmp_path: Path):
        """Test that export modal can be cancelled."""
        from build_tools.corpus_db_viewer.app import CorpusDBViewerApp, ExportModal

        app = CorpusDBViewerApp(
            db_path=test_db,
            export_dir=tmp_path / "exports",
            page_size=50,
        )

        async with app.run_test() as pilot:
            app.push_screen(ExportModal("test_file"))

            # Wait for the screen to be mounted and rendered
            await pilot.pause()

            assert any(isinstance(s, ExportModal) for s in app.screen_stack)

            # Click cancel
            await pilot.click("#export-cancel")

            # Modal should be gone
            assert not any(isinstance(s, ExportModal) for s in app.screen_stack)
