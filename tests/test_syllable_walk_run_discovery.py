"""Tests for syllable walker run discovery module.

This module tests the run directory discovery functions:
- RunInfo: Dataclass for run metadata
- _get_syllable_count_from_db: Count syllables from database
- _get_syllable_count_from_json: Count syllables from JSON
- _parse_timestamp: Parse timestamp strings
- _format_display_name: Format human-readable display names
- _discover_selections: Find selection files
- discover_runs: Discover all pipeline runs
- get_selection_data: Load selection data
- get_run_by_id: Get specific run by ID
"""

import json
import sqlite3

import pytest

from build_tools.syllable_walk_web.run_discovery import (
    RunInfo,
    _discover_selections,
    _format_display_name,
    _get_syllable_count_from_db,
    _get_syllable_count_from_json,
    _parse_timestamp,
    discover_runs,
    get_run_by_id,
    get_selection_data,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_run_dir(tmp_path):
    """Create a sample run directory structure."""
    run_dir = tmp_path / "20260121_084017_nltk"
    run_dir.mkdir()

    # Create data directory
    data_dir = run_dir / "data"
    data_dir.mkdir()

    # Create annotated JSON
    json_data = [
        {"syllable": "ka", "frequency": 100, "features": {}},
        {"syllable": "an", "frequency": 80, "features": {}},
        {"syllable": "ba", "frequency": 60, "features": {}},
    ]
    json_path = data_dir / "nltk_syllables_annotated.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f)

    # Create selections directory
    selections_dir = run_dir / "selections"
    selections_dir.mkdir()

    # Create selection files
    selection_data = {
        "metadata": {"name_class": "first_name", "admitted": 10},
        "selections": [{"name": "kaan", "score": 5}],
    }
    with open(selections_dir / "nltk_first_name_2syl.json", "w") as f:
        json.dump(selection_data, f)

    with open(selections_dir / "nltk_last_name_2syl.json", "w") as f:
        json.dump(selection_data, f)

    # Create a meta file that should be skipped
    with open(selections_dir / "nltk_selector_meta.json", "w") as f:
        json.dump({"meta": True}, f)

    return run_dir


@pytest.fixture
def sample_db(tmp_path):
    """Create a sample SQLite database."""
    db_path = tmp_path / "corpus.db"

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE syllables (
            syllable TEXT PRIMARY KEY,
            frequency INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO syllables VALUES (?, ?)",
        [("ka", 100), ("an", 80), ("ba", 60), ("da", 40)],
    )
    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def output_dir(tmp_path, sample_run_dir):
    """Create an output directory with the sample run."""
    output = tmp_path / "output"
    output.mkdir()

    # Move sample_run_dir into output
    import shutil

    dest = output / sample_run_dir.name
    shutil.copytree(sample_run_dir, dest)

    return output


# ============================================================
# RunInfo Tests
# ============================================================


class TestRunInfo:
    """Test RunInfo dataclass."""

    def test_to_dict(self, tmp_path):
        """Test to_dict serialization."""
        run_info = RunInfo(
            path=tmp_path / "run",
            extractor_type="nltk",
            timestamp="20260121_084017",
            display_name="Test Run",
            corpus_db_path=tmp_path / "corpus.db",
            annotated_json_path=tmp_path / "annotated.json",
            syllable_count=100,
            selections={"first_name": tmp_path / "first.json"},
        )

        result = run_info.to_dict()

        assert result["extractor_type"] == "nltk"
        assert result["timestamp"] == "20260121_084017"
        assert result["display_name"] == "Test Run"
        assert result["syllable_count"] == 100
        assert result["selection_count"] == 1
        assert "corpus_db_path" in result
        assert "annotated_json_path" in result

    def test_to_dict_with_none_paths(self, tmp_path):
        """Test to_dict with None paths."""
        run_info = RunInfo(
            path=tmp_path / "run",
            extractor_type="pyphen",
            timestamp="20260121_084017",
            display_name="Test Run",
            corpus_db_path=None,
            annotated_json_path=None,
            syllable_count=0,
        )

        result = run_info.to_dict()

        assert result["corpus_db_path"] is None
        assert result["annotated_json_path"] is None
        assert result["selection_count"] == 0


# ============================================================
# Syllable Count Tests
# ============================================================


class TestGetSyllableCountFromDb:
    """Test _get_syllable_count_from_db function."""

    def test_returns_correct_count(self, sample_db):
        """Test counting syllables from database."""
        count = _get_syllable_count_from_db(sample_db)
        assert count == 4

    def test_returns_zero_for_nonexistent(self, tmp_path):
        """Test returns 0 for nonexistent database."""
        count = _get_syllable_count_from_db(tmp_path / "nonexistent.db")
        assert count == 0

    def test_returns_zero_for_invalid_db(self, tmp_path):
        """Test returns 0 for invalid database."""
        invalid_db = tmp_path / "invalid.db"
        invalid_db.write_text("not a database")

        count = _get_syllable_count_from_db(invalid_db)
        assert count == 0


class TestGetSyllableCountFromJson:
    """Test _get_syllable_count_from_json function."""

    def test_returns_correct_count(self, tmp_path):
        """Test counting syllables from JSON."""
        json_path = tmp_path / "syllables.json"
        with open(json_path, "w") as f:
            json.dump([{"syllable": "a"}, {"syllable": "b"}, {"syllable": "c"}], f)

        count = _get_syllable_count_from_json(json_path)
        assert count == 3

    def test_returns_zero_for_nonexistent(self, tmp_path):
        """Test returns 0 for nonexistent file."""
        count = _get_syllable_count_from_json(tmp_path / "nonexistent.json")
        assert count == 0

    def test_returns_zero_for_non_list(self, tmp_path):
        """Test returns 0 for non-list JSON."""
        json_path = tmp_path / "object.json"
        with open(json_path, "w") as f:
            json.dump({"key": "value"}, f)

        count = _get_syllable_count_from_json(json_path)
        assert count == 0

    def test_returns_zero_for_invalid_json(self, tmp_path):
        """Test returns 0 for invalid JSON."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("not valid json")

        count = _get_syllable_count_from_json(json_path)
        assert count == 0


# ============================================================
# Parse Timestamp Tests
# ============================================================


class TestParseTimestamp:
    """Test _parse_timestamp function."""

    def test_parses_valid_timestamp(self):
        """Test parsing valid timestamp."""
        result = _parse_timestamp("20260121_084017")

        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 21
        assert result.hour == 8
        assert result.minute == 40
        assert result.second == 17

    def test_returns_none_for_invalid(self):
        """Test returns None for invalid timestamp."""
        assert _parse_timestamp("invalid") is None
        assert _parse_timestamp("2026-01-21") is None
        assert _parse_timestamp("") is None


# ============================================================
# Format Display Name Tests
# ============================================================


class TestFormatDisplayName:
    """Test _format_display_name function."""

    def test_format_without_selections(self):
        """Test formatting without selections."""
        result = _format_display_name("20260121_084017_nltk", "nltk", 1000, 0)
        assert result == "20260121_084017_nltk (1,000 syllables)"

    def test_format_with_selections(self):
        """Test formatting with selections."""
        result = _format_display_name("20260121_084017_nltk", "nltk", 1000, 3)
        assert result == "20260121_084017_nltk (1,000 syllables, 3 selections)"

    def test_format_large_number(self):
        """Test formatting with large syllable count."""
        result = _format_display_name("20260121_084017_pyphen", "pyphen", 1234567, 5)
        assert "1,234,567" in result


# ============================================================
# Discover Selections Tests
# ============================================================


class TestDiscoverSelections:
    """Test _discover_selections function."""

    def test_discovers_selection_files(self, sample_run_dir):
        """Test discovering selection files."""
        selections = _discover_selections(sample_run_dir, "nltk")

        assert "first_name" in selections
        assert "last_name" in selections
        assert len(selections) == 2

    def test_skips_meta_files(self, sample_run_dir):
        """Test that meta files are skipped."""
        selections = _discover_selections(sample_run_dir, "nltk")

        # meta file should not be included
        for name_class in selections:
            assert "meta" not in name_class

    def test_returns_empty_for_no_selections_dir(self, tmp_path):
        """Test returns empty dict when no selections directory."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        selections = _discover_selections(run_dir, "nltk")
        assert selections == {}

    def test_returns_empty_for_wrong_prefix(self, sample_run_dir):
        """Test returns empty for wrong extractor prefix."""
        selections = _discover_selections(sample_run_dir, "pyphen")
        assert selections == {}


# ============================================================
# Discover Runs Tests
# ============================================================


class TestDiscoverRuns:
    """Test discover_runs function."""

    def test_discovers_runs(self, output_dir):
        """Test discovering run directories."""
        runs = discover_runs(output_dir)

        assert len(runs) == 1
        assert runs[0].extractor_type == "nltk"
        assert runs[0].timestamp == "20260121_084017"

    def test_returns_empty_for_nonexistent_dir(self, tmp_path):
        """Test returns empty list for nonexistent directory."""
        runs = discover_runs(tmp_path / "nonexistent")
        assert runs == []

    def test_skips_files(self, output_dir):
        """Test that files are skipped."""
        # Create a file in output dir
        (output_dir / "some_file.txt").write_text("content")

        runs = discover_runs(output_dir)
        assert len(runs) == 1  # Only the directory

    def test_skips_invalid_dir_names(self, output_dir):
        """Test that invalid directory names are skipped."""
        # Create directories with invalid names
        (output_dir / "invalid").mkdir()
        (output_dir / "also_invalid").mkdir()
        (output_dir / "abc_def").mkdir()

        runs = discover_runs(output_dir)
        assert len(runs) == 1  # Only the valid run

    def test_skips_non_timestamp_dirs(self, output_dir):
        """Test that non-timestamp directories are skipped."""
        # Create directory without numeric timestamp
        (output_dir / "abc_def_nltk").mkdir()

        runs = discover_runs(output_dir)
        assert len(runs) == 1

    def test_sorted_by_timestamp(self, output_dir):
        """Test runs are sorted by timestamp descending."""
        # Create another older run
        older_run = output_dir / "20260120_084017_nltk"
        older_run.mkdir()
        data_dir = older_run / "data"
        data_dir.mkdir()
        with open(data_dir / "nltk_syllables_annotated.json", "w") as f:
            json.dump([{"syllable": "x"}], f)

        runs = discover_runs(output_dir)

        assert len(runs) == 2
        assert runs[0].timestamp == "20260121_084017"  # Newer first
        assert runs[1].timestamp == "20260120_084017"

    def test_multi_word_extractor(self, output_dir):
        """Test handling multi-word extractor types."""
        # Create run with multi-word extractor
        run_dir = output_dir / "20260122_084017_custom_extractor"
        run_dir.mkdir()
        data_dir = run_dir / "data"
        data_dir.mkdir()
        with open(data_dir / "custom_extractor_syllables_annotated.json", "w") as f:
            json.dump([{"syllable": "x"}], f)

        runs = discover_runs(output_dir)

        custom_run = next((r for r in runs if r.extractor_type == "custom_extractor"), None)
        assert custom_run is not None

    def test_prefers_db_over_json(self, output_dir, sample_db):
        """Test that database count is preferred over JSON."""
        import shutil

        run_dir = output_dir / "20260121_084017_nltk"
        data_dir = run_dir / "data"

        # Copy sample_db to data dir
        shutil.copy(sample_db, data_dir / "corpus.db")

        runs = discover_runs(output_dir)

        assert runs[0].syllable_count == 4  # From DB, not JSON (which has 3)

    def test_skips_empty_runs(self, output_dir):
        """Test that runs with no data are skipped."""
        # Create a run with no data directory
        empty_run = output_dir / "20260122_084017_empty"
        empty_run.mkdir()

        runs = discover_runs(output_dir)

        # Should not include the empty run
        assert all(r.path.name != "20260122_084017_empty" for r in runs)


# ============================================================
# Get Selection Data Tests
# ============================================================


class TestGetSelectionData:
    """Test get_selection_data function."""

    def test_loads_selection_data(self, sample_run_dir):
        """Test loading selection data."""
        selection_path = sample_run_dir / "selections" / "nltk_first_name_2syl.json"

        data = get_selection_data(selection_path)

        assert "metadata" in data
        assert "selections" in data
        assert data["metadata"]["name_class"] == "first_name"

    def test_raises_for_nonexistent(self, tmp_path):
        """Test raises FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            get_selection_data(tmp_path / "nonexistent.json")


# ============================================================
# Get Run By ID Tests
# ============================================================


class TestGetRunById:
    """Test get_run_by_id function."""

    def test_finds_existing_run(self, output_dir):
        """Test finding existing run by ID."""
        run = get_run_by_id("20260121_084017_nltk", output_dir)

        assert run is not None
        assert run.extractor_type == "nltk"

    def test_returns_none_for_nonexistent(self, output_dir):
        """Test returns None for nonexistent run."""
        run = get_run_by_id("nonexistent_run", output_dir)
        assert run is None

    def test_returns_none_for_empty_dir(self, tmp_path):
        """Test returns None when no runs exist."""
        empty_output = tmp_path / "empty_output"
        empty_output.mkdir()

        run = get_run_by_id("any_id", empty_output)
        assert run is None
