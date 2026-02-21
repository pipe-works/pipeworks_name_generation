"""Thermodynamic reach calculator for syllable walker profiles.

Computes the **mean effective vocabulary** of each walk profile — the average
number of syllables with non-negligible transition probability from any given
starting position, under the profile's complete parameter set (max_flips,
temperature, frequency_weight).

This is a deterministic, seed-independent metric that reflects the thermodynamic
structure of the profile's constraint regime, not stochastic walk behaviour.

The algorithm replicates the walker's softmax transition math (see
``SyllableWalker.walk()``), but exhaustively over all starting nodes rather than
sampling a single path. For each starting syllable, it computes the full
probability distribution over candidate neighbors, then counts how many
syllables exceed a probability threshold. The final reach value is the
**mean** of these per-node counts across all starting positions.

Why mean-per-node instead of union?
    An earlier implementation used the union of all reachable syllables
    across all starting nodes. This produced poor discrimination at
    production scale: with N=1,757 starting nodes and threshold=0.001,
    almost every syllable was reachable from *some* starting node, making
    reach ≈ total for any profile with max_flips ≥ 2. The mean-per-node
    approach captures the effective vocabulary *per step* of a walk,
    which scales correctly with corpus size and discriminates between
    profiles that differ only in temperature or frequency_weight.

Design reference:
    ``_working/syllable_walker_profile_field_micro_signal.md``

Key properties:
    - Deterministic: same corpus + profile always produces the same reach
    - Seed-independent: no random sampling involved
    - Captures all three profile parameters (max_flips, temperature, frequency_weight)
    - Produces genuinely different values for all four named profiles
    - Scales correctly with corpus size (no saturation)
    - Computed once per corpus load, not per walk

Example:
    >>> from build_tools.syllable_walk.reach import compute_all_reaches
    >>> from build_tools.syllable_walk import SyllableWalker
    >>> walker = SyllableWalker("data/annotated/syllables_annotated.json")
    >>> reaches = compute_all_reaches(walker)
    >>> for name, result in reaches.items():
    ...     print(f"{name}: reach {result.reach} / {result.total}")
    clerical: reach 4 / 2088
    dialect: reach 32 / 2088
    goblin: reach 58 / 2088
    ritual: reach 147 / 2088
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from build_tools.syllable_walk.profiles import WALK_PROFILES

if TYPE_CHECKING:
    from build_tools.syllable_walk.walker import SyllableWalker

# ============================================================
# Threshold Configuration
# ============================================================

# THRESHOLD NOTE — Future Analysis Tab Integration
#
# The DEFAULT_REACH_THRESHOLD (0.001) determines the minimum transition
# probability for a syllable to be counted as "effectively reachable."
# This value was chosen as a sensible default for the Level 1 micro signal
# displayed inline on profile labels.
#
# In a future iteration, this threshold could be exposed as a configurable
# slider in the Analysis tab, allowing users to explore how reach changes
# across different probability thresholds (sensitivity analysis). This would
# visualise the relationship between threshold and reach as a curve,
# providing deeper insight into the profile's probability landscape.
#
# Potential Analysis tab features:
#   - Threshold slider (0.0001 to 0.1, log scale)
#   - Reach-vs-threshold curve per profile (all four overlaid)
#   - Comparison view: how the same corpus behaves under different thresholds
#   - Exportable data for external analysis
#
# See: _working/syllable_walker_profile_field_micro_signal.md §8
DEFAULT_REACH_THRESHOLD: float = 0.001


# ============================================================
# Result Data Class
# ============================================================


@dataclass(frozen=True)
class ReachResult:
    """Result of a thermodynamic reach computation for a single profile.

    Encapsulates both the reach count and the full context of how it was
    computed, including the profile parameters and timing metadata.

    Attributes:
        profile_name: Name of the profile (e.g., "clerical", "dialect").
        reach: Mean number of syllables reachable per starting node (rounded).
            This is the primary micro signal — the average effective vocabulary
            size at each step of a walk under this profile's constraints.
        total: Total syllables in the corpus (the "field" size).
        threshold: Probability threshold used for the reachability test.
            A syllable is counted if p > threshold from the starting node.
        max_flips: Profile's max_flips parameter (edge existence constraint).
        temperature: Profile's temperature parameter (probability shape).
        frequency_weight: Profile's frequency_weight parameter (rarity bias).
        computation_ms: Wall-clock time for this profile's computation in
            milliseconds. Captured as metadata to monitor performance across
            different systems and corpus sizes.
        unique_reachable: Total unique syllables reachable from at least one
            starting node (union across all nodes). This is supplementary
            context — the mean per-node count (``reach``) is the primary
            metric displayed in the UI.
        reachable_indices: Tuple of ``(syllable_index, reachability_count)``
            pairs for all syllables in the union reachable set, sorted by
            reachability count descending (most commonly reachable first).
            The count is how many starting nodes can reach that syllable.
            Maps to syllable text via ``walker.syllables[idx]``.
            Omitted from ``to_dict()`` to keep API responses lean.

    Example:
        >>> result = ReachResult(
        ...     profile_name="dialect",
        ...     reach=32,
        ...     total=2088,
        ...     threshold=0.001,
        ...     max_flips=2,
        ...     temperature=0.7,
        ...     frequency_weight=0.0,
        ...     computation_ms=42.5,
        ...     unique_reachable=1850,
        ... )
        >>> result.reach
        32
    """

    profile_name: str
    reach: int
    total: int
    threshold: float
    max_flips: int
    temperature: float
    frequency_weight: float
    computation_ms: float
    unique_reachable: int = 0
    reachable_indices: tuple[tuple[int, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary for API responses.

        Returns:
            Dictionary with all fields, suitable for JSON serialisation.

        Example:
            >>> result.to_dict()
            {'profile_name': 'dialect', 'reach': 32, 'total': 2088, ...}
        """
        return {
            "profile_name": self.profile_name,
            "reach": self.reach,
            "total": self.total,
            "threshold": self.threshold,
            "max_flips": self.max_flips,
            "temperature": self.temperature,
            "frequency_weight": self.frequency_weight,
            "computation_ms": self.computation_ms,
            "unique_reachable": self.unique_reachable,
        }


# ============================================================
# Core Computation
# ============================================================


def compute_reach(
    walker: SyllableWalker,
    profile_name: str,
    max_flips: int,
    temperature: float,
    frequency_weight: float,
    threshold: float = DEFAULT_REACH_THRESHOLD,
) -> ReachResult:
    """Compute mean effective vocabulary for a single profile.

    For each syllable in the corpus, computes the softmax transition
    probability distribution over all neighbors within ``max_flips``
    distance, using the profile's ``temperature`` and ``frequency_weight``.
    Counts how many neighbors exceed the probability threshold, then
    returns the **mean** of these per-node counts as the reach value.

    This replicates the same math as ``SyllableWalker.walk()`` (lines
    526–549 of walker.py), but exhaustively over all starting nodes
    rather than sampling a single stochastic path.

    The computation is:
        1. For each starting syllable *s*:
           a. Collect all neighbors within max_flips Hamming distance
           b. Compute cost per neighbor: flip_cost + rarity_cost
           c. Add inertia option (staying at *s*) for normalisation
           d. Apply softmax: weight_i = exp(-cost_i / temperature)
           e. Normalise to probabilities
           f. Count **other** syllables (not *s* itself) with p > threshold.
              Inertia participates in normalisation but self-transitions
              do not count toward reach.
        2. Return the **mean** per-node count (rounded to nearest integer)

    Why mean-per-node instead of union?
        The union approach (counting syllables reachable from *any* starting
        node) saturates to near-total for production corpora. With N=1,757
        nodes and threshold=0.001, almost every syllable is reachable from
        at least one starting node, making reach ≈ total for any profile
        with max_flips ≥ 2. The mean-per-node count captures the effective
        vocabulary *per step*, which scales correctly with corpus size.

    Args:
        walker: Initialised SyllableWalker with pre-computed neighbor graph.
            Must have ``neighbor_graph``, ``_flip_cost()``, ``_rarity_cost()``,
            ``_hamming_distance()``, and ``inertia_cost`` available.
        profile_name: Human-readable name for the profile (e.g., "dialect").
            Stored in the result for identification.
        max_flips: Maximum feature flips per step (1–3). Determines which
            edges in the neighbor graph are traversable.
        temperature: Softmax temperature (0.1–5.0). Controls the shape of
            the probability distribution. Low temperature concentrates
            probability on low-cost transitions; high temperature flattens
            the distribution toward uniform.
        frequency_weight: Frequency bias (-2.0 to 2.0). Positive values
            penalise rare syllables (favour common); negative values reward
            rare syllables (favour uncommon).
        threshold: Minimum transition probability for a syllable to be
            counted as "effectively reachable." Default: 0.001.

    Returns:
        ReachResult with the mean per-node reach count, corpus total,
        unique reachable count (union), and metadata.

    Raises:
        ValueError: If walker has no syllables loaded.

    Example:
        >>> result = compute_reach(
        ...     walker, "dialect",
        ...     max_flips=2, temperature=0.7, frequency_weight=0.0,
        ... )
        >>> print(f"Dialect reach: {result.reach} / {result.total}")
        Dialect reach: 32 / 2088
    """
    total_syllables = len(walker.syllables)
    if total_syllables == 0:
        raise ValueError("Walker has no syllables loaded.")

    start_time = time.monotonic()

    # Per-node reachable counts. For each starting node, we count how many
    # OTHER syllables have transition probability > threshold. The mean of
    # these counts is the primary reach metric.
    per_node_counts: list[int] = []

    # Union set: tracks ALL syllables reachable from ANY starting node.
    # This is supplementary context (stored as unique_reachable).
    union_reachable: set[int] = set()

    # Per-syllable reachability count: how many starting nodes can reach
    # each syllable.  Used to identify the "commonly reachable" set —
    # syllables reachable from >= 50% of starting positions.
    reachability_counts: dict[int, int] = {}

    # Iterate over every syllable as a potential starting node.
    # This is the "exhaustive" part — we compute the transition
    # distribution from every possible position in the graph.
    for start_idx in range(total_syllables):
        # Collect candidate transitions (same logic as walker.walk()).
        # Each candidate is a (syllable_index, cost) pair.
        candidates: list[tuple[int, float]] = []

        # Find all neighbors within max_flips Hamming distance.
        # The neighbor_graph was pre-computed during walker init and
        # contains all neighbors within max_neighbor_distance.
        for neighbor_idx in walker.neighbor_graph[start_idx]:
            if walker._hamming_distance(start_idx, neighbor_idx) <= max_flips:
                # Total cost = weighted feature flip cost + frequency bias cost.
                # This is the same formula as walker.walk() lines 534-536.
                cost = walker._flip_cost(start_idx, neighbor_idx)
                cost += walker._rarity_cost(neighbor_idx, frequency_weight)
                candidates.append((neighbor_idx, cost))

        # Add inertia option: the walker can choose to stay at the current
        # syllable with a fixed cost. This is important because it affects
        # the normalisation — a high inertia cost makes transitions more
        # likely; a low inertia cost makes staying more likely.
        candidates.append((start_idx, walker.inertia_cost))

        # Softmax: convert costs to unnormalised weights.
        # Lower cost → higher weight → higher probability.
        # Temperature controls the distribution shape:
        #   - Low T (0.3): sharply peaked, strongly prefers lowest cost
        #   - High T (2.5): nearly uniform across all candidates
        #
        # Formula: weight_i = exp(-cost_i / temperature)
        weights = [math.exp(-cost / temperature) for _, cost in candidates]

        # Normalise to probabilities (sum to 1.0).
        total_weight = sum(weights)

        # Count candidates whose probability exceeds the threshold.
        # This is the key step — we're asking "from this starting node,
        # how many OTHER syllables have a meaningful chance of being visited?"
        #
        # The inertia option (idx == start_idx) is deliberately excluded.
        # Inertia is included in the softmax to affect normalisation (it
        # competes for probability mass, shaping the distribution over
        # actual transitions), but self-transitions do not count as
        # "reaching" a new syllable.
        node_count = 0
        for (idx, _), weight in zip(candidates, weights):
            if idx == start_idx:
                continue  # Skip inertia (self-transition)
            probability = weight / total_weight
            if probability > threshold:
                node_count += 1
                union_reachable.add(idx)
                reachability_counts[idx] = reachability_counts.get(idx, 0) + 1
        per_node_counts.append(node_count)

    elapsed_ms = (time.monotonic() - start_time) * 1000.0

    # The primary reach metric is the mean per-node count, rounded to the
    # nearest integer for display. This represents "on average, how many
    # syllables are effectively available at each step of a walk?"
    mean_reach = sum(per_node_counts) / len(per_node_counts)

    # Build reachable entries sorted by reachability count descending
    # (most commonly reachable syllables first).  Each entry is
    # (syllable_index, count_of_starting_nodes_that_can_reach_it).
    reachable_entries = sorted(reachability_counts.items(), key=lambda x: (-x[1], x[0]))

    return ReachResult(
        profile_name=profile_name,
        reach=round(mean_reach),
        total=total_syllables,
        threshold=threshold,
        max_flips=max_flips,
        temperature=temperature,
        frequency_weight=frequency_weight,
        computation_ms=round(elapsed_ms, 2),
        unique_reachable=len(union_reachable),
        reachable_indices=tuple(reachable_entries),
    )


def compute_all_reaches(
    walker: SyllableWalker,
    threshold: float = DEFAULT_REACH_THRESHOLD,
    progress_callback: "Callable[[str], None] | None" = None,
) -> dict[str, ReachResult]:
    """Compute mean effective vocabulary for all four named walk profiles.

    Iterates over the predefined profiles (clerical, dialect, goblin, ritual)
    and computes the mean per-node thermodynamic reach for each. Returns a
    dictionary mapping profile names to their ReachResult.

    This is intended to be called once after the walker finishes initialising,
    typically in the background thread that builds the neighbor graph. The
    results are cached in PatchState and served via the stats endpoint.

    Args:
        walker: Initialised SyllableWalker with pre-computed neighbor graph.
        threshold: Minimum transition probability for reachability.
            Default: 0.001. See ``DEFAULT_REACH_THRESHOLD`` for rationale.
        progress_callback: Optional callable invoked with a progress message
            after each profile is computed. Used by the web UI to show
            incremental reach results like
            ``"Computing reaches: clerical ~4, dialect ~32..."``.

    Returns:
        Dictionary mapping profile name to ReachResult.
        Keys: ``"clerical"``, ``"dialect"``, ``"goblin"``, ``"ritual"``.

    Example:
        >>> reaches = compute_all_reaches(walker)
        >>> for name, r in reaches.items():
        ...     print(f"{name}: reach={r.reach}, time={r.computation_ms}ms")
        clerical: reach=4, time=12.3ms
        dialect: reach=32, time=15.1ms
        goblin: reach=58, time=14.8ms
        ritual: reach=147, time=18.2ms

    Note:
        Custom profile reach is not computed here. See the TODO note in
        ``api/walker.py`` regarding on-demand computation for custom profiles.
    """
    results: dict[str, ReachResult] = {}

    for name, profile in WALK_PROFILES.items():
        results[name] = compute_reach(
            walker=walker,
            profile_name=name,
            max_flips=profile.max_flips,
            temperature=profile.temperature,
            frequency_weight=profile.frequency_weight,
            threshold=threshold,
        )

        # Report incremental reach results so the UI can show progress.
        # Builds a string like "clerical ~4 · dialect ~32 · ..."
        if progress_callback is not None:
            parts = [f"{n} ~{r.reach}" for n, r in results.items()]
            progress_callback(f"Computing reaches: {' \u00b7 '.join(parts)}")

    return results
