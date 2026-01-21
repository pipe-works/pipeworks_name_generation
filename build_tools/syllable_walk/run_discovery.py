"""Run directory discovery for the simplified syllable walker web interface.

This module discovers complete pipeline run directories in _working/output/,
including their SQLite databases, annotated JSON files, and selection outputs.

The discovery system provides a unified view of all pipeline runs with their
associated data, making it easy to browse and select runs in the web interface.

Functions:
    discover_runs: Scan _working/output/ for complete pipeline runs
    get_selection_data: Load selection data from a specific file
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


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
    corpus_db_path: Optional[Path]
    annotated_json_path: Optional[Path]
    syllable_count: int
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
            "selections": {k: str(v) for k, v in self.selections.items()},
            "selection_count": len(self.selections),
        }


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


def _parse_timestamp(timestamp_str: str) -> Optional[datetime]:
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

    for json_file in selections_dir.glob(f"{prefix}*_*.json"):
        # Parse filename: {prefix}_{name_class}_{syllables}syl.json
        # e.g., nltk_first_name_2syl.json
        filename = json_file.stem  # e.g., "nltk_first_name_2syl"

        # Skip meta files
        if filename.endswith("_meta"):
            continue

        # Remove prefix and extract name class
        name_part = filename[len(prefix) :]  # e.g., "first_name_2syl"

        # Extract name class (everything before _Nsyl)
        parts = name_part.rsplit("_", 1)  # ["first_name", "2syl"]
        if len(parts) == 2 and parts[1].endswith("syl"):
            name_class = parts[0]  # e.g., "first_name"
            selections[name_class] = json_file

    return selections


def discover_runs(base_path: Optional[Path] = None) -> list[RunInfo]:
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

        # Parse directory name: YYYYMMDD_HHMMSS_{extractor}
        dir_name = run_dir.name
        parts = dir_name.split("_")

        if len(parts) < 3:
            continue

        # Validate timestamp parts
        if not (parts[0].isdigit() and parts[1].isdigit()):
            continue

        timestamp = f"{parts[0]}_{parts[1]}"
        extractor_type = "_".join(parts[2:])  # Handle multi-word extractors

        # Look for corpus.db in data/ subdirectory
        data_dir = run_dir / "data"
        corpus_db_path = data_dir / "corpus.db" if data_dir.exists() else None
        if corpus_db_path and not corpus_db_path.exists():
            corpus_db_path = None

        # Look for annotated JSON
        annotated_json_path = None
        if data_dir.exists():
            for json_file in data_dir.glob(f"{extractor_type}_syllables_annotated.json"):
                annotated_json_path = json_file
                break

        # Get syllable count (prefer DB, fall back to JSON)
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
                selections=selections,
            )
        )

    # Sort by timestamp (newest first)
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


def get_run_by_id(run_id: str, base_path: Optional[Path] = None) -> Optional[RunInfo]:
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
