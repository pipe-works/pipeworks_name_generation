"""
Pipeline API handlers for the web application.

Handles pipeline start, status, cancel, and run listing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from build_tools.syllable_walk_web.state import ServerState


def handle_start(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/pipeline/start.

    Starts a new pipeline run in a background thread.

    Args:
        body: Request body with pipeline configuration.
        state: Global server state.

    Returns:
        Immediate response with job ID and status.
    """
    job = state.pipeline_job

    if job.status == "running":
        return {"error": "A pipeline job is already running."}

    source = body.get("source_path")
    output = body.get("output_dir")

    if not source:
        return {"error": "Missing source_path"}

    source_path = Path(source)
    if not source_path.is_dir() and not source_path.is_file():
        return {"error": f"Source path not found: {source}"}

    # Default output to _working/output
    if not output:
        output = str(state.output_base)

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    from build_tools.syllable_walk_web.services.pipeline_runner import start_pipeline

    start_pipeline(
        job,
        extractor=body.get("extractor", "pyphen"),
        language=body.get("language", "auto"),
        source_path=source,
        output_dir=output,
        file_pattern=body.get("file_pattern", "*.txt"),
        min_syllable_length=body.get("min_syllable_length", 2),
        max_syllable_length=body.get("max_syllable_length", 8),
        run_normalize=body.get("run_normalize", True),
        run_annotate=body.get("run_annotate", True),
    )

    return {
        "job_id": job.job_id,
        "status": "running",
    }


def handle_status(state: ServerState) -> dict[str, Any]:
    """Handle GET /api/pipeline/status.

    Returns current pipeline job status with log lines.

    Args:
        state: Global server state.

    Returns:
        Job status dict.
    """
    from build_tools.syllable_walk_web.services.pipeline_runner import get_status

    return get_status(state.pipeline_job)


def handle_cancel(state: ServerState) -> dict[str, Any]:
    """Handle POST /api/pipeline/cancel.

    Cancels the running pipeline job.

    Args:
        state: Global server state.

    Returns:
        Confirmation dict.
    """
    job = state.pipeline_job

    if job.status != "running":
        return {"error": "No pipeline job is running."}

    from build_tools.syllable_walk_web.services.pipeline_runner import cancel_pipeline

    cancel_pipeline(job)

    return {"status": "cancelled"}


def handle_runs(state: ServerState, patch: str | None = None) -> dict[str, Any]:
    """Handle GET /api/pipeline/runs.

    Lists discovered pipeline runs.  When *patch* is ``"a"`` or ``"b"``
    and a per-patch corpus directory is configured, runs are discovered
    from that directory instead of *output_base*.

    Args:
        state: Global server state.
        patch: Optional patch key (``"a"`` or ``"b"``).

    Returns:
        Dict with runs list.
    """
    from build_tools.syllable_walk_web.run_discovery import discover_runs

    if patch == "a" and state.corpus_dir_a:
        base = state.corpus_dir_a
    elif patch == "b" and state.corpus_dir_b:
        base = state.corpus_dir_b
    else:
        base = state.output_base

    runs = discover_runs(base)
    return {"runs": [r.to_dict() for r in runs]}
