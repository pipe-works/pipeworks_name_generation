"""Manifest helpers for syllable-walk web pipeline runs.

This module centralises ``manifest.json`` creation and updates for pipeline runs
under ``_working/output/<run_id>/manifest.json``.

Design goals:

- deterministic output ordering (stable JSON, sorted artifact lists)
- additive schema that tolerates partial/failed/cancelled runs
- explicit stage timing records suitable for History-tab rendering
- minimal coupling so pipeline runner orchestration remains readable
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from fnmatch import fnmatch
from importlib.metadata import PackageNotFoundError, version
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from pipeworks_ipc.hashing import compute_output_hash, compute_payload_hash


def _resolve_pipeworks_ipc_version() -> str:
    """Resolve installed ``pipeworks-ipc`` version for manifest metadata."""

    try:
        return version("pipeworks-ipc")
    except PackageNotFoundError:
        # Local editable/test environments should install pipeworks-ipc first,
        # but we keep manifest generation resilient by using an explicit
        # unknown marker when packaging metadata is unavailable.
        return "unknown"


IPC_SCHEMA_VERSION = 1
IPC_LIBRARY_NAME = "pipeworks-ipc"
IPC_LIBRARY_REF = f"pipeworks-ipc-v{_resolve_pipeworks_ipc_version()}"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ManifestIPCVerificationResult:
    """Outcome of validating one manifest's IPC hash integrity."""

    status: str
    reason: str
    input_hash: str | None = None
    output_hash: str | None = None


def utc_now_iso() -> str:
    """Return a UTC timestamp in ISO-8601 ``YYYY-MM-DDTHH:MM:SSZ`` format.

    The manifest schema uses second precision because millisecond precision is
    unnecessary for stage telemetry and makes snapshot diffs noisier.
    """

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_manifest(
    *,
    run_id: str,
    extractor: str,
    language: str,
    source_path: str | None,
    file_pattern: str,
    min_syllable_length: int,
    max_syllable_length: int,
    run_normalize: bool,
    run_annotate: bool,
    created_at_utc: str,
) -> dict[str, Any]:
    """Create a new in-memory manifest document.

    Args:
        run_id: Run directory name (e.g. ``20260222_093033_pyphen``).
        extractor: Extractor type (``pyphen`` or ``nltk``).
        language: Language selector used by the pipeline.
        source_path: Source file or directory input path.
        file_pattern: Glob pattern for directory mode extraction.
        min_syllable_length: Minimum syllable length filter.
        max_syllable_length: Maximum syllable length filter.
        run_normalize: Whether normalize stage was requested.
        run_annotate: Whether annotate stage was requested.
        created_at_utc: Run start timestamp in UTC ISO format.

    Returns:
        Manifest dictionary matching schema v1.
    """

    # Keep config shape stable across all runs so downstream consumers (History
    # API, future migration scripts, tests) can safely assume key presence.
    input_payload = {
        "extractor": extractor,
        "language": language,
        "source_path": source_path,
        "file_pattern": file_pattern,
        "min_syllable_length": int(min_syllable_length),
        "max_syllable_length": int(max_syllable_length),
        "run_normalize": bool(run_normalize),
        "run_annotate": bool(run_annotate),
    }
    return {
        "manifest_version": 1,
        "run_id": run_id,
        "created_at_utc": created_at_utc,
        "completed_at_utc": None,
        "status": "running",
        "extractor": extractor,
        "language": language,
        "config": {
            "source_path": source_path,
            "file_pattern": file_pattern,
            "min_syllable_length": int(min_syllable_length),
            "max_syllable_length": int(max_syllable_length),
            "run_normalize": bool(run_normalize),
            "run_annotate": bool(run_annotate),
        },
        "metrics": {
            "syllable_count_unique": None,
            "files_processed": None,
        },
        "stages": [],
        "artifacts": [],
        "ipc": {
            "version": IPC_SCHEMA_VERSION,
            "library": IPC_LIBRARY_NAME,
            "library_ref": IPC_LIBRARY_REF,
            "input_hash": compute_payload_hash(input_payload),
            "output_hash": None,
            "input_payload": input_payload,
            "output_payload": None,
        },
        "errors": [],
    }


def upsert_stage(
    manifest: dict[str, Any],
    *,
    name: str,
    status: str,
    started_at_utc: str | None = None,
    ended_at_utc: str | None = None,
) -> None:
    """Insert or update one stage record in-place.

    Args:
        manifest: Mutable manifest document.
        name: Stage name (extract, normalize, annotate, database).
        status: Stage status (running/completed/failed/cancelled/skipped).
        started_at_utc: Optional stage start timestamp.
        ended_at_utc: Optional stage end timestamp.
    """

    stages = manifest.setdefault("stages", [])
    stage = next((item for item in stages if item.get("name") == name), None)
    if stage is None:
        stage = {
            "name": name,
            "status": status,
            "started_at_utc": started_at_utc,
            "ended_at_utc": ended_at_utc,
            "duration_seconds": None,
        }
        stages.append(stage)
    else:
        stage["status"] = status
        if started_at_utc is not None:
            stage["started_at_utc"] = started_at_utc
        if ended_at_utc is not None:
            stage["ended_at_utc"] = ended_at_utc

    if stage.get("started_at_utc") and stage.get("ended_at_utc"):
        stage["duration_seconds"] = _duration_seconds(
            stage["started_at_utc"], stage["ended_at_utc"]
        )


def set_terminal_status(
    manifest: dict[str, Any],
    *,
    status: str,
    completed_at_utc: str,
    error_message: str | None = None,
) -> None:
    """Set final run status and optional error in-place."""

    manifest["status"] = status
    manifest["completed_at_utc"] = completed_at_utc
    if error_message:
        errors = manifest.setdefault("errors", [])
        errors.append({"message": error_message, "recorded_at_utc": completed_at_utc})


def refresh_metrics_and_artifacts(
    manifest: dict[str, Any],
    *,
    run_directory: Path,
    source_path: str | None,
    file_pattern: str,
) -> None:
    """Populate manifest ``metrics`` and ``artifacts`` from run outputs.

    This helper is idempotent and deterministic:

    - artifact list is always sorted by relative path
    - file counts use a stable path/glob rule set
    - syllable count prefers ``data/corpus.db`` when present
    """

    artifacts = _collect_artifacts(run_directory)
    metrics = manifest.setdefault("metrics", {})
    metrics["syllable_count_unique"] = _detect_syllable_count(run_directory)
    metrics["files_processed"] = _detect_files_processed(source_path, file_pattern)
    manifest["artifacts"] = artifacts
    refresh_ipc(manifest)


def _is_sha256_hex(value: Any) -> bool:
    """Return ``True`` when value is a canonical lowercase SHA-256 hash."""

    return isinstance(value, str) and _SHA256_RE.match(value) is not None


def _build_ipc_input_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical manifest IPC input payload."""

    config = manifest.get("config", {})
    return {
        "extractor": manifest.get("extractor"),
        "language": manifest.get("language"),
        "source_path": config.get("source_path") if isinstance(config, dict) else None,
        "file_pattern": config.get("file_pattern") if isinstance(config, dict) else None,
        "min_syllable_length": (
            config.get("min_syllable_length") if isinstance(config, dict) else None
        ),
        "max_syllable_length": (
            config.get("max_syllable_length") if isinstance(config, dict) else None
        ),
        "run_normalize": config.get("run_normalize") if isinstance(config, dict) else None,
        "run_annotate": config.get("run_annotate") if isinstance(config, dict) else None,
    }


def _build_ipc_output_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical manifest IPC output payload."""

    artifacts: list[dict[str, Any]] = []
    for item in manifest.get("artifacts", []):
        if not isinstance(item, dict):
            continue
        artifacts.append(
            {
                "path": item.get("path"),
                "type": item.get("type"),
                "size_bytes": item.get("size_bytes"),
            }
        )
    metrics = manifest.get("metrics", {})
    return {
        "artifacts": artifacts,
        "metrics": {
            "syllable_count_unique": (
                metrics.get("syllable_count_unique") if isinstance(metrics, dict) else None
            ),
            "files_processed": (
                metrics.get("files_processed") if isinstance(metrics, dict) else None
            ),
        },
    }


def refresh_ipc(manifest: dict[str, Any]) -> None:
    """Refresh deterministic IPC fields from current manifest state.

    Input hash is computed from canonical run configuration fields.
    Output hash is computed from a canonical serialized payload containing:

    - artifact summaries (path/type/size), already deterministically sorted
    - selected metrics (syllable_count_unique/files_processed)
    """

    input_payload = _build_ipc_input_payload(manifest)
    output_payload = _build_ipc_output_payload(manifest)
    output_payload_serialized = json.dumps(
        output_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    manifest["ipc"] = {
        "version": IPC_SCHEMA_VERSION,
        "library": IPC_LIBRARY_NAME,
        "library_ref": IPC_LIBRARY_REF,
        "input_hash": compute_payload_hash(input_payload),
        "output_hash": compute_output_hash(output_payload_serialized),
        "input_payload": input_payload,
        "output_payload": output_payload,
    }


def verify_manifest_ipc(manifest: dict[str, Any]) -> ManifestIPCVerificationResult:
    """Verify that stored manifest IPC hashes match deterministic payload hashes.

    Returns ``verified`` when both hashes are present and match canonical
    recomputation from manifest content.
    """

    ipc = manifest.get("ipc")
    if not isinstance(ipc, dict):
        return ManifestIPCVerificationResult(status="missing", reason="missing-ipc-block")

    input_hash_raw = ipc.get("input_hash")
    output_hash_raw = ipc.get("output_hash")
    input_hash = str(input_hash_raw) if _is_sha256_hex(input_hash_raw) else None
    output_hash = str(output_hash_raw) if _is_sha256_hex(output_hash_raw) else None

    if input_hash is None and output_hash is None:
        return ManifestIPCVerificationResult(
            status="missing",
            reason="missing-input-output-hash",
        )
    if input_hash is None:
        return ManifestIPCVerificationResult(
            status="missing",
            reason="missing-input-hash",
            output_hash=output_hash,
        )
    if output_hash is None:
        return ManifestIPCVerificationResult(
            status="missing",
            reason="missing-output-hash",
            input_hash=input_hash,
        )

    try:
        expected_input_hash = compute_payload_hash(_build_ipc_input_payload(manifest))
        output_payload_serialized = json.dumps(
            _build_ipc_output_payload(manifest),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        expected_output_hash = compute_output_hash(output_payload_serialized)
    except Exception as exc:  # pragma: no cover - defensive guard
        return ManifestIPCVerificationResult(
            status="error",
            reason=f"verification-error:{exc.__class__.__name__}",
            input_hash=input_hash,
            output_hash=output_hash,
        )

    input_matches = input_hash == expected_input_hash
    output_matches = output_hash == expected_output_hash
    if input_matches and output_matches:
        return ManifestIPCVerificationResult(
            status="verified",
            reason="hashes-match",
            input_hash=input_hash,
            output_hash=output_hash,
        )
    if not input_matches and not output_matches:
        reason = "input-output-mismatch"
    elif not input_matches:
        reason = "input-mismatch"
    else:
        reason = "output-mismatch"
    return ManifestIPCVerificationResult(
        status="mismatch",
        reason=reason,
        input_hash=input_hash,
        output_hash=output_hash,
    )


def verify_manifest_ipc_file(run_directory: Path) -> ManifestIPCVerificationResult:
    """Read ``manifest.json`` and verify its IPC hash integrity."""

    manifest_path = run_directory / "manifest.json"
    if not manifest_path.exists():
        return ManifestIPCVerificationResult(status="missing", reason="manifest-missing")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, JSONDecodeError):
        return ManifestIPCVerificationResult(status="error", reason="manifest-parse-error")
    if not isinstance(payload, dict):
        return ManifestIPCVerificationResult(status="error", reason="manifest-not-object")
    return verify_manifest_ipc(payload)


def write_manifest(run_directory: Path, manifest: dict[str, Any]) -> Path:
    """Write manifest to ``run_directory/manifest.json`` atomically.

    Atomic write semantics:

    1. Write JSON to ``manifest.json.tmp``.
    2. Replace target path with ``Path.replace``.

    This prevents partially-written files if a run is interrupted mid-write.
    """

    run_directory.mkdir(parents=True, exist_ok=True)
    target = run_directory / "manifest.json"
    tmp_path = target.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(target)
    return target


def _duration_seconds(started_at_utc: str, ended_at_utc: str) -> float:
    """Return positive stage duration in seconds from two UTC ISO strings."""

    started = datetime.strptime(started_at_utc, "%Y-%m-%dT%H:%M:%SZ")
    ended = datetime.strptime(ended_at_utc, "%Y-%m-%dT%H:%M:%SZ")
    return max((ended - started).total_seconds(), 0.0)


def _detect_syllable_count(run_directory: Path) -> int | None:
    """Detect syllable count from run outputs.

    Priority:

    1. ``data/corpus.db`` row count from ``syllables`` table
    2. first matching ``*_syllables_annotated.json`` list length
    """

    data_dir = run_directory / "data"
    corpus_db = data_dir / "corpus.db"
    if corpus_db.exists():
        try:
            conn = sqlite3.connect(f"file:{corpus_db}?mode=ro", uri=True)
            cursor = conn.execute("SELECT COUNT(*) FROM syllables")
            value = cursor.fetchone()[0]
            conn.close()
            return int(value)
        except (sqlite3.Error, OSError, ValueError, TypeError):
            # Graceful fallback to JSON below; we do not fail manifest writing
            # because partial outputs are still valuable for diagnostics.
            value = None

    for json_path in sorted(data_dir.glob("*_syllables_annotated.json")):
        payload: Any = None
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (JSONDecodeError, OSError, UnicodeDecodeError, TypeError, ValueError):
            payload = None
        if isinstance(payload, list):
            return len(payload)
    return None


def _detect_files_processed(source_path: str | None, file_pattern: str) -> int | None:
    """Detect number of source files processed from configured input path."""

    if not source_path:
        return None
    source = Path(source_path)
    if source.is_file():
        return 1
    if not source.is_dir():
        return None

    # ``Path.rglob`` does not support full shell-style patterns the same way
    # across all usage here, so we apply fnmatch on sorted directory entries
    # for explicit deterministic matching.
    matches = [p for p in sorted(source.iterdir()) if p.is_file() and fnmatch(p.name, file_pattern)]
    return len(matches)


def _collect_artifacts(run_directory: Path) -> list[dict[str, Any]]:
    """Collect deterministic artifact metadata from run directory.

    Returns:
        Sorted list of artifact dictionaries with path/type/size fields.
    """

    artifacts: list[dict[str, Any]] = []

    for file_path in sorted(p for p in run_directory.rglob("*") if p.is_file()):
        relative = file_path.relative_to(run_directory).as_posix()
        artifacts.append(
            {
                "path": relative,
                "type": _artifact_type(relative),
                "size_bytes": file_path.stat().st_size,
            }
        )

    return artifacts


def _artifact_type(relative_path: str) -> str:
    """Classify a relative artifact path into a compact artifact type key."""

    if relative_path == "manifest.json":
        return "manifest"
    if relative_path == "data/corpus.db":
        return "sqlite"
    if relative_path.endswith("_syllables_annotated.json"):
        return "annotated_json"
    if relative_path.endswith("_syllables_unique.txt"):
        return "syllables_unique"
    if relative_path.endswith("_syllables_frequencies.json"):
        return "syllables_frequencies"
    if relative_path.startswith("meta/"):
        return "meta"
    return "file"
