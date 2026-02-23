"""Unit tests for walker API lock helper module."""

from unittest.mock import patch

from build_tools.syllable_walk_web.api.walker_lock import (
    clear_active_session_context,
    coerce_lock_holder_id,
    enforce_active_session_lock,
    lock_conflict_error,
)
from build_tools.syllable_walk_web.state import ServerState


def test_coerce_lock_holder_id_accepts_trimmed_string() -> None:
    """Coercion should trim valid holder IDs and return no error."""

    holder_id, error = coerce_lock_holder_id({"lock_holder_id": "  holder_1  "})
    assert holder_id == "holder_1"
    assert error is None


def test_coerce_lock_holder_id_handles_optional_and_invalid_forms() -> None:
    """Coercion should return deterministic errors for invalid input forms."""

    holder_none, err_none = coerce_lock_holder_id({})
    assert holder_none is None
    assert err_none is None

    holder_type, err_type = coerce_lock_holder_id({"lock_holder_id": 123})
    assert holder_type is None
    assert err_type == "lock_holder_id must be a string when provided."

    holder_blank, err_blank = coerce_lock_holder_id({"lock_holder_id": "   "})
    assert holder_blank is None
    assert err_blank == "lock_holder_id must not be blank when provided."


def test_lock_conflict_error_payload_shape() -> None:
    """Conflict payload should include canonical lock metadata fields."""

    payload = lock_conflict_error(
        active_session_id="session_1",
        lock_payload={"holder_id": "holder_a"},
    )
    assert payload["lock_status"] == "locked"
    assert payload["active_session_id"] == "session_1"
    assert payload["lock"] == {"holder_id": "holder_a"}
    assert "Take Over Lock" in payload["error"]


def test_enforce_active_session_lock_allows_when_no_active_context() -> None:
    """Requests should pass through when no active lock context is configured."""

    state = ServerState()
    assert enforce_active_session_lock({}, state) is None

    state.active_session_id = "session_1"
    state.active_session_lock_holder_id = None
    assert enforce_active_session_lock({}, state) is None


def test_enforce_active_session_lock_requires_holder_id_when_locked() -> None:
    """Active lock context should require a valid lock_holder_id."""

    state = ServerState()
    state.active_session_id = "session_1"
    state.active_session_lock_holder_id = "holder_owner"

    missing = enforce_active_session_lock({}, state)
    assert isinstance(missing, dict)
    assert missing["lock_status"] == "locked"
    assert missing["active_session_id"] == "session_1"

    invalid = enforce_active_session_lock({"lock_holder_id": 123}, state)
    assert isinstance(invalid, dict)
    assert invalid["lock_status"] == "error"
    assert invalid["active_session_id"] == "session_1"
    assert "requires lock_holder_id" in invalid["error"]


def test_enforce_active_session_lock_accepts_acquired_and_held_statuses() -> None:
    """Acquired/held status should allow request and refresh holder ownership."""

    state = ServerState()
    state.active_session_id = "session_1"
    state.active_session_lock_holder_id = "holder_owner"

    with patch(
        "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
        return_value={"status": "acquired", "reason": "ok"},
    ):
        result = enforce_active_session_lock({"lock_holder_id": "holder_new"}, state)
    assert result is None
    assert state.active_session_lock_holder_id == "holder_new"

    with patch(
        "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
        return_value={"status": "held", "reason": "ok"},
    ):
        result = enforce_active_session_lock({"lock_holder_id": "holder_new"}, state)
    assert result is None
    assert state.active_session_lock_holder_id == "holder_new"


def test_enforce_active_session_lock_returns_conflict_for_locked_status() -> None:
    """Locked status should return deterministic conflict payload."""

    state = ServerState()
    state.active_session_id = "session_1"
    state.active_session_lock_holder_id = "holder_owner"

    with patch(
        "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
        return_value={
            "status": "locked",
            "reason": "held elsewhere",
            "lock": {"holder_id": "holder_owner"},
        },
    ):
        result = enforce_active_session_lock({"lock_holder_id": "holder_other"}, state)
    assert isinstance(result, dict)
    assert result["lock_status"] == "locked"
    assert result["active_session_id"] == "session_1"
    assert result["lock"] == {"holder_id": "holder_owner"}


def test_enforce_active_session_lock_returns_error_for_unexpected_status() -> None:
    """Unknown lock statuses should map to one deterministic error payload."""

    state = ServerState()
    state.active_session_id = "session_1"
    state.active_session_lock_holder_id = "holder_owner"

    with patch(
        "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
        return_value={"status": "error", "reason": "service failure"},
    ):
        result = enforce_active_session_lock({"lock_holder_id": "holder_owner"}, state)
    assert isinstance(result, dict)
    assert result["lock_status"] == "error"
    assert result["active_session_id"] == "session_1"
    assert "service failure" in result["error"]


def test_clear_active_session_context_resets_session_fields() -> None:
    """Context clear should reset active session and holder IDs."""

    state = ServerState()
    state.active_session_id = "session_1"
    state.active_session_lock_holder_id = "holder_1"
    clear_active_session_context(state)
    assert state.active_session_id is None
    assert state.active_session_lock_holder_id is None
