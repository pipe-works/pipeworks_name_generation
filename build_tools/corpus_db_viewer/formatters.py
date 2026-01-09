"""
Export formatters for corpus database viewer.

Provides functions to export database query results to various formats.
"""

import csv
import json
from pathlib import Path
from typing import Any


def export_to_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    """
    Export data to CSV format.

    Parameters
    ----------
    rows : list[dict[str, Any]]
        List of row data as dictionaries
    output_path : Path
        Path where CSV file will be written

    Raises
    ------
    ValueError
        If rows list is empty

    Examples
    --------
    >>> rows = [
    ...     {'id': 1, 'name': 'Alice', 'age': 30},
    ...     {'id': 2, 'name': 'Bob', 'age': 25}
    ... ]
    >>> export_to_csv(rows, Path("_working/exports/data.csv"))
    """
    if not rows:
        raise ValueError("Cannot export empty data to CSV")

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get column names from first row
    fieldnames = list(rows[0].keys())

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_to_json(rows: list[dict[str, Any]], output_path: Path) -> None:
    """
    Export data to JSON format.

    Parameters
    ----------
    rows : list[dict[str, Any]]
        List of row data as dictionaries
    output_path : Path
        Path where JSON file will be written

    Raises
    ------
    ValueError
        If rows list is empty

    Examples
    --------
    >>> rows = [
    ...     {'id': 1, 'name': 'Alice', 'age': 30},
    ...     {'id': 2, 'name': 'Bob', 'age': 25}
    ... ]
    >>> export_to_json(rows, Path("_working/exports/data.json"))
    """
    if not rows:
        raise ValueError("Cannot export empty data to JSON")

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as jsonfile:
        json.dump(rows, jsonfile, indent=2, default=str, ensure_ascii=False)


def format_row_count(count: int) -> str:
    """
    Format row count with thousands separator.

    Parameters
    ----------
    count : int
        Number of rows

    Returns
    -------
    str
        Formatted count string (e.g., "1,234 rows")

    Examples
    --------
    >>> format_row_count(1234)
    '1,234 rows'
    >>> format_row_count(1)
    '1 row'
    """
    if count == 1:
        return "1 row"
    return f"{count:,} rows"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Parameters
    ----------
    size_bytes : int
        Size in bytes

    Returns
    -------
    str
        Formatted size (e.g., "1.2 MB")

    Examples
    --------
    >>> format_file_size(1234567)
    '1.2 MB'
    >>> format_file_size(1234)
    '1.2 KB'
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"
