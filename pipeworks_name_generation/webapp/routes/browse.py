"""Browse route handlers for file-system navigation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class _BrowseHandler(Protocol):
    """Structural protocol for browse endpoint handler behavior."""

    def _read_json_body(self) -> dict[str, Any]: ...

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...


def post_browse_directory(handler: _BrowseHandler) -> None:
    """Browse a directory, returning subdirectories and ``*_metadata.json`` files."""
    try:
        body = handler._read_json_body()
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    raw_path = body.get("path", ".")

    try:
        target = Path(raw_path).expanduser().resolve()
    except (ValueError, RuntimeError):
        handler._send_json({"error": f"Invalid path: {raw_path}"}, status=400)
        return

    if not target.is_dir():
        handler._send_json({"error": f"Not a directory: {raw_path}"}, status=400)
        return

    entries: list[dict[str, Any]] = []

    try:
        for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
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
            elif item.name.endswith("_metadata.json"):
                entries.append(
                    {
                        "name": item.name,
                        "type": "file",
                        "path": str(item),
                        "size": item.stat().st_size,
                    }
                )
    except PermissionError:
        handler._send_json({"error": f"Permission denied: {raw_path}"}, status=403)
        return

    handler._send_json(
        {
            "path": str(target),
            "parent": str(target.parent) if target.parent != target else None,
            "entries": entries,
        }
    )


def post_read_metadata(handler: _BrowseHandler) -> None:
    """Read a ``*_metadata.json`` file and return its contents."""
    try:
        body = handler._read_json_body()
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    raw_path = str(body.get("path", "")).strip()
    if not raw_path:
        handler._send_json({"error": "'path' is required."}, status=400)
        return

    try:
        file_path = Path(raw_path).expanduser().resolve()
    except (ValueError, RuntimeError):
        handler._send_json({"error": f"Invalid path: {raw_path}"}, status=400)
        return

    if not file_path.name.endswith("_metadata.json"):
        handler._send_json({"error": "Only *_metadata.json files are supported."}, status=400)
        return

    if not file_path.is_file():
        handler._send_json({"error": f"File not found: {raw_path}"}, status=404)
        return

    try:
        with open(file_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        handler._send_json({"error": f"Failed to read metadata: {exc}"}, status=400)
        return

    handler._send_json({"metadata": data, "directory": str(file_path.parent)})


__all__ = ["post_browse_directory", "post_read_metadata"]
