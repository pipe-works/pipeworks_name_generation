"""Tests for cooperative walker session lock service."""

from __future__ import annotations

from build_tools.syllable_walk_web.services.walker_session_lock import (
    acquire_session_lock,
    get_session_lock_info,
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


def test_invalid_holder_inputs_and_info_validation() -> None:
    """Invalid holder/session identifiers should return deterministic errors."""

    state = ServerState()

    bad_holder = acquire_session_lock(
        state=state,
        session_id="session_3",
        holder_id="",
    )
    assert bad_holder["status"] == "error"
    assert bad_holder["reason"] == "lock_holder_id missing or invalid"

    info_invalid = get_session_lock_info(state=state, session_id="   ")
    assert info_invalid["status"] == "error"
    assert info_invalid["reason"] == "session_id missing or invalid"

    bad_release_session = release_session_lock(
        state=state,
        session_id="",
        holder_id="holder_a",
    )
    assert bad_release_session["status"] == "error"
    assert bad_release_session["reason"] == "session_id missing or invalid"

    bad_release_holder = release_session_lock(
        state=state,
        session_id="session_3",
        holder_id="",
    )
    assert bad_release_holder["status"] == "error"
    assert bad_release_holder["reason"] == "lock_holder_id missing or invalid"

    bad_type_holder = acquire_session_lock(
        state=state,
        session_id="session_3",
        holder_id=123,  # type: ignore[arg-type]
    )
    assert bad_type_holder["status"] == "error"


def test_prune_invalid_lock_record_clears_active_holder() -> None:
    """Pruning malformed lock records should clear active holder for active session."""

    state = ServerState()
    state.active_session_id = "session_4"
    state.active_session_lock_holder_id = "holder_a"
    state.walker_session_locks["session_4"] = {
        "session_id": "session_4",
        "holder_id": "holder_a",
        "acquired_at_utc": "2026-01-01T00:00:00Z",
        "refreshed_at_utc": "2026-01-01T00:00:00Z",
        "expires_at_utc": "2099-01-01T00:00:00Z",
        "expires_at_epoch": "not-a-number",
    }

    info = get_session_lock_info(state=state, session_id="session_4")
    assert info["status"] == "unlocked"
    assert info["lock"] is None
    assert state.active_session_lock_holder_id is None

    missing_release = release_session_lock(
        state=state,
        session_id="session_4",
        holder_id="holder_a",
    )
    assert missing_release["status"] == "missing"


def test_release_existing_lock_clears_active_holder_for_active_session() -> None:
    """Releasing the active session lock should clear active holder tracking."""

    state = ServerState()
    state.active_session_id = "session_5"
    state.active_session_lock_holder_id = "holder_a"
    acquired = acquire_session_lock(
        state=state,
        session_id="session_5",
        holder_id="holder_a",
    )
    assert acquired["status"] == "acquired"

    released = release_session_lock(
        state=state,
        session_id="session_5",
        holder_id="holder_a",
    )
    assert released["status"] == "released"
    assert state.active_session_lock_holder_id is None
