"""Cache rebuild and lock endpoint helpers for walker API.

This module isolates operational handlers that manage:
- profile reach cache rebuild requests
- session lock heartbeat/release requests

The extraction is mechanical and behavior-preserving. ``api/walker.py`` keeps
public wrapper names and delegates into these functions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from build_tools.syllable_walk_web.api.walker_types import (
    ErrorResponse,
    ErrorWithLockResponse,
    RebuildReachCacheResponse,
    SessionLockStatusResponse,
)
from build_tools.syllable_walk_web.state import PatchState, ServerState

EnforceActiveLockFn = Callable[[dict[str, Any], ServerState], dict[str, Any] | None]
ResolvePatchStateFn = Callable[[dict[str, Any], ServerState], tuple[str, PatchState] | None]
CoerceLockHolderFn = Callable[[dict[str, Any]], tuple[str | None, str | None]]
IsSha256HexFn = Callable[[Any], bool]


def _coerce_lock_request(
    body: dict[str, Any],
    *,
    coerce_lock_holder_id_fn: CoerceLockHolderFn,
) -> tuple[str | None, str | None, ErrorResponse | None]:
    """Validate lock request body and return session/holder identifiers."""

    raw_session_id = body.get("session_id")
    if not isinstance(raw_session_id, str) or not raw_session_id.strip():
        return None, None, {"error": "Missing or invalid session_id."}
    holder_id, holder_error = coerce_lock_holder_id_fn(body)
    if holder_error is not None or holder_id is None:
        return None, None, {"error": holder_error or "Missing lock_holder_id."}
    return raw_session_id.strip(), holder_id, None


def _lock_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract normalized lock metadata block from lock service result."""

    lock = result.get("lock")
    return lock if isinstance(lock, dict) else None


def _lock_error_response(
    *,
    result: dict[str, Any],
    default_message: str,
) -> ErrorWithLockResponse:
    """Build consistent lock error payload for heartbeat/release endpoints."""

    return {
        "error": result.get("reason", default_message),
        "lock_status": str(result.get("status", "error")),
        "lock": _lock_payload(result),
    }


def handle_rebuild_reach_cache(
    body: dict[str, Any],
    state: ServerState,
    *,
    enforce_active_session_lock_fn: EnforceActiveLockFn,
    resolve_patch_state_fn: ResolvePatchStateFn,
    is_sha256_hex_fn: IsSha256HexFn,
) -> RebuildReachCacheResponse | ErrorResponse | ErrorWithLockResponse:
    """Handle ``POST /api/walker/rebuild-reach-cache``.

    Recomputes profile reaches for one loaded patch and rewrites run-local
    cache IPC artifact.
    """

    lock_error = enforce_active_session_lock_fn(body, state)
    if lock_error is not None:
        return cast(ErrorWithLockResponse, lock_error)

    resolved = resolve_patch_state_fn(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved

    requested_run_id = body.get("run_id")
    if requested_run_id is not None and (
        not isinstance(requested_run_id, str) or not requested_run_id.strip()
    ):
        return {"error": "run_id must be a non-empty string when provided."}
    if isinstance(requested_run_id, str) and patch.run_id and requested_run_id != patch.run_id:
        return {"error": f"run_id mismatch for patch {patch_key.upper()}."}

    if not patch.walker_ready or patch.walker is None:
        return {"error": f"Walker not ready for patch {patch_key.upper()}. Load a corpus first."}
    if not isinstance(patch.corpus_dir, Path):
        return {"error": f"Run directory missing for patch {patch_key.upper()}."}
    if not isinstance(patch.run_id, str) or not patch.run_id.strip():
        return {"error": f"run_id missing for patch {patch_key.upper()}."}

    from build_tools.syllable_walk.reach import compute_all_reaches
    from build_tools.syllable_walk_web.services.profile_reaches_cache import (
        read_cached_profile_reach_hashes,
        write_cached_profile_reaches,
    )

    try:
        profile_reaches = compute_all_reaches(patch.walker)
    except Exception as e:
        return {"error": f"Failed to compute profile reaches: {e}"}

    wrote = write_cached_profile_reaches(
        run_dir=patch.corpus_dir,
        run_id=patch.run_id,
        walker=patch.walker,
        profile_reaches=profile_reaches,
    )
    if not wrote:
        return {"error": "Failed to write reach cache artifact."}

    cache_input_hash, cache_output_hash = read_cached_profile_reach_hashes(patch.corpus_dir)
    patch.profile_reaches = profile_reaches
    patch.reach_cache_status = "hit"
    patch.reach_cache_ipc_input_hash = cache_input_hash
    patch.reach_cache_ipc_output_hash = cache_output_hash
    if is_sha256_hex_fn(cache_input_hash) and is_sha256_hex_fn(cache_output_hash):
        patch.reach_cache_ipc_verification_status = "verified"
        patch.reach_cache_ipc_verification_reason = "cache-rebuilt"
    else:
        patch.reach_cache_ipc_verification_status = "error"
        patch.reach_cache_ipc_verification_reason = "cache-rebuilt-hashes-missing"

    return {
        "patch": patch_key,
        "run_id": patch.run_id,
        "status": "rebuilt",
        "ipc_input_hash": patch.reach_cache_ipc_input_hash,
        "ipc_output_hash": patch.reach_cache_ipc_output_hash,
        "verification_status": patch.reach_cache_ipc_verification_status,
        "verification_reason": patch.reach_cache_ipc_verification_reason,
    }


def handle_session_lock_heartbeat(
    body: dict[str, Any],
    state: ServerState,
    *,
    coerce_lock_holder_id_fn: CoerceLockHolderFn,
) -> SessionLockStatusResponse | ErrorResponse | ErrorWithLockResponse:
    """Handle ``POST /api/walker/session-lock/heartbeat``."""

    session_id, holder_id, request_error = _coerce_lock_request(
        body,
        coerce_lock_holder_id_fn=coerce_lock_holder_id_fn,
    )
    if request_error is not None:
        return request_error
    assert session_id is not None
    assert holder_id is not None

    from build_tools.syllable_walk_web.services.walker_session_lock import heartbeat_session_lock

    result = heartbeat_session_lock(
        state=state,
        session_id=session_id,
        holder_id=holder_id,
    )
    status = result.get("status")
    if status in {"locked", "error"}:
        return _lock_error_response(
            result=result,
            default_message="Session lock heartbeat failed.",
        )
    if status == "missing":
        return {
            "status": "missing",
            "reason": result.get("reason", "Session lock not found."),
            "lock": None,
        }
    return {
        "status": "held",
        "reason": result.get("reason", "session lock refreshed"),
        "lock": _lock_payload(result),
    }


def handle_session_lock_release(
    body: dict[str, Any],
    state: ServerState,
    *,
    coerce_lock_holder_id_fn: CoerceLockHolderFn,
) -> SessionLockStatusResponse | ErrorResponse | ErrorWithLockResponse:
    """Handle ``POST /api/walker/session-lock/release``."""

    session_id, holder_id, request_error = _coerce_lock_request(
        body,
        coerce_lock_holder_id_fn=coerce_lock_holder_id_fn,
    )
    if request_error is not None:
        return request_error
    assert session_id is not None
    assert holder_id is not None

    from build_tools.syllable_walk_web.services.walker_session_lock import release_session_lock

    result = release_session_lock(
        state=state,
        session_id=session_id,
        holder_id=holder_id,
    )
    status = result.get("status")
    if status in {"locked", "error"}:
        return _lock_error_response(
            result=result,
            default_message="Session lock release failed.",
        )
    safe_status = str(status) if isinstance(status, str) else "released"
    return {
        "status": safe_status,
        "reason": result.get("reason", "session lock released"),
        "lock": _lock_payload(result),
    }
