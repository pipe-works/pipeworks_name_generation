"""
Server-side state for the Pipe-Works Build Tools web application.

Holds ephemeral state for pipeline jobs and walker patches.
All state is in-memory only — not persisted across restarts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PatchState:
    """State for one walker patch (A or B)."""

    run_id: str | None = None
    corpus_type: str | None = None
    corpus_dir: Path | None = None
    syllable_count: int = 0
    walker: Any | None = None  # SyllableWalker, lazy-loaded
    walker_ready: bool = False
    loading_stage: str | None = None  # Current loading stage (for progress display)
    profile_reaches: dict[str, Any] | None = None  # ReachResult per profile
    annotated_data: list[dict] | None = None
    frequencies: dict[str, int] | None = None
    walks: list[dict] = field(default_factory=list)
    candidates: list[dict] | None = None  # combiner output (in-memory)
    candidates_path: Path | None = None
    selections_path: Path | None = None
    selected_names: list[dict] = field(default_factory=list)


@dataclass
class PipelineJobState:
    """State for the running pipeline job."""

    job_id: str | None = None
    status: str = "idle"
    config: dict | None = None
    current_stage: str | None = None
    progress_percent: int = 0
    log_lines: list[dict] = field(default_factory=list)
    output_path: Path | None = None
    error_message: str | None = None
    process: Any | None = None  # subprocess.Popen


@dataclass
class ServerState:
    """Global server state."""

    patch_a: PatchState = field(default_factory=PatchState)
    patch_b: PatchState = field(default_factory=PatchState)
    pipeline_job: PipelineJobState = field(default_factory=PipelineJobState)
    output_base: Path = field(default_factory=lambda: Path("_working/output"))
    corpus_dir_a: Path | None = None
    corpus_dir_b: Path | None = None
