"""Session-focused walker API helpers and handlers.

This module isolates session save/list/load behavior from ``api/walker.py``.
The extraction is mechanical: endpoint behavior and payload contracts are
preserved, while dependencies are passed as callables where needed so the
legacy wrapper functions in ``walker.py`` remain the patch/test authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, cast

from build_tools.syllable_walk_web.api.walker_types import (
    ErrorResponse,
    ErrorWithLockResponse,
    RestorePatchArtifactsResult,
    SessionListEntry,
    SessionLoadPatchResult,
    SessionLoadResponse,
    SessionSaveResponse,
    SessionsResponse,
)
from build_tools.syllable_walk_web.state import PatchState, ServerState

EnforceActiveLockFn = Callable[[dict[str, Any], ServerState], dict[str, Any] | None]
CoerceLockHolderFn = Callable[[dict[str, Any]], tuple[str | None, str | None]]
LockConflictErrorFn = Callable[..., dict[str, Any]]
LoadCorpusFn = Callable[[dict[str, Any], ServerState], dict[str, Any]]
RestorePatchArtifactsFn = Callable[..., RestorePatchArtifactsResult]
ReadJsonObjectFn = Callable[[Path], dict[str, Any] | None]


def _build_restore_result(
    *,
    status: str,
    reason: str,
    restored: bool,
    restored_kinds: list[str],
    run_state_ipc_input_hash: str | None,
    run_state_ipc_output_hash: str | None,
) -> RestorePatchArtifactsResult:
    """Build a run-state restore result payload with consistent shape."""

    return {
        "status": status,
        "reason": reason,
        "restored": restored,
        "restored_kinds": restored_kinds,
        "run_state_ipc_input_hash": run_state_ipc_input_hash,
        "run_state_ipc_output_hash": run_state_ipc_output_hash,
    }


def _patch_load_failure_result(
    *,
    verification_status: str,
    verification_reason: str,
    run_id: str | None = None,
) -> SessionLoadPatchResult:
    """Build one deterministic failed patch-load result block."""

    return {
        "loaded": False,
        "restored": False,
        "verification_status": verification_status,
        "verification_reason": verification_reason,
        "run_id": run_id,
    }


def handle_save_session(
    body: dict[str, Any],
    state: ServerState,
    *,
    enforce_active_session_lock_fn: EnforceActiveLockFn,
) -> SessionSaveResponse | ErrorResponse:
    """Handle POST ``/api/walker/save-session`` with injected lock enforcement."""

    lock_error = enforce_active_session_lock_fn(body, state)
    if lock_error is not None:
        return cast(ErrorWithLockResponse, lock_error)

    from build_tools.syllable_walk_web.services.session_paths import resolve_sessions_base
    from build_tools.syllable_walk_web.services.walker_session_store import save_session

    label = body.get("label")
    session_id = body.get("session_id")
    repair_from_session_id = body.get("repair_from_session_id")

    if label is not None and not isinstance(label, str):
        return {"error": "label must be a string or null."}
    if session_id is not None and not isinstance(session_id, str):
        return {"error": "session_id must be a string or null."}
    if repair_from_session_id is not None and not isinstance(repair_from_session_id, str):
        return {"error": "repair_from_session_id must be a string or null."}

    try:
        result = save_session(
            state=state,
            label=label,
            session_id=session_id,
            repair_from_session_id=repair_from_session_id,
        )
    except Exception as e:
        return {"error": f"Session save failed: {e}"}

    return {
        "status": result.status,
        "reason": result.reason,
        "session_id": result.session_id,
        "session_path": str(result.session_path) if isinstance(result.session_path, Path) else None,
        "sessions_base": str(
            resolve_sessions_base(
                output_base=state.output_base,
                configured_sessions_base=state.sessions_base,
            )
        ),
        "patch_a": {
            "status": result.patch_a_status,
            "reason": result.patch_a_reason,
        },
        "patch_b": {
            "status": result.patch_b_status,
            "reason": result.patch_b_reason,
        },
        "ipc_input_hash": result.ipc_input_hash,
        "ipc_output_hash": result.ipc_output_hash,
        "root_session_id": result.root_session_id,
        "parent_session_id": result.parent_session_id,
        "revision": result.revision,
    }


def handle_sessions(state: ServerState) -> SessionsResponse | ErrorResponse:
    """Handle GET ``/api/walker/sessions``."""

    from build_tools.syllable_walk_web.services.walker_session_lock import get_session_lock_info
    from build_tools.syllable_walk_web.services.walker_session_store import list_sessions

    try:
        entries = list_sessions(
            output_base=state.output_base,
            configured_sessions_base=state.sessions_base,
        )
    except Exception as e:
        return {"error": f"Session listing failed: {e}"}

    serialized_sessions: list[SessionListEntry] = []
    for entry in entries:
        lock_info = get_session_lock_info(
            state=state,
            session_id=entry.session_id,
        )
        serialized_sessions.append(
            {
                "session_id": entry.session_id,
                "created_at_utc": entry.created_at_utc,
                "label": entry.label,
                "patch_a_run_id": entry.patch_a_run_id,
                "patch_b_run_id": entry.patch_b_run_id,
                "verification_status": entry.verification_status,
                "verification_reason": entry.verification_reason,
                "session_path": str(entry.session_path),
                "root_session_id": entry.root_session_id,
                "parent_session_id": entry.parent_session_id,
                "revision": entry.revision,
                "lock_status": lock_info.get("status"),
                "lock": lock_info.get("lock"),
            }
        )
    return {"sessions": serialized_sessions}


def read_json_object(path: Path) -> dict[str, Any] | None:
    """Read one JSON object from ``path``.

    Returns ``None`` on IO, decode, parse, or type failures.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def restore_patch_artifacts_from_run_state(
    *,
    patch_key: str,
    patch: PatchState,
    read_json_object_fn: ReadJsonObjectFn = read_json_object,
) -> RestorePatchArtifactsResult:
    """Restore patch artifacts from verified run-state sidecars."""

    if not isinstance(patch.run_id, str) or not patch.run_id.strip():
        return _build_restore_result(
            status="skipped",
            reason="run-state-context-missing:run-id",
            restored=False,
            restored_kinds=[],
            run_state_ipc_input_hash=None,
            run_state_ipc_output_hash=None,
        )
    if not isinstance(patch.corpus_dir, Path):
        return _build_restore_result(
            status="skipped",
            reason="run-state-context-missing:run-dir",
            restored=False,
            restored_kinds=[],
            run_state_ipc_input_hash=None,
            run_state_ipc_output_hash=None,
        )

    from build_tools.syllable_walk_web.services.walker_run_state_store import load_run_state

    run_state_result = load_run_state(
        run_dir=patch.corpus_dir,
        run_id=patch.run_id,
        manifest_ipc_output_hash=patch.manifest_ipc_output_hash,
    )
    if run_state_result.status != "verified" or not isinstance(run_state_result.payload, dict):
        return _build_restore_result(
            status=run_state_result.status,
            reason=run_state_result.reason,
            restored=False,
            restored_kinds=[],
            run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
            run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
        )

    raw_sidecars = run_state_result.payload.get("sidecars")
    if not isinstance(raw_sidecars, dict):
        return _build_restore_result(
            status="mismatch",
            reason="run-state-sidecars-missing",
            restored=False,
            restored_kinds=[],
            run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
            run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
        )

    run_dir_resolved = patch.corpus_dir.resolve()
    restored_kinds: list[str] = []
    for artifact_kind in ("walks", "candidates", "selections", "package"):
        slot = f"patch_{patch_key}_{artifact_kind}"
        ref = raw_sidecars.get(slot)
        if ref is None:
            continue
        if not isinstance(ref, dict):
            return _build_restore_result(
                status="mismatch",
                reason=f"run-state-sidecar-ref-invalid:{slot}",
                restored=False,
                restored_kinds=restored_kinds,
                run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
            )

        relative_path = ref.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path:
            return _build_restore_result(
                status="mismatch",
                reason=f"run-state-sidecar-relative-path-invalid:{slot}",
                restored=False,
                restored_kinds=restored_kinds,
                run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
            )

        sidecar_path = (patch.corpus_dir / relative_path).resolve()
        if not str(sidecar_path).startswith(str(run_dir_resolved)):
            return _build_restore_result(
                status="mismatch",
                reason=f"run-state-sidecar-path-outside-run-dir:{slot}",
                restored=False,
                restored_kinds=restored_kinds,
                run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
            )
        if not sidecar_path.exists():
            return _build_restore_result(
                status="missing",
                reason=f"run-state-sidecar-missing:{slot}",
                restored=False,
                restored_kinds=restored_kinds,
                run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
            )

        sidecar_payload = read_json_object_fn(sidecar_path)
        if sidecar_payload is None:
            return _build_restore_result(
                status="error",
                reason=f"run-state-sidecar-parse-error:{slot}",
                restored=False,
                restored_kinds=restored_kinds,
                run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
            )

        payload_block = sidecar_payload.get("payload")
        if not isinstance(payload_block, dict):
            return _build_restore_result(
                status="mismatch",
                reason=f"run-state-sidecar-payload-invalid:{slot}",
                restored=False,
                restored_kinds=restored_kinds,
                run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
            )

        if artifact_kind == "walks":
            walks = payload_block.get("walks")
            if not isinstance(walks, list):
                return _build_restore_result(
                    status="mismatch",
                    reason=f"run-state-sidecar-walks-invalid:{slot}",
                    restored=False,
                    restored_kinds=restored_kinds,
                    run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                    run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
                )
            patch.walks = walks
            restored_kinds.append("walks")
            continue

        if artifact_kind == "candidates":
            candidates = payload_block.get("candidates")
            if not isinstance(candidates, list):
                return _build_restore_result(
                    status="mismatch",
                    reason=f"run-state-sidecar-candidates-invalid:{slot}",
                    restored=False,
                    restored_kinds=restored_kinds,
                    run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                    run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
                )
            patch.candidates = candidates
            restored_kinds.append("candidates")
            continue

        if artifact_kind == "selections":
            selected_names = payload_block.get("selected_names")
            if not isinstance(selected_names, list):
                return _build_restore_result(
                    status="mismatch",
                    reason=f"run-state-sidecar-selections-invalid:{slot}",
                    restored=False,
                    restored_kinds=restored_kinds,
                    run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                    run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
                )
            patch.selected_names = selected_names
            restored_kinds.append("selections")
            continue

        package_payload = payload_block.get("package")
        if not isinstance(package_payload, dict):
            return _build_restore_result(
                status="mismatch",
                reason=f"run-state-sidecar-package-invalid:{slot}",
                restored=False,
                restored_kinds=restored_kinds,
                run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
                run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
            )
        restored_kinds.append("package")

    return _build_restore_result(
        status="verified",
        reason="run-state-restored",
        restored=len(restored_kinds) > 0,
        restored_kinds=restored_kinds,
        run_state_ipc_input_hash=run_state_result.run_state_ipc_input_hash,
        run_state_ipc_output_hash=run_state_result.run_state_ipc_output_hash,
    )


def is_stale_session_recoverable(*, status: str, reason: str | None) -> bool:
    """Return ``True`` for mismatch states safe to recover from raw payload."""

    if status != "mismatch" or not isinstance(reason, str):
        return False
    return reason.endswith("run-state-output-hash-mismatch")


def handle_load_session(
    body: dict[str, Any],
    state: ServerState,
    *,
    coerce_lock_holder_id_fn: CoerceLockHolderFn,
    lock_conflict_error_fn: LockConflictErrorFn,
    handle_load_corpus_fn: LoadCorpusFn,
    restore_patch_artifacts_from_run_state_fn: RestorePatchArtifactsFn,
    read_json_object_fn: ReadJsonObjectFn,
) -> SessionLoadResponse | ErrorResponse | ErrorWithLockResponse:
    """Handle POST ``/api/walker/load-session`` with injected dependencies."""

    from build_tools.syllable_walk_web.services.walker_session_store import load_session

    raw_session_id = body.get("session_id")
    if not isinstance(raw_session_id, str) or not raw_session_id.strip():
        return {"error": "Missing or invalid session_id."}
    session_id = raw_session_id.strip()
    lock_holder_id, lock_holder_error = coerce_lock_holder_id_fn(body)
    if lock_holder_error is not None:
        return {"error": lock_holder_error}
    force_lock = bool(body.get("force_lock", False))

    lock_result: dict[str, Any] | None = None
    if isinstance(lock_holder_id, str):
        from build_tools.syllable_walk_web.services.walker_session_lock import acquire_session_lock

        lock_result = acquire_session_lock(
            state=state,
            session_id=session_id,
            holder_id=lock_holder_id,
            force=force_lock,
        )
        lock_status = lock_result.get("status")
        if lock_status == "locked":
            return cast(
                ErrorWithLockResponse,
                lock_conflict_error_fn(
                    active_session_id=session_id,
                    lock_payload=(
                        lock_result.get("lock")
                        if isinstance(lock_result.get("lock"), dict)
                        else None
                    ),
                ),
            )
        if lock_status not in {"acquired", "held", "taken_over"}:
            return {
                "error": f"Failed to acquire session lock: {lock_result.get('reason', 'unknown')}"
            }

    try:
        result = load_session(
            session_id=session_id,
            output_base=state.output_base,
            configured_sessions_base=state.sessions_base,
        )
    except Exception as e:
        return {"error": f"Session load failed: {e}"}

    payload: dict[str, Any] | None = result.payload if isinstance(result.payload, dict) else None
    recovered_from_stale_session = False
    if payload is None and is_stale_session_recoverable(status=result.status, reason=result.reason):
        candidate_path = getattr(result, "session_path", None)
        if isinstance(candidate_path, Path):
            recovered_payload = read_json_object_fn(candidate_path)
            if isinstance(recovered_payload, dict):
                payload = recovered_payload
                recovered_from_stale_session = True

    if payload is None:
        if isinstance(lock_holder_id, str):
            from build_tools.syllable_walk_web.services.walker_session_lock import (
                release_session_lock,
            )

            release_session_lock(
                state=state,
                session_id=session_id,
                holder_id=lock_holder_id,
            )
        return {
            "status": result.status,
            "reason": result.reason,
            "session_id": result.session_id or session_id,
            "ipc_input_hash": result.ipc_input_hash,
            "ipc_output_hash": result.ipc_output_hash,
            "patch_a": {
                "loaded": False,
                "restored": False,
                "verification_status": result.status,
                "verification_reason": result.reason,
            },
            "patch_b": {
                "loaded": False,
                "restored": False,
                "verification_status": result.status,
                "verification_reason": result.reason,
            },
        }

    patch_load_results: dict[str, SessionLoadPatchResult] = {}
    for patch_key in ("a", "b"):
        patch_ref = payload.get(f"patch_{patch_key}")
        if patch_ref is None:
            patch_load_results[patch_key] = _patch_load_failure_result(
                verification_status="missing",
                verification_reason=f"session-patch-{patch_key}-absent",
            )
            continue
        if not isinstance(patch_ref, dict):
            patch_load_results[patch_key] = _patch_load_failure_result(
                verification_status="mismatch",
                verification_reason=f"session-patch-{patch_key}-invalid",
            )
            continue
        run_id = patch_ref.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            patch_load_results[patch_key] = _patch_load_failure_result(
                verification_status="mismatch",
                verification_reason=f"session-patch-{patch_key}-run-id-missing",
            )
            continue

        load_result = handle_load_corpus_fn(
            {
                "patch": patch_key,
                "run_id": run_id,
                "_internal_session_load": True,
                "lock_holder_id": lock_holder_id,
            },
            state,
        )
        if "error" in load_result:
            patch_load_results[patch_key] = _patch_load_failure_result(
                verification_status="error",
                verification_reason=str(load_result["error"]),
                run_id=run_id,
            )
            continue

        patch_state = state.patch_a if patch_key == "a" else state.patch_b
        restore_result = restore_patch_artifacts_from_run_state_fn(
            patch_key=patch_key,
            patch=patch_state,
        )
        verification_status = "verified"
        verification_reason = "session-load-started"
        restored = False
        if restore_result["status"] == "verified":
            verification_reason = str(restore_result["reason"])
            restored = bool(restore_result["restored"])
        elif restore_result["status"] == "skipped":
            verification_reason = str(restore_result["reason"])
        else:
            verification_status = str(restore_result["status"])
            verification_reason = str(restore_result["reason"])

        patch_load_results[patch_key] = {
            "loaded": True,
            "restored": restored,
            "restored_kinds": list(restore_result["restored_kinds"]),
            "verification_status": verification_status,
            "verification_reason": verification_reason,
            "run_id": run_id,
            "status": load_result.get("status"),
            "source": load_result.get("source"),
            "syllable_count": load_result.get("syllable_count"),
            "run_state_ipc_input_hash": restore_result["run_state_ipc_input_hash"],
            "run_state_ipc_output_hash": restore_result["run_state_ipc_output_hash"],
        }

    loaded_session_id = (
        payload.get("session_id", session_id)
        if isinstance(payload.get("session_id", session_id), str)
        else session_id
    )
    state.active_session_id = loaded_session_id
    state.active_session_lock_holder_id = lock_holder_id

    lock_status_value = (
        str(lock_result.get("status"))
        if isinstance(lock_result, dict) and isinstance(lock_result.get("status"), str)
        else "unlocked"
    )
    lock_reason_value = (
        str(lock_result.get("reason"))
        if isinstance(lock_result, dict) and isinstance(lock_result.get("reason"), str)
        else "no-lock-holder"
    )

    return {
        "status": result.status if recovered_from_stale_session else "verified",
        "reason": result.reason if recovered_from_stale_session else "verified",
        "session_id": loaded_session_id,
        "ipc_input_hash": result.ipc_input_hash,
        "ipc_output_hash": result.ipc_output_hash,
        "recovered_from_stale_session": recovered_from_stale_session,
        "session_lock": {
            "status": lock_status_value,
            "reason": lock_reason_value,
            "lock": (
                lock_result.get("lock")
                if isinstance(lock_result, dict) and isinstance(lock_result.get("lock"), dict)
                else None
            ),
        },
        "patch_a": patch_load_results["a"],
        "patch_b": patch_load_results["b"],
    }
