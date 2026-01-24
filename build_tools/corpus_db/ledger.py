"""
Corpus extraction run ledger - observational database for build provenance.

This module provides the CorpusLedger class, which manages SQLite-based tracking
of all syllable extraction runs. The ledger records who ran what extraction tool,
when, with which settings, and what outputs were produced.

Critical Design Principle:
    The ledger is **observational only** - it records what happened but does not
    influence extraction behavior. Extractors remain pure, deterministic functions.
    The ledger just watches and remembers.

Typical Usage:
    >>> from build_tools.corpus_db import CorpusLedger
    >>> from pathlib import Path
    >>>
    >>> # Initialize ledger (finds or creates database)
    >>> ledger = CorpusLedger()
    >>>
    >>> # Start a new extraction run
    >>> run_id = ledger.start_run(
    ...     extractor_tool="syllable_extractor",
    ...     extractor_version="0.2.0",
    ...     pyphen_lang="en_US",
    ...     min_len=2,
    ...     max_len=8,
    ...     command_line="python -m build_tools.syllable_extractor --file input.txt"
    ... )
    >>>
    >>> # Record input sources
    >>> ledger.record_input(run_id, Path("data/corpus/english.txt"))
    >>>
    >>> # ... extraction happens (ledger doesn't participate) ...
    >>>
    >>> # Record outputs
    >>> ledger.record_output(
    ...     run_id,
    ...     output_path=Path("data/raw/en_US/corpus_v1.syllables"),
    ...     syllable_count=5432,
    ...     unique_syllable_count=1234,
    ...     meta_path=Path("data/raw/en_US/corpus_v1.meta")
    ... )
    >>>
    >>> # Mark run complete
    >>> ledger.complete_run(run_id, exit_code=0, status="completed")
    >>>
    >>> # Query runs later
    >>> runs = ledger.get_runs_by_tool("syllable_extractor")
    >>> recent = ledger.get_recent_runs(limit=10)
"""

from __future__ import annotations

import socket
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schema import SCHEMA_VERSION, get_all_ddl_statements


class CorpusLedger:
    """
    Manages the corpus extraction run ledger database.

    The CorpusLedger provides a simple API for recording extraction runs,
    their inputs, outputs, and outcomes. All operations are append-only -
    runs are never modified or deleted once recorded.

    The database file location is configurable but defaults to:
    - data/raw/syllable_extractor.db

    Attributes:
        db_path: Path to the SQLite database file
        _conn: Active database connection (None if not connected)

    Example:
        >>> ledger = CorpusLedger()
        >>> run_id = ledger.start_run(
        ...     extractor_tool="syllable_extractor",
        ...     extractor_version="0.2.0",
        ...     pyphen_lang="en_US"
        ... )
        >>> ledger.complete_run(run_id, exit_code=0, status="completed")
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize the corpus ledger.

        Creates the database and tables if they don't exist. If the database
        already exists, validates the schema version.

        Args:
            db_path: Path to SQLite database file. If None, defaults to
                data/raw/syllable_extractor.db in the project root.

        Raises:
            sqlite3.Error: If database initialization fails

        Example:
            >>> # Use default location
            >>> ledger = CorpusLedger()
            >>>
            >>> # Use custom location
            >>> ledger = CorpusLedger(Path("_working/test.db"))
        """
        if db_path is None:
            # Default to data/raw/syllable_extractor.db
            # Assumes we're running from project root or tests
            project_root = Path.cwd()
            db_path = project_root / "data" / "raw" / "syllable_extractor.db"

        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._initialize_db()

    def _initialize_db(self) -> None:
        """
        Create database tables and indexes if they don't exist.

        This method is idempotent - safe to call multiple times. If the
        database already exists with the correct schema, no changes are made.

        Raises:
            sqlite3.Error: If database creation fails
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Execute all DDL statements
            for ddl in get_all_ddl_statements():
                cursor.execute(ddl)

            # Check if schema version is recorded
            cursor.execute(
                "SELECT version FROM schema_version WHERE version = ?", (SCHEMA_VERSION,)
            )
            if cursor.fetchone() is None:
                # Record schema version
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, now),
                )

            conn.commit()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager for database connections.

        Ensures connections are properly managed and closed. Uses row factory
        for dict-like row access.

        Yields:
            Active SQLite connection

        Example:
            >>> with ledger._get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM runs")
        """
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row

        try:
            yield self._conn
        finally:
            # Keep connection open for reuse, but ensure changes are committed
            self._conn.commit()

    def close(self) -> None:
        """
        Close the database connection.

        Should be called when done with the ledger. Using the ledger as a
        context manager (with statement) is preferred as it handles cleanup
        automatically.

        Example:
            >>> ledger = CorpusLedger()
            >>> # ... use ledger ...
            >>> ledger.close()
            >>>
            >>> # Preferred: use context manager
            >>> with CorpusLedger() as ledger:
            ...     ledger.start_run(...)
        """
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "CorpusLedger":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures connection is closed."""
        self.close()

    def start_run(
        self,
        extractor_tool: str,
        extractor_version: str | None = None,
        pyphen_lang: str | None = None,
        auto_lang_detected: str | None = None,
        min_len: int | None = None,
        max_len: int | None = None,
        recursive: bool = False,
        pattern: str | None = None,
        command_line: str | None = None,
        notes: str | None = None,
    ) -> int:
        """
        Record the start of a new extraction run.

        Creates a new run record with status='running' and returns the run ID.
        The caller should use this ID to record inputs, outputs, and eventually
        mark the run complete or failed.

        Args:
            extractor_tool: Name of the extraction tool (e.g., 'syllable_extractor',
                'syllable_extractor_nltk', 'syllable_extractor_espeak')
            extractor_version: Version string or git SHA of the tool
            pyphen_lang: Pyphen language code (NULL for non-pyphen tools)
            auto_lang_detected: Auto-detected language code if auto-detection was used
            min_len: Minimum syllable length constraint
            max_len: Maximum syllable length constraint
            recursive: Whether source directory was processed recursively
            pattern: File pattern filter (e.g., '*.txt')
            command_line: Full command-line invocation for reproducibility
            notes: User-provided annotations about this run

        Returns:
            Unique run ID (integer) for this extraction run

        Example:
            >>> run_id = ledger.start_run(
            ...     extractor_tool="syllable_extractor",
            ...     extractor_version="0.2.0",
            ...     pyphen_lang="en_US",
            ...     min_len=2,
            ...     max_len=8,
            ...     command_line="python -m build_tools.syllable_extractor --file input.txt",
            ...     notes="Testing new corpus from Project Gutenberg"
            ... )
            >>> print(f"Started run {run_id}")
            Started run 42
        """
        # Get current timestamp in ISO 8601 format (UTC)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Get hostname for tracking which machine ran this
        hostname = socket.gethostname()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO runs (
                    run_timestamp, extractor_tool, extractor_version, hostname,
                    status, pyphen_lang, auto_lang_detected, min_len, max_len,
                    recursive, pattern, command_line, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    extractor_tool,
                    extractor_version,
                    hostname,
                    "running",  # Initial status
                    pyphen_lang,
                    auto_lang_detected,
                    min_len,
                    max_len,
                    1 if recursive else 0,
                    pattern,
                    command_line,
                    notes,
                ),
            )
            conn.commit()
            run_id = cursor.lastrowid
            # lastrowid is guaranteed to be not None after INSERT with AUTOINCREMENT
            assert run_id is not None, "Failed to get run_id from database"

        return run_id

    def record_input(
        self,
        run_id: int,
        source_path: Path,
        file_count: int | None = None,
    ) -> None:
        """
        Record an input source for a run.

        Associates an input file or directory with an extraction run. Multiple
        inputs can be recorded for a single run.

        Note: Paths are stored in POSIX format (forward slashes) for cross-platform
        compatibility.

        Args:
            run_id: Run ID from start_run()
            source_path: Path to input file or directory
            file_count: Number of files if source_path is a directory (None for single file)

        Example:
            >>> run_id = ledger.start_run("syllable_extractor", "0.2.0")
            >>> ledger.record_input(run_id, Path("data/corpus/english.txt"))
            >>> ledger.record_input(run_id, Path("data/corpus/german/"), file_count=42)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO inputs (run_id, source_path, file_count)
                VALUES (?, ?, ?)
                """,
                (run_id, source_path.as_posix(), file_count),
            )
            conn.commit()

    def record_output(
        self,
        run_id: int,
        output_path: Path,
        syllable_count: int | None = None,
        unique_syllable_count: int | None = None,
        meta_path: Path | None = None,
    ) -> None:
        """
        Record an output file for a run.

        Associates an output .syllables file with an extraction run. Multiple
        outputs can be recorded for a single run (e.g., batch processing).

        Note: Paths are stored in POSIX format (forward slashes) for cross-platform
        compatibility.

        Args:
            run_id: Run ID from start_run()
            output_path: Path to generated .syllables file
            syllable_count: Total number of syllables (including duplicates)
            unique_syllable_count: Number of unique syllables
            meta_path: Path to corresponding .meta file (if generated)

        Example:
            >>> ledger.record_output(
            ...     run_id=42,
            ...     output_path=Path("data/raw/en_US/corpus_v1.syllables"),
            ...     syllable_count=5432,
            ...     unique_syllable_count=1234,
            ...     meta_path=Path("data/raw/en_US/corpus_v1.meta")
            ... )
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO outputs (
                    run_id, output_path, syllable_count,
                    unique_syllable_count, meta_path
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    output_path.as_posix(),
                    syllable_count,
                    unique_syllable_count,
                    meta_path.as_posix() if meta_path else None,
                ),
            )
            conn.commit()

    def complete_run(
        self,
        run_id: int,
        exit_code: int,
        status: str = "completed",
    ) -> None:
        """
        Mark a run as complete or failed.

        Updates the run status and exit code. This should be called when
        extraction finishes, whether successfully or with errors.

        Args:
            run_id: Run ID from start_run()
            exit_code: Unix exit code (0 = success, non-zero = failure)
            status: Final status - one of 'completed', 'failed', 'interrupted'

        Raises:
            ValueError: If status is not a valid value

        Example:
            >>> # Successful run
            >>> ledger.complete_run(run_id, exit_code=0, status="completed")
            >>>
            >>> # Failed run
            >>> ledger.complete_run(run_id, exit_code=1, status="failed")
        """
        valid_statuses = {"completed", "failed", "interrupted"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE runs
                SET exit_code = ?, status = ?
                WHERE id = ?
                """,
                (exit_code, status, run_id),
            )
            conn.commit()

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        """
        Get details for a specific run.

        Args:
            run_id: Run ID to fetch

        Returns:
            Dictionary with run details, or None if run_id doesn't exist

        Example:
            >>> run = ledger.get_run(42)
            >>> if run:
            ...     print(f"Tool: {run['extractor_tool']}")
            ...     print(f"Status: {run['status']}")
            ...     print(f"Command: {run['command_line']}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_runs_by_tool(self, extractor_tool: str) -> list[dict[str, Any]]:
        """
        Get all runs for a specific extractor tool.

        Args:
            extractor_tool: Tool name to filter by (e.g., 'syllable_extractor')

        Returns:
            List of run dictionaries, ordered by timestamp descending (newest first)

        Example:
            >>> runs = ledger.get_runs_by_tool("syllable_extractor")
            >>> for run in runs:
            ...     print(f"Run {run['id']}: {run['pyphen_lang']} ({run['status']})")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM runs
                WHERE extractor_tool = ?
                ORDER BY run_timestamp DESC
                """,
                (extractor_tool,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the most recent extraction runs.

        Args:
            limit: Maximum number of runs to return (default: 10)

        Returns:
            List of run dictionaries, ordered by timestamp descending (newest first)

        Example:
            >>> recent = ledger.get_recent_runs(limit=5)
            >>> for run in recent:
            ...     print(f"{run['run_timestamp']}: {run['extractor_tool']}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM runs
                ORDER BY run_timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_run_inputs(self, run_id: int) -> list[dict[str, Any]]:
        """
        Get all input sources for a run.

        Args:
            run_id: Run ID to fetch inputs for

        Returns:
            List of input dictionaries with source_path and file_count

        Example:
            >>> inputs = ledger.get_run_inputs(42)
            >>> for inp in inputs:
            ...     print(f"Source: {inp['source_path']}")
            ...     if inp['file_count']:
            ...         print(f"  Files: {inp['file_count']}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM inputs WHERE run_id = ?",
                (run_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_run_outputs(self, run_id: int) -> list[dict[str, Any]]:
        """
        Get all outputs for a run.

        Args:
            run_id: Run ID to fetch outputs for

        Returns:
            List of output dictionaries with paths and syllable counts

        Example:
            >>> outputs = ledger.get_run_outputs(42)
            >>> for out in outputs:
            ...     print(f"Output: {out['output_path']}")
            ...     print(f"  Unique syllables: {out['unique_syllable_count']}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM outputs WHERE run_id = ?",
                (run_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def find_run_by_output(self, output_path: Path) -> dict[str, Any] | None:
        """
        Find which run produced a specific output file.

        This is the "reverse lookup" - given a .syllables file, find out
        how it was created.

        Args:
            output_path: Path to .syllables file to search for

        Returns:
            Run dictionary if found, None otherwise

        Example:
            >>> run = ledger.find_run_by_output(Path("data/raw/en_US/corpus_v1.syllables"))
            >>> if run:
            ...     print(f"Created by: {run['command_line']}")
            ...     print(f"On: {run['run_timestamp']}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.* FROM runs r
                JOIN outputs o ON r.id = o.run_id
                WHERE o.output_path = ?
                """,
                (output_path.as_posix(),),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_stats(self) -> dict[str, Any]:
        """
        Get overall ledger statistics.

        Returns summary stats about all recorded runs, useful for understanding
        build history at a glance.

        Returns:
            Dictionary with statistics:
                - total_runs: Total number of runs recorded
                - completed_runs: Runs with status='completed'
                - failed_runs: Runs with status='failed'
                - tools_used: Set of unique extractor tools
                - languages_used: Set of unique pyphen language codes

        Example:
            >>> stats = ledger.get_stats()
            >>> print(f"Total runs: {stats['total_runs']}")
            >>> print(f"Success rate: {stats['completed_runs']/stats['total_runs']*100:.1f}%")
            >>> print(f"Tools: {', '.join(stats['tools_used'])}")
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total runs
            cursor.execute("SELECT COUNT(*) FROM runs")
            total_runs = cursor.fetchone()[0]

            # Completed runs
            cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'completed'")
            completed_runs = cursor.fetchone()[0]

            # Failed runs
            cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'failed'")
            failed_runs = cursor.fetchone()[0]

            # Unique tools
            cursor.execute("SELECT DISTINCT extractor_tool FROM runs")
            tools_used = {row[0] for row in cursor.fetchall()}

            # Unique languages
            cursor.execute("SELECT DISTINCT pyphen_lang FROM runs WHERE pyphen_lang IS NOT NULL")
            languages_used = {row[0] for row in cursor.fetchall()}

            return {
                "total_runs": total_runs,
                "completed_runs": completed_runs,
                "failed_runs": failed_runs,
                "tools_used": tools_used,
                "languages_used": languages_used,
            }
