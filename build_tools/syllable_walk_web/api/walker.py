"""
Walker API handlers for the web application.

Handles corpus loading, walk generation, name generation, analysis,
and walker state queries.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, cast

from build_tools.syllable_walk_web.api.walker_cache_lock import (
    handle_rebuild_reach_cache as _handle_rebuild_reach_cache_impl,
)
from build_tools.syllable_walk_web.api.walker_cache_lock import (
    handle_session_lock_heartbeat as _handle_session_lock_heartbeat_impl,
)
from build_tools.syllable_walk_web.api.walker_cache_lock import (
    handle_session_lock_release as _handle_session_lock_release_impl,
)
from build_tools.syllable_walk_web.api.walker_common import (
    coerce_optional_constraint_int as _coerce_optional_constraint_int_impl,
)
from build_tools.syllable_walk_web.api.walker_common import (
    compute_patch_comparison as _compute_patch_comparison_impl,
)
from build_tools.syllable_walk_web.api.walker_common import (
    is_sha256_hex as _is_sha256_hex_impl,
)
from build_tools.syllable_walk_web.api.walker_common import (
    reach_cache_verification_from_read as _reach_cache_verification_from_read_impl,
)
from build_tools.syllable_walk_web.api.walker_common import (
    resolve_patch_state as _resolve_patch_state_impl,
)
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
from build_tools.syllable_walk_web.api.walker_ops import (
    combine_via_walks as _combine_via_walks_impl,
)
from build_tools.syllable_walk_web.api.walker_ops import (
    handle_analysis as _handle_analysis_impl,
)
from build_tools.syllable_walk_web.api.walker_ops import (
    handle_combine as _handle_combine_impl,
)
from build_tools.syllable_walk_web.api.walker_ops import (
    handle_export as _handle_export_impl,
)
from build_tools.syllable_walk_web.api.walker_ops import (
    handle_package as _handle_package_impl,
)
from build_tools.syllable_walk_web.api.walker_ops import (
    handle_reach_syllables as _handle_reach_syllables_impl,
)
from build_tools.syllable_walk_web.api.walker_ops import (
    handle_select as _handle_select_impl,
)
from build_tools.syllable_walk_web.api.walker_ops import (
    handle_walk as _handle_walk_impl,
)
from build_tools.syllable_walk_web.api.walker_session import (
    handle_load_session as _handle_load_session_impl,
)
from build_tools.syllable_walk_web.api.walker_session import (
    handle_save_session as _handle_save_session_impl,
)
from build_tools.syllable_walk_web.api.walker_session import (
    handle_sessions as _handle_sessions_impl,
)
from build_tools.syllable_walk_web.api.walker_session import (
    is_stale_session_recoverable as _is_stale_session_recoverable_impl,
)
from build_tools.syllable_walk_web.api.walker_session import (
    read_json_object as _read_json_object_impl,
)
from build_tools.syllable_walk_web.api.walker_session import (
    restore_patch_artifacts_from_run_state as _restore_patch_artifacts_from_run_state_impl,
)
from build_tools.syllable_walk_web.api.walker_types import RestorePatchArtifactsResult
from build_tools.syllable_walk_web.state import PatchState, ServerState


def _is_sha256_hex(value: Any) -> bool:
    """Backward-compatible wrapper for SHA-256 string validator."""

    return _is_sha256_hex_impl(value)


def _reach_cache_verification_from_read(
    *,
    cache_status: str | None,
    cache_message: str | None,
    input_hash: str | None,
    output_hash: str | None,
) -> tuple[str | None, str | None]:
    """Backward-compatible wrapper for reach-cache verification mapping."""

    return _reach_cache_verification_from_read_impl(
        cache_status=cache_status,
        cache_message=cache_message,
        input_hash=input_hash,
        output_hash=output_hash,
    )


def _resolve_patch_state(
    body: dict[str, Any],
    state: ServerState,
) -> tuple[str, PatchState] | None:
    """Backward-compatible wrapper for patch-state resolver."""

    return _resolve_patch_state_impl(body, state)


def _coerce_optional_constraint_int(
    body: dict[str, Any],
    field_name: str,
    *,
    default: int,
) -> tuple[int | None, str | None]:
    """Backward-compatible wrapper for optional constraint int coercion."""

    return _coerce_optional_constraint_int_impl(
        body,
        field_name,
        default=default,
    )


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
    """Backward-compatible wrapper for patch comparison helper."""

    return _compute_patch_comparison_impl(
        patch_a_manifest_hash=patch_a_manifest_hash,
        patch_b_manifest_hash=patch_b_manifest_hash,
    )


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
    return cast(
        dict[str, Any],
        _handle_walk_impl(
            body,
            state,
            enforce_active_session_lock_fn=_enforce_active_session_lock,
            resolve_patch_state_fn=_resolve_patch_state,
            coerce_optional_constraint_int_fn=_coerce_optional_constraint_int,
            persist_patch_artifact_sidecar_fn=_persist_patch_artifact_sidecar,
        ),
    )


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

    return cast(
        dict[str, Any],
        _handle_save_session_impl(
            body,
            state,
            enforce_active_session_lock_fn=_enforce_active_session_lock,
        ),
    )


def handle_sessions(state: ServerState) -> dict[str, Any]:
    """Handle GET /api/walker/sessions.

    Returns saved session artifacts ordered newest-first with verification
    metadata so clients can decide what is safe to load.
    """

    return cast(dict[str, Any], _handle_sessions_impl(state))


def _read_json_object(path: Path) -> dict[str, Any] | None:
    """Read one JSON object from ``path``.

    Returns ``None`` on IO, decode, parse, or type failures.
    """

    return _read_json_object_impl(path)


def _restore_patch_artifacts_from_run_state(
    *,
    patch_key: str,
    patch: PatchState,
) -> RestorePatchArtifactsResult:
    """Restore patch artifacts from verified run-state sidecars.

    The restore path is strict: if run-state/sidecar structure is missing or
    invalid, restoration is aborted and the caller receives a deterministic
    verification status.
    """

    return cast(
        RestorePatchArtifactsResult,
        _restore_patch_artifacts_from_run_state_impl(
            patch_key=patch_key,
            patch=patch,
            read_json_object_fn=_read_json_object,
        ),
    )


def _is_stale_session_recoverable(*, status: str, reason: str | None) -> bool:
    """Return ``True`` for mismatch states safe to recover from raw payload.

    Recovery is intentionally narrow and limited to session/run-state drift
    caused by later valid writes in another tab/window.
    """

    return _is_stale_session_recoverable_impl(status=status, reason=reason)


def handle_load_session(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/load-session.

    Verifies one persisted session payload and triggers corpus loading for each
    referenced patch run. This reuses the existing corpus-load API semantics
    rather than mutating state via internal shortcuts.
    """

    return cast(
        dict[str, Any],
        _handle_load_session_impl(
            body,
            state,
            coerce_lock_holder_id_fn=_coerce_lock_holder_id,
            lock_conflict_error_fn=_lock_conflict_error,
            handle_load_corpus_fn=handle_load_corpus,
            restore_patch_artifacts_from_run_state_fn=_restore_patch_artifacts_from_run_state,
            read_json_object_fn=_read_json_object,
        ),
    )


def handle_rebuild_reach_cache(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/rebuild-reach-cache.

    Recomputes profile reach tables for one loaded patch and rewrites the
    run-local IPC cache artifact.
    """

    return cast(
        dict[str, Any],
        _handle_rebuild_reach_cache_impl(
            body,
            state,
            enforce_active_session_lock_fn=_enforce_active_session_lock,
            resolve_patch_state_fn=_resolve_patch_state,
            is_sha256_hex_fn=_is_sha256_hex,
        ),
    )


def handle_session_lock_heartbeat(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/session-lock/heartbeat.

    Refreshes a session lock lease for the caller's holder id.
    This is cooperative multi-tab coordination, not an auth/security layer.
    """

    return cast(
        dict[str, Any],
        _handle_session_lock_heartbeat_impl(
            body,
            state,
            coerce_lock_holder_id_fn=_coerce_lock_holder_id,
        ),
    )


def handle_session_lock_release(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/session-lock/release.

    Releases the current lease when called by lock owner.
    """

    return cast(
        dict[str, Any],
        _handle_session_lock_release_impl(
            body,
            state,
            coerce_lock_holder_id_fn=_coerce_lock_holder_id,
        ),
    )


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
    return cast(
        dict[str, Any],
        _handle_reach_syllables_impl(
            body,
            state,
            resolve_patch_state_fn=_resolve_patch_state,
        ),
    )


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
    """Backward-compatible wrapper for walk-based combine helper."""

    return _combine_via_walks_impl(
        patch=patch,
        profile=profile,
        syllable_counts=syllable_counts,
        count=count,
        seed=seed,
        max_flips=max_flips,
        temperature=temperature,
        frequency_weight=frequency_weight,
    )


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
    return cast(
        dict[str, Any],
        _handle_combine_impl(
            body,
            state,
            enforce_active_session_lock_fn=_enforce_active_session_lock,
            resolve_patch_state_fn=_resolve_patch_state,
            combine_via_walks_fn=_combine_via_walks,
            persist_patch_artifact_sidecar_fn=_persist_patch_artifact_sidecar,
        ),
    )


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
    return cast(
        dict[str, Any],
        _handle_select_impl(
            body,
            state,
            enforce_active_session_lock_fn=_enforce_active_session_lock,
            resolve_patch_state_fn=_resolve_patch_state,
            persist_patch_artifact_sidecar_fn=_persist_patch_artifact_sidecar,
        ),
    )


def handle_export(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/export.

    Returns selected names as a downloadable list.

    Args:
        body: Request body with ``patch``.
        state: Global server state.

    Returns:
        Dict with names list for client-side download.
    """
    return cast(
        dict[str, Any],
        _handle_export_impl(
            body,
            state,
            resolve_patch_state_fn=_resolve_patch_state,
        ),
    )


def handle_package(body: dict[str, Any], state: ServerState) -> tuple[bytes, str, str | None]:
    """Handle POST /api/walker/package.

    Builds a ZIP archive from in-memory walker state.

    Args:
        body: Request body with ``name``, ``version``, and include flags.
        state: Global server state.

    Returns:
        Tuple of (zip_bytes, filename, error_message_or_none).
    """
    return _handle_package_impl(
        body,
        state,
        enforce_active_session_lock_fn=_enforce_active_session_lock,
        persist_patch_artifact_sidecar_fn=_persist_patch_artifact_sidecar,
    )


def handle_analysis(patch_key: str, state: ServerState) -> dict[str, Any]:
    """Handle GET /api/walker/analysis/<patch>.

    Computes corpus shape metrics for a patch.

    Args:
        patch_key: ``"a"`` or ``"b"``.
        state: Global server state.

    Returns:
        Corpus analysis metrics (inventory, frequency, terrain).
    """
    return cast(dict[str, Any], _handle_analysis_impl(patch_key, state))
