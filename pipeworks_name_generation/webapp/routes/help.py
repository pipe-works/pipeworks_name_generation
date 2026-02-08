"""Help tab route handlers."""

from __future__ import annotations

from typing import Any, Callable, Protocol


class _HelpHandler(Protocol):
    """Structural protocol for help endpoint handler behavior."""

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...


def get_help(
    handler: _HelpHandler,
    *,
    list_entries: Callable[[], list[dict[str, str]]],
) -> None:
    """Return Help tab Q&A entries."""
    try:
        entries = list_entries()
        handler._send_json({"entries": entries})
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Failed to load help entries: {exc}"}, status=500)


__all__ = ["get_help"]
