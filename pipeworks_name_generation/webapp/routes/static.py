"""Static/basic route handlers for the webapp HTTP API."""

from __future__ import annotations

from typing import Any, Protocol


class _StaticHandler(Protocol):
    """Structural protocol for static route handler capabilities."""

    def _send_text(
        self, content: str, status: int = 200, content_type: str = "text/plain"
    ) -> None: ...

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...

    def send_response(self, code: int) -> None: ...

    def end_headers(self) -> None: ...


def get_root(handler: _StaticHandler, html_template: str) -> None:
    """Serve the single-page web UI shell."""
    handler._send_text(html_template, content_type="text/html")


def get_text_asset(handler: _StaticHandler, *, content: str, content_type: str) -> None:
    """Serve one UTF-8 static text asset (for example CSS/JS)."""
    handler._send_text(content, content_type=content_type)


def get_health(handler: _StaticHandler) -> None:
    """Return a lightweight liveness response."""
    handler._send_json({"ok": True})


def get_favicon(handler: _StaticHandler) -> None:
    """Reply to browser favicon probes without noisy 404 logs."""
    handler.send_response(204)
    handler.end_headers()


__all__ = ["get_root", "get_text_asset", "get_health", "get_favicon"]
