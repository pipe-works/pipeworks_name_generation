"""
Comprehensive test suite for the corpus_db build tool.

This module tests all functionality of the corpus database ledger including:
- CorpusLedger initialization and database creation
- Recording runs with all parameters
- Recording inputs and outputs
- Completing runs with status and exit codes
- Querying runs by various criteria
- Context manager support
- Schema creation and versioning
- Error handling and edge cases

The ledger is observational only - these tests verify it correctly records
extraction metadata without influencing extraction behavior.
"""

import sqlite3
from pathlib import Path

import pytest

from build_tools.corpus_db import SCHEMA_VERSION, CorpusLedger, get_schema_description


class TestCorpusLedgerInitialization:
    """Test suite for CorpusLedger initialization and setup."""

    def test_init_creates_database(self, tmp_path):
        """Test that initializing ledger creates database file."""
        db_path = tmp_path / "test.db"
        assert not db_path.exists()

        ledger = CorpusLedger(db_path=db_path)
        assert db_path.exists()
        ledger.close()

    def test_init_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        db_path = tmp_path / "nested" / "dir" / "test.db"
        assert not db_path.parent.exists()

        ledger = CorpusLedger(db_path=db_path)
        assert db_path.parent.exists()
        assert db_path.exists()
        ledger.close()

    def test_init_creates_all_tables(self, tmp_path):
        """Test that all required tables are created."""
        db_path = tmp_path / "test.db"
        ledger = CorpusLedger(db_path=db_path)

        # Check tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "runs" in tables
        assert "inputs" in tables
        assert "outputs" in tables
        assert "schema_version" in tables

        conn.close()
        ledger.close()

    def test_init_records_schema_version(self, tmp_path):
        """Test that schema version is recorded in database."""
        db_path = tmp_path / "test.db"
        ledger = CorpusLedger(db_path=db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_version")
        version = cursor.fetchone()[0]

        assert version == SCHEMA_VERSION

        conn.close()
        ledger.close()

    def test_init_idempotent(self, tmp_path):
        """Test that multiple initializations don't cause errors."""
        db_path = tmp_path / "test.db"

        # Initialize twice
        ledger1 = CorpusLedger(db_path=db_path)
        ledger1.close()

        ledger2 = CorpusLedger(db_path=db_path)
        ledger2.close()

        # Should not raise any errors


class TestCorpusLedgerContextManager:
    """Test suite for context manager support."""

    def test_context_manager_closes_connection(self, tmp_path):
        """Test that context manager properly closes connection."""
        db_path = tmp_path / "test.db"

        with CorpusLedger(db_path=db_path) as ledger:
            assert ledger._conn is not None

        # Connection should be closed after exiting context
        assert ledger._conn is None

    def test_context_manager_can_record_runs(self, tmp_path):
        """Test that ledger works correctly within context manager."""
        db_path = tmp_path / "test.db"

        with CorpusLedger(db_path=db_path) as ledger:
            run_id = ledger.start_run(
                extractor_tool="test_tool",
                extractor_version="1.0.0",
            )
            ledger.complete_run(run_id, exit_code=0, status="completed")

        # Verify run was recorded
        ledger = CorpusLedger(db_path=db_path)
        run = ledger.get_run(run_id)
        assert run is not None
        assert run["extractor_tool"] == "test_tool"
        ledger.close()


class TestStartRun:
    """Test suite for starting new extraction runs."""

    def test_start_run_minimal(self, tmp_path):
        """Test starting a run with minimal required parameters."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(
            extractor_tool="syllable_extractor",
        )

        assert isinstance(run_id, int)
        assert run_id > 0

        ledger.close()

    def test_start_run_returns_unique_ids(self, tmp_path):
        """Test that each run gets a unique ID."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id1 = ledger.start_run(extractor_tool="tool1")
        run_id2 = ledger.start_run(extractor_tool="tool2")

        assert run_id1 != run_id2

        ledger.close()

    def test_start_run_all_parameters(self, tmp_path):
        """Test starting a run with all optional parameters."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(
            extractor_tool="syllable_extractor",
            extractor_version="0.2.0",
            pyphen_lang="en_US",
            auto_lang_detected="en",
            min_len=2,
            max_len=8,
            recursive=True,
            pattern="*.txt",
            command_line="python -m build_tools.syllable_extractor --file input.txt",
            notes="Test run for documentation",
        )

        run = ledger.get_run(run_id)
        assert run is not None
        assert run["extractor_tool"] == "syllable_extractor"
        assert run["extractor_version"] == "0.2.0"
        assert run["pyphen_lang"] == "en_US"
        assert run["auto_lang_detected"] == "en"
        assert run["min_len"] == 2
        assert run["max_len"] == 8
        assert run["recursive"] == 1  # SQLite stores as integer
        assert run["pattern"] == "*.txt"
        assert run["command_line"] == "python -m build_tools.syllable_extractor --file input.txt"
        assert run["notes"] == "Test run for documentation"
        assert run["status"] == "running"
        assert run["hostname"] is not None  # Should capture hostname

        ledger.close()

    def test_start_run_sets_timestamp(self, tmp_path):
        """Test that run timestamp is set automatically."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        run = ledger.get_run(run_id)
        assert run is not None

        assert run["run_timestamp"] is not None
        # Should be ISO 8601 format
        assert "T" in run["run_timestamp"]

        ledger.close()

    def test_start_run_sets_hostname(self, tmp_path):
        """Test that hostname is captured automatically."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        run = ledger.get_run(run_id)
        assert run is not None

        assert run["hostname"] is not None
        assert len(run["hostname"]) > 0

        ledger.close()

    def test_start_run_initial_status_is_running(self, tmp_path):
        """Test that new runs start with status='running'."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        run = ledger.get_run(run_id)
        assert run is not None

        assert run["status"] == "running"
        assert run["exit_code"] is None  # Not set yet

        ledger.close()


class TestRecordInput:
    """Test suite for recording input sources."""

    def test_record_input_single_file(self, tmp_path):
        """Test recording a single input file."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.record_input(run_id, Path("/data/corpus/english.txt"))

        inputs = ledger.get_run_inputs(run_id)
        assert len(inputs) == 1
        assert inputs[0]["source_path"] == "/data/corpus/english.txt"
        assert inputs[0]["file_count"] is None

        ledger.close()

    def test_record_input_directory(self, tmp_path):
        """Test recording a directory with file count."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.record_input(run_id, Path("/data/corpus/"), file_count=42)

        inputs = ledger.get_run_inputs(run_id)
        assert len(inputs) == 1
        # Paths are stored in POSIX format (forward slashes)
        assert inputs[0]["source_path"] == Path("/data/corpus/").as_posix()
        assert inputs[0]["file_count"] == 42

        ledger.close()

    def test_record_multiple_inputs(self, tmp_path):
        """Test recording multiple input sources for one run."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.record_input(run_id, Path("/data/corpus/file1.txt"))
        ledger.record_input(run_id, Path("/data/corpus/file2.txt"))
        ledger.record_input(run_id, Path("/data/corpus/dir/"), file_count=10)

        inputs = ledger.get_run_inputs(run_id)
        assert len(inputs) == 3

        ledger.close()


class TestRecordOutput:
    """Test suite for recording output files."""

    def test_record_output_minimal(self, tmp_path):
        """Test recording output with minimal parameters."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.record_output(run_id, Path("/data/raw/output.syllables"))

        outputs = ledger.get_run_outputs(run_id)
        assert len(outputs) == 1
        assert outputs[0]["output_path"] == "/data/raw/output.syllables"

        ledger.close()

    def test_record_output_with_counts(self, tmp_path):
        """Test recording output with syllable counts."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.record_output(
            run_id,
            Path("/data/raw/output.syllables"),
            syllable_count=5432,
            unique_syllable_count=1234,
        )

        outputs = ledger.get_run_outputs(run_id)
        assert outputs[0]["syllable_count"] == 5432
        assert outputs[0]["unique_syllable_count"] == 1234

        ledger.close()

    def test_record_output_with_meta(self, tmp_path):
        """Test recording output with metadata file path."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.record_output(
            run_id,
            Path("/data/raw/output.syllables"),
            meta_path=Path("/data/raw/output.meta"),
        )

        outputs = ledger.get_run_outputs(run_id)
        assert outputs[0]["meta_path"] == "/data/raw/output.meta"

        ledger.close()

    def test_record_multiple_outputs(self, tmp_path):
        """Test recording multiple outputs for one run (batch processing)."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.record_output(run_id, Path("/data/raw/en_US.syllables"), unique_syllable_count=100)
        ledger.record_output(run_id, Path("/data/raw/de_DE.syllables"), unique_syllable_count=150)

        outputs = ledger.get_run_outputs(run_id)
        assert len(outputs) == 2

        ledger.close()


class TestCompleteRun:
    """Test suite for marking runs complete."""

    def test_complete_run_success(self, tmp_path):
        """Test marking run as successfully completed."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.complete_run(run_id, exit_code=0, status="completed")

        run = ledger.get_run(run_id)
        assert run is not None
        assert run["exit_code"] == 0
        assert run["status"] == "completed"

        ledger.close()

    def test_complete_run_failure(self, tmp_path):
        """Test marking run as failed."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.complete_run(run_id, exit_code=1, status="failed")

        run = ledger.get_run(run_id)
        assert run is not None
        assert run["exit_code"] == 1
        assert run["status"] == "failed"

        ledger.close()

    def test_complete_run_interrupted(self, tmp_path):
        """Test marking run as interrupted."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")
        ledger.complete_run(run_id, exit_code=130, status="interrupted")

        run = ledger.get_run(run_id)
        assert run is not None
        assert run["exit_code"] == 130
        assert run["status"] == "interrupted"

        ledger.close()

    def test_complete_run_invalid_status(self, tmp_path):
        """Test that invalid status raises ValueError."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool")

        with pytest.raises(ValueError, match="Invalid status"):
            ledger.complete_run(run_id, exit_code=0, status="invalid_status")

        ledger.close()


class TestQueryRuns:
    """Test suite for querying recorded runs."""

    def test_get_run_exists(self, tmp_path):
        """Test getting details for an existing run."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool", extractor_version="1.0.0")
        run = ledger.get_run(run_id)

        assert run is not None
        assert run["id"] == run_id
        assert run["extractor_tool"] == "test_tool"
        assert run["extractor_version"] == "1.0.0"

        ledger.close()

    def test_get_run_not_exists(self, tmp_path):
        """Test getting details for non-existent run returns None."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run = ledger.get_run(99999)
        assert run is None

        ledger.close()

    def test_get_runs_by_tool(self, tmp_path):
        """Test filtering runs by extractor tool."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        # Create runs with different tools
        ledger.start_run(extractor_tool="syllable_extractor")
        ledger.start_run(extractor_tool="syllable_extractor_nltk")
        ledger.start_run(extractor_tool="syllable_extractor")

        runs = ledger.get_runs_by_tool("syllable_extractor")
        assert len(runs) == 2
        for run in runs:
            assert run["extractor_tool"] == "syllable_extractor"

        ledger.close()

    def test_get_runs_by_tool_ordered_by_timestamp(self, tmp_path):
        """Test that runs are returned newest first."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id1 = ledger.start_run(extractor_tool="test_tool")
        run_id2 = ledger.start_run(extractor_tool="test_tool")
        run_id3 = ledger.start_run(extractor_tool="test_tool")

        runs = ledger.get_runs_by_tool("test_tool")

        # Should be ordered newest to oldest
        assert runs[0]["id"] == run_id3
        assert runs[1]["id"] == run_id2
        assert runs[2]["id"] == run_id1

        ledger.close()

    def test_get_recent_runs(self, tmp_path):
        """Test getting most recent runs with limit."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        # Create 5 runs
        for i in range(5):
            ledger.start_run(extractor_tool=f"tool_{i}")

        # Get 3 most recent
        recent = ledger.get_recent_runs(limit=3)
        assert len(recent) == 3

        ledger.close()

    def test_get_recent_runs_default_limit(self, tmp_path):
        """Test that default limit is 10."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        # Create 15 runs
        for i in range(15):
            ledger.start_run(extractor_tool=f"tool_{i}")

        # Get recent with default limit
        recent = ledger.get_recent_runs()
        assert len(recent) == 10

        ledger.close()


class TestFindRunByOutput:
    """Test suite for reverse lookup - finding run that produced an output."""

    def test_find_run_by_output_exists(self, tmp_path):
        """Test finding run that produced a specific output file."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run_id = ledger.start_run(extractor_tool="test_tool", command_line="test command")
        ledger.record_output(run_id, Path("/data/raw/output.syllables"))

        run = ledger.find_run_by_output(Path("/data/raw/output.syllables"))

        assert run is not None
        assert run["id"] == run_id
        assert run["command_line"] == "test command"

        ledger.close()

    def test_find_run_by_output_not_exists(self, tmp_path):
        """Test finding run for non-existent output returns None."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        run = ledger.find_run_by_output(Path("/data/raw/nonexistent.syllables"))
        assert run is None

        ledger.close()


class TestGetStats:
    """Test suite for ledger statistics."""

    def test_get_stats_empty_ledger(self, tmp_path):
        """Test statistics for empty ledger."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        stats = ledger.get_stats()

        assert stats["total_runs"] == 0
        assert stats["completed_runs"] == 0
        assert stats["failed_runs"] == 0
        assert len(stats["tools_used"]) == 0
        assert len(stats["languages_used"]) == 0

        ledger.close()

    def test_get_stats_with_runs(self, tmp_path):
        """Test statistics with various runs."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        # Create completed run
        run_id1 = ledger.start_run(
            extractor_tool="syllable_extractor",
            pyphen_lang="en_US",
        )
        ledger.complete_run(run_id1, exit_code=0, status="completed")

        # Create failed run
        run_id2 = ledger.start_run(
            extractor_tool="syllable_extractor_nltk",
            pyphen_lang="de_DE",
        )
        ledger.complete_run(run_id2, exit_code=1, status="failed")

        # Create another completed run
        run_id3 = ledger.start_run(
            extractor_tool="syllable_extractor",
            pyphen_lang="en_GB",
        )
        ledger.complete_run(run_id3, exit_code=0, status="completed")

        stats = ledger.get_stats()

        assert stats["total_runs"] == 3
        assert stats["completed_runs"] == 2
        assert stats["failed_runs"] == 1
        assert stats["tools_used"] == {"syllable_extractor", "syllable_extractor_nltk"}
        assert stats["languages_used"] == {"en_US", "de_DE", "en_GB"}

        ledger.close()


class TestCompleteWorkflow:
    """Integration tests for complete extraction workflows."""

    def test_complete_single_file_workflow(self, tmp_path):
        """Test complete workflow for single file extraction."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        # Start run
        run_id = ledger.start_run(
            extractor_tool="syllable_extractor",
            extractor_version="0.2.0",
            pyphen_lang="en_US",
            min_len=2,
            max_len=8,
            command_line="python -m build_tools.syllable_extractor --file input.txt",
        )

        # Record input
        ledger.record_input(run_id, Path("/data/corpus/input.txt"))

        # Record output
        ledger.record_output(
            run_id,
            output_path=Path("/data/raw/output.syllables"),
            syllable_count=500,
            unique_syllable_count=250,
            meta_path=Path("/data/raw/output.meta"),
        )

        # Complete run
        ledger.complete_run(run_id, exit_code=0, status="completed")

        # Verify everything was recorded
        run = ledger.get_run(run_id)
        assert run is not None
        assert run["status"] == "completed"
        assert run["exit_code"] == 0

        inputs = ledger.get_run_inputs(run_id)
        assert len(inputs) == 1
        assert inputs[0]["source_path"] == "/data/corpus/input.txt"

        outputs = ledger.get_run_outputs(run_id)
        assert len(outputs) == 1
        assert outputs[0]["unique_syllable_count"] == 250

        # Reverse lookup
        found_run = ledger.find_run_by_output(Path("/data/raw/output.syllables"))
        assert found_run is not None
        assert found_run["id"] == run_id

        ledger.close()

    def test_complete_batch_workflow(self, tmp_path):
        """Test complete workflow for batch processing multiple files."""
        ledger = CorpusLedger(db_path=tmp_path / "test.db")

        # Start run
        run_id = ledger.start_run(
            extractor_tool="syllable_extractor",
            extractor_version="0.2.0",
            recursive=True,
            pattern="*.txt",
            command_line="python -m build_tools.syllable_extractor --source /data/ --recursive",
        )

        # Record input directory
        ledger.record_input(run_id, Path("/data/corpus/"), file_count=5)

        # Record multiple outputs
        ledger.record_output(run_id, Path("/data/raw/file1.syllables"), unique_syllable_count=100)
        ledger.record_output(run_id, Path("/data/raw/file2.syllables"), unique_syllable_count=150)
        ledger.record_output(run_id, Path("/data/raw/file3.syllables"), unique_syllable_count=200)

        # Complete run
        ledger.complete_run(run_id, exit_code=0, status="completed")

        # Verify batch processing recorded correctly
        outputs = ledger.get_run_outputs(run_id)
        assert len(outputs) == 3

        total_unique = sum(out["unique_syllable_count"] for out in outputs)
        assert total_unique == 450

        ledger.close()


class TestSchemaHelpers:
    """Test suite for schema helper functions."""

    def test_get_schema_description(self):
        """Test that schema description is generated."""
        description = get_schema_description()

        assert "runs" in description
        assert "inputs" in description
        assert "outputs" in description
        assert "extractor_tool" in description
        assert "Indexes" in description

    def test_schema_version_constant(self):
        """Test that schema version is defined."""
        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1
