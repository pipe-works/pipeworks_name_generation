"""Run directory discovery for the simplified syllable walker web interface.

This module discovers complete pipeline run directories in _working/output/,
including their SQLite databases, annotated JSON files, and selection outputs.

The discovery system provides a unified view of all pipeline runs with their
associated data, making it easy to browse and select runs in the web interface.

Functions:
    discover_runs: Scan _working/output/ for complete pipeline runs
    get_selection_data: Load selection data from a specific file
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class RunInfo:
    """Metadata about a complete pipeline run directory.

    Attributes:
        path: Absolute path to the run directory
        extractor_type: Type of extractor ("nltk" or "pyphen")
        timestamp: Run timestamp in YYYYMMDD_HHMMSS format
        display_name: Human-readable display name
        corpus_db_path: Path to corpus.db if it exists, None otherwise
        annotated_json_path: Path to annotated JSON if it exists
        syllable_count: Number of syllables (from DB or JSON)
        selections: Dict mapping name class to selection file path
    """

    path: Path
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

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all run metadata
        """
        return {
            "path": str(self.path),
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
        }


def _parse_history_metadata(
    run_dir: Path, extractor_type: str
) -> tuple[str | None, int | None, str | None]:
    """Parse source/file-count/duration metadata from run artifacts."""
    source_path: str | None = None
    files_processed: int | None = None
    processing_time: str | None = None

    # Extractor metadata (source path)
    meta_dir = run_dir / "meta"
    if meta_dir.exists():
        for meta_file in sorted(meta_dir.glob("*.txt")):
            try:
                with open(meta_file, encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith("Input File:"):
                            source_path = stripped.split(":", 1)[1].strip()
                            break
                        if stripped.startswith("Input Directory:"):
                            source_path = stripped.split(":", 1)[1].strip()
                            break
                if source_path:
                    break
            except (OSError, UnicodeDecodeError):
                continue

    # Normalization metadata (files processed + processing time)
    norm_meta = run_dir / f"{extractor_type}_normalization_meta.txt"
    if not norm_meta.exists():
        fallback = sorted(run_dir.glob("*_normalization_meta.txt"))
        norm_meta = fallback[0] if fallback else norm_meta
    if norm_meta.exists():
        try:
            with open(norm_meta, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("Input Files:"):
                        m = re.search(r"(\d+)", stripped)
                        if m:
                            files_processed = int(m.group(1))
                    elif stripped.startswith("Processing Time:"):
                        processing_time = stripped.split(":", 1)[1].strip()
        except (OSError, UnicodeDecodeError):
            pass

    # Fallback for file count when metadata line is unavailable
    if files_processed is None:
        syllables_dir = run_dir / "syllables"
        if syllables_dir.exists():
            txt_count = len(list(syllables_dir.glob("*.txt")))
            if txt_count > 0:
                files_processed = txt_count

    return source_path, files_processed, processing_time


def _get_syllable_count_from_db(db_path: Path) -> int:
    """Get syllable count from SQLite database.

    Args:
        db_path: Path to corpus.db

    Returns:
        Number of syllables in database, or 0 if error
    """
    import sqlite3

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.execute("SELECT COUNT(*) FROM syllables")
        count: int = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def _get_syllable_count_from_json(json_path: Path) -> int:
    """Get syllable count from annotated JSON file.

    Args:
        json_path: Path to annotated JSON file

    Returns:
        Number of syllables in file, or 0 if error
    """
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


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
    run_dir: Path,
    syllable_count: int,
    max_depth: int = 1,
    max_entries_per_dir: int = 24,
) -> list[str]:
    """Build a deterministic, compact filesystem tree for History output."""
    lines: list[str] = [f"{run_dir.name}/"]

    def _annotation(relative_path: str) -> str | None:
        if relative_path == "data/corpus.db":
            return f"{syllable_count:,} syllables"
        if relative_path.startswith("data/") and relative_path.endswith(
            "_syllables_annotated.json"
        ):
            return "annotated data"
        return None

    def _children(dir_path: Path) -> list[Path]:
        try:
            entries = list(dir_path.iterdir())
        except Exception:
            return []

        filtered = [
            p
            for p in entries
            if p.name != ".DS_Store"
            and not p.name.endswith(".db-shm")
            and not p.name.endswith(".db-wal")
        ]
        return sorted(filtered, key=lambda p: (not p.is_dir(), p.name.lower(), p.name))

    def _render_dir(dir_path: Path, prefix: str, depth: int) -> None:
        entries = _children(dir_path)
        if not entries:
            return

        visible = entries[:max_entries_per_dir]
        hidden_count = len(entries) - len(visible)
        display_items: list[Path | str] = list(visible)
        if hidden_count > 0:
            display_items.append(f"... (+{hidden_count} more entries)")

        for i, item in enumerate(display_items):
            is_last = i == len(display_items) - 1
            connector = "└── " if is_last else "├── "

            if isinstance(item, str):
                lines.append(f"{prefix}{connector}{item}")
                continue

            child = item
            rel = child.relative_to(run_dir).as_posix()
            label = f"{child.name}/" if child.is_dir() else child.name
            note = _annotation(rel)
            if note:
                label = f"{label}  {note}"
            lines.append(f"{prefix}{connector}{label}")

            if child.is_dir() and depth < max_depth:
                next_prefix = prefix + ("    " if is_last else "│   ")
                _render_dir(child, next_prefix, depth + 1)

    _render_dir(run_dir, "", 0)
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

        # Pipeline run directories follow the convention
        # YYYYMMDD_HHMMSS_{extractor}, e.g. "20260121_084017_nltk".
        dir_name = run_dir.name
        parts = dir_name.split("_")

        if len(parts) < 3:
            continue

        # First two parts must be numeric (date and time).
        if not (parts[0].isdigit() and parts[1].isdigit()):
            continue

        timestamp = f"{parts[0]}_{parts[1]}"
        # parts[2:] is joined to handle multi-word extractors like
        # "custom_extractor".
        extractor_type = "_".join(parts[2:])

        # DB in data/ is the canonical post-pipeline-v2 location for the
        # indexed corpus.
        data_dir = run_dir / "data"
        corpus_db_path = data_dir / "corpus.db" if data_dir.exists() else None
        if corpus_db_path and not corpus_db_path.exists():
            corpus_db_path = None

        # Glob with the extractor prefix to match only the correct file and
        # avoid cross-contamination if multiple extractors share a directory.
        annotated_json_path = None
        if data_dir.exists():
            for json_file in data_dir.glob(f"{extractor_type}_syllables_annotated.json"):
                annotated_json_path = json_file
                break

        # Prefer DB for syllable count — the database has the authoritative
        # indexed count after the corpus_sqlite_builder stage.  Fall back to
        # JSON for runs that skipped the database stage.
        syllable_count = 0
        if corpus_db_path:
            syllable_count = _get_syllable_count_from_db(corpus_db_path)
        elif annotated_json_path:
            syllable_count = _get_syllable_count_from_json(annotated_json_path)

        # Skip runs with no data
        if syllable_count == 0 and not corpus_db_path and not annotated_json_path:
            continue

        # Discover selections
        selections = _discover_selections(run_dir, extractor_type)
        source_path, files_processed, processing_time = _parse_history_metadata(
            run_dir, extractor_type
        )
        output_tree_lines = _build_output_tree_lines(run_dir, syllable_count)

        # Create display name using actual folder name
        display_name = _format_display_name(
            dir_name, extractor_type, syllable_count, len(selections)
        )

        runs.append(
            RunInfo(
                path=run_dir.resolve(),
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
        if run.path.name == run_id:
            return run
    return None
