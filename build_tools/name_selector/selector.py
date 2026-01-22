"""
Main selector orchestration logic.

This module provides the high-level selection function that coordinates
loading candidates, evaluating them against a policy, and producing
ranked output.

The selector is the central orchestrator of the Selection Policy Layer.
It ties together:
- Candidate loading (from name_combiner output)
- Policy evaluation (from policy.py)
- Result ranking and filtering

Usage
-----
>>> from build_tools.name_selector import select_names, load_name_classes
>>>
>>> # Load policies and candidates
>>> policies = load_name_classes("data/name_classes.yml")
>>> with open("candidates/pyphen_candidates_2syl.json") as f:
...     candidates_data = json.load(f)
>>>
>>> # Select names
>>> selected = select_names(
...     candidates=candidates_data["candidates"],
...     policy=policies["first_name"],
...     count=100,
...     mode="hard",
... )
>>>
>>> for name in selected[:5]:
...     print(f"{name['name']}: score={name['score']}, rank={name['rank']}")
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal

from build_tools.name_selector.policy import check_syllable_count, evaluate_candidate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from build_tools.name_selector.name_class import NameClassPolicy


def select_names(
    candidates: Sequence[dict],
    policy: NameClassPolicy,
    count: int = 100,
    mode: Literal["hard", "soft"] = "hard",
    order: Literal["alphabetical", "random"] = "alphabetical",
    seed: int | None = None,
) -> list[dict]:
    """
    Select and rank name candidates against a policy.

    Evaluates all candidates, filters out rejected ones, ranks by score,
    and returns the top N.

    Parameters
    ----------
    candidates : Sequence[dict]
        List of candidate dictionaries from name_combiner output.
        Each must have "name", "syllables", and "features" keys.

    policy : NameClassPolicy
        The policy to evaluate against.

    count : int, optional
        Maximum number of names to return. Default: 100.

    mode : {"hard", "soft"}, optional
        Evaluation mode. "hard" rejects on discouraged features.
        "soft" applies penalties. Default: "hard".

    order : {"alphabetical", "random"}, optional
        Ordering for names with equal scores. "alphabetical" sorts by name
        for deterministic output. "random" shuffles within score groups
        using the provided seed. Default: "alphabetical".

    seed : int, optional
        RNG seed for random ordering. Only used when order="random".
        Required for deterministic random ordering. Default: None.

    Returns
    -------
    list[dict]
        List of selected candidates, sorted by score (descending).
        Each candidate is augmented with "score", "rank", and "evaluation".

    Examples
    --------
    >>> selected = select_names(candidates, policy, count=50)
    >>> selected[0]["rank"]
    1
    >>> selected[0]["score"]  # Highest score
    4
    >>> len(selected)
    50

    Notes
    -----
    The returned candidates are augmented with:
    - score: int - The policy score
    - rank: int - 1-based rank (1 = best)
    - evaluation: dict - Detailed evaluation breakdown
    """
    admitted: list[dict] = []
    rejected_count = 0
    rejection_reasons: dict[str, int] = {}

    for candidate in candidates:
        # Check syllable count constraint
        if not check_syllable_count(candidate, policy):
            rejected_count += 1
            reason = "syllable_count_out_of_range"
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            continue

        # Evaluate against policy
        is_admitted, score, details = evaluate_candidate(candidate, policy, mode=mode)

        if not is_admitted:
            rejected_count += 1
            reason = details.get("rejection_reason", "unknown")
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            continue

        # Build augmented candidate
        admitted.append(
            {
                "name": candidate["name"],
                "syllables": candidate.get("syllables", []),
                "features": candidate.get("features", {}),
                "score": score,
                "evaluation": details,
            }
        )

    # Sort by score (descending)
    if order == "random":
        # Random shuffle within score groups for variety
        rng = random.Random(seed)  # nosec B311 - deterministic name ordering, not security
        # First sort alphabetically for stable grouping, then shuffle within groups
        admitted.sort(key=lambda x: (-x["score"], x["name"]))
        # Group by score and shuffle within each group
        admitted = _shuffle_within_score_groups(admitted, rng)
    else:
        # Alphabetical: sort by score (descending), then by name (deterministic)
        admitted.sort(key=lambda x: (-x["score"], x["name"]))

    # Assign ranks and limit output
    result = admitted[:count]
    for i, candidate in enumerate(result, start=1):
        candidate["rank"] = i

    return result


def _shuffle_within_score_groups(admitted: list[dict], rng: random.Random) -> list[dict]:
    """
    Shuffle candidates within each score group while preserving score order.

    Parameters
    ----------
    admitted : list[dict]
        List of candidates sorted by score descending.

    rng : random.Random
        Random number generator for shuffling.

    Returns
    -------
    list[dict]
        Candidates with shuffled order within score groups.
    """
    if not admitted:
        return admitted

    result: list[dict] = []
    current_score = admitted[0]["score"]
    current_group: list[dict] = []

    for candidate in admitted:
        if candidate["score"] == current_score:
            current_group.append(candidate)
        else:
            # Shuffle and add the previous group
            rng.shuffle(current_group)
            result.extend(current_group)
            # Start new group
            current_score = candidate["score"]
            current_group = [candidate]

    # Don't forget the last group
    rng.shuffle(current_group)
    result.extend(current_group)

    return result


def compute_selection_statistics(
    candidates: Sequence[dict],
    policy: NameClassPolicy,
    mode: Literal["hard", "soft"] = "hard",
) -> dict:
    """
    Compute statistics about a selection operation.

    Evaluates all candidates and returns aggregate statistics without
    building the full result list.

    Parameters
    ----------
    candidates : Sequence[dict]
        List of candidate dictionaries.

    policy : NameClassPolicy
        The policy to evaluate against.

    mode : {"hard", "soft"}, optional
        Evaluation mode. Default: "hard".

    Returns
    -------
    dict
        Statistics dictionary containing:
        - total_evaluated: int
        - admitted: int
        - rejected: int
        - rejection_reasons: dict[str, int]
        - score_distribution: dict[int, int] (score -> count)

    Examples
    --------
    >>> stats = compute_selection_statistics(candidates, policy)
    >>> stats["admitted"]
    2341
    >>> stats["rejection_reasons"]["ends_with_stop"]
    1234
    """
    total_evaluated = len(candidates)
    admitted_count = 0
    rejection_reasons: dict[str, int] = {}
    score_distribution: dict[int, int] = {}

    for candidate in candidates:
        # Check syllable count
        if not check_syllable_count(candidate, policy):
            reason = "syllable_count_out_of_range"
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            continue

        # Evaluate
        is_admitted, score, details = evaluate_candidate(candidate, policy, mode=mode)

        if not is_admitted:
            reason = details.get("rejection_reason", "unknown")
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            continue

        admitted_count += 1
        score_distribution[score] = score_distribution.get(score, 0) + 1

    return {
        "total_evaluated": total_evaluated,
        "admitted": admitted_count,
        "rejected": total_evaluated - admitted_count,
        "rejection_reasons": rejection_reasons,
        "score_distribution": dict(sorted(score_distribution.items(), reverse=True)),
    }
