"""
Directory browser API handler for the web application.

Lists directory contents for source and output directory selection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def handle_browse_directory(body: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /api/browse-directory.

    Lists directories and text files in the given path.

    Args:
        body: Request body with ``path`` (directory to list).

    Returns:
        Dict with ``path``, ``parent``, ``entries`` list.
    """
    raw_path = body.get("path", ".")

    # Expand ~ and resolve
    try:
        target = Path(raw_path).expanduser().resolve()
    except (ValueError, RuntimeError):
        return {"error": f"Invalid path: {raw_path}"}

    if not target.is_dir():
        return {"error": f"Not a directory: {raw_path}"}

    entries: list[dict[str, Any]] = []

    try:
        for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            # Skip hidden files
            if item.name.startswith("."):
                continue

            if item.is_dir():
                entries.append(
                    {
                        "name": item.name,
                        "type": "directory",
                        "path": str(item),
                    }
                )
            elif item.suffix in (".txt", ".text", ".csv", ".tsv"):
                entries.append(
                    {
                        "name": item.name,
                        "type": "file",
                        "path": str(item),
                        "size": item.stat().st_size,
                    }
                )
    except PermissionError:
        return {"error": f"Permission denied: {raw_path}"}

    return {
        "path": str(target),
        "parent": str(target.parent) if target.parent != target else None,
        "entries": entries,
    }
