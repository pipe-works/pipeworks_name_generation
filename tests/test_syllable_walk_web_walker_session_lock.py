"""Tests for cooperative walker session lock service."""

from __future__ import annotations

from build_tools.syllable_walk_web.services.walker_session_lock import (
    acquire_session_lock,
    heartbeat_session_lock,
    release_session_lock,
)
from build_tools.syllable_walk_web.state import ServerState


def test_acquire_heartbeat_and_release_flow() -> None:
    """One holder should acquire/refresh/release; others should be blocked."""

    state = ServerState()
    acquired = acquire_session_lock(
        state=state,
        session_id="session_1",
        holder_id="holder_a",
    )
    assert acquired["status"] == "acquired"
    assert acquired["lock"]["holder_id"] == "holder_a"

    held = heartbeat_session_lock(
        state=state,
        session_id="session_1",
        holder_id="holder_a",
    )
    assert held["status"] == "held"

    blocked = acquire_session_lock(
        state=state,
        session_id="session_1",
        holder_id="holder_b",
    )
    assert blocked["status"] == "locked"
    assert blocked["lock"]["holder_id"] == "holder_a"

    takeover = acquire_session_lock(
        state=state,
        session_id="session_1",
        holder_id="holder_b",
        force=True,
    )
    assert takeover["status"] == "taken_over"
    assert takeover["lock"]["holder_id"] == "holder_b"

    old_release = release_session_lock(
        state=state,
        session_id="session_1",
        holder_id="holder_a",
    )
    assert old_release["status"] == "locked"

    released = release_session_lock(
        state=state,
        session_id="session_1",
        holder_id="holder_b",
    )
    assert released["status"] == "released"


def test_expired_lock_is_pruned_before_acquire() -> None:
    """Expired in-memory lock records should not block a new holder."""

    state = ServerState()
    acquired = acquire_session_lock(
        state=state,
        session_id="session_2",
        holder_id="holder_a",
    )
    assert acquired["status"] == "acquired"
    lock = state.walker_session_locks["session_2"]
    lock["expires_at_epoch"] = 0.0

    next_acquire = acquire_session_lock(
        state=state,
        session_id="session_2",
        holder_id="holder_b",
    )
    assert next_acquire["status"] == "acquired"
    assert next_acquire["lock"]["holder_id"] == "holder_b"


def test_invalid_inputs_and_missing_release() -> None:
    """Invalid ids and missing releases should return deterministic statuses."""

    state = ServerState()
    bad_acquire = acquire_session_lock(
        state=state,
        session_id="",
        holder_id="holder_a",
    )
    assert bad_acquire["status"] == "error"

    missing_release = release_session_lock(
        state=state,
        session_id="session_missing",
        holder_id="holder_a",
    )
    assert missing_release["status"] == "missing"
