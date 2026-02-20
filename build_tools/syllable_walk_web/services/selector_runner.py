"""
Name selector service for the web application.

Evaluates name candidates against name class policies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Sequence

# Module-level cache (not functools.lru_cache) because YAML parsing is
# expensive (file I/O + parsing), but policies never change during a server
# session.  A simple None sentinel avoids the overhead of cache key hashing.
_policies: dict | None = None

# parents[3] traverses from services/selector_runner.py up to the project
# root (services → syllable_walk_web → build_tools → project root) where
# data/name_classes.yml lives.
NAME_CLASSES_PATH = Path(__file__).resolve().parents[3] / "data" / "name_classes.yml"


def _get_policies() -> dict:
    """Load and cache name class policies from YAML."""
    global _policies
    if _policies is None:
        from build_tools.name_selector.name_class import load_name_classes

        _policies = load_name_classes(NAME_CLASSES_PATH)
    return _policies


def list_name_classes() -> list[dict[str, Any]]:
    """Return available name classes with metadata.

    Returns:
        List of dicts with ``name``, ``description``, ``syllable_range``.
    """
    policies = _get_policies()
    return [
        {
            "name": name,
            "description": policy.description,
            "syllable_range": list(policy.syllable_range),
        }
        for name, policy in policies.items()
    ]


def run_selector(
    candidates: Sequence[dict[str, Any]],
    *,
    name_class: str = "first_name",
    count: int = 100,
    mode: Literal["hard", "soft"] = "hard",
    order: Literal["alphabetical", "random"] = "alphabetical",
    seed: int | None = None,
) -> dict[str, Any]:
    """Select names from candidates using a name class policy.

    Args:
        candidates: Candidate dicts from the combiner.
        name_class: Policy name (e.g. ``first_name``, ``last_name``).
        count: Maximum names to return.
        mode: ``hard`` rejects discouraged; ``soft`` applies penalty.
        order: Output ordering.
        seed: RNG seed (required for ``order="random"``).

    Returns:
        Dict with ``selected`` (list of name dicts) and ``stats``.
    """
    from build_tools.name_selector.selector import select_names

    policies = _get_policies()
    if name_class not in policies:
        return {"error": f"Unknown name class: {name_class}"}

    policy = policies[name_class]

    selected = select_names(
        candidates=candidates,
        policy=policy,
        count=count,
        mode=mode,
        order=order,
        seed=seed,
    )

    return {
        "name_class": name_class,
        "mode": mode,
        "count": len(selected),
        "requested": count,
        "selected": selected,
    }
