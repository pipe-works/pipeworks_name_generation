"""
Shared corpus database ledger helpers for extraction tools.

This module provides a context manager and helper functions for integrating
with the corpus database ledger. The ledger is observational only - it records
what happened but does not influence extraction behavior.

These utilities eliminate duplicated corpus DB integration patterns across
the pyphen and NLTK syllable extractors.

Usage::

    from build_tools.tui_common.ledger import ExtractionLedgerContext

    with ExtractionLedgerContext(
        extractor_tool="pyphen_syllable_extractor",
        extractor_version="0.5.0",
        min_len=2,
        max_len=8,
        quiet=False,
    ) as ctx:
        # Record inputs
        ctx.record_input(input_path)

        # ... do extraction ...

        # Record outputs
        ctx.record_output(
            output_path=syllables_path,
            unique_syllable_count=len(syllables),
            meta_path=metadata_path,
        )

        # Mark success or failure
        ctx.set_result(success=True)
"""

from __future__ import annotations

import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from build_tools.tui_common.cli_utils import CORPUS_DB_AVAILABLE, record_corpus_db_safe

if TYPE_CHECKING:
    from build_tools.corpus_db import CorpusLedger


class ExtractionLedgerContext:
    """
    Context manager for corpus database ledger integration.

    Handles the full lifecycle of ledger operations:
    - Initialize ledger on entry
    - Start run with extraction parameters
    - Record inputs and outputs during extraction
    - Complete run with success/failure status on exit
    - Close ledger connection

    All operations are safe - failures are logged but don't block extraction.

    Attributes:
        extractor_tool: Name of the extraction tool
        extractor_version: Version string of the tool
        pyphen_lang: Language code for pyphen (None for NLTK)
        min_len: Minimum syllable length constraint
        max_len: Maximum syllable length constraint
        recursive: Whether directory scanning was recursive
        pattern: File pattern for directory scanning
        command_line: Full command-line invocation
        quiet: Suppress warning messages

    Example:
        >>> with ExtractionLedgerContext(
        ...     extractor_tool="pyphen_syllable_extractor",
        ...     extractor_version="0.5.0",
        ...     pyphen_lang="en_US",
        ...     min_len=2,
        ...     max_len=8,
        ... ) as ctx:
        ...     ctx.record_input(Path("input.txt"))
        ...     # ... extraction ...
        ...     ctx.record_output(syllables_path, len(syllables), metadata_path)
        ...     ctx.set_result(success=True)
    """

    def __init__(
        self,
        extractor_tool: str,
        extractor_version: str = "unknown",
        pyphen_lang: Optional[str] = None,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None,
        recursive: bool = False,
        pattern: Optional[str] = None,
        command_line: Optional[str] = None,
        quiet: bool = False,
    ) -> None:
        """
        Initialize the ledger context.

        Args:
            extractor_tool: Name of the extraction tool
            extractor_version: Version string of the tool
            pyphen_lang: Language code for pyphen (None for NLTK or auto-detect)
            min_len: Minimum syllable length constraint
            max_len: Maximum syllable length constraint
            recursive: Whether directory scanning was recursive
            pattern: File pattern for directory scanning
            command_line: Full command-line invocation (defaults to sys.argv)
            quiet: Suppress warning messages
        """
        self.extractor_tool = extractor_tool
        self.extractor_version = extractor_version
        self.pyphen_lang = pyphen_lang
        self.min_len = min_len
        self.max_len = max_len
        self.recursive = recursive
        self.pattern = pattern
        self.command_line = command_line or " ".join(sys.argv)
        self.quiet = quiet

        self._ledger: Optional[CorpusLedger] = None
        self._run_id: Optional[int] = None
        self._success: Optional[bool] = None

    @property
    def is_available(self) -> bool:
        """Check if corpus DB integration is available and initialized."""
        return self._ledger is not None and self._run_id is not None

    @property
    def run_id(self) -> Optional[int]:
        """Get the current run ID, or None if not initialized."""
        return self._run_id

    def __enter__(self) -> "ExtractionLedgerContext":
        """
        Enter context: initialize ledger and start run.

        Returns:
            Self for use in with statement.
        """
        if not CORPUS_DB_AVAILABLE:
            return self

        try:
            from build_tools.corpus_db import CorpusLedger

            self._ledger = CorpusLedger()
            self._run_id = self._ledger.start_run(
                extractor_tool=self.extractor_tool,
                extractor_version=self.extractor_version,
                pyphen_lang=self.pyphen_lang,
                min_len=self.min_len,
                max_len=self.max_len,
                recursive=self.recursive,
                pattern=self.pattern,
                command_line=self.command_line,
            )
        except Exception as e:
            if not self.quiet:
                print(f"Warning: Failed to initialize corpus_db: {e}", file=sys.stderr)
            self._ledger = None
            self._run_id = None

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit context: complete run and close ledger.

        Determines success based on:
        1. Explicit set_result() call
        2. Whether an exception occurred
        """
        if not self.is_available:
            return

        # Determine final status
        if exc_type is not None:
            # Exception occurred
            exit_code = 1
            status = "failed"
        elif self._success is False:
            # Explicitly marked as failed
            exit_code = 1
            status = "failed"
        elif self._success is True:
            # Explicitly marked as success
            exit_code = 0
            status = "completed"
        else:
            # No explicit result, assume success if no exception
            exit_code = 0
            status = "completed"

        # Complete the run (ledger is guaranteed non-None when is_available is True)
        ledger = self._ledger
        run_id = self._run_id
        if ledger is not None and run_id is not None:
            self._safe_call(
                "complete run",
                lambda: ledger.complete_run(run_id, exit_code=exit_code, status=status),
            )

            # Close the ledger
            self._safe_call("close ledger", lambda: ledger.close(), quiet=True)

    def _safe_call(
        self,
        operation: str,
        func: Callable[[], Any],
        quiet: Optional[bool] = None,
    ) -> Any:
        """
        Execute a ledger operation with safe error handling.

        Args:
            operation: Description of the operation
            func: Callable to execute
            quiet: Override instance quiet setting

        Returns:
            Result of func() if successful, None if failed
        """
        if quiet is None:
            quiet = self.quiet
        return record_corpus_db_safe(operation, func, quiet=quiet)

    def set_result(self, success: bool) -> None:
        """
        Explicitly set the extraction result.

        Call this before exiting the context to indicate success or failure.
        If not called, success is assumed unless an exception occurs.

        Args:
            success: True if extraction succeeded, False if failed
        """
        self._success = success

    def record_input(
        self,
        source_path: Path,
        file_count: Optional[int] = None,
    ) -> None:
        """
        Record an input source for this run.

        Args:
            source_path: Path to input file or directory
            file_count: Number of files if source_path is a directory
        """
        if not self.is_available:
            return

        ledger = self._ledger
        run_id = self._run_id
        if ledger is not None and run_id is not None:
            self._safe_call(
                "input",
                lambda: ledger.record_input(run_id, source_path, file_count),
            )

    def record_inputs(
        self,
        files: list[Path],
        source_dir: Optional[Path] = None,
    ) -> None:
        """
        Record multiple input files for this run.

        If source_dir is provided, records the directory with file count.
        Otherwise, records each file individually.

        Args:
            files: List of input file paths
            source_dir: Source directory (if files were discovered from a directory)
        """
        if not self.is_available:
            return

        ledger = self._ledger
        run_id = self._run_id
        if ledger is not None and run_id is not None:
            if source_dir is not None:
                # Record directory with file count
                self._safe_call(
                    "input",
                    lambda: ledger.record_input(run_id, source_dir, file_count=len(files)),
                )
            else:
                # Record each file individually
                for fp in files:
                    self._safe_call("input", partial(ledger.record_input, run_id, fp))

    def record_output(
        self,
        output_path: Path,
        unique_syllable_count: Optional[int] = None,
        meta_path: Optional[Path] = None,
    ) -> None:
        """
        Record an output file for this run.

        Args:
            output_path: Path to generated syllables file
            unique_syllable_count: Number of unique syllables extracted
            meta_path: Path to corresponding metadata file
        """
        if not self.is_available:
            return

        ledger = self._ledger
        run_id = self._run_id
        if ledger is not None and run_id is not None:
            self._safe_call(
                "output",
                lambda: ledger.record_output(
                    run_id,
                    output_path=output_path,
                    unique_syllable_count=unique_syllable_count,
                    meta_path=meta_path,
                ),
            )


__all__ = [
    "ExtractionLedgerContext",
    "CORPUS_DB_AVAILABLE",
]
