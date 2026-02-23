"""Operational walker API handlers (walk/combine/select/export/package/analysis).

This module holds behavior-preserving extractions from ``api/walker.py``.
The public handler names remain in ``walker.py`` as wrappers, while this
module contains implementation logic.
"""

from __future__ import annotations

from typing import Any, Callable, cast

from build_tools.syllable_walk_web.api.walker_types import (
    AnalysisResponse,
    CombineResponse,
    ErrorResponse,
    ErrorWithLockResponse,
    ExportResponse,
    ReachSyllableRow,
    ReachSyllablesResponse,
    SelectResponse,
    WalkResponse,
)
from build_tools.syllable_walk_web.state import PatchState, ServerState

EnforceActiveLockFn = Callable[[dict[str, Any], ServerState], dict[str, Any] | None]
ResolvePatchStateFn = Callable[[dict[str, Any], ServerState], tuple[str, PatchState] | None]
CoerceOptionalConstraintIntFn = Callable[..., tuple[int | None, str | None]]
PersistPatchArtifactSidecarFn = Callable[..., None]
CombineViaWalksFn = Callable[..., list[dict[str, Any]]]


def _resolve_locked_patch_state(
    *,
    body: dict[str, Any],
    state: ServerState,
    enforce_active_session_lock_fn: EnforceActiveLockFn,
    resolve_patch_state_fn: ResolvePatchStateFn,
) -> tuple[str, PatchState] | ErrorResponse | ErrorWithLockResponse:
    """Resolve patch state with lock enforcement for mutating endpoints."""

    lock_error = enforce_active_session_lock_fn(body, state)
    if lock_error is not None:
        return cast(ErrorWithLockResponse, lock_error)

    resolved = resolve_patch_state_fn(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    return resolved


def combine_via_walks(
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
    """Generate name candidates using walk-based graph traversal."""

    from build_tools.name_combiner.aggregator import aggregate_features
    from build_tools.syllable_walk_web.services.walk_generator import generate_walks

    assert patch.annotated_data is not None
    syl_lookup: dict[str, dict[str, Any]] = {}
    for rec in patch.annotated_data:
        syl_lookup[rec["syllable"]] = rec

    candidates: list[dict[str, Any]] = []

    for sc in syllable_counts:
        steps = sc - 1
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


def handle_walk(
    body: dict[str, Any],
    state: ServerState,
    *,
    enforce_active_session_lock_fn: EnforceActiveLockFn,
    resolve_patch_state_fn: ResolvePatchStateFn,
    coerce_optional_constraint_int_fn: CoerceOptionalConstraintIntFn,
    persist_patch_artifact_sidecar_fn: PersistPatchArtifactSidecarFn,
) -> WalkResponse | ErrorResponse | ErrorWithLockResponse:
    """Handle ``POST /api/walker/walk``."""

    resolved_or_error = _resolve_locked_patch_state(
        body=body,
        state=state,
        enforce_active_session_lock_fn=enforce_active_session_lock_fn,
        resolve_patch_state_fn=resolve_patch_state_fn,
    )
    if isinstance(resolved_or_error, dict):
        return resolved_or_error
    patch_key, patch = resolved_or_error

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

    neighbor_limit, neighbor_err = coerce_optional_constraint_int_fn(
        body, "neighbor_limit", default=10
    )
    if neighbor_err:
        return {"error": neighbor_err}

    min_length, min_err = coerce_optional_constraint_int_fn(body, "min_length", default=2)
    if min_err:
        return {"error": min_err}

    max_length, max_err = coerce_optional_constraint_int_fn(body, "max_length", default=5)
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

    patch.walks = walks
    persist_patch_artifact_sidecar_fn(
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


def handle_reach_syllables(
    body: dict[str, Any],
    state: ServerState,
    *,
    resolve_patch_state_fn: ResolvePatchStateFn,
) -> ReachSyllablesResponse | ErrorResponse:
    """Handle ``POST /api/walker/reach-syllables``."""

    resolved = resolve_patch_state_fn(body, state)
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

    top_entries = reach_result.reachable_indices[: reach_result.reach]
    syllables: list[ReachSyllableRow] = []
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


def handle_combine(
    body: dict[str, Any],
    state: ServerState,
    *,
    enforce_active_session_lock_fn: EnforceActiveLockFn,
    resolve_patch_state_fn: ResolvePatchStateFn,
    combine_via_walks_fn: CombineViaWalksFn,
    persist_patch_artifact_sidecar_fn: PersistPatchArtifactSidecarFn,
) -> CombineResponse | ErrorResponse | ErrorWithLockResponse:
    """Handle ``POST /api/walker/combine``."""

    resolved_or_error = _resolve_locked_patch_state(
        body=body,
        state=state,
        enforce_active_session_lock_fn=enforce_active_session_lock_fn,
        resolve_patch_state_fn=resolve_patch_state_fn,
    )
    if isinstance(resolved_or_error, dict):
        return resolved_or_error
    patch_key, patch = resolved_or_error

    if not patch.annotated_data:
        return {"error": f"No corpus loaded for patch {patch_key.upper()}."}

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
            if not patch.walker_ready or patch.walker is None:
                return {
                    "error": (
                        f"Walker not ready for patch {patch_key.upper()}. "
                        "Load a corpus in the Walk tab first."
                    )
                }

            candidates = combine_via_walks_fn(
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

    patch.candidates = candidates
    persist_patch_artifact_sidecar_fn(
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


def handle_select(
    body: dict[str, Any],
    state: ServerState,
    *,
    enforce_active_session_lock_fn: EnforceActiveLockFn,
    resolve_patch_state_fn: ResolvePatchStateFn,
    persist_patch_artifact_sidecar_fn: PersistPatchArtifactSidecarFn,
) -> SelectResponse | ErrorResponse | ErrorWithLockResponse:
    """Handle ``POST /api/walker/select``."""

    resolved_or_error = _resolve_locked_patch_state(
        body=body,
        state=state,
        enforce_active_session_lock_fn=enforce_active_session_lock_fn,
        resolve_patch_state_fn=resolve_patch_state_fn,
    )
    if isinstance(resolved_or_error, dict):
        return resolved_or_error
    patch_key, patch = resolved_or_error

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
        return {"error": str(result["error"])}

    patch.selected_names = result["selected"]
    persist_patch_artifact_sidecar_fn(
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


def handle_export(
    body: dict[str, Any],
    state: ServerState,
    *,
    resolve_patch_state_fn: ResolvePatchStateFn,
) -> ExportResponse | ErrorResponse:
    """Handle ``POST /api/walker/export``."""

    resolved = resolve_patch_state_fn(body, state)
    if resolved is None:
        return {"error": "Invalid patch. Must be 'a' or 'b'."}
    patch_key, patch = resolved

    if not patch.selected_names:
        return {"error": f"No selected names for patch {patch_key.upper()}."}

    names = [n["name"] if isinstance(n, dict) else n for n in patch.selected_names]

    return {
        "patch": patch_key,
        "count": len(names),
        "names": names,
    }


def handle_package(
    body: dict[str, Any],
    state: ServerState,
    *,
    enforce_active_session_lock_fn: EnforceActiveLockFn,
    persist_patch_artifact_sidecar_fn: PersistPatchArtifactSidecarFn,
) -> tuple[bytes, str, str | None]:
    """Handle ``POST /api/walker/package``."""

    lock_error = enforce_active_session_lock_fn(body, state)
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
            patch_contributed = (
                (bool(include_walks) and len(patch_state.walks) > 0)
                or (bool(include_candidates) and patch_state.candidates is not None)
                or (bool(include_selections) and len(patch_state.selected_names) > 0)
            )
            if not patch_contributed:
                continue
            persist_patch_artifact_sidecar_fn(
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


def handle_analysis(patch_key: str, state: ServerState) -> AnalysisResponse | ErrorResponse:
    """Handle ``GET /api/walker/analysis/<patch>``."""

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
