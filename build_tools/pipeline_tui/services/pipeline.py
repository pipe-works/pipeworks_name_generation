"""
Pipeline execution service for Pipeline TUI.

This module provides subprocess-based execution of the syllable extraction
pipeline stages (extraction, normalization, annotation) with progress
monitoring, cancellation support, and log capture.

**Design Principles:**

- Non-blocking execution via asyncio subprocess
- Cancellation support via process termination
- Real-time log capture and progress updates
- Clean error handling with informative messages

**Usage Example:**

    >>> from build_tools.pipeline_tui.services.pipeline import PipelineExecutor
    >>> from build_tools.pipeline_tui.core.state import ExtractionConfig, ExtractorType
    >>>
    >>> config = ExtractionConfig(
    ...     extractor_type=ExtractorType.PYPHEN,
    ...     source_path=Path("/data/corpus"),
    ...     output_dir=Path("_working/output"),
    ...     language="en_US",
    ... )
    >>>
    >>> executor = PipelineExecutor()
    >>> result = await executor.run_pipeline(
    ...     config=config,
    ...     run_normalize=True,
    ...     run_annotate=True,
    ...     on_progress=lambda stage, pct, msg: print(f"{stage}: {pct}% - {msg}"),
    ... )
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from build_tools.pipeline_tui.core.state import ExtractionConfig


# Progress callback type: (stage, percent, message) -> None
ProgressCallback = Callable[[str, int, str], None]


@dataclass
class StageResult:
    """
    Result from executing a single pipeline stage.

    Attributes:
        stage: Name of the stage (extraction, normalization, annotation)
        success: Whether the stage completed successfully
        output_path: Path to the output (run directory or file)
        return_code: Process return code
        stdout: Captured standard output
        stderr: Captured standard error
        duration_seconds: How long the stage took
        error_message: Error message if stage failed
    """

    stage: str
    success: bool
    output_path: Path | None = None
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    error_message: str = ""


@dataclass
class PipelineResult:
    """
    Result from executing the full pipeline.

    Attributes:
        success: Whether all stages completed successfully
        stages: List of individual stage results
        run_directory: Path to the output run directory
        cancelled: Whether the pipeline was cancelled
        total_duration_seconds: Total pipeline duration
    """

    success: bool
    stages: list[StageResult] = field(default_factory=list)
    run_directory: Path | None = None
    cancelled: bool = False
    total_duration_seconds: float = 0.0


class PipelineExecutor:
    """
    Executes pipeline stages as subprocesses with progress monitoring.

    This class manages the execution of extraction, normalization, and
    annotation stages as separate Python subprocesses. It provides:

    - Real-time stdout/stderr capture
    - Progress updates via callbacks
    - Cancellation support
    - Clean error handling

    Attributes:
        _current_process: Currently running subprocess (for cancellation)
        _cancelled: Flag indicating if cancellation was requested

    Example:
        >>> executor = PipelineExecutor()
        >>> result = await executor.run_pipeline(config, on_progress=callback)
        >>> if result.success:
        ...     print(f"Output: {result.run_directory}")
    """

    def __init__(self) -> None:
        """Initialize the pipeline executor."""
        self._current_process: asyncio.subprocess.Process | None = None
        self._cancelled: bool = False

    async def run_pipeline(
        self,
        config: "ExtractionConfig",
        run_normalize: bool = True,
        run_annotate: bool = True,
        on_progress: ProgressCallback | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> PipelineResult:
        """
        Execute the full pipeline with configured stages.

        Runs extraction, then optionally normalization and annotation.
        Progress is reported via callbacks for UI updates.

        Args:
            config: Extraction configuration specifying source, output, etc.
            run_normalize: Whether to run normalization after extraction
            run_annotate: Whether to run annotation after normalization
            on_progress: Callback for progress updates (stage, percent, message)
            on_log: Callback for log messages

        Returns:
            PipelineResult with success status and stage results

        Raises:
            ValueError: If config is invalid
        """
        self._cancelled = False
        start_time = datetime.now()
        stages: list[StageResult] = []
        run_directory: Path | None = None

        # Validate config
        is_valid, error = config.is_valid()
        if not is_valid:
            return PipelineResult(
                success=False,
                stages=[
                    StageResult(
                        stage="validation",
                        success=False,
                        error_message=error,
                    )
                ],
            )

        def log(msg: str) -> None:
            """Helper to send log messages."""
            if on_log:
                on_log(msg)

        def progress(stage: str, pct: int, msg: str) -> None:
            """Helper to send progress updates."""
            if on_progress:
                on_progress(stage, pct, msg)

        try:
            # Stage 1: Extraction
            progress("extraction", 0, "Starting extraction...")
            log(f"Starting extraction from {config.source_path}")

            extraction_result = await self._run_extraction(config, log)
            stages.append(extraction_result)

            if not extraction_result.success or self._cancelled:
                return PipelineResult(
                    success=False,
                    stages=stages,
                    cancelled=self._cancelled,
                    total_duration_seconds=(datetime.now() - start_time).total_seconds(),
                )

            run_directory = extraction_result.output_path
            progress("extraction", 100, "Extraction complete")
            log(f"Extraction complete: {run_directory}")

            # Stage 2: Normalization (optional)
            if run_normalize and not self._cancelled:
                progress("normalization", 0, "Starting normalization...")
                log("Starting normalization")

                norm_result = await self._run_normalization(config, run_directory, log)
                stages.append(norm_result)

                if not norm_result.success or self._cancelled:
                    return PipelineResult(
                        success=False,
                        stages=stages,
                        run_directory=run_directory,
                        cancelled=self._cancelled,
                        total_duration_seconds=(datetime.now() - start_time).total_seconds(),
                    )

                progress("normalization", 100, "Normalization complete")
                log("Normalization complete")

            # Stage 3: Annotation (optional, requires normalization)
            if run_annotate and run_normalize and not self._cancelled:
                progress("annotation", 0, "Starting annotation...")
                log("Starting feature annotation")

                annot_result = await self._run_annotation(config, run_directory, log)
                stages.append(annot_result)

                if not annot_result.success or self._cancelled:
                    return PipelineResult(
                        success=False,
                        stages=stages,
                        run_directory=run_directory,
                        cancelled=self._cancelled,
                        total_duration_seconds=(datetime.now() - start_time).total_seconds(),
                    )

                progress("annotation", 100, "Annotation complete")
                log("Feature annotation complete")

                # Stage 4: SQLite database build (after annotation)
                if not self._cancelled:
                    progress("database", 0, "Building SQLite database...")
                    log("Building corpus SQLite database")

                    db_result = await self._run_database_build(run_directory, log)
                    stages.append(db_result)

                    if not db_result.success or self._cancelled:
                        return PipelineResult(
                            success=False,
                            stages=stages,
                            run_directory=run_directory,
                            cancelled=self._cancelled,
                            total_duration_seconds=(datetime.now() - start_time).total_seconds(),
                        )

                    progress("database", 100, "Database build complete")
                    log("Corpus database built")

            # Success
            total_duration = (datetime.now() - start_time).total_seconds()
            log(f"Pipeline complete in {total_duration:.1f}s")

            return PipelineResult(
                success=True,
                stages=stages,
                run_directory=run_directory,
                total_duration_seconds=total_duration,
            )

        except asyncio.CancelledError:
            log("Pipeline cancelled")
            return PipelineResult(
                success=False,
                stages=stages,
                run_directory=run_directory,
                cancelled=True,
                total_duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

    async def cancel(self) -> None:
        """
        Cancel the currently running pipeline.

        Terminates the current subprocess if one is running.
        """
        self._cancelled = True
        if self._current_process is not None:
            try:
                self._current_process.terminate()
                # Give process time to terminate gracefully
                try:
                    await asyncio.wait_for(self._current_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if not terminated
                    self._current_process.kill()
            except ProcessLookupError:
                pass  # Process already terminated

    async def _run_extraction(
        self,
        config: "ExtractionConfig",
        log: Callable[[str], None],
    ) -> StageResult:
        """
        Run the extraction stage.

        Args:
            config: Extraction configuration
            log: Log callback

        Returns:
            StageResult with extraction outcome
        """
        from build_tools.pipeline_tui.core.state import ExtractorType

        start_time = datetime.now()

        # Select module based on extractor type
        if config.extractor_type == ExtractorType.PYPHEN:
            module = "build_tools.pyphen_syllable_extractor"
        else:
            module = "build_tools.nltk_syllable_extractor"

        # Build base command
        cmd = [
            sys.executable,
            "-m",
            module,
        ]

        # Add input specification (files or directory)
        if config.has_file_selection:
            # Use --files for specific file selection
            cmd.append("--files")
            for file_path in config.selected_files:
                cmd.append(str(file_path))
        else:
            # Use --source for directory scan
            cmd.extend(
                [
                    "--source",
                    str(config.source_path),
                    "--pattern",
                    config.file_pattern,
                ]
            )

        # Add common options
        cmd.extend(
            [
                "--min",
                str(config.min_syllable_length),
                "--max",
                str(config.max_syllable_length),
                "--output",
                str(config.output_dir),
            ]
        )

        # Add language option for pyphen
        if config.extractor_type == ExtractorType.PYPHEN:
            if config.language == "auto":
                cmd.append("--auto")
            else:
                cmd.extend(["--lang", config.language])

        log(f"Running: {' '.join(cmd)}")

        # Execute subprocess
        stdout, stderr, return_code = await self._run_subprocess(cmd)
        duration = (datetime.now() - start_time).total_seconds()

        # Parse output to find run directory
        run_directory = self._parse_run_directory(stdout, config)

        if return_code == 0:
            return StageResult(
                stage="extraction",
                success=True,
                output_path=run_directory,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )
        else:
            error_msg = stderr.strip() if stderr else f"Extraction failed with code {return_code}"
            return StageResult(
                stage="extraction",
                success=False,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                error_message=error_msg,
            )

    async def _run_normalization(
        self,
        config: "ExtractionConfig",
        run_directory: Path | None,
        log: Callable[[str], None],
    ) -> StageResult:
        """
        Run the normalization stage.

        Args:
            config: Extraction configuration
            run_directory: Path to extraction run directory
            log: Log callback

        Returns:
            StageResult with normalization outcome
        """
        from build_tools.pipeline_tui.core.state import ExtractorType

        if run_directory is None:
            return StageResult(
                stage="normalization",
                success=False,
                error_message="No run directory from extraction",
            )

        start_time = datetime.now()

        # Select normalizer based on extractor type
        if config.extractor_type == ExtractorType.PYPHEN:
            module = "build_tools.pyphen_syllable_normaliser"
        else:
            module = "build_tools.nltk_syllable_normaliser"

        cmd = [
            sys.executable,
            "-m",
            module,
            "--run-dir",
            str(run_directory),
            "--min",
            str(config.min_syllable_length),
            "--max",
            str(config.max_syllable_length),
        ]

        log(f"Running: {' '.join(cmd)}")

        # Execute subprocess
        stdout, stderr, return_code = await self._run_subprocess(cmd)
        duration = (datetime.now() - start_time).total_seconds()

        if return_code == 0:
            return StageResult(
                stage="normalization",
                success=True,
                output_path=run_directory,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )
        else:
            error_msg = (
                stderr.strip() if stderr else f"Normalization failed with code {return_code}"
            )
            return StageResult(
                stage="normalization",
                success=False,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                error_message=error_msg,
            )

    async def _run_annotation(
        self,
        config: "ExtractionConfig",
        run_directory: Path | None,
        log: Callable[[str], None],
    ) -> StageResult:
        """
        Run the annotation stage.

        Args:
            config: Extraction configuration
            run_directory: Path to extraction run directory
            log: Log callback

        Returns:
            StageResult with annotation outcome
        """
        from build_tools.pipeline_tui.core.state import ExtractorType

        if run_directory is None:
            return StageResult(
                stage="annotation",
                success=False,
                error_message="No run directory from extraction",
            )

        start_time = datetime.now()

        # Determine file prefix based on extractor type
        if config.extractor_type == ExtractorType.PYPHEN:
            prefix = "pyphen"
        else:
            prefix = "nltk"

        syllables_file = run_directory / f"{prefix}_syllables_unique.txt"
        frequencies_file = run_directory / f"{prefix}_syllables_frequencies.json"

        if not syllables_file.exists():
            return StageResult(
                stage="annotation",
                success=False,
                error_message=f"Syllables file not found: {syllables_file}",
            )

        if not frequencies_file.exists():
            return StageResult(
                stage="annotation",
                success=False,
                error_message=f"Frequencies file not found: {frequencies_file}",
            )

        cmd = [
            sys.executable,
            "-m",
            "build_tools.syllable_feature_annotator",
            "--syllables",
            str(syllables_file),
            "--frequencies",
            str(frequencies_file),
        ]

        log(f"Running: {' '.join(cmd)}")

        # Execute subprocess
        stdout, stderr, return_code = await self._run_subprocess(cmd)
        duration = (datetime.now() - start_time).total_seconds()

        if return_code == 0:
            output_file = run_directory / "data" / f"{prefix}_syllables_annotated.json"
            return StageResult(
                stage="annotation",
                success=True,
                output_path=output_file,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )
        else:
            error_msg = stderr.strip() if stderr else f"Annotation failed with code {return_code}"
            return StageResult(
                stage="annotation",
                success=False,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                error_message=error_msg,
            )

    async def _run_database_build(
        self,
        run_directory: Path | None,
        log: Callable[[str], None],
    ) -> StageResult:
        """
        Run the SQLite database build stage.

        Converts the annotated JSON to a SQLite database for efficient
        querying in the TUI tools.

        Args:
            run_directory: Path to extraction run directory
            log: Log callback

        Returns:
            StageResult with database build outcome
        """
        if run_directory is None:
            return StageResult(
                stage="database",
                success=False,
                error_message="No run directory for database build",
            )

        start_time = datetime.now()

        cmd = [
            sys.executable,
            "-m",
            "build_tools.corpus_sqlite_builder",
            str(run_directory),
            "--force",  # Overwrite if exists
        ]

        log(f"Running: {' '.join(cmd)}")

        # Execute subprocess
        stdout, stderr, return_code = await self._run_subprocess(cmd)
        duration = (datetime.now() - start_time).total_seconds()

        if return_code == 0:
            output_file = run_directory / "data" / "corpus.db"
            return StageResult(
                stage="database",
                success=True,
                output_path=output_file,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )
        else:
            error_msg = (
                stderr.strip() if stderr else f"Database build failed with code {return_code}"
            )
            return StageResult(
                stage="database",
                success=False,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                error_message=error_msg,
            )

    async def _run_subprocess(
        self,
        cmd: list[str],
    ) -> tuple[str, str, int]:
        """
        Run a subprocess and capture output.

        Args:
            cmd: Command to run as list of strings

        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        self._current_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await self._current_process.communicate()
            return_code = self._current_process.returncode or 0

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            return stdout, stderr, return_code

        finally:
            self._current_process = None

    def _parse_run_directory(
        self,
        stdout: str,
        config: "ExtractionConfig",
    ) -> Path | None:
        """
        Parse extraction output to find the run directory.

        The extractor outputs the run directory path in stdout.
        We look for "Run Directory:" lines which contain the timestamp-based
        path like YYYYMMDD_HHMMSS. The extractor may print without the
        _pyphen/_nltk suffix, so we try appending it.

        Args:
            stdout: Captured stdout from extraction
            config: Extraction configuration

        Returns:
            Path to run directory, or None if not found
        """
        import re

        from build_tools.pipeline_tui.core.state import ExtractorType

        # Determine expected suffix
        if config.extractor_type == ExtractorType.PYPHEN:
            suffix = "_pyphen"
        else:
            suffix = "_nltk"

        # Pattern to match timestamp directories (YYYYMMDD_HHMMSS)
        timestamp_pattern = re.compile(r"\d{8}_\d{6}")

        # First pass: look specifically for "Run Directory:" lines
        # These contain the specific run path, not the base output dir
        lines = stdout.split("\n")
        for line in lines:
            if "run directory:" in line.lower():
                # Extract path from line
                parts = line.split(":")
                if len(parts) >= 2:
                    path_str = ":".join(parts[1:]).strip().rstrip("/")
                    # Verify this looks like a run directory (has timestamp)
                    if timestamp_pattern.search(path_str):
                        path = Path(path_str)

                        # Try the path as-is first
                        if path.exists() and path.is_dir():
                            return path

                        # Try appending the suffix (extractor prints without suffix)
                        path_with_suffix = Path(str(path) + suffix)
                        if path_with_suffix.exists() and path_with_suffix.is_dir():
                            return path_with_suffix

        # Second pass: look for "Output Directory:" in summary section
        # (after "SUMMARY" or near end of output)
        for line in lines:
            if "output directory:" in line.lower():
                parts = line.split(":")
                if len(parts) >= 2:
                    path_str = ":".join(parts[1:]).strip().rstrip("/")
                    # Only consider paths that look like run directories (have timestamp)
                    if timestamp_pattern.search(path_str):
                        path = Path(path_str)

                        if path.exists() and path.is_dir():
                            return path

                        path_with_suffix = Path(str(path) + suffix)
                        if path_with_suffix.exists() and path_with_suffix.is_dir():
                            return path_with_suffix

        # Fallback: scan output directory for most recent run
        if config.output_dir and config.output_dir.exists():
            run_dirs = sorted(
                [d for d in config.output_dir.iterdir() if d.is_dir() and d.name.endswith(suffix)],
                reverse=True,  # Most recent first
            )
            if run_dirs:
                return run_dirs[0]

        return None
