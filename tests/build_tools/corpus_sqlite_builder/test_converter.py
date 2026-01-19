"""
Tests for corpus_sqlite_builder converter module.

Tests JSON to SQLite conversion logic, validation, and error handling.
"""

import json
from pathlib import Path

import pytest

from build_tools.corpus_sqlite_builder.converter import convert_json_to_sqlite, find_annotated_json


@pytest.fixture
def sample_annotated_data() -> list[dict]:
    """Sample annotated syllable data for testing."""
    return [
        {
            "syllable": "hello",
            "frequency": 100,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": True,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": False,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "world",
            "frequency": 50,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": True,
                "contains_nasal": False,
                "short_vowel": False,
                "long_vowel": False,
                "ends_with_vowel": False,
                "ends_with_nasal": False,
                "ends_with_stop": True,
            },
        },
    ]


@pytest.fixture
def mock_corpus_dir(tmp_path: Path, sample_annotated_data: list[dict]) -> Path:
    """Create a mock corpus directory with annotated JSON."""
    corpus_dir = tmp_path / "20260114_000000_test"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Write annotated JSON
    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sample_annotated_data, f)

    return corpus_dir


def test_find_annotated_json_nltk(tmp_path: Path) -> None:
    """Test finding NLTK annotated JSON file."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    json_path = data_dir / "nltk_syllables_annotated.json"
    json_path.write_text("[]")

    found = find_annotated_json(data_dir)
    assert found == json_path


def test_find_annotated_json_pyphen(tmp_path: Path) -> None:
    """Test finding Pyphen annotated JSON file."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    json_path = data_dir / "pyphen_syllables_annotated.json"
    json_path.write_text("[]")

    found = find_annotated_json(data_dir)
    assert found == json_path


def test_find_annotated_json_not_found(tmp_path: Path) -> None:
    """Test finding annotated JSON when none exists."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    found = find_annotated_json(data_dir)
    assert found is None


def test_find_annotated_json_nonexistent_dir(tmp_path: Path) -> None:
    """Test finding annotated JSON in nonexistent directory."""
    data_dir = tmp_path / "nonexistent"

    found = find_annotated_json(data_dir)
    assert found is None


def test_convert_json_to_sqlite_success(mock_corpus_dir: Path) -> None:
    """Test successful JSON to SQLite conversion."""
    db_path = convert_json_to_sqlite(mock_corpus_dir)

    # Verify database was created
    assert db_path.exists()
    assert db_path.name == "corpus.db"
    assert db_path.parent.name == "data"

    # Verify data was inserted
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    count = cursor.execute("SELECT COUNT(*) FROM syllables").fetchone()[0]
    assert count == 2

    # Verify syllable data
    syllables = cursor.execute(
        "SELECT syllable, frequency FROM syllables ORDER BY syllable"
    ).fetchall()

    assert syllables[0][0] == "hello"
    assert syllables[0][1] == 100
    assert syllables[1][0] == "world"
    assert syllables[1][1] == 50

    conn.close()


def test_convert_json_to_sqlite_corpus_dir_not_found(tmp_path: Path) -> None:
    """Test conversion with nonexistent corpus directory."""
    nonexistent = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError, match="Corpus directory not found"):
        convert_json_to_sqlite(nonexistent)


def test_convert_json_to_sqlite_no_json_found(tmp_path: Path) -> None:
    """Test conversion when no annotated JSON exists."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="No annotated JSON file found"):
        convert_json_to_sqlite(corpus_dir)


def test_convert_json_to_sqlite_already_exists(mock_corpus_dir: Path) -> None:
    """Test conversion when database already exists without force."""
    # First conversion
    convert_json_to_sqlite(mock_corpus_dir)

    # Second conversion should fail
    with pytest.raises(FileExistsError, match="Database already exists"):
        convert_json_to_sqlite(mock_corpus_dir, force=False)


def test_convert_json_to_sqlite_force_overwrite(mock_corpus_dir: Path) -> None:
    """Test conversion with force overwrite."""
    # First conversion
    db_path1 = convert_json_to_sqlite(mock_corpus_dir)

    # Second conversion with force should succeed
    db_path2 = convert_json_to_sqlite(mock_corpus_dir, force=True)

    assert db_path1 == db_path2
    assert db_path2.exists()


def test_convert_json_to_sqlite_invalid_json_structure(tmp_path: Path) -> None:
    """Test conversion with invalid JSON structure (not a list)."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Write invalid JSON (dict instead of list)
    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w") as f:
        json.dump({"invalid": "structure"}, f)

    with pytest.raises(ValueError, match="JSON must contain a list"):
        convert_json_to_sqlite(corpus_dir)


def test_convert_json_to_sqlite_empty_json(tmp_path: Path) -> None:
    """Test conversion with empty JSON array."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Write empty JSON
    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w") as f:
        json.dump([], f)

    with pytest.raises(ValueError, match="JSON contains no syllable records"):
        convert_json_to_sqlite(corpus_dir)


def test_convert_json_to_sqlite_missing_fields(tmp_path: Path) -> None:
    """Test conversion with records missing required fields."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Write JSON with incomplete record
    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w") as f:
        json.dump([{"syllable": "test"}], f)  # Missing frequency and features

    with pytest.raises(ValueError, match="missing required field"):
        convert_json_to_sqlite(corpus_dir)


def test_convert_json_to_sqlite_missing_features(tmp_path: Path) -> None:
    """Test conversion with records missing feature fields."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Write JSON with incomplete features
    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w") as f:
        json.dump(
            [
                {
                    "syllable": "test",
                    "frequency": 1,
                    "features": {
                        "starts_with_vowel": True
                        # Missing other features
                    },
                }
            ],
            f,
        )

    with pytest.raises(ValueError, match="features missing required field"):
        convert_json_to_sqlite(corpus_dir)


def test_convert_json_to_sqlite_data_integrity(
    mock_corpus_dir: Path, sample_annotated_data: list[dict]
) -> None:
    """Test that converted data matches source JSON."""
    db_path = convert_json_to_sqlite(mock_corpus_dir)

    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all syllables
    rows = cursor.execute("""
        SELECT syllable, frequency,
               starts_with_vowel, starts_with_cluster, starts_with_heavy_cluster,
               contains_plosive, contains_fricative, contains_liquid, contains_nasal,
               short_vowel, long_vowel,
               ends_with_vowel, ends_with_nasal, ends_with_stop
        FROM syllables ORDER BY syllable
        """).fetchall()

    # Sort sample data for comparison
    sorted_sample = sorted(sample_annotated_data, key=lambda x: x["syllable"])

    # Verify each record matches
    assert len(rows) == len(sorted_sample)

    for row, expected in zip(rows, sorted_sample):
        assert row["syllable"] == expected["syllable"]
        assert row["frequency"] == expected["frequency"]

        # Verify all features match (accounting for bool to int conversion)
        for feature_name, feature_value in expected["features"].items():
            assert bool(row[feature_name]) == feature_value

    conn.close()


def test_convert_json_to_sqlite_metadata(mock_corpus_dir: Path) -> None:
    """Test that metadata is correctly inserted."""
    db_path = convert_json_to_sqlite(mock_corpus_dir)

    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    metadata = dict(cursor.execute("SELECT key, value FROM metadata").fetchall())

    # Verify required metadata exists
    assert "schema_version" in metadata
    assert "source_tool" in metadata
    assert metadata["source_tool"] == "corpus_sqlite_builder"
    assert "generated_at" in metadata
    assert "total_syllables" in metadata
    assert metadata["total_syllables"] == "2"

    conn.close()


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_find_annotated_json_multiple_files(tmp_path: Path) -> None:
    """Test finding annotated JSON when multiple files exist."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create multiple annotated JSON files
    (data_dir / "nltk_syllables_annotated.json").write_text("[]")
    (data_dir / "pyphen_syllables_annotated.json").write_text("[]")

    # Should return the first one found (alphabetically)
    found = find_annotated_json(data_dir)
    assert found is not None
    # One of them should be returned
    assert found.name in ["nltk_syllables_annotated.json", "pyphen_syllables_annotated.json"]


def test_convert_json_to_sqlite_features_not_dict(tmp_path: Path) -> None:
    """Test conversion with features as non-dict type."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Write JSON with features as a list instead of dict
    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w") as f:
        json.dump(
            [
                {
                    "syllable": "test",
                    "frequency": 1,
                    "features": ["not", "a", "dict"],  # Invalid: list instead of dict
                }
            ],
            f,
        )

    with pytest.raises(ValueError, match="features.*must be a dictionary"):
        convert_json_to_sqlite(corpus_dir)


def test_convert_json_to_sqlite_large_batch(tmp_path: Path) -> None:
    """Test conversion with large data to trigger batch processing."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Create data with enough records to trigger multiple batches
    base_features = {
        "starts_with_vowel": False,
        "starts_with_cluster": False,
        "starts_with_heavy_cluster": False,
        "contains_plosive": False,
        "contains_fricative": False,
        "contains_liquid": False,
        "contains_nasal": False,
        "short_vowel": True,
        "long_vowel": False,
        "ends_with_vowel": False,
        "ends_with_nasal": False,
        "ends_with_stop": False,
    }

    # Create 25 records (will test batch processing with batch_size=10)
    data = [
        {
            "syllable": f"syl{i:03d}",
            "frequency": i,
            "features": base_features.copy(),
        }
        for i in range(25)
    ]

    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w") as f:
        json.dump(data, f)

    # Use small batch size to trigger batching
    db_path = convert_json_to_sqlite(corpus_dir, batch_size=10)

    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM syllables").fetchone()[0]
    conn.close()

    assert count == 25


def test_convert_json_to_sqlite_unicode_data(tmp_path: Path) -> None:
    """Test conversion with unicode syllable data."""
    corpus_dir = tmp_path / "corpus"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    base_features = {
        "starts_with_vowel": True,
        "starts_with_cluster": False,
        "starts_with_heavy_cluster": False,
        "contains_plosive": False,
        "contains_fricative": False,
        "contains_liquid": False,
        "contains_nasal": False,
        "short_vowel": True,
        "long_vowel": False,
        "ends_with_vowel": True,
        "ends_with_nasal": False,
        "ends_with_stop": False,
    }

    data = [
        {"syllable": "こん", "frequency": 100, "features": base_features.copy()},
        {"syllable": "日", "frequency": 50, "features": base_features.copy()},
        {"syllable": "você", "frequency": 30, "features": base_features.copy()},
    ]

    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    db_path = convert_json_to_sqlite(corpus_dir)

    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    syllables = cursor.execute("SELECT syllable FROM syllables ORDER BY frequency DESC").fetchall()
    conn.close()

    assert syllables[0][0] == "こん"
    assert syllables[1][0] == "日"
    assert syllables[2][0] == "você"


def test_convert_json_to_sqlite_is_directory(tmp_path: Path) -> None:
    """Test conversion fails when corpus_dir is a file."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("not a directory")

    with pytest.raises(FileNotFoundError, match="Corpus directory not found"):
        convert_json_to_sqlite(file_path)
