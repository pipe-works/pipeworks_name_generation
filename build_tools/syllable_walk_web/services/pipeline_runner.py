"""
Pipeline runner service for the web application.

Executes extraction → normalization → annotation → database build
as sequential subprocesses in a background thread.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from build_tools.syllable_walk_web.services import pipeline_manifest
from build_tools.syllable_walk_web.state import PipelineJobState

# Stage names used in progress reporting
STAGE_NAMES = ("extract", "normalize", "annotate", "database")


def start_pipeline(
    job: PipelineJobState,
    *,
    extractor: str = "pyphen",
    language: str = "auto",
    source_path: str | None = None,
    output_dir: str | None = None,
    file_pattern: str = "*.txt",
    min_syllable_length: int = 2,
    max_syllable_length: int = 8,
    run_normalize: bool = True,
    run_annotate: bool = True,
) -> None:
    """Start a pipeline run in a background thread.

    Updates ``job`` state in-place as stages progress.

    Args:
        job: Mutable pipeline job state (shared with server).
        extractor: ``"pyphen"`` or ``"nltk"``.
        language: Language code for pyphen (e.g. ``"en_US"``, ``"auto"``).
        source_path: Source directory containing text files.
        output_dir: Parent directory for pipeline output.
        file_pattern: Glob pattern for input files.
        min_syllable_length: Minimum syllable length filter.
        max_syllable_length: Maximum syllable length filter.
        run_normalize: Whether to run normalization stage.
        run_annotate: Whether to run annotation stage (requires normalization).
    """
    job.job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    job.status = "running"
    job.config = {
        "extractor": extractor,
        "language": language,
        "source_path": source_path,
        "output_dir": output_dir,
        "file_pattern": file_pattern,
        "min_syllable_length": min_syllable_length,
        "max_syllable_length": max_syllable_length,
        "run_normalize": run_normalize,
        "run_annotate": run_annotate,
    }
    job.current_stage = None
    job.progress_percent = 0
    job.log_lines = []
    job.output_path = None
    job.error_message = None
    job.process = None

    thread = threading.Thread(target=_run_pipeline, args=(job,), daemon=True)
    thread.start()


def cancel_pipeline(job: PipelineJobState) -> None:
    """Cancel a running pipeline job."""
    if job.status != "running":
        return
    job.status = "cancelled"
    if job.process is not None:
        try:
            job.process.terminate()
        except OSError:
            pass
    _log(job, "warn", "[pipeline] run cancelled by user")


def get_status(job: PipelineJobState) -> dict[str, Any]:
    """Return current pipeline job status as a JSON-serialisable dict."""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "current_stage": job.current_stage,
        "progress_percent": job.progress_percent,
        "output_path": str(job.output_path) if job.output_path else None,
        "error_message": job.error_message,
        "log_lines": job.log_lines,
        "log_offset": len(job.log_lines),
    }


# ── Internal execution ──────────────────────────────────────────────────────


def _log(job: PipelineJobState, cls: str, text: str) -> None:
    """Append a log line to the job."""
    job.log_lines.append({"cls": f"log-line--{cls}", "text": text})


def _run_stage(
    job: PipelineJobState,
    cmd: list[str],
    stage_name: str,
) -> tuple[bool, str]:
    """Run a single subprocess stage.

    Returns:
        (success, stdout) tuple.
    """
    _log(job, "info", f"[{stage_name}] running: {' '.join(cmd[-3:])}")

    try:
        proc = subprocess.Popen(  # nosec B603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        job.process = proc

        output_lines: list[str] = []
        assert proc.stdout is not None  # guaranteed by stdout=PIPE
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            output_lines.append(line)
            _log(job, "info", f"[{stage_name}] {line}")

            # Checking cancellation on every line allows near-immediate
            # abort without waiting for the subprocess to finish naturally.
            if job.status == "cancelled":
                proc.terminate()
                return False, ""

        proc.wait()
        job.process = None

        if proc.returncode != 0:
            _log(job, "error", f"[{stage_name}] failed (exit code {proc.returncode})")
            return False, "\n".join(output_lines)

        _log(job, "ok", f"[{stage_name}] complete")
        return True, "\n".join(output_lines)

    except Exception as e:
        _log(job, "error", f"[{stage_name}] error: {e}")
        return False, ""


# Extractors print their output directory in varying formats (e.g.
# "Run Directory: /path", "Output: /path", "Created /path").  This regex
# captures the path after any of these labels.
_RUNDIR_RE = re.compile(r"(?:Run Directory|Output|Created)[:\s]+(.+)", re.IGNORECASE)

# Fallback: if stdout parsing fails, we scan for the most recently created
# timestamped directory matching the extractor name.
_TIMESTAMP_RE = re.compile(r"\d{8}_\d{6}")


def _parse_run_directory(stdout: str, output_dir: str, extractor: str) -> Path | None:
    """Extract the run directory path from extractor stdout."""
    # Try parsing from stdout
    for line in stdout.splitlines():
        m = _RUNDIR_RE.search(line)
        if m:
            candidate = Path(m.group(1).strip())
            if candidate.is_dir():
                return candidate
            # Some extractor versions append the type to the directory name.
            suffixed = candidate.parent / f"{candidate.name}_{extractor}"
            if suffixed.is_dir():
                return suffixed

    # Last-resort heuristic: iterate all directories, filter by timestamp
    # pattern and extractor name, pick the newest.
    base = Path(output_dir)
    if not base.exists():
        return None

    best: Path | None = None
    best_ts = ""
    for d in base.iterdir():
        if d.is_dir() and _TIMESTAMP_RE.match(d.name) and extractor in d.name:
            if d.name > best_ts:
                best_ts = d.name
                best = d

    return best


def _run_pipeline(job: PipelineJobState) -> None:
    """Execute pipeline stages sequentially in a background thread.

    The runner now maintains an on-disk ``manifest.json`` for each discovered
    run directory. Manifest writes are additive and do not alter existing job
    status/log semantics used by the frontend polling endpoints.
    """
    assert job.config is not None  # set by start_pipeline before thread starts
    cfg = job.config
    extractor = cfg["extractor"]
    language = cfg["language"]
    source_path = cfg["source_path"]
    output_dir = cfg["output_dir"]
    min_syl = str(cfg["min_syllable_length"])
    max_syl = str(cfg["max_syllable_length"])
    file_pattern = cfg["file_pattern"]
    run_normalize = cfg["run_normalize"]
    run_annotate = cfg["run_annotate"]
    run_started_utc = pipeline_manifest.utc_now_iso()
    manifest_doc: dict[str, Any] | None = None

    _log(job, "info", "[pipeline] starting run…")
    _log(job, "info", f"[config]   extractor: {extractor} · language: {language}")
    # Annotation requires normalization output (unique syllables +
    # frequencies), so "annotate" is only added when run_normalize is also
    # true.  "database" always follows annotation because it indexes the
    # annotated data.
    stages = ["extract"]
    if run_normalize:
        stages.append("normalize")
    if run_annotate and run_normalize:
        stages.append("annotate")
        stages.append("database")
    _log(job, "info", f"[config]   stages: {' → '.join(stages)}")

    total_stages = len(stages)
    run_directory: Path | None = None

    # ── Stage 1: Extraction ──────────────────────────────────────────────
    job.current_stage = "extract"
    job.progress_percent = 0
    _log(job, "accent", "[extract]  scanning source directory…")
    extract_started_utc = pipeline_manifest.utc_now_iso()

    extractor_module = (
        "build_tools.pyphen_syllable_extractor"
        if extractor == "pyphen"
        else "build_tools.nltk_syllable_extractor"
    )

    source_is_file = Path(source_path).is_file()

    cmd = [sys.executable, "-m", extractor_module]
    if source_is_file:
        cmd.extend(["--file", source_path])
    else:
        cmd.extend(["--source", source_path, "--pattern", file_pattern])
    cmd.extend(["--min", min_syl, "--max", max_syl, "--output", output_dir])
    if extractor == "pyphen":
        if language == "auto":
            cmd.append("--auto")
        else:
            cmd.extend(["--lang", language])

    ok, stdout = _run_stage(job, cmd, "extract")
    extract_ended_utc = pipeline_manifest.utc_now_iso()
    if not ok or job.status == "cancelled":
        if job.status != "cancelled":
            job.status = "failed"
            job.error_message = "Extraction failed"
        # Best-effort manifest persistence for extraction failures/cancellations.
        # If extractor created a run dir before failing, we still write a
        # diagnostic manifest so History tooling has a concrete trace.
        run_directory = _parse_run_directory(stdout, output_dir, extractor)
        if run_directory is not None:
            manifest_doc = pipeline_manifest.create_manifest(
                run_id=run_directory.name,
                extractor=extractor,
                language=language,
                source_path=source_path,
                file_pattern=file_pattern,
                min_syllable_length=int(min_syl),
                max_syllable_length=int(max_syl),
                run_normalize=run_normalize,
                run_annotate=run_annotate,
                created_at_utc=run_started_utc,
            )
            pipeline_manifest.upsert_stage(
                manifest_doc,
                name="extract",
                status=job.status,
                started_at_utc=extract_started_utc,
                ended_at_utc=extract_ended_utc,
            )
            pipeline_manifest.refresh_metrics_and_artifacts(
                manifest_doc,
                run_directory=run_directory,
                source_path=source_path,
                file_pattern=file_pattern,
            )
            pipeline_manifest.set_terminal_status(
                manifest_doc,
                status=job.status,
                completed_at_utc=pipeline_manifest.utc_now_iso(),
                error_message=job.error_message,
            )
            pipeline_manifest.write_manifest(run_directory, manifest_doc)
        return

    # Progress is evenly distributed across stages, not weighted by actual
    # duration — simple and predictable for the UI progress bar.
    job.progress_percent = int(100 / total_stages)

    # Parse run directory from stdout
    run_directory = _parse_run_directory(stdout, output_dir, extractor)
    if run_directory is None:
        job.status = "failed"
        job.error_message = "Could not determine run directory from extraction output"
        _log(job, "error", "[pipeline] " + job.error_message)
        return

    # Manifest starts once the canonical run directory is known.
    manifest_doc = pipeline_manifest.create_manifest(
        run_id=run_directory.name,
        extractor=extractor,
        language=language,
        source_path=source_path,
        file_pattern=file_pattern,
        min_syllable_length=int(min_syl),
        max_syllable_length=int(max_syl),
        run_normalize=run_normalize,
        run_annotate=run_annotate,
        created_at_utc=run_started_utc,
    )
    pipeline_manifest.upsert_stage(
        manifest_doc,
        name="extract",
        status="completed",
        started_at_utc=extract_started_utc,
        ended_at_utc=extract_ended_utc,
    )
    pipeline_manifest.write_manifest(run_directory, manifest_doc)

    job.output_path = run_directory
    _log(job, "info", f"[extract]  run directory: {run_directory.name}")

    # ── Stage 2: Normalization ───────────────────────────────────────────
    if run_normalize:
        job.current_stage = "normalize"
        _log(job, "accent", "[normalize] deduplicating and cleaning…")
        normalize_started_utc = pipeline_manifest.utc_now_iso()
        pipeline_manifest.upsert_stage(
            manifest_doc,
            name="normalize",
            status="running",
            started_at_utc=normalize_started_utc,
        )
        pipeline_manifest.write_manifest(run_directory, manifest_doc)

        normaliser_module = (
            "build_tools.pyphen_syllable_normaliser"
            if extractor == "pyphen"
            else "build_tools.nltk_syllable_normaliser"
        )

        cmd = [
            sys.executable,
            "-m",
            normaliser_module,
            "--run-dir",
            str(run_directory),
            "--min",
            min_syl,
            "--max",
            max_syl,
        ]

        ok, stdout = _run_stage(job, cmd, "normalize")
        normalize_ended_utc = pipeline_manifest.utc_now_iso()
        if not ok or job.status == "cancelled":
            if job.status != "cancelled":
                job.status = "failed"
                job.error_message = "Normalization failed"
            pipeline_manifest.upsert_stage(
                manifest_doc,
                name="normalize",
                status=job.status,
                started_at_utc=normalize_started_utc,
                ended_at_utc=normalize_ended_utc,
            )
            pipeline_manifest.refresh_metrics_and_artifacts(
                manifest_doc,
                run_directory=run_directory,
                source_path=source_path,
                file_pattern=file_pattern,
            )
            pipeline_manifest.set_terminal_status(
                manifest_doc,
                status=job.status,
                completed_at_utc=pipeline_manifest.utc_now_iso(),
                error_message=job.error_message,
            )
            pipeline_manifest.write_manifest(run_directory, manifest_doc)
            return

        pipeline_manifest.upsert_stage(
            manifest_doc,
            name="normalize",
            status="completed",
            started_at_utc=normalize_started_utc,
            ended_at_utc=normalize_ended_utc,
        )
        pipeline_manifest.write_manifest(run_directory, manifest_doc)
        job.progress_percent = int(200 / total_stages)

    # ── Stage 3: Annotation ──────────────────────────────────────────────
    if run_annotate and run_normalize:
        job.current_stage = "annotate"
        _log(job, "accent", "[annotate]  computing phonetic features…")
        annotate_started_utc = pipeline_manifest.utc_now_iso()
        pipeline_manifest.upsert_stage(
            manifest_doc,
            name="annotate",
            status="running",
            started_at_utc=annotate_started_utc,
        )
        pipeline_manifest.write_manifest(run_directory, manifest_doc)

        prefix = "pyphen" if extractor == "pyphen" else "nltk"
        syllables_file = run_directory / f"{prefix}_syllables_unique.txt"
        frequencies_file = run_directory / f"{prefix}_syllables_frequencies.json"

        if not syllables_file.exists() or not frequencies_file.exists():
            job.status = "failed"
            job.error_message = f"Missing input files for annotation in {run_directory.name}"
            _log(job, "error", "[annotate] " + job.error_message)
            pipeline_manifest.upsert_stage(
                manifest_doc,
                name="annotate",
                status="failed",
                started_at_utc=annotate_started_utc,
                ended_at_utc=pipeline_manifest.utc_now_iso(),
            )
            pipeline_manifest.refresh_metrics_and_artifacts(
                manifest_doc,
                run_directory=run_directory,
                source_path=source_path,
                file_pattern=file_pattern,
            )
            pipeline_manifest.set_terminal_status(
                manifest_doc,
                status="failed",
                completed_at_utc=pipeline_manifest.utc_now_iso(),
                error_message=job.error_message,
            )
            pipeline_manifest.write_manifest(run_directory, manifest_doc)
            return

        cmd = [
            sys.executable,
            "-m",
            "build_tools.syllable_feature_annotator",
            "--syllables",
            str(syllables_file),
            "--frequencies",
            str(frequencies_file),
        ]

        ok, stdout = _run_stage(job, cmd, "annotate")
        annotate_ended_utc = pipeline_manifest.utc_now_iso()
        if not ok or job.status == "cancelled":
            if job.status != "cancelled":
                job.status = "failed"
                job.error_message = "Annotation failed"
            pipeline_manifest.upsert_stage(
                manifest_doc,
                name="annotate",
                status=job.status,
                started_at_utc=annotate_started_utc,
                ended_at_utc=annotate_ended_utc,
            )
            pipeline_manifest.refresh_metrics_and_artifacts(
                manifest_doc,
                run_directory=run_directory,
                source_path=source_path,
                file_pattern=file_pattern,
            )
            pipeline_manifest.set_terminal_status(
                manifest_doc,
                status=job.status,
                completed_at_utc=pipeline_manifest.utc_now_iso(),
                error_message=job.error_message,
            )
            pipeline_manifest.write_manifest(run_directory, manifest_doc)
            return

        pipeline_manifest.upsert_stage(
            manifest_doc,
            name="annotate",
            status="completed",
            started_at_utc=annotate_started_utc,
            ended_at_utc=annotate_ended_utc,
        )
        pipeline_manifest.write_manifest(run_directory, manifest_doc)
        job.progress_percent = int(300 / total_stages)

        # ── Stage 4: Database build ──────────────────────────────────────
        job.current_stage = "database"
        _log(job, "accent", "[database] building SQLite index…")
        database_started_utc = pipeline_manifest.utc_now_iso()
        pipeline_manifest.upsert_stage(
            manifest_doc,
            name="database",
            status="running",
            started_at_utc=database_started_utc,
        )
        pipeline_manifest.write_manifest(run_directory, manifest_doc)

        cmd = [
            sys.executable,
            "-m",
            "build_tools.corpus_sqlite_builder",
            str(run_directory),
            "--force",
        ]

        ok, stdout = _run_stage(job, cmd, "database")
        database_ended_utc = pipeline_manifest.utc_now_iso()
        if not ok or job.status == "cancelled":
            if job.status != "cancelled":
                job.status = "failed"
                job.error_message = "Database build failed"
            pipeline_manifest.upsert_stage(
                manifest_doc,
                name="database",
                status=job.status,
                started_at_utc=database_started_utc,
                ended_at_utc=database_ended_utc,
            )
            pipeline_manifest.refresh_metrics_and_artifacts(
                manifest_doc,
                run_directory=run_directory,
                source_path=source_path,
                file_pattern=file_pattern,
            )
            pipeline_manifest.set_terminal_status(
                manifest_doc,
                status=job.status,
                completed_at_utc=pipeline_manifest.utc_now_iso(),
                error_message=job.error_message,
            )
            pipeline_manifest.write_manifest(run_directory, manifest_doc)
            return

        pipeline_manifest.upsert_stage(
            manifest_doc,
            name="database",
            status="completed",
            started_at_utc=database_started_utc,
            ended_at_utc=database_ended_utc,
        )
        pipeline_manifest.write_manifest(run_directory, manifest_doc)
        job.progress_percent = 100

    # ── Done ─────────────────────────────────────────────────────────────
    job.current_stage = "complete"
    job.progress_percent = 100
    job.status = "completed"
    pipeline_manifest.refresh_metrics_and_artifacts(
        manifest_doc,
        run_directory=run_directory,
        source_path=source_path,
        file_pattern=file_pattern,
    )
    pipeline_manifest.set_terminal_status(
        manifest_doc,
        status="completed",
        completed_at_utc=pipeline_manifest.utc_now_iso(),
    )
    pipeline_manifest.write_manifest(run_directory, manifest_doc)
    _log(job, "ok", "[pipeline]  run complete ✓")

    # Log output summary
    data_dir = run_directory / "data"
    if data_dir.exists():
        for f in sorted(data_dir.iterdir()):
            _log(job, "info", f"[output]    {f.name}")
