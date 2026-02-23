"""Lock-related helper functions for walker API handlers.

This module isolates cooperative session-lock logic used by walker endpoints.
It keeps the lock behavior in one place so `api/walker.py` can focus on
endpoint orchestration.

Important:
- These helpers implement single-user multi-tab consistency behavior.
- They are not an authentication or security boundary.
"""

from __future__ import annotations

from typing import Any

from build_tools.syllable_walk_web.state import ServerState


def coerce_lock_holder_id(body: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract optional ``lock_holder_id`` from request payload.

    Args:
        body: Request JSON payload.

    Returns:
        Tuple of ``(holder_id, error_message)``.
        ``holder_id`` is stripped when present and valid.
        ``error_message`` is populated when input is present but invalid.
    """

    raw_holder = body.get("lock_holder_id")
    if raw_holder is None:
        return None, None
    if not isinstance(raw_holder, str):
        return None, "lock_holder_id must be a string when provided."
    holder_id = raw_holder.strip()
    if not holder_id:
        return None, "lock_holder_id must not be blank when provided."
    return holder_id, None


def lock_conflict_error(
    *, active_session_id: str, lock_payload: dict[str, Any] | None
) -> dict[str, Any]:
    """Build one deterministic lock-conflict response payload."""

    return {
        "error": (
            "Session is locked by another tab/window. "
            "Use Take Over Lock to continue from this tab."
        ),
        "lock_status": "locked",
        "active_session_id": active_session_id,
        "lock": lock_payload,
    }


def enforce_active_session_lock(body: dict[str, Any], state: ServerState) -> dict[str, Any] | None:
    """Enforce active-session lock ownership for mutating requests.

    Behavior:
    - If no active session lock context exists, request is allowed.
    - If active lock exists, caller must provide matching ``lock_holder_id``.
    - Lock is refreshed via cooperative lock service when holder matches.
    """

    active_session_id = state.active_session_id
    active_holder_id = state.active_session_lock_holder_id
    if not isinstance(active_session_id, str) or not active_session_id:
        return None
    if not isinstance(active_holder_id, str) or not active_holder_id:
        return None

    holder_id, holder_error = coerce_lock_holder_id(body)
    if holder_error is not None:
        return {
            "error": (
                "Active session lock requires lock_holder_id on mutating requests. "
                f"{holder_error}"
            ),
            "lock_status": "error",
            "active_session_id": active_session_id,
        }
    if holder_id is None:
        return {
            "error": "Active session is locked; missing lock_holder_id for this request.",
            "lock_status": "locked",
            "active_session_id": active_session_id,
        }

    from build_tools.syllable_walk_web.services.walker_session_lock import acquire_session_lock

    lock_result = acquire_session_lock(
        state=state,
        session_id=active_session_id,
        holder_id=holder_id,
        force=False,
    )
    lock_status = lock_result.get("status")
    if lock_status in {"acquired", "held"}:
        state.active_session_lock_holder_id = holder_id
        return None
    if lock_status == "locked":
        return lock_conflict_error(
            active_session_id=active_session_id,
            lock_payload=(
                lock_result.get("lock") if isinstance(lock_result.get("lock"), dict) else None
            ),
        )
    return {
        "error": f"Session lock validation failed: {lock_result.get('reason', 'unknown')}",
        "lock_status": "error",
        "active_session_id": active_session_id,
    }


def clear_active_session_context(state: ServerState) -> None:
    """Clear active loaded-session metadata from server state."""

    state.active_session_id = None
    state.active_session_lock_holder_id = None
