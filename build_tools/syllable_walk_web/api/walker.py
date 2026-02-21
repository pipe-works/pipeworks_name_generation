"""
Walker API handlers for the web application.

Handles corpus loading, walk generation, name generation, analysis,
and walker state queries.
"""

from __future__ import annotations

import threading
from typing import Any

from build_tools.syllable_walk_web.state import PatchState, ServerState


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
    patch_key = body.get("patch", "a").lower()
    run_id = body.get("run_id")

    if not run_id:
        return {"error": "Missing run_id"}

    if patch_key not in ("a", "b"):
        return {"error": f"Invalid patch: {patch_key}"}

    patch: PatchState = state.patch_a if patch_key == "a" else state.patch_b

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

    # Reset ALL patch fields when a new corpus is loaded.  This prevents
    # stale state from a previous run leaking through (e.g. old candidates
    # or selections generated from a different corpus).
    patch.run_id = run_id
    patch.corpus_type = run.extractor_type
    patch.corpus_dir = run.path
    patch.syllable_count = len(syllables)
    patch.annotated_data = syllables
    patch.walker_ready = False
    patch.loading_stage = "Loading corpus data"
    patch.walker = None
    patch.profile_reaches = None
    patch.walks = []
    patch.candidates_path = None
    patch.selections_path = None
    patch.selected_names = []

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
        try:
            from build_tools.syllable_walk.walker import SyllableWalker

            # Progress callback writes directly to patch.loading_stage.
            # The UI poller reads this field every second via /api/walker/stats.
            def _on_progress(message: str) -> None:
                patch.loading_stage = message

            patch.loading_stage = "Building neighbour graph"
            walker = SyllableWalker.from_data(
                syllables,
                max_neighbor_distance=3,
                progress_callback=_on_progress,
            )
            patch.walker = walker

            # Compute profile reaches (deterministic, typically <1s).
            # This runs BEFORE setting walker_ready so that when the
            # UI poller sees walker_ready=True, reaches are guaranteed
            # to be available in the same stats response. Without this
            # ordering, the poller could see walker_ready=True, stop
            # polling, and miss the reaches entirely.
            from build_tools.syllable_walk.reach import compute_all_reaches

            patch.loading_stage = "Computing profile reaches"
            patch.profile_reaches = compute_all_reaches(
                walker,
                progress_callback=_on_progress,
            )
            patch.loading_stage = None
            patch.walker_ready = True

            # TODO: Custom profile reach — on-demand computation
            # When "custom" is selected with manual slider parameters,
            # reach could be computed on-demand via a dedicated API
            # endpoint. This is deferred because it would require an
            # API call each time sliders change and would need
            # debouncing. For now, only the four named profiles have
            # pre-computed reach. Tracked for future implementation.
        except Exception:
            patch.loading_stage = None
            patch.walker_ready = False

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
    patch_key = body.get("patch", "a").lower()
    patch: PatchState = state.patch_a if patch_key == "a" else state.patch_b

    if not patch.walker_ready or patch.walker is None:
        return {"error": f"Walker not ready for patch {patch_key.upper()}. Load a corpus first."}

    from build_tools.syllable_walk_web.services.walk_generator import generate_walks

    try:
        walks = generate_walks(
            patch.walker,
            profile=body.get("profile"),
            steps=body.get("steps", 5),
            count=body.get("count", 2),
            max_flips=body.get("max_flips", 2),
            temperature=body.get("temperature", 0.7),
            frequency_weight=body.get("frequency_weight", 0.0),
            neighbor_limit=body.get("neighbor_limit", 10),
            min_length=body.get("min_length", 2),
            max_length=body.get("max_length", 5),
            seed=body.get("seed"),
        )
    except Exception as e:
        return {"error": f"Walk generation failed: {e}"}

    # Store walks in state
    patch.walks = walks

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
        info: dict[str, Any] = {
            "corpus": patch.run_id,
            "corpus_type": patch.corpus_type,
            "syllable_count": patch.syllable_count,
            "walker_ready": patch.walker_ready,
            "loading_stage": patch.loading_stage,
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
    }


def handle_combine(body: dict[str, Any], state: ServerState) -> dict[str, Any]:
    """Handle POST /api/walker/combine.

    Generates name candidates from the loaded corpus syllables.

    Args:
        body: Request body with ``patch``, ``count``, ``syllables``,
            ``seed``, ``frequency_weight``.
        state: Global server state.

    Returns:
        Candidate generation summary with count and sample.
    """
    patch_key = body.get("patch", "a").lower()
    patch: PatchState = state.patch_a if patch_key == "a" else state.patch_b

    if not patch.annotated_data:
        return {"error": f"No corpus loaded for patch {patch_key.upper()}."}

    from build_tools.syllable_walk_web.services.combiner_runner import run_combiner

    # Accept either a single int or a list of syllable counts.
    raw_syllables = body.get("syllables", 2)
    syllable_counts: list[int] = (
        raw_syllables if isinstance(raw_syllables, list) else [raw_syllables]
    )
    count = body.get("count", 10000)
    seed = body.get("seed")
    frequency_weight = body.get("frequency_weight", 1.0)

    try:
        candidates: list[dict[str, Any]] = []
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
    patch_key = body.get("patch", "a").lower()
    patch: PatchState = state.patch_a if patch_key == "a" else state.patch_b

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
    patch_key = body.get("patch", "a").lower()
    patch: PatchState = state.patch_a if patch_key == "a" else state.patch_b

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
    from build_tools.syllable_walk_web.services.packager import build_package

    name = body.get("name", "corpus-package")
    version = body.get("version", "0.1.0")

    zip_bytes, error = build_package(
        state,
        name=name,
        version=version,
        include_walks_a=body.get("include_walks_a", True),
        include_walks_b=body.get("include_walks_b", True),
        include_candidates=body.get("include_candidates", True),
        include_selections=body.get("include_selections", True),
    )

    filename = f"{name}-{version}.zip"
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
