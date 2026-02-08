"""HTTP transport helpers for the webapp request handler.

These utilities centralize UTF-8 response writing and JSON body parsing so the
request handler can focus on route dispatch and endpoint behavior.
"""

from __future__ import annotations

import json
from typing import Any


def send_text(
    handler: Any,
    content: str,
    *,
    status: int = 200,
    content_type: str = "text/plain",
) -> None:
    """Write a UTF-8 text response through a ``BaseHTTPRequestHandler``-like object."""
    encoded = content.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def send_json(handler: Any, payload: dict[str, Any], *, status: int = 200) -> None:
    """Serialize and write a JSON object response."""
    send_text(handler, json.dumps(payload), status=status, content_type="application/json")


def read_json_body(handler: Any) -> dict[str, Any]:
    """Read and validate a JSON object request body from the handler stream."""
    try:
        content_length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Invalid Content-Length header.") from exc

    if content_length <= 0:
        raise ValueError("Request body is required.")

    raw_body = handler.rfile.read(content_length)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


__all__ = ["send_text", "send_json", "read_json_body"]
