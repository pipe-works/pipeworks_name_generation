"""
Export functionality for Syllable Walker TUI.

Provides functions for exporting selected names to various formats.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path


def export_names_to_txt(
    names: list[str],
    json_output_path: str,
) -> tuple[Path, str | None]:
    """
    Export names to a plain text file (one name per line).

    The TXT file is written to the same directory as the JSON output,
    using the same base filename with .txt extension.

    Args:
        names: List of names to export
        json_output_path: Path to JSON output file (TXT will have same base name)

    Returns:
        Tuple of (output_path, error_message_or_none)
        - output_path: Path where TXT was written (or would be written on error)
        - error: Error message if failed, None if successful

    Examples:
        >>> names = ["Alara", "Benton", "Carla"]
        >>> txt_path, error = export_names_to_txt(names, "/path/to/names.json")
        >>> if error:
        ...     print(f"Export failed: {error}")
        >>> else:
        ...     print(f"Exported to {txt_path}")
    """
    # Derive TXT path from JSON path
    json_path = Path(json_output_path)
    txt_path = json_path.with_suffix(".txt")

    try:
        # Write names to TXT file (one per line)
        with open(txt_path, "w", encoding="utf-8") as f:
            for name in names:
                f.write(f"{name}\n")

        return txt_path, None

    except PermissionError as e:
        return txt_path, f"Permission denied: {e}"
    except OSError as e:
        return txt_path, f"File system error: {e}"
    except Exception as e:
        return txt_path, f"Unexpected error: {e}"


def export_sample_json(
    names: list[str],
    name_class: str,
    selections_dir: Path,
    sample_size: int = 5,
    seed: int | None = None,
) -> tuple[Path, str | None]:
    """
    Export a random sample of names to a JSON file.

    This helper is used by the TUI renderer screen to create lightweight
    example payloads for API consumers. The output is named
    ``<name_class>_sample.json`` inside the selections directory.

    Args:
        names: Raw selected names to sample from
        name_class: Name class identifier (e.g., "first_name")
        selections_dir: Directory to write the JSON file into
        sample_size: Number of names to include (default: 5)
        seed: Optional seed for deterministic sampling (test support)

    Returns:
        Tuple of (output_path, error_message_or_none)
    """
    # Ensure we have a valid selections directory to write into
    try:
        selections_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return selections_dir / f"{name_class}_sample.json", (
            f"Failed to create selections dir: {exc}"
        )

    # Normalize names to lowercase and remove duplicates while preserving order
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in names:
        if not raw:
            continue
        value = raw.strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    if not normalized:
        return selections_dir / f"{name_class}_sample.json", "No names available to sample."

    # Clamp the sample size to the available pool
    sample_count = min(sample_size, len(normalized))

    # Use deterministic RNG when a seed is provided for testability; no crypto needed.
    rng = random.Random(seed) if seed is not None else random.SystemRandom()  # nosec B311
    sampled = rng.sample(normalized, sample_count)

    output_path = selections_dir / f"{name_class}_sample.json"

    # Build the sample payload for downstream consumers
    payload = {
        "name_class": name_class,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": sample_count,
        "samples": sampled,
    }

    try:
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return output_path, None
    except OSError as exc:
        return output_path, f"Failed to write sample JSON: {exc}"
