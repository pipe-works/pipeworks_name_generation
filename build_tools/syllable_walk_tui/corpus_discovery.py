"""
Corpus Discovery - Find Available Annotated Syllable Files

Scans _working/output/ for available corpus datasets.
"""

from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """
    Get the project root directory (pipeworks_name_generation/).

    Returns the project root regardless of where the app is run from.
    This is the directory containing the build_tools/ folder.
    """
    # This file is at: pipeworks_name_generation/build_tools/syllable_walk_tui/corpus_discovery.py
    # Project root is 3 levels up
    return Path(__file__).resolve().parent.parent.parent


def discover_corpora(output_dir: str | None = None) -> list[dict]:
    """
    Discover available annotated corpus files.

    Scans the output directory for subdirectories containing
    annotated syllable JSON files.

    Args:
        output_dir: Path to the output directory to scan.
                   If None, defaults to {project_root}/_working/output

    Returns:
        List of corpus info dicts with keys:
        - name: Display name (e.g., "pyphen - 2026-01-10 11:54")
        - path: Full path to the annotated JSON file
        - type: Corpus type ("nltk" or "pyphen")
        - timestamp: Directory timestamp (YYYYMMDD_HHMMSS)
    """
    if output_dir is None:
        output_dir = str(get_project_root() / "_working" / "output")

    output_path = Path(output_dir)
    if not output_path.exists():
        return []

    corpora = []

    # Scan for run directories
    for run_dir in sorted(output_path.iterdir(), reverse=True):  # Newest first
        if not run_dir.is_dir():
            continue

        # Look for annotated JSON in data/ subdirectory
        data_dir = run_dir / "data"
        if not data_dir.exists():
            continue

        # Check for both pyphen and nltk variants
        for json_file in data_dir.glob("*_syllables_annotated.json"):
            # Extract corpus type from filename
            corpus_type = None
            if "pyphen" in json_file.name:
                corpus_type = "pyphen"
            elif "nltk" in json_file.name:
                corpus_type = "nltk"
            else:
                continue  # Unknown type

            # Parse timestamp from directory name
            dir_name = run_dir.name
            timestamp = None
            if "_" in dir_name:
                parts = dir_name.split("_")
                if len(parts) >= 2:
                    # Format: YYYYMMDD_HHMMSS_type
                    date_part = parts[0]
                    time_part = parts[1]
                    # Convert to readable format
                    if len(date_part) == 8 and len(time_part) == 6:
                        timestamp = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}"

            # Create display name
            display_name = f"{corpus_type.upper()}"
            if timestamp:
                display_name += f" ({timestamp})"

            corpora.append(
                {
                    "name": display_name,
                    "path": str(json_file.absolute()),
                    "type": corpus_type,
                    "timestamp": dir_name,
                    "run_dir": str(run_dir.absolute()),
                }
            )

    return corpora


def get_latest_corpus(corpus_type: str, output_dir: str | None = None) -> Optional[str]:
    """
    Get the path to the latest corpus of a given type.

    Args:
        corpus_type: "nltk" or "pyphen"
        output_dir: Path to the output directory to scan.
                   If None, defaults to {project_root}/_working/output

    Returns:
        Path to the latest annotated JSON file, or None if not found
    """
    corpora = discover_corpora(output_dir)
    for corpus in corpora:
        if corpus["type"] == corpus_type:
            return corpus["path"]
    return None
