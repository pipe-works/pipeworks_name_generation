"""
Tests for corpus_db_viewer module.

Tests for database query functions and export formatters.
"""

import json
import sqlite3
from pathlib import Path

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
