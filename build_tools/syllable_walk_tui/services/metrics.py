"""
Corpus shape metrics computation.

This module provides dataclasses and pure functions for computing raw,
objective metrics about corpus shape. These metrics characterize the
statistical structure of a syllable corpus without interpretation.

Design Philosophy:
    - Raw numbers only, no interpretation or judgment
    - Pure functions (no side effects, no I/O)
    - All metrics are observable facts about the corpus
    - Users draw their own conclusions from the data

Metric Categories:
    - Inventory: What exists (counts, lengths)
    - Frequency: Weight distribution (how syllables are distributed)
    - Feature Saturation: Phonetic feature coverage (per-feature counts)

Usage:
    >>> from build_tools.syllable_walk_tui.services.metrics import (
    ...     compute_corpus_shape_metrics
    ... )
    >>> metrics = compute_corpus_shape_metrics(syllables, frequencies, annotated_data)
    >>> print(f"Total syllables: {metrics.inventory.total_count}")
    >>> print(f"Hapax count: {metrics.frequency.hapax_count}")
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

# =============================================================================
# Inventory Metrics
# =============================================================================


@dataclass(frozen=True)
class InventoryMetrics:
    """
    Raw inventory metrics describing what exists in the corpus.

    All metrics are objective counts and statistics about syllable inventory.

    Attributes:
        total_count: Total number of unique syllables
        length_min: Minimum syllable length (characters)
        length_max: Maximum syllable length (characters)
        length_mean: Mean syllable length
        length_median: Median syllable length
        length_std: Standard deviation of syllable lengths
        length_distribution: Count of syllables at each length {length: count}
    """

    total_count: int
    length_min: int
    length_max: int
    length_mean: float
    length_median: float
    length_std: float
    length_distribution: dict[int, int] = field(default_factory=dict)


def compute_inventory_metrics(syllables: Sequence[str]) -> InventoryMetrics:
    """
    Compute inventory metrics from a list of syllables.

    Args:
        syllables: List of unique syllables

    Returns:
        InventoryMetrics with all computed values

    Raises:
        ValueError: If syllables list is empty
    """
    if not syllables:
        raise ValueError("Cannot compute metrics for empty syllable list")

    lengths = [len(s) for s in syllables]

    # Build length distribution
    length_dist: dict[int, int] = {}
    for length in lengths:
        length_dist[length] = length_dist.get(length, 0) + 1

    # Handle edge case of single syllable (stdev requires 2+ values)
    length_std = 0.0
    if len(lengths) >= 2:
        length_std = statistics.stdev(lengths)

    return InventoryMetrics(
        total_count=len(syllables),
        length_min=min(lengths),
        length_max=max(lengths),
        length_mean=statistics.mean(lengths),
        length_median=statistics.median(lengths),
        length_std=length_std,
        length_distribution=dict(sorted(length_dist.items())),
    )


# =============================================================================
# Frequency Metrics
# =============================================================================


@dataclass(frozen=True)
class FrequencyMetrics:
    """
    Raw frequency distribution metrics.

    Describes how syllable occurrences are distributed across the corpus.

    Attributes:
        total_occurrences: Sum of all frequency counts
        freq_min: Minimum frequency value
        freq_max: Maximum frequency value
        freq_mean: Mean frequency
        freq_median: Median frequency
        freq_std: Standard deviation of frequencies
        percentile_10: 10th percentile frequency
        percentile_25: 25th percentile frequency (Q1)
        percentile_50: 50th percentile frequency (median)
        percentile_75: 75th percentile frequency (Q3)
        percentile_90: 90th percentile frequency
        percentile_99: 99th percentile frequency
        unique_freq_count: Number of distinct frequency values
        hapax_count: Count of syllables appearing exactly once
        top_10: Top 10 syllables by frequency [(syllable, freq), ...]
        bottom_10: Bottom 10 syllables by frequency [(syllable, freq), ...]
    """

    total_occurrences: int
    freq_min: int
    freq_max: int
    freq_mean: float
    freq_median: float
    freq_std: float
    percentile_10: int
    percentile_25: int
    percentile_50: int
    percentile_75: int
    percentile_90: int
    percentile_99: int
    unique_freq_count: int
    hapax_count: int
    top_10: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    bottom_10: tuple[tuple[str, int], ...] = field(default_factory=tuple)


def compute_frequency_metrics(frequencies: dict[str, int]) -> FrequencyMetrics:
    """
    Compute frequency distribution metrics.

    Args:
        frequencies: Dictionary mapping syllable to frequency count

    Returns:
        FrequencyMetrics with all computed values

    Raises:
        ValueError: If frequencies dict is empty
    """
    if not frequencies:
        raise ValueError("Cannot compute metrics for empty frequencies dict")

    freq_values = list(frequencies.values())
    freq_array = np.array(freq_values, dtype=np.int64)

    # Compute percentiles
    percentiles = np.percentile(freq_array, [10, 25, 50, 75, 90, 99])

    # Count hapax legomena (frequency = 1)
    hapax_count = sum(1 for f in freq_values if f == 1)

    # Unique frequency values
    unique_freq_count = len(set(freq_values))

    # Sort for top/bottom
    sorted_by_freq = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
    top_10 = tuple(sorted_by_freq[:10])
    bottom_10 = tuple(sorted_by_freq[-10:][::-1])  # Reverse to show lowest first

    # Handle edge case of single entry
    freq_std = 0.0
    if len(freq_values) >= 2:
        freq_std = statistics.stdev(freq_values)

    return FrequencyMetrics(
        total_occurrences=sum(freq_values),
        freq_min=min(freq_values),
        freq_max=max(freq_values),
        freq_mean=statistics.mean(freq_values),
        freq_median=statistics.median(freq_values),
        freq_std=freq_std,
        percentile_10=int(percentiles[0]),
        percentile_25=int(percentiles[1]),
        percentile_50=int(percentiles[2]),
        percentile_75=int(percentiles[3]),
        percentile_90=int(percentiles[4]),
        percentile_99=int(percentiles[5]),
        unique_freq_count=unique_freq_count,
        hapax_count=hapax_count,
        top_10=top_10,
        bottom_10=bottom_10,
    )


# =============================================================================
# Feature Saturation Metrics
# =============================================================================

# Canonical feature order (matches annotator output)
FEATURE_NAMES: tuple[str, ...] = (
    "starts_with_vowel",
    "starts_with_cluster",
    "starts_with_heavy_cluster",
    "contains_plosive",
    "contains_fricative",
    "contains_liquid",
    "contains_nasal",
    "short_vowel",
    "long_vowel",
    "ends_with_vowel",
    "ends_with_nasal",
    "ends_with_stop",
)


@dataclass(frozen=True)
class FeatureSaturation:
    """
    Saturation metrics for a single phonetic feature.

    Attributes:
        feature_name: Name of the feature
        true_count: Number of syllables with feature = True
        false_count: Number of syllables with feature = False
        true_percentage: Percentage of corpus with feature = True
    """

    feature_name: str
    true_count: int
    false_count: int
    true_percentage: float


@dataclass(frozen=True)
class FeatureSaturationMetrics:
    """
    Feature saturation metrics for all 12 phonetic features.

    Attributes:
        total_syllables: Total syllables analyzed
        features: Tuple of FeatureSaturation for each feature (in canonical order)
        by_name: Dict mapping feature name to FeatureSaturation (for lookup)
    """

    total_syllables: int
    features: tuple[FeatureSaturation, ...] = field(default_factory=tuple)
    by_name: dict[str, FeatureSaturation] = field(default_factory=dict)


def compute_feature_saturation_metrics(
    annotated_data: Sequence[dict],
) -> FeatureSaturationMetrics:
    """
    Compute feature saturation metrics from annotated syllable data.

    Args:
        annotated_data: List of dicts with 'syllable', 'frequency', 'features' keys

    Returns:
        FeatureSaturationMetrics with per-feature saturation counts

    Raises:
        ValueError: If annotated_data is empty or malformed
    """
    if not annotated_data:
        raise ValueError("Cannot compute metrics for empty annotated data")

    # Validate first entry has expected structure
    first = annotated_data[0]
    if "features" not in first:
        raise ValueError("Annotated data entries must have 'features' key")

    total = len(annotated_data)

    # Count True values for each feature
    feature_counts: dict[str, int] = {name: 0 for name in FEATURE_NAMES}

    for entry in annotated_data:
        features = entry.get("features", {})
        for name in FEATURE_NAMES:
            if features.get(name, False):
                feature_counts[name] += 1

    # Build FeatureSaturation objects
    saturations: list[FeatureSaturation] = []
    by_name: dict[str, FeatureSaturation] = {}

    for name in FEATURE_NAMES:
        true_count = feature_counts[name]
        false_count = total - true_count
        true_pct = (true_count / total) * 100.0 if total > 0 else 0.0

        sat = FeatureSaturation(
            feature_name=name,
            true_count=true_count,
            false_count=false_count,
            true_percentage=true_pct,
        )
        saturations.append(sat)
        by_name[name] = sat

    return FeatureSaturationMetrics(
        total_syllables=total,
        features=tuple(saturations),
        by_name=by_name,
    )


# =============================================================================
# Composite Corpus Shape Metrics
# =============================================================================


@dataclass(frozen=True)
class CorpusShapeMetrics:
    """
    Complete corpus shape metrics combining all categories.

    This is the primary interface for corpus analysis. Contains all raw
    metrics needed to understand corpus structure.

    Attributes:
        inventory: Inventory metrics (counts, lengths)
        frequency: Frequency distribution metrics
        feature_saturation: Per-feature saturation metrics
    """

    inventory: InventoryMetrics
    frequency: FrequencyMetrics
    feature_saturation: FeatureSaturationMetrics


def compute_corpus_shape_metrics(
    syllables: Sequence[str],
    frequencies: dict[str, int],
    annotated_data: Sequence[dict],
) -> CorpusShapeMetrics:
    """
    Compute complete corpus shape metrics.

    This is the main entry point for corpus analysis. Computes all metric
    categories and returns a composite result.

    Args:
        syllables: List of unique syllables
        frequencies: Dictionary mapping syllable to frequency count
        annotated_data: List of annotated syllable dicts

    Returns:
        CorpusShapeMetrics containing all computed metrics

    Raises:
        ValueError: If any input is empty or malformed

    Example:
        >>> metrics = compute_corpus_shape_metrics(syllables, frequencies, annotated_data)
        >>> print(f"Corpus has {metrics.inventory.total_count} syllables")
        >>> print(f"Hapax legomena: {metrics.frequency.hapax_count}")
        >>> vowel_pct = metrics.feature_saturation.by_name['starts_with_vowel'].true_percentage
        >>> print(f"Starts with vowel: {vowel_pct:.1f}%")
    """
    return CorpusShapeMetrics(
        inventory=compute_inventory_metrics(syllables),
        frequency=compute_frequency_metrics(frequencies),
        feature_saturation=compute_feature_saturation_metrics(annotated_data),
    )
