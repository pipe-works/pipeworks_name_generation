"""
Export functionality for Syllable Walker TUI.

Provides functions for exporting selected names to various formats.
"""

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
