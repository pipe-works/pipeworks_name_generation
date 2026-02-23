"""
Server-side state for the Pipe-Works Build Tools web application.

Holds ephemeral state for pipeline jobs and walker patches.
All state is in-memory only — not persisted across restarts.
"""

from __future__ import annotations

import threading
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
    # Monotonic counter for corpus load attempts on this patch.
    # Each new load request increments the generation so in-flight
    # background threads can detect if they became stale.
    load_generation: int = 0
    # Generation ID currently considered authoritative.
    # ``None`` means no load is currently in progress.
    active_load_generation: int | None = None
    # Terminal loader error for the current generation, if any.
    # Cleared at the start of each new load request.
    loading_error: str | None = None
    # Manifest IPC hashes for the currently loaded run (if available).
    manifest_ipc_input_hash: str | None = None
    manifest_ipc_output_hash: str | None = None
    # Manifest IPC verification outcome for the loaded run.
    # Values: verified|mismatch|missing|error (or None before first verification).
    manifest_ipc_verification_status: str | None = None
    manifest_ipc_verification_reason: str | None = None
    # Profile reach cache outcome for the currently loaded run.
    # Values: hit|miss|invalid|error|none (or None before first attempt).
    reach_cache_status: str | None = None
    # Reach-cache IPC hashes for the cache artifact loaded/written for this run.
    reach_cache_ipc_input_hash: str | None = None
    reach_cache_ipc_output_hash: str | None = None
    # Reach-cache IPC verification outcome.
    # Values: verified|mismatch|missing|error (or None before first verification).
    reach_cache_ipc_verification_status: str | None = None
    reach_cache_ipc_verification_reason: str | None = None
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
    # Optional explicit sessions directory override.
    # When ``None``, session storage should default to ``output_base/sessions``.
    sessions_base: Path | None = None
    corpus_dir_a: Path | None = None
    corpus_dir_b: Path | None = None
    # Cooperative single-user session locks keyed by session_id.
    # This is a UX consistency guard for multi-tab use, not a security boundary.
    walker_session_locks: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Thread-safety guard for lock map updates under ThreadingHTTPServer.
    walker_session_locks_guard: threading.Lock = field(default_factory=threading.Lock)
    # Active loaded session context (if current patch state came from load-session API).
    active_session_id: str | None = None
    # Current holder id for the active session lock.
    active_session_lock_holder_id: str | None = None
