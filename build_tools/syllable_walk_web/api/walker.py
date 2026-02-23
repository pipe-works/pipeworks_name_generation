"""
Walker API handlers for the web application.

Handles corpus loading, walk generation, name generation, analysis,
and walker state queries.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from build_tools.syllable_walk_web.api.walker_lock import (
    clear_active_session_context as _clear_active_session_context_impl,
)
from build_tools.syllable_walk_web.api.walker_lock import (
    coerce_lock_holder_id as _coerce_lock_holder_id_impl,
)
from build_tools.syllable_walk_web.api.walker_lock import (
    enforce_active_session_lock as _enforce_active_session_lock_impl,
)
from build_tools.syllable_walk_web.api.walker_lock import (
    lock_conflict_error as _lock_conflict_error_impl,
)
from build_tools.syllable_walk_web.state import PatchState, ServerState

_MISSING = object()
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_sha256_hex(value: Any) -> bool:
    """Return ``True`` when value is a lowercase 64-character SHA-256 hash."""

    return isinstance(value, str) and _SHA256_RE.match(value) is not None


def _reach_cache_verification_from_read(
    *,
    cache_status: str | None,
    cache_message: str | None,
    input_hash: str | None,
    output_hash: str | None,
) -> tuple[str | None, str | None]:
    """Map cache read outcome to a user-facing verification status/reason."""

    if cache_status is None:
        return None, None
    if cache_status == "hit":
        if _is_sha256_hex(input_hash) and _is_sha256_hex(output_hash):
            return "verified", "cache-hit-hashes-match"
        return "error", "cache-hit-missing-hashes"
    if cache_status == "invalid":
        return "mismatch", cache_message or "cache-invalid"
    if cache_status == "error":
        return "error", cache_message or "cache-read-error"
    if cache_status == "none":
        return "missing", "manifest-ipc-missing"
    if cache_status == "miss":
        return "missing", "cache-miss"
    return "error", "cache-status-unknown"


def _resolve_patch_state(
    body: dict[str, Any],
    state: ServerState,
) -> tuple[str, PatchState] | None:
    """Resolve and validate ``patch`` from request body.

    Args:
        body: Request payload expected to include optional ``patch``.
        state: Global server state containing patch A and B.

    Returns:
        Tuple of ``(patch_key, patch_state)`` when valid, else ``None``.
    """
    raw_patch = body.get("patch", "a")
    if not isinstance(raw_patch, str):
        return None

    patch_key = raw_patch.lower()
    if patch_key not in ("a", "b"):
        return None

    patch = state.patch_a if patch_key == "a" else state.patch_b
    return patch_key, patch


def _coerce_optional_constraint_int(
    body: dict[str, Any],
    field_name: str,
    *,
    default: int,
) -> tuple[int | None, str | None]:
    """Coerce one optional constraint field from request payload.

    Semantics:
    - Field missing: use provided default for backward compatibility.
    - Field set to null: disable the constraint (returns ``None``).
    - Field set to value: coerce to integer.
    """
    raw = body.get(field_name, _MISSING)
    if raw is _MISSING:
        return default, None
    if raw is None:
        return None, None
    try:
        return int(raw), None
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer or null."


def _persist_patch_artifact_sidecar(
    *,
    state: ServerState,
    patch_key: str,
    artifact_kind: str,
    artifact_payload: dict[str, Any],
) -> None:
    """Persist one patch artifact sidecar + run-state index non-blockingly.

    Persistence is best-effort for UX resilience: API responses for mutable
    actions should still succeed even when filesystem or IPC write operations
    fail (for example due to permission issues in custom output directories).
    """

    from build_tools.syllable_walk_web.services.walker_run_state_store import save_run_state

    try:
        save_run_state(
            state=state,
            patch=patch_key,
            artifact_kind=artifact_kind,
            artifact_payload=artifact_payload,
        )
    except Exception:
        # Phase 1 policy: do not fail user actions on sidecar persistence.
        # Verification/load endpoints will surface missing/mismatch states.
        return


def _compute_patch_comparison(
    *,
    patch_a_manifest_hash: str | None,
    patch_b_manifest_hash: str | None,
) -> dict[str, str]:
    """Compute corpus-hash relationship and policy signal for Patch A/B.

    Returns a compact API object used by UI and automation clients to determine
    whether Patch A and Patch B are operating on the same manifest baseline.
    """

    if not _is_sha256_hex(patch_a_manifest_hash) or not _is_sha256_hex(patch_b_manifest_hash):
        return {
            "corpus_hash_relation": "unknown",
            "policy": "none",
            "reason": "manifest-hash-unavailable",
        }
    if patch_a_manifest_hash == patch_b_manifest_hash:
        return {
            "corpus_hash_relation": "same",
            "policy": "none",
            "reason": "patch-manifest-hashes-match",
        }
    return {
        "corpus_hash_relation": "different",
        "policy": "warn",
        "reason": "patch-manifest-hashes-differ",
    }


def _coerce_lock_holder_id(body: dict[str, Any]) -> tuple[str | None, str | None]:
    """Backward-compatible wrapper for lock holder coercion helper."""

    return _coerce_lock_holder_id_impl(body)


def _lock_conflict_error(
    *, active_session_id: str, lock_payload: dict[str, Any] | None
) -> dict[str, Any]:
    """Backward-compatible wrapper for lock conflict payload helper."""

    return _lock_conflict_error_impl(
        active_session_id=active_session_id,
        lock_payload=lock_payload,
    )


def _enforce_active_session_lock(body: dict[str, Any], state: ServerState) -> dict[str, Any] | None:
    """Backward-compatible wrapper for active-session lock enforcement."""

    return _enforce_active_session_lock_impl(body, state)


def _clear_active_session_context(state: ServerState) -> None:
    """Backward-compatible wrapper for active-session context clear helper."""

    _clear_active_session_context_impl(state)


def handle_load_corpus(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/load-corpus.

    Loads syllables from a discovered pipeline run and initialises the
    SyllableWalker in a background thread.

    Args:
        body: Request body with ``patch`` ("a" or "b") and ``run_id``.
        state: Global server state.

    Returns:
        Immediate response with syllable count and loading status.
    """
    lock_error = _enforce_active_session_lock(body, state)
    if lock_error is not None:
        return lock_error

    resolved = _resolve_patch_state(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved
    run_id = body.get("run_id")

    if not run_id:
        return {"error": "Missing run_id"}

    # Manual corpus loads intentionally detach active session context because
    # patch state is no longer guaranteed to match the loaded session artifact.
    internal_session_load = bool(body.get("_internal_session_load"))
    if not internal_session_load and isinstance(state.active_session_id, str):
        holder_id, _ = _coerce_lock_holder_id(body)
        if (
            isinstance(holder_id, str)
            and isinstance(state.active_session_lock_holder_id, str)
            and holder_id == state.active_session_lock_holder_id
        ):
            from build_tools.syllable_walk_web.services.walker_session_lock import (
                release_session_lock,
            )

            release_session_lock(
                state=state,
                session_id=state.active_session_id,
                holder_id=holder_id,
            )
        _clear_active_session_context(state)

    # Discover the run from the patch's corpus directory (if configured),
    # falling back to the global output_base.
    from build_tools.syllable_walk_web.run_discovery import get_run_by_id

    if patch_key == "a" and state.corpus_dir_a:
        base_path = state.corpus_dir_a
    elif patch_key == "b" and state.corpus_dir_b:
        base_path = state.corpus_dir_b
    else:
        base_path = state.output_base

    run = get_run_by_id(run_id, base_path=base_path)
    if run is None:
        return {"error": f"Run not found: {run_id}"}

    # Load syllables (synchronous — fast, just reads file/DB)
    from build_tools.syllable_walk_web.services.corpus_loader import load_corpus

    try:
        syllables, source = load_corpus(
            corpus_db_path=run.corpus_db_path,
            annotated_json_path=run.annotated_json_path,
        )
    except Exception as e:
        return {"error": f"Failed to load corpus: {e}"}

    run_dir = run.path if isinstance(run.path, Path) else Path(str(run.path))
    from build_tools.syllable_walk_web.services.pipeline_manifest import verify_manifest_ipc_file

    # Reset ALL patch fields when a new corpus is loaded.  This prevents
    # stale state from a previous run leaking through (e.g. old candidates
    # or selections generated from a different corpus).
    patch.run_id = run_id
    patch.corpus_type = run.extractor_type
    patch.corpus_dir = run_dir
    patch.syllable_count = len(syllables)
    patch.annotated_data = syllables
    patch.walker_ready = False
    patch.loading_stage = "Loading corpus data"
    patch.walker = None
    patch.profile_reaches = None
    patch.walks = []
    patch.candidates = None
    patch.candidates_path = None
    patch.selections_path = None
    patch.selected_names = []
    patch.loading_error = None
    raw_manifest_input_hash = getattr(run, "ipc_input_hash", None)
    raw_manifest_output_hash = getattr(run, "ipc_output_hash", None)
    patch.manifest_ipc_input_hash = (
        str(raw_manifest_input_hash) if _is_sha256_hex(raw_manifest_input_hash) else None
    )
    patch.manifest_ipc_output_hash = (
        str(raw_manifest_output_hash) if _is_sha256_hex(raw_manifest_output_hash) else None
    )
    patch.manifest_ipc_verification_status = None
    patch.manifest_ipc_verification_reason = None
    patch.reach_cache_status = None
    patch.reach_cache_ipc_input_hash = None
    patch.reach_cache_ipc_output_hash = None
    patch.reach_cache_ipc_verification_status = None
    patch.reach_cache_ipc_verification_reason = None

    manifest_verification = verify_manifest_ipc_file(run_dir)
    patch.manifest_ipc_verification_status = manifest_verification.status
    patch.manifest_ipc_verification_reason = manifest_verification.reason
    if manifest_verification.input_hash is not None:
        patch.manifest_ipc_input_hash = manifest_verification.input_hash
    if manifest_verification.output_hash is not None:
        patch.manifest_ipc_output_hash = manifest_verification.output_hash
    # Advance generation and mark this request as the only authoritative
    # loader. Older background threads are treated as stale and their
    # writes are ignored.
    patch.load_generation += 1
    load_generation = patch.load_generation
    patch.active_load_generation = load_generation

    # Build a denormalised frequency lookup once here to avoid repeated
    # O(n) scans during later metrics / analysis operations.
    patch.frequencies = {}
    for s in syllables:
        patch.frequencies[s["syllable"]] = s.get("frequency", 1)

    # Walker initialisation is done in a background thread because
    # SyllableWalker.from_data() builds an O(n²) neighbor graph that can
    # take seconds for large corpora.  The HTTP request returns immediately
    # with status="loading" so the UI can poll walker_ready.
    #
    # The loading_stage field is updated at each phase boundary so the UI
    # poller can show progress to the user (e.g. "Building neighbour graph…").
    def _init_walker() -> None:
        def _is_current_generation() -> bool:
            return patch.active_load_generation == load_generation

        try:
            from build_tools.syllable_walk.walker import SyllableWalker

            # Ignore progress updates from stale initialisation threads.
            # The UI poller reads loading_stage via /api/walker/stats.
            def _on_progress(message: str) -> None:
                if _is_current_generation():
                    patch.loading_stage = message

            if not _is_current_generation():
                return

            patch.loading_stage = "Building neighbour graph"
            walker = SyllableWalker.from_data(
                syllables,
                max_neighbor_distance=3,
                progress_callback=_on_progress,
            )

            if not _is_current_generation():
                return

            from build_tools.syllable_walk.reach import compute_all_reaches
            from build_tools.syllable_walk_web.services.profile_reaches_cache import (
                load_cached_profile_reaches,
                read_cached_profile_reach_hashes,
                write_cached_profile_reaches,
            )

            patch.loading_stage = "Loading cached profile reaches"
            cache_result = load_cached_profile_reaches(
                run_dir=run_dir,
                run_id=run_id,
                walker=walker,
            )

            if cache_result.status == "hit" and cache_result.profile_reaches is not None:
                profile_reaches = cache_result.profile_reaches
                patch.reach_cache_status = "hit"
                patch.reach_cache_ipc_input_hash = cache_result.ipc_input_hash
                patch.reach_cache_ipc_output_hash = cache_result.ipc_output_hash
                (
                    patch.reach_cache_ipc_verification_status,
                    patch.reach_cache_ipc_verification_reason,
                ) = _reach_cache_verification_from_read(
                    cache_status=cache_result.status,
                    cache_message=cache_result.message,
                    input_hash=cache_result.ipc_input_hash,
                    output_hash=cache_result.ipc_output_hash,
                )
            else:
                patch.reach_cache_status = cache_result.status
                (
                    patch.reach_cache_ipc_verification_status,
                    patch.reach_cache_ipc_verification_reason,
                ) = _reach_cache_verification_from_read(
                    cache_status=cache_result.status,
                    cache_message=cache_result.message,
                    input_hash=cache_result.ipc_input_hash,
                    output_hash=cache_result.ipc_output_hash,
                )
                # Compute profile reaches (deterministic, typically <1s).
                # This runs BEFORE setting walker_ready so that when the
                # UI poller sees walker_ready=True, reaches are guaranteed
                # to be available in the same stats response. Without this
                # ordering, the poller could see walker_ready=True, stop
                # polling, and miss the reaches entirely.
                patch.loading_stage = "Computing profile reaches"
                profile_reaches = compute_all_reaches(
                    walker,
                    progress_callback=_on_progress,
                )
                if _is_current_generation():
                    cache_written = write_cached_profile_reaches(
                        run_dir=run_dir,
                        run_id=run_id,
                        walker=walker,
                        profile_reaches=profile_reaches,
                    )
                    if cache_written:
                        (
                            patch.reach_cache_ipc_input_hash,
                            patch.reach_cache_ipc_output_hash,
                        ) = read_cached_profile_reach_hashes(run_dir)
                        if _is_sha256_hex(patch.reach_cache_ipc_input_hash) and _is_sha256_hex(
                            patch.reach_cache_ipc_output_hash
                        ):
                            patch.reach_cache_ipc_verification_status = "verified"
                            patch.reach_cache_ipc_verification_reason = (
                                f"cache-written-after-{cache_result.status}"
                            )

            if not _is_current_generation():
                return

            patch.walker = walker
            patch.profile_reaches = profile_reaches
            patch.loading_stage = None
            patch.walker_ready = True
            patch.active_load_generation = None
            patch.loading_error = None

            # TODO: Custom profile reach — on-demand computation
            # When "custom" is selected with manual slider parameters,
            # reach could be computed on-demand via a dedicated API
            # endpoint. This is deferred because it would require an
            # API call each time sliders change and would need
            # debouncing. For now, only the four named profiles have
            # pre-computed reach. Tracked for future implementation.
        except Exception as exc:
            if _is_current_generation():
                patch.loading_stage = None
                patch.walker_ready = False
                patch.active_load_generation = None
                patch.reach_cache_status = "error"
                patch.reach_cache_ipc_input_hash = None
                patch.reach_cache_ipc_output_hash = None
                patch.reach_cache_ipc_verification_status = "error"
                error_message = str(exc).strip() or "Unknown walker initialisation error"
                patch.reach_cache_ipc_verification_reason = f"loader-error:{exc.__class__.__name__}"
                patch.loading_error = f"Walker initialisation failed: {error_message}"

    thread = threading.Thread(target=_init_walker, daemon=True)
    thread.start()

    return {
        "patch": patch_key,
        "run_id": run_id,
        "corpus_type": run.extractor_type,
        "syllable_count": len(syllables),
        "source": source,
        "status": "loading",
    }


def handle_walk(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/walk.

    Generates walks for a specified patch.

    Args:
        body: Request body with walk parameters.
        state: Global server state.

    Returns:
        Walk results with formatted walks.
    """
    lock_error = _enforce_active_session_lock(body, state)
    if lock_error is not None:
        return lock_error

    resolved = _resolve_patch_state(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved

    if not patch.walker_ready or patch.walker is None:
        return {"error": f"Walker not ready for patch {patch_key.upper()}. Load a corpus first."}

    try:
        count = int(body.get("count", 2))
        steps = int(body.get("steps", 5))
        max_flips = int(body.get("max_flips", 2))
        temperature = float(body.get("temperature", 0.7))
        frequency_weight = float(body.get("frequency_weight", 0.0))
    except (TypeError, ValueError):
        return {"error": "Invalid walk parameters: expected numeric values."}

    neighbor_limit, neighbor_err = _coerce_optional_constraint_int(
        body, "neighbor_limit", default=10
    )
    if neighbor_err:
        return {"error": neighbor_err}

    min_length, min_err = _coerce_optional_constraint_int(body, "min_length", default=2)
    if min_err:
        return {"error": min_err}

    max_length, max_err = _coerce_optional_constraint_int(body, "max_length", default=5)
    if max_err:
        return {"error": max_err}

    seed_raw = body.get("seed")
    try:
        seed = int(seed_raw) if seed_raw is not None else None
    except (TypeError, ValueError):
        return {"error": "Invalid seed: expected integer or null."}

    if count < 1:
        return {"error": "count must be >= 1."}
    if steps < 0:
        return {"error": "steps must be >= 0."}
    if max_flips < 1:
        return {"error": "max_flips must be >= 1."}
    if neighbor_limit is not None and neighbor_limit < 1:
        return {"error": "neighbor_limit must be >= 1."}
    if min_length is not None and min_length < 1:
        return {"error": "min_length must be >= 1."}
    if max_length is not None and max_length < 1:
        return {"error": "max_length must be >= 1."}
    if min_length is not None and max_length is not None and min_length > max_length:
        return {"error": "min_length must be <= max_length."}
    if temperature <= 0:
        return {"error": "temperature must be > 0."}

    from build_tools.syllable_walk_web.services.walk_generator import generate_walks

    try:
        walks = generate_walks(
            patch.walker,
            profile=body.get("profile"),
            steps=steps,
            count=count,
            max_flips=max_flips,
            temperature=temperature,
            frequency_weight=frequency_weight,
            neighbor_limit=neighbor_limit,
            min_length=min_length,
            max_length=max_length,
            seed=seed,
        )
    except Exception as e:
        return {"error": f"Walk generation failed: {e}"}

    # Store walks in state
    patch.walks = walks
    _persist_patch_artifact_sidecar(
        state=state,
        patch_key=patch_key,
        artifact_kind="walks",
        artifact_payload={
            "walks": walks,
            "params": {
                "profile": body.get("profile"),
                "count": count,
                "steps": steps,
                "max_flips": max_flips,
                "temperature": temperature,
                "frequency_weight": frequency_weight,
                "neighbor_limit": neighbor_limit,
                "min_length": min_length,
                "max_length": max_length,
                "seed": seed,
            },
        },
    )

    return {
        "patch": patch_key,
        "walks": walks,
    }


def handle_stats(state: ServerState) -> dict[str, Any]:
    """Handle GET /api/walker/stats.

    Returns current walker state for both patches.

    Args:
        state: Global server state.

    Returns:
        State summary for patches A and B.
    """

    def _patch_info(patch: PatchState) -> dict[str, Any]:
        if patch.loading_error:
            loader_status = "error"
        elif patch.walker_ready:
            loader_status = "ready"
        elif patch.active_load_generation is not None:
            loader_status = "loading"
        elif patch.run_id:
            loader_status = "idle"
        else:
            loader_status = "idle"

        info: dict[str, Any] = {
            "corpus": patch.run_id,
            "corpus_type": patch.corpus_type,
            "syllable_count": patch.syllable_count,
            "walker_ready": patch.walker_ready,
            "loading_stage": patch.loading_stage,
            "loading_error": patch.loading_error,
            "loader_status": loader_status,
            "manifest_ipc_input_hash": patch.manifest_ipc_input_hash,
            "manifest_ipc_output_hash": patch.manifest_ipc_output_hash,
            "manifest_ipc_verification_status": patch.manifest_ipc_verification_status,
            "manifest_ipc_verification_reason": patch.manifest_ipc_verification_reason,
            "reach_cache_status": patch.reach_cache_status,
            "reach_cache_ipc_input_hash": patch.reach_cache_ipc_input_hash,
            "reach_cache_ipc_output_hash": patch.reach_cache_ipc_output_hash,
            "reach_cache_ipc_verification_status": patch.reach_cache_ipc_verification_status,
            "reach_cache_ipc_verification_reason": patch.reach_cache_ipc_verification_reason,
            "has_walks": len(patch.walks) > 0,
            "has_candidates": patch.candidates is not None,
            "has_selections": len(patch.selected_names) > 0,
        }
        # Include profile reaches once computed. Each entry contains
        # reach count, total, threshold, and computation timing —
        # enough for the UI micro signal and performance monitoring.
        if patch.profile_reaches:
            info["reaches"] = {
                name: {
                    "reach": r.reach,
                    "total": r.total,
                    "threshold": r.threshold,
                    "computation_ms": r.computation_ms,
                    "unique_reachable": r.unique_reachable,
                }
                for name, r in patch.profile_reaches.items()
            }
        return info

    return {
        "patch_a": _patch_info(state.patch_a),
        "patch_b": _patch_info(state.patch_b),
        "patch_comparison": _compute_patch_comparison(
            patch_a_manifest_hash=state.patch_a.manifest_ipc_output_hash,
            patch_b_manifest_hash=state.patch_b.manifest_ipc_output_hash,
        ),
    }


def handle_save_session(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/save-session.

    Persists one dual-patch session artifact under the runtime-resolved
    sessions base directory.
    """

    lock_error = _enforce_active_session_lock(body, state)
    if lock_error is not None:
        return lock_error

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


def handle_sessions(state: ServerState) -> dict[str, Any]:
    """Handle GET /api/walker/sessions.

    Returns saved session artifacts ordered newest-first with verification
    metadata so clients can decide what is safe to load.
    """

    from build_tools.syllable_walk_web.services.walker_session_lock import get_session_lock_info
    from build_tools.syllable_walk_web.services.walker_session_store import list_sessions

    try:
        entries = list_sessions(
            output_base=state.output_base,
            configured_sessions_base=state.sessions_base,
        )
    except Exception as e:
        return {"error": f"Session listing failed: {e}"}

    serialized_sessions: list[dict[str, Any]] = []
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


def _read_json_object(path: Path) -> dict[str, Any] | None:
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


def _restore_patch_artifacts_from_run_state(
    *,
    patch_key: str,
    patch: PatchState,
) -> dict[str, Any]:
    """Restore patch artifacts from verified run-state sidecars.

    The restore path is strict: if run-state/sidecar structure is missing or
    invalid, restoration is aborted and the caller receives a deterministic
    verification status.
    """

    if not isinstance(patch.run_id, str) or not patch.run_id.strip():
        return {
            "status": "skipped",
            "reason": "run-state-context-missing:run-id",
            "restored": False,
            "restored_kinds": [],
            "run_state_ipc_input_hash": None,
            "run_state_ipc_output_hash": None,
        }
    if not isinstance(patch.corpus_dir, Path):
        return {
            "status": "skipped",
            "reason": "run-state-context-missing:run-dir",
            "restored": False,
            "restored_kinds": [],
            "run_state_ipc_input_hash": None,
            "run_state_ipc_output_hash": None,
        }

    from build_tools.syllable_walk_web.services.walker_run_state_store import load_run_state

    run_state_result = load_run_state(
        run_dir=patch.corpus_dir,
        run_id=patch.run_id,
        manifest_ipc_output_hash=patch.manifest_ipc_output_hash,
    )
    if run_state_result.status != "verified" or not isinstance(run_state_result.payload, dict):
        return {
            "status": run_state_result.status,
            "reason": run_state_result.reason,
            "restored": False,
            "restored_kinds": [],
            "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
            "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
        }

    raw_sidecars = run_state_result.payload.get("sidecars")
    if not isinstance(raw_sidecars, dict):
        return {
            "status": "mismatch",
            "reason": "run-state-sidecars-missing",
            "restored": False,
            "restored_kinds": [],
            "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
            "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
        }

    run_dir_resolved = patch.corpus_dir.resolve()
    restored_kinds: list[str] = []
    for artifact_kind in ("walks", "candidates", "selections", "package"):
        slot = f"patch_{patch_key}_{artifact_kind}"
        ref = raw_sidecars.get(slot)
        if ref is None:
            continue
        if not isinstance(ref, dict):
            return {
                "status": "mismatch",
                "reason": f"run-state-sidecar-ref-invalid:{slot}",
                "restored": False,
                "restored_kinds": restored_kinds,
                "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
            }

        relative_path = ref.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path:
            return {
                "status": "mismatch",
                "reason": f"run-state-sidecar-relative-path-invalid:{slot}",
                "restored": False,
                "restored_kinds": restored_kinds,
                "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
            }

        sidecar_path = (patch.corpus_dir / relative_path).resolve()
        if not str(sidecar_path).startswith(str(run_dir_resolved)):
            return {
                "status": "mismatch",
                "reason": f"run-state-sidecar-path-outside-run-dir:{slot}",
                "restored": False,
                "restored_kinds": restored_kinds,
                "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
            }
        if not sidecar_path.exists():
            return {
                "status": "missing",
                "reason": f"run-state-sidecar-missing:{slot}",
                "restored": False,
                "restored_kinds": restored_kinds,
                "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
            }

        sidecar_payload = _read_json_object(sidecar_path)
        if sidecar_payload is None:
            return {
                "status": "error",
                "reason": f"run-state-sidecar-parse-error:{slot}",
                "restored": False,
                "restored_kinds": restored_kinds,
                "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
            }

        payload_block = sidecar_payload.get("payload")
        if not isinstance(payload_block, dict):
            return {
                "status": "mismatch",
                "reason": f"run-state-sidecar-payload-invalid:{slot}",
                "restored": False,
                "restored_kinds": restored_kinds,
                "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
            }

        if artifact_kind == "walks":
            walks = payload_block.get("walks")
            if not isinstance(walks, list):
                return {
                    "status": "mismatch",
                    "reason": f"run-state-sidecar-walks-invalid:{slot}",
                    "restored": False,
                    "restored_kinds": restored_kinds,
                    "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                    "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
                }
            patch.walks = walks
            restored_kinds.append("walks")
            continue

        if artifact_kind == "candidates":
            candidates = payload_block.get("candidates")
            if not isinstance(candidates, list):
                return {
                    "status": "mismatch",
                    "reason": f"run-state-sidecar-candidates-invalid:{slot}",
                    "restored": False,
                    "restored_kinds": restored_kinds,
                    "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                    "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
                }
            patch.candidates = candidates
            restored_kinds.append("candidates")
            continue

        if artifact_kind == "selections":
            selected_names = payload_block.get("selected_names")
            if not isinstance(selected_names, list):
                return {
                    "status": "mismatch",
                    "reason": f"run-state-sidecar-selections-invalid:{slot}",
                    "restored": False,
                    "restored_kinds": restored_kinds,
                    "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                    "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
                }
            patch.selected_names = selected_names
            restored_kinds.append("selections")
            continue

        # Package sidecar tracks package metadata only; we validate structure
        # for trust but do not mutate in-memory patch fields.
        package_payload = payload_block.get("package")
        if not isinstance(package_payload, dict):
            return {
                "status": "mismatch",
                "reason": f"run-state-sidecar-package-invalid:{slot}",
                "restored": False,
                "restored_kinds": restored_kinds,
                "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
                "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
            }
        restored_kinds.append("package")

    return {
        "status": "verified",
        "reason": "run-state-restored",
        "restored": len(restored_kinds) > 0,
        "restored_kinds": restored_kinds,
        "run_state_ipc_input_hash": run_state_result.run_state_ipc_input_hash,
        "run_state_ipc_output_hash": run_state_result.run_state_ipc_output_hash,
    }


def _is_stale_session_recoverable(*, status: str, reason: str | None) -> bool:
    """Return ``True`` for mismatch states safe to recover from raw payload.

    Recovery is intentionally narrow and limited to session/run-state drift
    caused by later valid writes in another tab/window.
    """

    if status != "mismatch" or not isinstance(reason, str):
        return False
    return reason.endswith("run-state-output-hash-mismatch")


def handle_load_session(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/load-session.

    Verifies one persisted session payload and triggers corpus loading for each
    referenced patch run. This reuses the existing corpus-load API semantics
    rather than mutating state via internal shortcuts.
    """

    from build_tools.syllable_walk_web.services.walker_session_store import load_session

    raw_session_id = body.get("session_id")
    if not isinstance(raw_session_id, str) or not raw_session_id.strip():
        return {"error": "Missing or invalid session_id."}
    session_id = raw_session_id.strip()
    lock_holder_id, lock_holder_error = _coerce_lock_holder_id(body)
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
            return _lock_conflict_error(
                active_session_id=session_id,
                lock_payload=(
                    lock_result.get("lock") if isinstance(lock_result.get("lock"), dict) else None
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
    if payload is None and _is_stale_session_recoverable(
        status=result.status, reason=result.reason
    ):
        candidate_path = getattr(result, "session_path", None)
        if isinstance(candidate_path, Path):
            recovered_payload = _read_json_object(candidate_path)
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

    patch_load_results: dict[str, dict[str, Any]] = {}
    for patch_key in ("a", "b"):
        patch_ref = payload.get(f"patch_{patch_key}")
        if patch_ref is None:
            patch_load_results[patch_key] = {
                "loaded": False,
                "restored": False,
                "verification_status": "missing",
                "verification_reason": f"session-patch-{patch_key}-absent",
                "run_id": None,
            }
            continue
        if not isinstance(patch_ref, dict):
            patch_load_results[patch_key] = {
                "loaded": False,
                "restored": False,
                "verification_status": "mismatch",
                "verification_reason": f"session-patch-{patch_key}-invalid",
                "run_id": None,
            }
            continue
        run_id = patch_ref.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            patch_load_results[patch_key] = {
                "loaded": False,
                "restored": False,
                "verification_status": "mismatch",
                "verification_reason": f"session-patch-{patch_key}-run-id-missing",
                "run_id": None,
            }
            continue

        load_result = handle_load_corpus(
            {
                "patch": patch_key,
                "run_id": run_id,
                "_internal_session_load": True,
                "lock_holder_id": lock_holder_id,
            },
            state,
        )
        if "error" in load_result:
            patch_load_results[patch_key] = {
                "loaded": False,
                "restored": False,
                "verification_status": "error",
                "verification_reason": str(load_result["error"]),
                "run_id": run_id,
            }
            continue

        patch_state = state.patch_a if patch_key == "a" else state.patch_b
        restore_result = _restore_patch_artifacts_from_run_state(
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

    return {
        "status": result.status if recovered_from_stale_session else "verified",
        "reason": result.reason if recovered_from_stale_session else "verified",
        "session_id": loaded_session_id,
        "ipc_input_hash": result.ipc_input_hash,
        "ipc_output_hash": result.ipc_output_hash,
        "recovered_from_stale_session": recovered_from_stale_session,
        "session_lock": {
            "status": lock_result.get("status") if isinstance(lock_result, dict) else "unlocked",
            "reason": (
                lock_result.get("reason") if isinstance(lock_result, dict) else "no-lock-holder"
            ),
            "lock": (
                lock_result.get("lock")
                if isinstance(lock_result, dict) and isinstance(lock_result.get("lock"), dict)
                else None
            ),
        },
        "patch_a": patch_load_results["a"],
        "patch_b": patch_load_results["b"],
    }


def handle_rebuild_reach_cache(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/rebuild-reach-cache.

    Recomputes profile reach tables for one loaded patch and rewrites the
    run-local IPC cache artifact.
    """

    lock_error = _enforce_active_session_lock(body, state)
    if lock_error is not None:
        return lock_error

    resolved = _resolve_patch_state(body, state)
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
    if _is_sha256_hex(cache_input_hash) and _is_sha256_hex(cache_output_hash):
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


def handle_session_lock_heartbeat(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/session-lock/heartbeat.

    Refreshes a session lock lease for the caller's holder id.
    This is cooperative multi-tab coordination, not an auth/security layer.
    """

    raw_session_id = body.get("session_id")
    if not isinstance(raw_session_id, str) or not raw_session_id.strip():
        return {"error": "Missing or invalid session_id."}
    holder_id, holder_error = _coerce_lock_holder_id(body)
    if holder_error is not None or holder_id is None:
        return {"error": holder_error or "Missing lock_holder_id."}

    from build_tools.syllable_walk_web.services.walker_session_lock import heartbeat_session_lock

    result = heartbeat_session_lock(
        state=state,
        session_id=raw_session_id.strip(),
        holder_id=holder_id,
    )
    status = result.get("status")
    if status in {"locked", "error"}:
        return {
            "error": result.get("reason", "Session lock heartbeat failed."),
            "lock_status": status,
            "lock": result.get("lock") if isinstance(result.get("lock"), dict) else None,
        }
    if status == "missing":
        return {
            "status": "missing",
            "reason": result.get("reason", "Session lock not found."),
            "lock": None,
        }
    return {
        "status": "held",
        "reason": result.get("reason", "session lock refreshed"),
        "lock": result.get("lock") if isinstance(result.get("lock"), dict) else None,
    }


def handle_session_lock_release(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/session-lock/release.

    Releases the current lease when called by lock owner.
    """

    raw_session_id = body.get("session_id")
    if not isinstance(raw_session_id, str) or not raw_session_id.strip():
        return {"error": "Missing or invalid session_id."}
    holder_id, holder_error = _coerce_lock_holder_id(body)
    if holder_error is not None or holder_id is None:
        return {"error": holder_error or "Missing lock_holder_id."}

    from build_tools.syllable_walk_web.services.walker_session_lock import release_session_lock

    result = release_session_lock(
        state=state,
        session_id=raw_session_id.strip(),
        holder_id=holder_id,
    )
    status = result.get("status")
    if status in {"locked", "error"}:
        return {
            "error": result.get("reason", "Session lock release failed."),
            "lock_status": status,
            "lock": result.get("lock") if isinstance(result.get("lock"), dict) else None,
        }
    return {
        "status": status,
        "reason": result.get("reason", "session lock released"),
        "lock": result.get("lock") if isinstance(result.get("lock"), dict) else None,
    }


def handle_reach_syllables(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/reach-syllables.

    Returns the list of reachable syllables for a given profile and patch,
    sorted alphabetically with frequency data.

    Args:
        body: Request body with ``patch`` and ``profile``.
        state: Global server state.

    Returns:
        Dict with ``profile``, ``reach``, ``total``, and ``syllables`` list.
    """
    resolved = _resolve_patch_state(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved
    profile = body.get("profile", "")

    if not patch.profile_reaches:
        return {"error": f"No reach data for patch {patch_key.upper()}. Load a corpus first."}

    if profile not in patch.profile_reaches:
        valid = ", ".join(sorted(patch.profile_reaches.keys()))
        return {"error": f"Unknown profile '{profile}'. Valid profiles: {valid}"}

    reach_result = patch.profile_reaches[profile]
    walker = patch.walker

    if walker is None:
        return {"error": f"Walker not ready for patch {patch_key.upper()}."}

    # reachable_indices is a tuple of (syllable_index, reachability_count)
    # pairs, pre-sorted by count descending.  Slice to the top `reach`
    # entries — these are the most commonly available syllables per step,
    # matching the reach badge count shown in the UI.
    top_entries = reach_result.reachable_indices[: reach_result.reach]
    syllables = []
    for idx, reachability in top_entries:
        syllables.append(
            {
                "syllable": walker.syllables[idx],
                "frequency": int(walker.frequencies[idx]),
                "reachability": reachability,
            }
        )

    return {
        "profile": profile,
        "reach": reach_result.reach,
        "total": reach_result.total,
        "unique_reachable": reach_result.unique_reachable,
        "syllables": syllables,
    }


def _combine_via_walks(
    *,
    patch: PatchState,
    profile: str,
    syllable_counts: list[int],
    count: int,
    seed: int | None,
    max_flips: int,
    temperature: float,
    frequency_weight: float,
) -> list[dict[str, Any]]:
    """Generate name candidates using walk-based graph traversal.

    Each candidate is produced by walking the syllable neighbor graph.
    The walk length determines the number of syllables in the name
    (steps + 1 = syllable count).

    Args:
        patch: Patch state with loaded walker and annotated_data.
        profile: Walk profile name or ``"custom"``.
        syllable_counts: List of syllable counts to generate for.
        count: Number of candidates per syllable count.
        seed: RNG seed for determinism.
        max_flips: Max feature flips per step (custom mode only).
        temperature: Exploration temperature (custom mode only).
        frequency_weight: Frequency bias (custom mode only).

    Returns:
        List of candidate dicts with ``name``, ``syllables``, ``features``.
    """
    from build_tools.name_combiner.aggregator import aggregate_features
    from build_tools.syllable_walk_web.services.walk_generator import generate_walks

    # Build a lookup from syllable text → annotated record for feature
    # aggregation.  Walk results contain syllable text but not features.
    assert patch.annotated_data is not None  # caller guards this
    syl_lookup: dict[str, dict[str, Any]] = {}
    for rec in patch.annotated_data:
        syl_lookup[rec["syllable"]] = rec

    candidates: list[dict[str, Any]] = []

    for sc in syllable_counts:
        steps = sc - 1  # walk of N steps → N+1 syllables
        if steps < 1:
            steps = 1

        walk_kwargs: dict[str, Any] = {
            "steps": steps,
            "count": count,
            "seed": seed,
        }
        if profile != "custom":
            walk_kwargs["profile"] = profile
        else:
            walk_kwargs["max_flips"] = max_flips
            walk_kwargs["temperature"] = temperature
            walk_kwargs["frequency_weight"] = frequency_weight

        walks = generate_walks(patch.walker, **walk_kwargs)

        for walk in walks:
            syllable_texts = walk["syllables"]
            # Build annotated records for feature aggregation
            annotated_records = [
                syl_lookup.get(s, {"syllable": s, "features": {}}) for s in syllable_texts
            ]
            features = aggregate_features(annotated_records)
            candidates.append(
                {
                    "name": "".join(syllable_texts),
                    "syllables": syllable_texts,
                    "features": features,
                }
            )

    return candidates


def handle_combine(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/combine.

    Generates name candidates from the loaded corpus syllables.

    Supports two generation modes selected by the ``profile`` parameter:

    - **Flat** (``profile`` absent or ``"flat"``): Independent random sampling
      using ``frequency_weight`` (0.0–1.0).  No walker required.
    - **Walk-based** (``profile`` is a named profile or ``"custom"``): Graph
      traversal using the walker's neighbor graph.  Requires the walker to be
      initialised (``walker_ready``).

    Args:
        body: Request body with ``patch``, ``count``, ``syllables``,
            ``seed``, ``frequency_weight``, and optionally ``profile``,
            ``max_flips``, ``temperature``.
        state: Global server state.

    Returns:
        Candidate generation summary with count and sample.
    """
    lock_error = _enforce_active_session_lock(body, state)
    if lock_error is not None:
        return lock_error

    resolved = _resolve_patch_state(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved

    if not patch.annotated_data:
        return {"error": f"No corpus loaded for patch {patch_key.upper()}."}

    # Accept either a single int or a list of syllable counts.
    raw_syllables = body.get("syllables", 2)
    syllable_counts: list[int] = (
        raw_syllables if isinstance(raw_syllables, list) else [raw_syllables]
    )
    count = body.get("count", 10000)
    seed = body.get("seed")
    frequency_weight = body.get("frequency_weight", 1.0)
    profile = body.get("profile")

    try:
        candidates: list[dict[str, Any]] = []

        if profile and profile != "flat":
            # Walk-based generation — requires initialised walker.
            if not patch.walker_ready or patch.walker is None:
                return {
                    "error": (
                        f"Walker not ready for patch {patch_key.upper()}. "
                        "Load a corpus in the Walk tab first."
                    )
                }

            candidates = _combine_via_walks(
                patch=patch,
                profile=profile,
                syllable_counts=syllable_counts,
                count=count,
                seed=seed,
                max_flips=body.get("max_flips", 2),
                temperature=body.get("temperature", 0.7),
                frequency_weight=body.get("frequency_weight", 0.0),
            )
        else:
            # Flat sampling — original combiner path.
            from build_tools.syllable_walk_web.services.combiner_runner import run_combiner

            for sc in syllable_counts:
                candidates.extend(
                    run_combiner(
                        patch.annotated_data,
                        syllable_count=sc,
                        count=count,
                        seed=seed,
                        frequency_weight=frequency_weight,
                    )
                )
    except Exception as e:
        return {"error": f"Combiner failed: {e}"}

    # Store in patch state
    patch.candidates = candidates
    _persist_patch_artifact_sidecar(
        state=state,
        patch_key=patch_key,
        artifact_kind="candidates",
        artifact_payload={
            "candidates": candidates,
            "params": {
                "profile": profile,
                "syllables": body.get("syllables", 2),
                "count": count,
                "seed": seed,
                "frequency_weight": frequency_weight,
                "max_flips": body.get("max_flips", 2),
                "temperature": body.get("temperature", 0.7),
            },
        },
    )

    # Deduplicate — the combiner may produce duplicate names when the corpus
    # has high-frequency syllables.  Reporting the duplication rate lets the
    # UI show it as a corpus quality signal.
    seen: set[str] = set()
    unique = []
    for c in candidates:
        if c["name"] not in seen:
            seen.add(c["name"])
            unique.append(c)

    return {
        "patch": patch_key,
        "generated": len(candidates),
        "unique": len(unique),
        "duplicates": len(candidates) - len(unique),
        "syllables": body.get("syllables", 2),
        "source": patch.run_id,
    }


def handle_select(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/select.

    Selects names from candidates using a name class policy.

    Args:
        body: Request body with ``patch``, ``name_class``, ``count``,
            ``mode``, ``seed``.
        state: Global server state.

    Returns:
        Selection results with names and metadata.
    """
    lock_error = _enforce_active_session_lock(body, state)
    if lock_error is not None:
        return lock_error

    resolved = _resolve_patch_state(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved

    if not patch.candidates:
        return {"error": f"No candidates for patch {patch_key.upper()}. Run combiner first."}

    from build_tools.syllable_walk_web.services.selector_runner import run_selector

    try:
        result = run_selector(
            patch.candidates,
            name_class=body.get("name_class", "first_name"),
            count=body.get("count", 100),
            mode=body.get("mode", "hard"),
            order=body.get("order", "alphabetical"),
            seed=body.get("seed"),
        )
    except Exception as e:
        return {"error": f"Selector failed: {e}"}

    if "error" in result:
        return result

    # Store selected names in state
    patch.selected_names = result["selected"]
    _persist_patch_artifact_sidecar(
        state=state,
        patch_key=patch_key,
        artifact_kind="selections",
        artifact_payload={
            "selected_names": result["selected"],
            "params": {
                "name_class": body.get("name_class", "first_name"),
                "count": body.get("count", 100),
                "mode": body.get("mode", "hard"),
                "order": body.get("order", "alphabetical"),
                "seed": body.get("seed"),
            },
        },
    )

    return {
        "patch": patch_key,
        "name_class": result["name_class"],
        "mode": result["mode"],
        "count": result["count"],
        "requested": result["requested"],
        "names": [n["name"] for n in result["selected"]],
    }


def handle_export(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/export.

    Returns selected names as a downloadable list.

    Args:
        body: Request body with ``patch``.
        state: Global server state.

    Returns:
        Dict with names list for client-side download.
    """
    resolved = _resolve_patch_state(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved

    if not patch.selected_names:
        return {"error": f"No selected names for patch {patch_key.upper()}."}

    # isinstance check: selections can be either dicts (from select_names)
    # or plain strings (from older code paths or manual state injection).
    names = [n["name"] if isinstance(n, dict) else n for n in patch.selected_names]

    return {
        "patch": patch_key,
        "count": len(names),
        "names": names,
    }


def handle_package(body: dict[str, Any], state: ServerState) -> tuple[bytes, str, str | None]:
    """Handle POST /api/walker/package.

    Builds a ZIP archive from in-memory walker state.

    Args:
        body: Request body with ``name``, ``version``, and include flags.
        state: Global server state.

    Returns:
        Tuple of (zip_bytes, filename, error_message_or_none).
    """
    lock_error = _enforce_active_session_lock(body, state)
    if lock_error is not None:
        return b"", "", str(lock_error.get("error", "Session lock validation failed."))

    from build_tools.syllable_walk_web.services.packager import build_package

    name = body.get("name", "corpus-package")
    version = body.get("version", "0.1.0")

    include_walks_a = body.get("include_walks_a", True)
    include_walks_b = body.get("include_walks_b", True)
    include_candidates = body.get("include_candidates", True)
    include_selections = body.get("include_selections", True)

    zip_bytes, error = build_package(
        state,
        name=name,
        version=version,
        include_walks_a=include_walks_a,
        include_walks_b=include_walks_b,
        include_candidates=include_candidates,
        include_selections=include_selections,
    )

    filename = f"{name}-{version}.zip"
    if error is None:
        for patch_key, include_walks, patch_state in (
            ("a", include_walks_a, state.patch_a),
            ("b", include_walks_b, state.patch_b),
        ):
            # Persist package sidecar only when this patch contributed data.
            patch_contributed = (
                (bool(include_walks) and len(patch_state.walks) > 0)
                or (bool(include_candidates) and patch_state.candidates is not None)
                or (bool(include_selections) and len(patch_state.selected_names) > 0)
            )
            if not patch_contributed:
                continue
            _persist_patch_artifact_sidecar(
                state=state,
                patch_key=patch_key,
                artifact_kind="package",
                artifact_payload={
                    "package": {
                        "name": name,
                        "version": version,
                        "filename": filename,
                        "zip_size_bytes": len(zip_bytes),
                    },
                    "include_flags": {
                        "walks": bool(include_walks),
                        "candidates": bool(include_candidates),
                        "selections": bool(include_selections),
                    },
                    "patch_data_presence": {
                        "has_walks": len(patch_state.walks) > 0,
                        "has_candidates": patch_state.candidates is not None,
                        "has_selections": len(patch_state.selected_names) > 0,
                    },
                },
            )
    return zip_bytes, filename, error


def handle_analysis(patch_key: str, state: ServerState) -> dict[str, Any]:
    """Handle GET /api/walker/analysis/<patch>.

    Computes corpus shape metrics for a patch.

    Args:
        patch_key: ``"a"`` or ``"b"``.
        state: Global server state.

    Returns:
        Corpus analysis metrics (inventory, frequency, terrain).
    """
    if patch_key not in ("a", "b"):
        return {"error": f"Invalid patch: {patch_key}"}

    patch: PatchState = state.patch_a if patch_key == "a" else state.patch_b

    if not patch.annotated_data or not patch.frequencies:
        return {"error": f"No corpus loaded for patch {patch_key.upper()}."}

    from build_tools.syllable_walk_web.services.metrics import compute_analysis

    try:
        return {
            "patch": patch_key,
            "analysis": compute_analysis(patch.annotated_data, patch.frequencies),
        }
    except Exception as e:
        return {"error": f"Analysis failed: {e}"}
