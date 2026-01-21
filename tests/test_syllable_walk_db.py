"""Tests for syllable walker SQLite database access module.

This module tests the database access layer functions:
- _get_connection: Read-only database connections
- load_syllables_from_sqlite: Load all syllables with features
- get_syllable_count: Count total syllables
- syllable_exists: Check syllable existence
- get_syllable_data: Get specific syllable data
- get_random_syllable: Get frequency-weighted random syllable
- load_syllables_from_json: Load from JSON fallback
- load_syllables: Load with automatic source detection
"""

import json
import sqlite3

import pytest

from build_tools.syllable_walk.db import (
    FEATURE_COLUMNS,
    _get_connection,
    get_random_syllable,
    get_syllable_count,
    get_syllable_data,
    load_syllables,
    load_syllables_from_json,
    load_syllables_from_sqlite,
    syllable_exists,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_db(tmp_path):
    """Create a temporary SQLite database with test data."""
    db_path = tmp_path / "corpus.db"

    conn = sqlite3.connect(db_path)

    # Create syllables table with all feature columns
    feature_cols = ", ".join(f"{col} INTEGER" for col in FEATURE_COLUMNS)
    conn.execute(f"""
        CREATE TABLE syllables (
            syllable TEXT PRIMARY KEY,
            frequency INTEGER,
            {feature_cols}
        )
    """)

    # Insert test data
    test_syllables = [
        # syllable, frequency, starts_with_vowel, starts_with_cluster, starts_with_heavy_cluster,
        # contains_plosive, contains_fricative, contains_liquid, contains_nasal,
        # short_vowel, long_vowel, ends_with_vowel, ends_with_nasal, ends_with_stop
        ("ka", 100, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0),
        ("an", 80, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0),
        ("str", 50, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        ("ee", 30, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0),
    ]

    placeholders = ", ".join(["?"] * (2 + len(FEATURE_COLUMNS)))
    conn.executemany(f"INSERT INTO syllables VALUES ({placeholders})", test_syllables)
    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def sample_json(tmp_path):
    """Create a temporary JSON file with test data."""
    json_path = tmp_path / "syllables_annotated.json"

    # Create features dict with some True values for "ka"
    ka_features = {col: False for col in FEATURE_COLUMNS}
    ka_features["contains_plosive"] = True
    ka_features["short_vowel"] = True
    ka_features["ends_with_vowel"] = True

    data = [
        {
            "syllable": "ka",
            "frequency": 100,
            "features": ka_features,
        },
        {
            "syllable": "an",
            "frequency": 80,
            "features": {col: False for col in FEATURE_COLUMNS},
        },
    ]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return json_path


@pytest.fixture
def empty_db(tmp_path):
    """Create an empty database."""
    db_path = tmp_path / "empty.db"

    conn = sqlite3.connect(db_path)
    feature_cols = ", ".join(f"{col} INTEGER" for col in FEATURE_COLUMNS)
    conn.execute(f"""
        CREATE TABLE syllables (
            syllable TEXT PRIMARY KEY,
            frequency INTEGER,
            {feature_cols}
        )
    """)
    conn.commit()
    conn.close()

    return db_path


# ============================================================
# Connection Tests
# ============================================================


class TestGetConnection:
    """Test _get_connection function."""

    def test_returns_connection(self, sample_db):
        """Test that _get_connection returns a valid connection."""
        conn = _get_connection(sample_db)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_connection_is_read_only(self, sample_db):
        """Test that connection is read-only."""
        conn = _get_connection(sample_db)

        # Attempting to write should fail
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO syllables (syllable, frequency) VALUES ('test', 1)")

        conn.close()

    def test_row_factory_set(self, sample_db):
        """Test that row_factory is set to sqlite3.Row."""
        conn = _get_connection(sample_db)
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_nonexistent_db_raises(self, tmp_path):
        """Test that nonexistent database raises error."""
        with pytest.raises(sqlite3.OperationalError):
            _get_connection(tmp_path / "nonexistent.db")


# ============================================================
# Load Syllables Tests
# ============================================================


class TestLoadSyllablesFromSqlite:
    """Test load_syllables_from_sqlite function."""

    def test_loads_all_syllables(self, sample_db):
        """Test loading all syllables from database."""
        syllables = load_syllables_from_sqlite(sample_db)
        assert len(syllables) == 4

    def test_syllable_structure(self, sample_db):
        """Test that loaded syllables have correct structure."""
        syllables = load_syllables_from_sqlite(sample_db)

        for syl in syllables:
            assert "syllable" in syl
            assert "frequency" in syl
            assert "features" in syl
            assert isinstance(syl["features"], dict)
            assert len(syl["features"]) == 12

    def test_ordered_by_frequency(self, sample_db):
        """Test that syllables are ordered by frequency descending."""
        syllables = load_syllables_from_sqlite(sample_db)

        frequencies = [s["frequency"] for s in syllables]
        assert frequencies == sorted(frequencies, reverse=True)

    def test_features_are_booleans(self, sample_db):
        """Test that feature values are booleans."""
        syllables = load_syllables_from_sqlite(sample_db)

        for syl in syllables:
            for col, val in syl["features"].items():
                assert isinstance(val, bool), f"Feature {col} should be bool"

    def test_specific_syllable_data(self, sample_db):
        """Test loading specific syllable data."""
        syllables = load_syllables_from_sqlite(sample_db)

        # Find 'ka' syllable (highest frequency, should be first)
        ka = syllables[0]
        assert ka["syllable"] == "ka"
        assert ka["frequency"] == 100
        assert ka["features"]["contains_plosive"] is True
        assert ka["features"]["starts_with_vowel"] is False


# ============================================================
# Count and Existence Tests
# ============================================================


class TestGetSyllableCount:
    """Test get_syllable_count function."""

    def test_returns_correct_count(self, sample_db):
        """Test that count is correct."""
        count = get_syllable_count(sample_db)
        assert count == 4

    def test_empty_database(self, empty_db):
        """Test count of empty database."""
        count = get_syllable_count(empty_db)
        assert count == 0


class TestSyllableExists:
    """Test syllable_exists function."""

    def test_existing_syllable(self, sample_db):
        """Test that existing syllable returns True."""
        assert syllable_exists(sample_db, "ka") is True
        assert syllable_exists(sample_db, "an") is True

    def test_nonexistent_syllable(self, sample_db):
        """Test that nonexistent syllable returns False."""
        assert syllable_exists(sample_db, "xyz") is False
        assert syllable_exists(sample_db, "") is False


# ============================================================
# Get Syllable Data Tests
# ============================================================


class TestGetSyllableData:
    """Test get_syllable_data function."""

    def test_returns_data_for_existing(self, sample_db):
        """Test getting data for existing syllable."""
        data = get_syllable_data(sample_db, "ka")

        assert data is not None
        assert data["syllable"] == "ka"
        assert data["frequency"] == 100
        assert "features" in data

    def test_returns_none_for_nonexistent(self, sample_db):
        """Test getting data for nonexistent syllable."""
        data = get_syllable_data(sample_db, "xyz")
        assert data is None

    def test_features_match_db(self, sample_db):
        """Test that features match database values."""
        data = get_syllable_data(sample_db, "an")

        assert data is not None
        assert data["features"]["starts_with_vowel"] is True
        assert data["features"]["contains_nasal"] is True
        assert data["features"]["ends_with_nasal"] is True


# ============================================================
# Random Syllable Tests
# ============================================================


class TestGetRandomSyllable:
    """Test get_random_syllable function."""

    def test_returns_valid_syllable(self, sample_db):
        """Test that random syllable is from database."""
        syllable = get_random_syllable(sample_db)
        assert syllable in ["ka", "an", "str", "ee"]

    def test_deterministic_with_seed(self, sample_db):
        """Test that same seed produces same result."""
        result1 = get_random_syllable(sample_db, seed=42)
        result2 = get_random_syllable(sample_db, seed=42)
        assert result1 == result2

    def test_different_seeds_may_differ(self, sample_db):
        """Test that different seeds can produce different results."""
        # With enough tries, different seeds should produce different results
        results = {get_random_syllable(sample_db, seed=i) for i in range(100)}
        # Should have more than one unique result (frequency-weighted)
        assert len(results) >= 2

    def test_empty_database_raises(self, empty_db):
        """Test that empty database raises ValueError."""
        with pytest.raises(ValueError, match="Database is empty"):
            get_random_syllable(empty_db)


# ============================================================
# JSON Loading Tests
# ============================================================


class TestLoadSyllablesFromJson:
    """Test load_syllables_from_json function."""

    def test_loads_json_data(self, sample_json):
        """Test loading syllables from JSON."""
        syllables = load_syllables_from_json(sample_json)
        assert len(syllables) == 2

    def test_preserves_structure(self, sample_json):
        """Test that JSON structure is preserved."""
        syllables = load_syllables_from_json(sample_json)

        assert syllables[0]["syllable"] == "ka"
        assert syllables[0]["frequency"] == 100
        assert "features" in syllables[0]


# ============================================================
# Load Syllables (Auto-Detection) Tests
# ============================================================


class TestLoadSyllables:
    """Test load_syllables function with automatic source detection."""

    def test_prefers_sqlite(self, sample_db, sample_json):
        """Test that SQLite is preferred over JSON."""
        syllables, source = load_syllables(db_path=sample_db, json_path=sample_json)

        assert "SQLite" in source
        assert len(syllables) == 4  # SQLite has 4, JSON has 2

    def test_falls_back_to_json(self, sample_json, tmp_path):
        """Test fallback to JSON when no database."""
        nonexistent_db = tmp_path / "nonexistent.db"

        syllables, source = load_syllables(db_path=nonexistent_db, json_path=sample_json)

        assert "JSON" in source
        assert len(syllables) == 2

    def test_json_only(self, sample_json):
        """Test loading with only JSON path."""
        syllables, source = load_syllables(json_path=sample_json)

        assert "JSON" in source
        assert len(syllables) == 2

    def test_raises_when_no_source(self, tmp_path):
        """Test that error is raised when no valid source."""
        with pytest.raises(ValueError, match="No valid data source"):
            load_syllables(
                db_path=tmp_path / "nonexistent.db", json_path=tmp_path / "nonexistent.json"
            )

    def test_raises_when_both_none(self):
        """Test that error is raised when both paths are None."""
        with pytest.raises(ValueError, match="No valid data source"):
            load_syllables()

    def test_source_description_format(self, sample_db):
        """Test that source description includes count."""
        syllables, source = load_syllables(db_path=sample_db)

        assert "4" in source  # Count should be in description
        assert "syllables" in source


# ============================================================
# Feature Columns Tests
# ============================================================


class TestFeatureColumns:
    """Test FEATURE_COLUMNS constant."""

    def test_has_12_features(self):
        """Test that there are exactly 12 features."""
        assert len(FEATURE_COLUMNS) == 12

    def test_expected_features(self):
        """Test that expected features are present."""
        expected = [
            "starts_with_vowel",
            "starts_with_cluster",
            "contains_plosive",
            "ends_with_vowel",
            "ends_with_stop",
        ]
        for feat in expected:
            assert feat in FEATURE_COLUMNS
