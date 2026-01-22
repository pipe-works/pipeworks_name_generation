"""Dataset discovery for syllable walker.

This module provides functionality to discover and enumerate available annotated
syllable datasets across the project's working directories. It scans for files
produced by the syllable feature annotator and extracts metadata.

The discovery system is designed for the web interface to provide easy dataset
selection without requiring users to specify full file paths.

Functions:
    discover_datasets: Scan directories for annotated datasets
    load_dataset_metadata: Extract metadata from a dataset file
    get_default_dataset: Find the most recent dataset
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class DatasetInfo:
    """Metadata about an annotated syllable dataset.

    Attributes:
        path: Absolute path to the JSON file
        name: Display name for the dataset
        extractor_type: Extractor that produced the data ("pyphen", "nltk", or "unknown")
        timestamp: Run timestamp from directory name (if available)
        syllable_count: Number of syllables in the dataset
        run_directory: Parent directory of the dataset
        is_legacy: Whether this is a legacy location (data/annotated/)
    """

    path: Path
    name: str
    extractor_type: str
    timestamp: Optional[str]
    syllable_count: int
    run_directory: Path
    is_legacy: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all dataset metadata
        """
        return {
            "path": str(self.path),
            "name": self.name,
            "extractor_type": self.extractor_type,
            "timestamp": self.timestamp,
            "syllable_count": self.syllable_count,
            "run_directory": str(self.run_directory),
            "is_legacy": self.is_legacy,
        }


def load_dataset_metadata(json_path: Path) -> Optional[DatasetInfo]:
    """Load metadata from an annotated syllable dataset file.

    Reads the JSON file to determine syllable count and infers metadata from
    the file path (extractor type, run timestamp, etc.).

    Args:
        json_path: Path to *_syllables_annotated.json file

    Returns:
        DatasetInfo object with metadata, or None if file is invalid

    Examples:
        >>> path = Path("_working/output/20260110_115601_nltk/data/nltk_syllables_annotated.json")
        >>> info = load_dataset_metadata(path)
        >>> info.extractor_type
        'nltk'
        >>> info.syllable_count
        33640
    """
    if not json_path.exists():
        return None

    try:
        # Load JSON to count syllables
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return None

        syllable_count = len(data)

        # Extract metadata from path
        filename = json_path.name
        parent_dir = json_path.parent
        run_dir = parent_dir.parent if parent_dir.name == "data" else parent_dir

        # Detect extractor type from filename
        if filename.startswith("pyphen_"):
            extractor_type = "pyphen"
        elif filename.startswith("nltk_"):
            extractor_type = "nltk"
        else:
            extractor_type = "unknown"

        # Extract timestamp from run directory name (format: YYYYMMDD_HHMMSS_extractor)
        timestamp = None
        run_dir_name = run_dir.name
        if "_" in run_dir_name:
            parts = run_dir_name.split("_")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                # Format: 20260110_115601
                timestamp = f"{parts[0]}_{parts[1]}"

        # Check if this is a legacy location (cross-platform check using Path parts)
        path_parts = json_path.resolve().parts
        is_legacy = "data" in path_parts and "annotated" in path_parts

        # Create display name
        if is_legacy:
            name = f"Legacy ({extractor_type}, {syllable_count:,} syllables)"
        elif timestamp:
            # Format timestamp for display: 2026-01-10 11:56
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                name = f"{extractor_type.upper()} - {formatted_date} ({syllable_count:,} syllables)"
            except ValueError:
                name = f"{extractor_type.upper()} - {run_dir_name} ({syllable_count:,} syllables)"
        else:
            name = f"{extractor_type.upper()} - {run_dir_name} ({syllable_count:,} syllables)"

        return DatasetInfo(
            path=json_path.resolve(),
            name=name,
            extractor_type=extractor_type,
            timestamp=timestamp,
            syllable_count=syllable_count,
            run_directory=run_dir.resolve(),
            is_legacy=is_legacy,
        )

    except (json.JSONDecodeError, OSError):
        return None


def discover_datasets(
    search_paths: Optional[List[Path]] = None, include_legacy: bool = True
) -> List[DatasetInfo]:
    """Discover available annotated syllable datasets.

    Scans specified directories (or default locations) for annotated syllable
    datasets produced by syllable_feature_annotator. Returns metadata for all
    valid datasets found, sorted by timestamp (newest first).

    Default search locations:
        - _working/output/*/data/*_syllables_annotated.json
        - data/annotated/syllables_annotated.json (if include_legacy=True)

    Args:
        search_paths: Optional list of directories to search. If None, uses defaults:
            [Path("_working/output"), Path("data/annotated")]
        include_legacy: Whether to include legacy data/annotated/ location. Default: True

    Returns:
        List of DatasetInfo objects, sorted by timestamp (newest first)

    Examples:
        >>> datasets = discover_datasets()
        >>> len(datasets)
        2
        >>> datasets[0].extractor_type
        'nltk'

    Notes:
        - Invalid JSON files are silently skipped
        - Directories that don't exist are silently skipped
        - Returns empty list if no datasets found
    """
    datasets = []

    # Default search paths
    if search_paths is None:
        search_paths = [Path("_working/output")]
        if include_legacy:
            search_paths.append(Path("data/annotated"))

    # Search each path
    for base_path in search_paths:
        if not base_path.exists():
            continue

        if base_path.name == "annotated" and base_path.parent.name == "data":
            # Legacy location: data/annotated/syllables_annotated.json
            legacy_file = base_path / "syllables_annotated.json"
            if legacy_file.exists():
                info = load_dataset_metadata(legacy_file)
                if info:
                    datasets.append(info)

        else:
            # Search for run directories with data/ subdirectories
            # Pattern: _working/output/YYYYMMDD_HHMMSS_extractor/data/*_syllables_annotated.json
            for run_dir in base_path.iterdir():
                if not run_dir.is_dir():
                    continue

                # Check for data/ subdirectory
                data_dir = run_dir / "data"
                if not data_dir.exists():
                    continue

                # Look for annotated files
                for json_file in data_dir.glob("*_syllables_annotated.json"):
                    info = load_dataset_metadata(json_file)
                    if info:
                        datasets.append(info)

    # Sort by timestamp (newest first), with legacy items last
    datasets.sort(
        key=lambda x: (
            not x.is_legacy,  # Non-legacy items first (True > False)
            x.timestamp or "",  # Sort by timestamp descending
        ),
        reverse=True,
    )

    return datasets


def get_default_dataset(datasets: Optional[List[DatasetInfo]] = None) -> Optional[DatasetInfo]:
    """Get the default dataset to load (most recent non-legacy).

    Args:
        datasets: Optional list of datasets. If None, discovers datasets automatically.

    Returns:
        The most recent non-legacy dataset, or None if no datasets found

    Examples:
        >>> default = get_default_dataset()
        >>> default.extractor_type
        'nltk'
        >>> default.is_legacy
        False
    """
    if datasets is None:
        datasets = discover_datasets()

    # Return first non-legacy dataset (they're already sorted by timestamp)
    for dataset in datasets:
        if not dataset.is_legacy:
            return dataset

    # Fall back to any dataset if only legacy exists
    return datasets[0] if datasets else None
