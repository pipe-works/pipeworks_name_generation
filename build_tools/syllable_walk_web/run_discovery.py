"""Run directory discovery for the syllable-walk web pipeline history.

History discovery is manifest-driven: a run is discoverable only when
``manifest.json`` exists and is parseable. This keeps the run directory itself as
the single source of truth and avoids legacy text-file parsing heuristics.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class RunInfo:
    """Metadata about one manifest-backed pipeline run directory.

    Attributes:
        path: Absolute path to the run directory
        run_id: Canonical run identifier (matches directory name)
        extractor_type: Type of extractor ("nltk" or "pyphen")
        timestamp: Run timestamp in YYYYMMDD_HHMMSS format
        display_name: Human-readable display name
        corpus_db_path: Path to corpus.db artifact if present and exists
        annotated_json_path: Path to annotated JSON artifact if present and exists
        syllable_count: Number of unique syllables from manifest metrics
        selections: Dict mapping name class to selection file path
    """

    path: Path
    run_id: str
    extractor_type: str
    timestamp: str
    display_name: str
    corpus_db_path: Path | None
    annotated_json_path: Path | None
    syllable_count: int
    source_path: str | None = None
    files_processed: int | None = None
    processing_time: str | None = None
    output_tree_lines: list[str] = field(default_factory=list)
    selections: dict[str, Path] = field(default_factory=dict)
    status: str = "unknown"
    created_at_utc: str | None = None
    completed_at_utc: str | None = None
    stage_statuses: dict[str, str] = field(default_factory=dict)
    ipc_input_hash: str | None = None
    ipc_output_hash: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all run metadata
        """
        return {
            "path": str(self.path),
            "run_id": self.run_id,
            "extractor_type": self.extractor_type,
            "timestamp": self.timestamp,
            "display_name": self.display_name,
            "corpus_db_path": str(self.corpus_db_path) if self.corpus_db_path else None,
            "annotated_json_path": (
                str(self.annotated_json_path) if self.annotated_json_path else None
            ),
            "syllable_count": self.syllable_count,
            "source_path": self.source_path,
            "files_processed": self.files_processed,
            "processing_time": self.processing_time,
            "output_tree_lines": self.output_tree_lines,
            "selections": {k: str(v) for k, v in self.selections.items()},
            "selection_count": len(self.selections),
            "status": self.status,
            "created_at_utc": self.created_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "stage_statuses": self.stage_statuses,
            "ipc_input_hash": self.ipc_input_hash,
            "ipc_output_hash": self.ipc_output_hash,
        }


_TIMESTAMP_RUN_RE = re.compile(r"^(\d{8}_\d{6})_(.+)$")


def _load_manifest(run_dir: Path) -> dict[str, Any] | None:
    """Load ``manifest.json`` for one run directory.

    Returns ``None`` when the manifest file is missing or malformed.
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _looks_like_run_directory_name(name: str) -> bool:
    """Return True when folder name follows ``YYYYMMDD_HHMMSS_<extractor>``."""
    return _TIMESTAMP_RUN_RE.match(name) is not None


def _manifest_has_required_keys(manifest: dict[str, Any]) -> bool:
    """Validate required manifest structure used by the History API."""
    required = (
        "manifest_version",
        "run_id",
        "status",
        "extractor",
        "config",
        "metrics",
        "stages",
        "artifacts",
    )
    if any(key not in manifest for key in required):
        return False
    if not isinstance(manifest.get("config"), dict):
        return False
    if not isinstance(manifest.get("metrics"), dict):
        return False
    if not isinstance(manifest.get("stages"), list):
        return False
    if not isinstance(manifest.get("artifacts"), list):
        return False
    return True


def _parse_timestamp(timestamp_str: str) -> datetime | None:
    """Parse timestamp string to datetime.

    Args:
        timestamp_str: Timestamp in YYYYMMDD_HHMMSS format

    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def _parse_iso_utc(timestamp: str | None) -> datetime | None:
    """Parse ``YYYY-MM-DDTHH:MM:SSZ`` timestamp into aware UTC datetime."""
    if not timestamp or not isinstance(timestamp, str):
        return None
    try:
        parsed = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC)


def _format_processing_time(manifest: dict[str, Any]) -> str | None:
    """Build a history-friendly duration string from manifest timestamps.

    Prefers run-level ``created_at_utc``/``completed_at_utc`` and falls back to
    summing stage durations when a complete run-level interval is unavailable.
    """
    created = _parse_iso_utc(manifest.get("created_at_utc"))
    completed = _parse_iso_utc(manifest.get("completed_at_utc"))
    if created and completed:
        seconds = max((completed - created).total_seconds(), 0.0)
        return f"{seconds:.2f}s"

    durations = [
        stage.get("duration_seconds")
        for stage in manifest.get("stages", [])
        if isinstance(stage, dict)
    ]
    numeric = [value for value in durations if isinstance(value, (int, float))]
    if numeric:
        return f"{sum(float(v) for v in numeric):.2f}s"
    return None


def _extract_artifact_paths(manifest: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract canonical corpus DB and annotated JSON artifact paths."""
    corpus_rel: str | None = None
    annotated_rel: str | None = None
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        rel_path = artifact.get("path")
        if not isinstance(rel_path, str):
            continue
        if rel_path == "data/corpus.db":
            corpus_rel = rel_path
        if rel_path.startswith("data/") and rel_path.endswith("_syllables_annotated.json"):
            if annotated_rel is None:
                annotated_rel = rel_path
    return corpus_rel, annotated_rel


def _build_stage_statuses(manifest: dict[str, Any]) -> dict[str, str]:
    """Return stage status map keyed by stage name."""
    stage_statuses: dict[str, str] = {}
    for stage in manifest.get("stages", []):
        if not isinstance(stage, dict):
            continue
        name = stage.get("name")
        status = stage.get("status")
        if isinstance(name, str) and isinstance(status, str):
            stage_statuses[name] = status
    return stage_statuses


def _format_display_name(
    folder_name: str, extractor_type: str, syllable_count: int, selection_count: int
) -> str:
    """Format a human-readable display name for a run.

    Uses the actual folder name for clarity, with syllable and selection counts.

    Args:
        folder_name: The actual directory name (e.g., "20260121_084017_nltk")
        extractor_type: Extractor type (nltk, pyphen)
        syllable_count: Number of syllables
        selection_count: Number of selection files

    Returns:
        Formatted display name showing folder name and counts
    """
    sel_info = f", {selection_count} selections" if selection_count > 0 else ""
    return f"{folder_name} ({syllable_count:,} syllables{sel_info})"


def _discover_selections(run_dir: Path, extractor_type: str) -> dict[str, Path]:
    """Discover selection files in a run directory.

    Args:
        run_dir: Path to run directory
        extractor_type: Extractor type for filename prefix

    Returns:
        Dict mapping name class (e.g., "first_name") to file path
    """
    selections_dir = run_dir / "selections"
    if not selections_dir.exists():
        return {}

    selections = {}
    prefix = f"{extractor_type}_"

    # Selection files follow the naming convention:
    #   {extractor}_{name_class}_{N}syl.json
    # e.g. "nltk_first_name_2syl.json".
    for json_file in selections_dir.glob(f"{prefix}*_*.json"):
        filename = json_file.stem  # e.g. "nltk_first_name_2syl"

        if filename.endswith("_meta"):
            continue

        # Strip the extractor prefix to isolate the name class + syllable
        # count portion (e.g. "first_name_2syl").
        name_part = filename[len(prefix) :]

        # rsplit("_", 1) splits from the right to handle compound name
        # classes like "first_name" — splitting from the left would break
        # on the underscore within the class name.
        parts = name_part.rsplit("_", 1)  # ["first_name", "2syl"]
        if len(parts) == 2 and parts[1].endswith("syl"):
            name_class = parts[0]  # e.g., "first_name"
            selections[name_class] = json_file

    return selections


def _build_output_tree_lines(
    run_name: str,
    artifacts: list[dict[str, Any]],
    syllable_count: int,
) -> list[str]:
    """Build a deterministic compact tree from manifest artifact paths."""
    lines: list[str] = [f"{run_name}/"]
    normalized_paths: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        rel_path = artifact.get("path")
        if isinstance(rel_path, str):
            normalized_paths.append(rel_path)

    unique_paths = sorted(set(normalized_paths))
    for idx, rel_path in enumerate(unique_paths):
        connector = "└── " if idx == len(unique_paths) - 1 else "├── "
        note = ""
        if rel_path == "data/corpus.db":
            note = f"  {syllable_count:,} syllables"
        elif rel_path.startswith("data/") and rel_path.endswith("_syllables_annotated.json"):
            note = "  annotated data"
        lines.append(f"{connector}{rel_path}{note}")
    return lines


def discover_runs(base_path: Path | None = None) -> list[RunInfo]:
    """Discover all pipeline run directories.

    Scans _working/output/ (or specified base path) for directories matching
    the pattern YYYYMMDD_HHMMSS_{extractor}. Returns metadata for all valid
    runs found, sorted by timestamp (newest first).

    Args:
        base_path: Directory to scan. Default: _working/output/

    Returns:
        List of RunInfo objects, sorted by timestamp (newest first)

    Examples:
        >>> runs = discover_runs()
        >>> len(runs)
        2
        >>> runs[0].extractor_type
        'nltk'
    """
    if base_path is None:
        base_path = Path("_working/output")

    if not base_path.exists():
        return []

    runs = []

    for run_dir in base_path.iterdir():
        if not run_dir.is_dir():
            continue

        dir_name = run_dir.name
        if not _looks_like_run_directory_name(dir_name):
            continue

        manifest = _load_manifest(run_dir)
        if manifest is None or not _manifest_has_required_keys(manifest):
            continue

        run_id = manifest.get("run_id")
        if not isinstance(run_id, str) or run_id != dir_name:
            continue

        extractor_type = manifest.get("extractor")
        if not isinstance(extractor_type, str) or not extractor_type:
            continue

        timestamp_match = _TIMESTAMP_RUN_RE.match(run_id)
        if timestamp_match is None:
            continue
        timestamp = timestamp_match.group(1)

        metrics = manifest.get("metrics", {})
        config = manifest.get("config", {})
        syllable_count = metrics.get("syllable_count_unique")
        if not isinstance(syllable_count, int) or syllable_count < 0:
            syllable_count = 0

        source_path = config.get("source_path")
        if not isinstance(source_path, str):
            source_path = None
        files_processed = metrics.get("files_processed")
        if not isinstance(files_processed, int):
            files_processed = None

        processing_time = _format_processing_time(manifest)
        selections = _discover_selections(run_dir, extractor_type)
        artifacts = manifest.get("artifacts", [])
        output_tree_lines = _build_output_tree_lines(run_id, artifacts, syllable_count)

        corpus_rel, annotated_rel = _extract_artifact_paths(manifest)
        corpus_db_path = (run_dir / corpus_rel) if corpus_rel else None
        if corpus_db_path and not corpus_db_path.exists():
            corpus_db_path = None
        annotated_json_path = (run_dir / annotated_rel) if annotated_rel else None
        if annotated_json_path and not annotated_json_path.exists():
            annotated_json_path = None

        display_name = _format_display_name(
            dir_name, extractor_type, syllable_count, len(selections)
        )
        ipc = manifest.get("ipc", {})
        ipc_input_hash = ipc.get("input_hash") if isinstance(ipc, dict) else None
        ipc_output_hash = ipc.get("output_hash") if isinstance(ipc, dict) else None
        if not isinstance(ipc_input_hash, str):
            ipc_input_hash = None
        if not isinstance(ipc_output_hash, str):
            ipc_output_hash = None

        runs.append(
            RunInfo(
                path=run_dir.resolve(),
                run_id=run_id,
                extractor_type=extractor_type,
                timestamp=timestamp,
                display_name=display_name,
                corpus_db_path=corpus_db_path.resolve() if corpus_db_path else None,
                annotated_json_path=(
                    annotated_json_path.resolve() if annotated_json_path else None
                ),
                syllable_count=syllable_count,
                source_path=source_path,
                files_processed=files_processed,
                processing_time=processing_time,
                output_tree_lines=output_tree_lines,
                selections=selections,
                status=str(manifest.get("status", "unknown")),
                created_at_utc=(
                    manifest.get("created_at_utc")
                    if isinstance(manifest.get("created_at_utc"), str)
                    else None
                ),
                completed_at_utc=(
                    manifest.get("completed_at_utc")
                    if isinstance(manifest.get("completed_at_utc"), str)
                    else None
                ),
                stage_statuses=_build_stage_statuses(manifest),
                ipc_input_hash=ipc_input_hash,
                ipc_output_hash=ipc_output_hash,
            )
        )

    # Deterministic ordering:
    # 1) timestamp descending (newest first)
    # 2) folder name ascending when timestamps match
    runs.sort(key=lambda r: r.path.name)
    runs.sort(key=lambda r: r.timestamp, reverse=True)

    return runs


def get_selection_data(selection_path: Path) -> dict:
    """Load selection data from a JSON file.

    Args:
        selection_path: Path to selection JSON file

    Returns:
        Dictionary with metadata and selections list

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(selection_path, encoding="utf-8") as f:
        data: dict = json.load(f)
        return data


def get_run_by_id(run_id: str, base_path: Path | None = None) -> RunInfo | None:
    """Get a specific run by its directory name.

    Args:
        run_id: Run directory name (e.g., "20260121_084017_nltk")
        base_path: Base path to search. Default: _working/output/

    Returns:
        RunInfo for the run, or None if not found
    """
    runs = discover_runs(base_path)
    for run in runs:
        if run.run_id == run_id:
            return run
    return None
