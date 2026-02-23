"""Cooperative walker session lock service for single-user multi-tab safety.

This module implements a lease-style lock for loaded walker sessions.

Important:
- This lock is a UX consistency guard to reduce accidental drift across tabs.
- It is not an authentication/authorization mechanism and not a security boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from build_tools.syllable_walk_web.state import ServerState

LOCK_TTL_SECONDS = 45


def _utc_now_iso() -> str:
    """Return current UTC time in ``YYYY-MM-DDTHH:MM:SSZ`` format."""

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_from_epoch(epoch: float) -> str:
    """Convert epoch seconds to ``YYYY-MM-DDTHH:MM:SSZ`` string."""

    return (
        datetime.fromtimestamp(epoch, tz=UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def _normalize_nonempty_str(value: Any) -> str | None:
    """Return stripped string or ``None`` when value is not a non-empty string."""

    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _prune_expired_locks(*, state: ServerState, now_epoch: float) -> None:
    """Remove expired session lock records from in-memory lock map."""

    expired: list[str] = []
    for session_id, lock in state.walker_session_locks.items():
        expires_at_epoch = lock.get("expires_at_epoch")
        if not isinstance(expires_at_epoch, (int, float)):
            expired.append(session_id)
            continue
        if float(expires_at_epoch) <= now_epoch:
            expired.append(session_id)
    for session_id in expired:
        del state.walker_session_locks[session_id]
        if state.active_session_id == session_id:
            state.active_session_lock_holder_id = None


def _lock_info(lock: dict[str, Any]) -> dict[str, Any]:
    """Extract one lock payload safe for API responses."""

    return {
        "session_id": lock.get("session_id"),
        "holder_id": lock.get("holder_id"),
        "acquired_at_utc": lock.get("acquired_at_utc"),
        "refreshed_at_utc": lock.get("refreshed_at_utc"),
        "expires_at_utc": lock.get("expires_at_utc"),
    }


def get_session_lock_info(*, state: ServerState, session_id: str) -> dict[str, Any]:
    """Return current lock info for one session after pruning expired leases."""

    import time

    clean_session_id = _normalize_nonempty_str(session_id)
    if clean_session_id is None:
        return {
            "status": "error",
            "reason": "session_id missing or invalid",
            "lock": None,
        }

    with state.walker_session_locks_guard:
        _prune_expired_locks(state=state, now_epoch=time.time())
        existing = state.walker_session_locks.get(clean_session_id)
        if not isinstance(existing, dict):
            return {
                "status": "unlocked",
                "reason": "no active lock",
                "lock": None,
            }
        return {
            "status": "locked",
            "reason": "active lock present",
            "lock": _lock_info(existing),
        }


def acquire_session_lock(
    *,
    state: ServerState,
    session_id: str,
    holder_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """Acquire or refresh one session lock lease.

    Returns a payload with status in:
    - ``acquired``: no prior lock existed (or it had expired)
    - ``held``: same holder already had the lock; lease refreshed
    - ``taken_over``: force-acquire replaced a different active holder
    - ``locked``: another active holder owns the lock and ``force`` was false
    - ``error``: invalid parameters
    """

    import time

    clean_session_id = _normalize_nonempty_str(session_id)
    clean_holder_id = _normalize_nonempty_str(holder_id)
    if clean_session_id is None:
        return {"status": "error", "reason": "session_id missing or invalid"}
    if clean_holder_id is None:
        return {"status": "error", "reason": "lock_holder_id missing or invalid"}

    now_epoch = time.time()
    now_utc = _utc_now_iso()
    expires_epoch = now_epoch + LOCK_TTL_SECONDS
    expires_utc = _utc_from_epoch(expires_epoch)

    with state.walker_session_locks_guard:
        _prune_expired_locks(state=state, now_epoch=now_epoch)
        existing = state.walker_session_locks.get(clean_session_id)

        if isinstance(existing, dict):
            existing_holder = existing.get("holder_id")
            if (
                isinstance(existing_holder, str)
                and existing_holder != clean_holder_id
                and not force
            ):
                return {
                    "status": "locked",
                    "reason": "session lock held by another holder",
                    "lock": _lock_info(existing),
                }
            if isinstance(existing_holder, str) and existing_holder == clean_holder_id:
                existing["refreshed_at_utc"] = now_utc
                existing["expires_at_utc"] = expires_utc
                existing["expires_at_epoch"] = expires_epoch
                return {
                    "status": "held",
                    "reason": "session lock refreshed",
                    "lock": _lock_info(existing),
                }

            # Different holder + force takeover.
            previous = _lock_info(existing)
            state.walker_session_locks[clean_session_id] = {
                "session_id": clean_session_id,
                "holder_id": clean_holder_id,
                "acquired_at_utc": now_utc,
                "refreshed_at_utc": now_utc,
                "expires_at_utc": expires_utc,
                "expires_at_epoch": expires_epoch,
            }
            return {
                "status": "taken_over",
                "reason": "session lock takeover complete",
                "lock": _lock_info(state.walker_session_locks[clean_session_id]),
                "previous_lock": previous,
            }

        state.walker_session_locks[clean_session_id] = {
            "session_id": clean_session_id,
            "holder_id": clean_holder_id,
            "acquired_at_utc": now_utc,
            "refreshed_at_utc": now_utc,
            "expires_at_utc": expires_utc,
            "expires_at_epoch": expires_epoch,
        }
        return {
            "status": "acquired",
            "reason": "session lock acquired",
            "lock": _lock_info(state.walker_session_locks[clean_session_id]),
        }


def heartbeat_session_lock(
    *,
    state: ServerState,
    session_id: str,
    holder_id: str,
) -> dict[str, Any]:
    """Refresh an existing session lock; fail when ownership does not match."""

    return acquire_session_lock(
        state=state,
        session_id=session_id,
        holder_id=holder_id,
        force=False,
    )


def release_session_lock(
    *,
    state: ServerState,
    session_id: str,
    holder_id: str,
) -> dict[str, Any]:
    """Release one session lock when called by the current holder."""

    import time

    clean_session_id = _normalize_nonempty_str(session_id)
    clean_holder_id = _normalize_nonempty_str(holder_id)
    if clean_session_id is None:
        return {"status": "error", "reason": "session_id missing or invalid"}
    if clean_holder_id is None:
        return {"status": "error", "reason": "lock_holder_id missing or invalid"}

    with state.walker_session_locks_guard:
        _prune_expired_locks(state=state, now_epoch=time.time())
        existing = state.walker_session_locks.get(clean_session_id)
        if not isinstance(existing, dict):
            if state.active_session_id == clean_session_id:
                state.active_session_lock_holder_id = None
            return {"status": "missing", "reason": "session lock not found"}

        existing_holder = existing.get("holder_id")
        if not isinstance(existing_holder, str) or existing_holder != clean_holder_id:
            return {
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": _lock_info(existing),
            }

        released = _lock_info(existing)
        del state.walker_session_locks[clean_session_id]
        if state.active_session_id == clean_session_id:
            state.active_session_lock_holder_id = None
        return {
            "status": "released",
            "reason": "session lock released",
            "lock": released,
        }
