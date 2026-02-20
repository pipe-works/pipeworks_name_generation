"""
Corpus metrics service for the web application.

Computes inventory, frequency, feature saturation, and terrain metrics
for the analysis screen.
"""

from __future__ import annotations

from typing import Any, Sequence


def compute_analysis(
    annotated_data: Sequence[dict[str, Any]],
    frequencies: dict[str, int],
) -> dict[str, Any]:
    """Compute corpus analysis metrics for a patch.

    Args:
        annotated_data: Annotated syllable records.
        frequencies: Syllable frequency map.

    Returns:
        JSON-serialisable dict with inventory, frequency, terrain metrics.
    """
    from build_tools.syllable_walk_tui.services.metrics import (
        compute_corpus_shape_metrics,
    )

    syllables = [s["syllable"] for s in annotated_data]

    metrics = compute_corpus_shape_metrics(syllables, frequencies, annotated_data)

    # Flatten to JSON-serialisable dict
    inv = metrics.inventory
    freq = metrics.frequency
    terrain = metrics.terrain

    # Syllables longer than 5 chars are rare; grouping them into a single
    # "5+" bucket keeps the UI histogram clean.
    len_dist: dict[str, list[int | float]] = {}
    for length, count in sorted(inv.length_distribution.items()):
        key = str(length) if length < 5 else "5+"
        if key in len_dist:
            len_dist[key][0] += count
        else:
            pct = (count / inv.total_count * 100) if inv.total_count else 0
            len_dist[key] = [count, round(pct, 1)]

    # When multiple lengths are merged into the 5+ bucket, the initial
    # percentage was calculated from one length only — recompute from the
    # merged count.
    if "5+" in len_dist:
        len_dist["5+"][1] = round(len_dist["5+"][0] / inv.total_count * 100, 1)

    # Each terrain axis has low-pole and high-pole exemplars (e.g. "shape"
    # axis: simple syllables vs complex syllables).  Merging both poles
    # into a flat list gives the UI a representative sample.
    def _exemplars(axis_exemplars: Any) -> list[str]:
        if axis_exemplars is None:
            return []
        low = axis_exemplars.low_pole_exemplars or []
        high = axis_exemplars.high_pole_exemplars or []
        return low + high

    return {
        "total": inv.total_count,
        "unique": inv.total_count,  # all are already unique
        "hapax": freq.hapax_count,
        "hapax_rate": round(freq.hapax_count / inv.total_count, 3) if inv.total_count else 0,
        "length_distribution": len_dist,
        "terrain": {
            "shape": {
                "score": round(terrain.shape_score, 3),
                "label": terrain.shape_label,
                "pct": round(terrain.shape_score * 100, 0),
                "exemplars": _exemplars(terrain.shape_exemplars),
            },
            "craft": {
                "score": round(terrain.craft_score, 3),
                "label": terrain.craft_label,
                "pct": round(terrain.craft_score * 100, 0),
                "exemplars": _exemplars(terrain.craft_exemplars),
            },
            "space": {
                "score": round(terrain.space_score, 3),
                "label": terrain.space_label,
                "pct": round(terrain.space_score * 100, 0),
                "exemplars": _exemplars(terrain.space_exemplars),
            },
        },
    }
