"""
Tests for corpus_sqlite_builder schema module.

Tests database schema creation, metadata handling, and versioning.
"""

import sqlite3
from pathlib import Path

import pytest

from build_tools.corpus_sqlite_builder.schema import (
    CORPUS_SCHEMA_VERSION,
    create_database,
    get_metadata,
    insert_metadata,
    verify_schema_version,
)


def test_create_database(tmp_path: Path) -> None:
    """Test that create_database creates a valid SQLite database."""
    db_path = tmp_path / "test_corpus.db"

    conn = create_database(db_path)

    # Verify database file was created
    assert db_path.exists()

    # Verify tables exist
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    table_names = [t[0] for t in tables]
    assert "metadata" in table_names
    assert "syllables" in table_names

    # Verify indexes exist
    indexes = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
    ).fetchall()

    index_names = [i[0] for i in indexes]
    assert "idx_starts_with_vowel" in index_names
    assert "idx_ends_with_vowel" in index_names
    assert "idx_frequency" in index_names

    conn.close()


def test_create_database_with_existing_file(tmp_path: Path) -> None:
    """Test that create_database fails on existing file."""
    db_path = tmp_path / "test_corpus.db"

    # Create initial database
    conn1 = create_database(db_path)
    conn1.close()

    # Create again should fail (table already exists)
    with pytest.raises(sqlite3.OperationalError, match="already exists"):
        create_database(db_path)


def test_insert_and_get_metadata(tmp_path: Path) -> None:
    """Test inserting and retrieving metadata."""
    db_path = tmp_path / "test_corpus.db"
    conn = create_database(db_path)

    # Insert metadata
    test_metadata = {
        "schema_version": "1",
        "source_tool": "test_tool",
        "total_syllables": "1000",
    }

    insert_metadata(conn, test_metadata)

    # Retrieve metadata
    retrieved = get_metadata(conn)

    assert retrieved == test_metadata
    assert retrieved["schema_version"] == "1"
    assert retrieved["source_tool"] == "test_tool"
    assert retrieved["total_syllables"] == "1000"

    conn.close()


def test_verify_schema_version_valid(tmp_path: Path) -> None:
    """Test schema version verification with valid version."""
    db_path = tmp_path / "test_corpus.db"
    conn = create_database(db_path)

    # Insert correct schema version
    insert_metadata(conn, {"schema_version": str(CORPUS_SCHEMA_VERSION)})

    # Should not raise
    version = verify_schema_version(conn)
    assert version == CORPUS_SCHEMA_VERSION

    conn.close()


def test_verify_schema_version_missing(tmp_path: Path) -> None:
    """Test schema version verification with missing version."""
    db_path = tmp_path / "test_corpus.db"
    conn = create_database(db_path)

    # Don't insert schema_version

    with pytest.raises(ValueError, match="missing schema_version"):
        verify_schema_version(conn)

    conn.close()


def test_verify_schema_version_incompatible(tmp_path: Path) -> None:
    """Test schema version verification with incompatible version."""
    db_path = tmp_path / "test_corpus.db"
    conn = create_database(db_path)

    # Insert wrong schema version
    insert_metadata(conn, {"schema_version": "999"})

    with pytest.raises(ValueError, match="incompatible"):
        verify_schema_version(conn)

    conn.close()


def test_syllables_table_structure(tmp_path: Path) -> None:
    """Test that syllables table has correct columns."""
    db_path = tmp_path / "test_corpus.db"
    conn = create_database(db_path)

    cursor = conn.cursor()
    columns = cursor.execute("PRAGMA table_info(syllables)").fetchall()

    column_names = [col[1] for col in columns]

    # Verify all required columns exist
    expected_columns = [
        "syllable",
        "frequency",
        "starts_with_vowel",
        "starts_with_cluster",
        "starts_with_heavy_cluster",
        "contains_plosive",
        "contains_fricative",
        "contains_liquid",
        "contains_nasal",
        "short_vowel",
        "long_vowel",
        "ends_with_vowel",
        "ends_with_nasal",
        "ends_with_stop",
    ]

    for col in expected_columns:
        assert col in column_names, f"Missing column: {col}"

    conn.close()


def test_syllables_primary_key(tmp_path: Path) -> None:
    """Test that syllable is the primary key."""
    db_path = tmp_path / "test_corpus.db"
    conn = create_database(db_path)

    cursor = conn.cursor()

    # Try to insert duplicate syllable
    cursor.execute("""
        INSERT INTO syllables (
            syllable, frequency,
            starts_with_vowel, starts_with_cluster, starts_with_heavy_cluster,
            contains_plosive, contains_fricative, contains_liquid, contains_nasal,
            short_vowel, long_vowel,
            ends_with_vowel, ends_with_nasal, ends_with_stop
        ) VALUES ('test', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        """)

    # Second insert should fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO syllables (
                syllable, frequency,
                starts_with_vowel, starts_with_cluster, starts_with_heavy_cluster,
                contains_plosive, contains_fricative, contains_liquid, contains_nasal,
                short_vowel, long_vowel,
                ends_with_vowel, ends_with_nasal, ends_with_stop
            ) VALUES ('test', 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            """)

    conn.close()


def test_optimization_pragmas_applied(tmp_path: Path) -> None:
    """Test that optimization pragmas are applied correctly."""
    db_path = tmp_path / "test_corpus.db"
    conn = create_database(db_path)

    cursor = conn.cursor()

    # Check journal mode (should be WAL)
    journal_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
    assert journal_mode.upper() == "WAL"

    # Check synchronous mode (should be NORMAL or 1)
    synchronous = cursor.execute("PRAGMA synchronous").fetchone()[0]
    assert synchronous in (1, "NORMAL")

    conn.close()
