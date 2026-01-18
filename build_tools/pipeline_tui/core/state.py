"""
Application state management for Pipeline TUI.

This module defines the state dataclasses that track pipeline configuration,
job status, and UI state throughout the application lifecycle.

**State Hierarchy:**

- :class:`PipelineState` - Top-level application state
  - :class:`ExtractionConfig` - Extractor settings (pyphen/nltk, options)
  - :class:`JobState` - Current job execution status
  - UI state (current screen, last browsed directory, etc.)

**Design Principles:**

- Immutable where possible (use dataclass frozen=True for config)
- Centralized state prevents scattered UI state
- State changes trigger UI updates via Textual reactivity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path


class ExtractorType(Enum):
    """Available syllable extractor types."""

    PYPHEN = auto()  # Multi-language, typographic hyphenation
    NLTK = auto()  # English-only, phonetic splitting


class JobStatus(Enum):
    """Pipeline job execution status."""

    IDLE = auto()  # No job running
    CONFIGURING = auto()  # User configuring job
    RUNNING = auto()  # Job in progress
    COMPLETED = auto()  # Job finished successfully
    FAILED = auto()  # Job finished with error
    CANCELLED = auto()  # Job cancelled by user


@dataclass
class ExtractionConfig:
    """
    Configuration for a syllable extraction job.

    Attributes:
        extractor_type: Which extractor to use (pyphen or nltk)
        source_path: Input file or directory path
        output_dir: Output directory for results
        language: Language code for pyphen (e.g., "en_US", "de_DE") or "auto"
                  for automatic detection via langdetect
        min_syllable_length: Minimum syllable length filter
        max_syllable_length: Maximum syllable length filter
        file_pattern: Glob pattern for input files (e.g., "*.txt")
    """

    extractor_type: ExtractorType = ExtractorType.PYPHEN
    source_path: Path | None = None
    output_dir: Path | None = None
    language: str = "auto"
    min_syllable_length: int = 2
    max_syllable_length: int = 8
    file_pattern: str = "*.txt"

    def is_valid(self) -> tuple[bool, str]:
        """
        Check if configuration is valid for execution.

        Returns:
            Tuple of (is_valid, error_message). Error message is empty if valid.
        """
        if self.source_path is None:
            return (False, "No source path selected")
        if not self.source_path.exists():
            return (False, f"Source path does not exist: {self.source_path}")
        if self.output_dir is None:
            return (False, "No output directory selected")
        if self.min_syllable_length > self.max_syllable_length:
            return (False, "Min syllable length cannot exceed max")
        return (True, "")


@dataclass
class JobState:
    """
    State for a running or completed pipeline job.

    Attributes:
        status: Current job status
        config: Configuration used for this job
        start_time: When the job started
        end_time: When the job ended (if completed/failed/cancelled)
        current_stage: Current pipeline stage (extract/normalize/annotate)
        progress_percent: Estimated progress (0-100)
        log_messages: List of log messages from the job
        output_path: Path to output directory (set after job starts)
        error_message: Error message if job failed
    """

    status: JobStatus = JobStatus.IDLE
    config: ExtractionConfig | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    current_stage: str = ""
    progress_percent: int = 0
    log_messages: list[str] = field(default_factory=list)
    output_path: Path | None = None
    error_message: str = ""

    def add_log(self, message: str) -> None:
        """
        Add a log message with timestamp.

        Args:
            message: Log message to add
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_messages.append(f"[{timestamp}] {message}")

    def duration_seconds(self) -> float | None:
        """
        Get job duration in seconds.

        Returns:
            Duration in seconds, or None if job hasn't started or is still running
        """
        if self.start_time is None:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


@dataclass
class PipelineState:
    """
    Top-level application state for Pipeline TUI.

    This dataclass holds all state for the application, including
    configuration, job status, and UI state.

    Attributes:
        config: Current extraction configuration
        job: Current or most recent job state
        last_source_dir: Last browsed source directory (for browser initial path)
        last_output_dir: Last browsed output directory
        run_normalize: Whether to run normalization after extraction
        run_annotate: Whether to run annotation after normalization
    """

    config: ExtractionConfig = field(default_factory=ExtractionConfig)
    job: JobState = field(default_factory=JobState)
    last_source_dir: Path = field(default_factory=Path.home)
    last_output_dir: Path = field(default_factory=lambda: Path.cwd() / "_working" / "output")
    run_normalize: bool = True
    run_annotate: bool = True

    def reset_job(self) -> None:
        """Reset job state to idle, preserving configuration."""
        self.job = JobState()

    def start_job(self) -> None:
        """
        Start a new job with current configuration.

        Creates a new JobState with RUNNING status and current timestamp.
        """
        self.job = JobState(
            status=JobStatus.RUNNING,
            config=self.config,
            start_time=datetime.now(),
            current_stage="extraction",
            progress_percent=0,
        )
        self.job.add_log("Pipeline job started")

    def complete_job(self, output_path: Path) -> None:
        """
        Mark job as completed successfully.

        Args:
            output_path: Path to the output directory
        """
        self.job.status = JobStatus.COMPLETED
        self.job.end_time = datetime.now()
        self.job.output_path = output_path
        self.job.progress_percent = 100
        self.job.add_log("Pipeline job completed successfully")

    def fail_job(self, error: str) -> None:
        """
        Mark job as failed with error message.

        Args:
            error: Error message describing the failure
        """
        self.job.status = JobStatus.FAILED
        self.job.end_time = datetime.now()
        self.job.error_message = error
        self.job.add_log(f"Pipeline job failed: {error}")
