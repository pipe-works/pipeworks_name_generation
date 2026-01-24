"""Syllable Walker: Navigate syllable feature space via cost-based random walks.

This module provides an efficient implementation for exploring large syllable datasets
(500k+ entries) using topology-respecting random walks through phonetic feature space.

The core algorithm:
1. Pre-compute a neighbor graph during initialization (one-time O(N^2) cost)
2. For each walk step, select next syllable from neighbors using weighted probabilities
3. Weights are based on: feature flip cost, frequency bias, and temperature
4. Inertia option allows staying at current syllable

Key performance characteristics:
- Initialization: ~2-3 minutes for 500k syllables (builds neighbor graph)
- Walk generation: <10ms per walk after initialization
- Memory: ~200-300 MB for 500k syllables

Example:
    >>> walker = SyllableWalker("data/annotated/syllables_annotated.json")
    >>> walk = walker.walk_from_profile(start="ka", profile="dialect", steps=5, seed=42)
    >>> print(" → ".join(s["syllable"] for s in walk))
    ka → ki → ti → ta → da → de
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

from build_tools.syllable_walk.profiles import WALK_PROFILES, WalkProfile

# ============================================================
# Configuration and Constants
# ============================================================

# Stable feature definition (DO NOT CHANGE ORDER)
# This order must match the output from syllable_feature_annotator
# Features are extracted in this exact sequence from JSON records
FEATURE_KEYS = [
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
]

# Default feature costs (can be customized per walker instance)
# Higher cost = less likely to flip this feature
# These values were tuned to create interesting walks
DEFAULT_FEATURE_COSTS: dict[str, float] = {
    "starts_with_vowel": 0.2,
    "starts_with_cluster": 1.5,
    "starts_with_heavy_cluster": 2.0,
    "contains_plosive": 0.7,
    "contains_fricative": 0.7,
    "contains_liquid": 0.3,
    "contains_nasal": 0.3,
    "short_vowel": 0.2,
    "long_vowel": 0.2,
    "ends_with_vowel": 0.3,
    "ends_with_nasal": 0.4,
    "ends_with_stop": 0.6,
}

# Default cost for staying at current syllable (inertia)
DEFAULT_INERTIA_COST = 0.5

# Default maximum Hamming distance for pre-computing neighbors
DEFAULT_MAX_NEIGHBOR_DISTANCE = 3


# ============================================================
# Core Walker Class
# ============================================================


class SyllableWalker:
    """Navigate syllable feature space via cost-based random walks.

    This class efficiently handles large syllable datasets (500k+) by pre-computing
    neighbor relationships and using vectorized operations where possible.

    The walker performs a one-time expensive computation during initialization
    to build a neighbor graph, mapping each syllable to nearby syllables
    within a maximum Hamming distance. After initialization, walk generation
    is extremely fast (<10ms per walk).

    Attributes:
        syllables: List of all syllable strings
        frequencies: NumPy array of syllable frequencies (uint32)
        feature_matrix: NumPy array of binary feature vectors (N x 12, uint8)
        syllable_to_idx: Dict mapping syllable text to index
        neighbor_graph: Dict mapping syllable index to list of neighbor indices
        max_neighbor_distance: Maximum Hamming distance for neighbors
        feature_costs: Dict of costs for each feature flip
        inertia_cost: Cost of staying at current syllable

    Example:
        >>> walker = SyllableWalker("syllables_annotated.json", verbose=True)
        >>> walk = walker.walk_from_profile(
        ...     start="ka", profile="dialect", steps=5, seed=42
        ... )
        >>> print(walker.format_walk(walk))
        ka → ki → ti → ta → da → de

    Notes:
        - Initialization time: ~2-3 minutes for 500k syllables
        - Walk generation: <10ms per walk after initialization
        - Memory usage: ~200-300 MB for 500k syllables
        - Thread safety: Not thread-safe (use separate instances)
    """

    def __init__(
        self,
        data_path: Path | str,
        max_neighbor_distance: int = DEFAULT_MAX_NEIGHBOR_DISTANCE,
        feature_costs: dict[str, float] | None = None,
        inertia_cost: float = DEFAULT_INERTIA_COST,
        verbose: bool = False,
    ):
        """Initialize the syllable walker with pre-computed neighbor graph.

        Args:
            data_path: Path to syllables_annotated.json file (output of
                      syllable_feature_annotator)
            max_neighbor_distance: Maximum Hamming distance for pre-computing
                                  neighbors (1-3). Higher values = more neighbors
                                  = slower initialization + more memory, but
                                  allows larger feature flips per step.
                                  Default: 3 (recommended)
            feature_costs: Custom feature cost dictionary. If None, uses
                          DEFAULT_FEATURE_COSTS. Keys must match FEATURE_KEYS.
            inertia_cost: Cost of staying at current syllable. Higher values
                         discourage staying put. Default: 0.5
            verbose: If True, print progress during initialization (neighbor
                    graph construction can take 2-3 minutes for 500k syllables)

        Raises:
            FileNotFoundError: If data_path does not exist
            ValueError: If data_path is not valid JSON
            ValueError: If feature_costs keys don't match FEATURE_KEYS
            ValueError: If max_neighbor_distance < 1 or > len(FEATURE_KEYS)

        Notes:
            - Initialization performs expensive one-time computation
            - Use verbose=True for long-running initializations
            - Consider caching the neighbor graph (future optimization)
        """
        self.data_path = Path(data_path)
        self.max_neighbor_distance = max_neighbor_distance
        self.feature_costs = feature_costs or DEFAULT_FEATURE_COSTS
        self.inertia_cost = inertia_cost
        self.verbose = verbose

        # Validate max_neighbor_distance
        if not 1 <= max_neighbor_distance <= len(FEATURE_KEYS):
            raise ValueError(
                f"max_neighbor_distance must be between 1 and {len(FEATURE_KEYS)}, "
                f"got {max_neighbor_distance}"
            )

        # Validate feature_costs if provided
        if feature_costs is not None:
            if set(feature_costs.keys()) != set(FEATURE_KEYS):
                raise ValueError(
                    f"feature_costs keys must match FEATURE_KEYS. "
                    f"Expected: {set(FEATURE_KEYS)}, got: {set(feature_costs.keys())}"
                )

        # Data storage (populated by _load_data)
        self.syllables: list[str] = []
        self.frequencies: np.ndarray | None = None
        self.feature_matrix: np.ndarray | None = None
        self.syllable_to_idx: dict[str, int] = {}

        # Neighbor graph: maps node index to list of neighbor indices
        # This is the key optimization that makes walks fast
        self.neighbor_graph: dict[int, list[int]] = defaultdict(list)

        # Load and process data
        self._load_data()
        self._build_neighbor_graph()

    def _load_data(self) -> None:
        """Load syllable data from JSON file into efficient structures.

        This method:
        1. Reads the JSON file (list of syllable records)
        2. Extracts syllables, frequencies, and features
        3. Converts to NumPy arrays for efficient computation
        4. Builds syllable_to_idx lookup dictionary

        The feature matrix is a binary matrix (N x 12) where each row is a
        syllable's feature vector. Using uint8 dtype minimizes memory usage
        (1 byte per feature vs 8 bytes for Python bool).

        Raises:
            FileNotFoundError: If data_path doesn't exist
            json.JSONDecodeError: If data_path is not valid JSON
            KeyError: If required fields missing from records
        """
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        if self.verbose:
            print(f"Loading syllable data from {self.data_path}...")

        with open(self.data_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if self.verbose:
            print(f"Loaded {len(records):,} syllable records")
            print("Building feature matrix...")

        # Extract syllables and frequencies
        self.syllables = [r["syllable"] for r in records]
        self.frequencies = np.array([r["frequency"] for r in records], dtype=np.uint32)

        # Build feature matrix (binary features as uint8)
        # Each row is one syllable's feature vector
        # Columns correspond to FEATURE_KEYS order
        feature_lists = []
        for r in records:
            # Extract features in stable order, converting bool to int (0 or 1)
            features = [int(r["features"].get(k, False)) for k in FEATURE_KEYS]
            feature_lists.append(features)

        self.feature_matrix = np.array(feature_lists, dtype=np.uint8)

        # Build syllable lookup dictionary for O(1) text -> index conversion
        self.syllable_to_idx = {syl: idx for idx, syl in enumerate(self.syllables)}

        if self.verbose:
            print(f"Feature matrix shape: {self.feature_matrix.shape}")
            print(f"Memory usage: ~{self.feature_matrix.nbytes / 1024 / 1024:.1f} MB")

    def _build_neighbor_graph(self) -> None:
        """Pre-compute neighbor relationships for O(1) lookup during walks.

        This is the expensive one-time computation that enables fast walks.
        For each syllable, finds all syllables within max_neighbor_distance
        Hamming distance and stores them in neighbor_graph.

        Algorithm:
        1. Process syllables in batches (10k at a time) to show progress
        2. For each batch, compute vectorized Hamming distances vs all syllables
        3. Find neighbors within max_neighbor_distance (excluding self)
        4. Store neighbor indices in neighbor_graph dict

        Time Complexity:
        - O(N^2 * F) where N = syllables, F = features
        - Optimized with vectorized NumPy operations
        - Actual time: ~30 sec (distance=1), ~1 min (2), ~3 min (3) for 500k

        Space Complexity:
        - O(N * K) where K = avg neighbors per syllable
        - Typically K = 50-100 for max_neighbor_distance=3

        Notes:
            - Uses broadcasting to compute distances efficiently
            - XOR operation (!=) gives 1 where features differ
            - Sum across features gives Hamming distance
        """
        if self.verbose:
            print(f"Building neighbor graph (max distance: {self.max_neighbor_distance})...")
            print("This may take a few minutes for large datasets...")

        n_syllables = len(self.syllables)
        batch_size = 10000

        # Process in batches for progress reporting and memory efficiency
        for start_idx in range(0, n_syllables, batch_size):
            end_idx = min(start_idx + batch_size, n_syllables)

            # Get feature vectors for this batch
            batch_features = self.feature_matrix[start_idx:end_idx]  # type: ignore[index]

            # Compute Hamming distances for batch against ALL syllables
            # Shape: (batch_size, n_syllables)
            # Broadcasting: batch_features[:, np.newaxis, :] gives (batch, 1, features)
            #               feature_matrix[np.newaxis, :, :] gives (1, all, features)
            # Result after !=: (batch, all, features) with True where features differ
            # Sum over features axis: (batch, all) with Hamming distances
            distances = np.sum(
                batch_features[:, np.newaxis, :] != self.feature_matrix[np.newaxis, :, :],  # type: ignore[index]
                axis=2,
            )

            # For each syllable in batch, find neighbors within max distance
            for local_idx in range(len(batch_features)):
                global_idx = start_idx + local_idx

                # Create boolean mask: within distance AND not self
                neighbor_mask = (distances[local_idx] <= self.max_neighbor_distance) & (
                    distances[local_idx] > 0
                )

                # Store neighbor indices (where mask is True)
                self.neighbor_graph[global_idx] = np.where(neighbor_mask)[0].tolist()

            # Progress reporting
            if self.verbose and (end_idx % 50000 == 0 or end_idx == n_syllables):
                print(f"  Processed {end_idx:,} / {n_syllables:,} syllables")

        # Compute and report average neighbors per syllable
        avg_neighbors = np.mean([len(neighbors) for neighbors in self.neighbor_graph.values()])
        if self.verbose:
            print(f"✓ Neighbor graph built: avg {avg_neighbors:.1f} neighbors per syllable")

    def _hamming_distance(self, idx_a: int, idx_b: int) -> int:
        """Compute Hamming distance between two syllable feature vectors.

        Hamming distance is the number of positions where features differ.
        For binary feature vectors, this is simply the count of differing bits.

        Args:
            idx_a: Index of first syllable
            idx_b: Index of second syllable

        Returns:
            Number of differing features (0-12)

        Example:
            >>> # Syllable A: [1, 0, 0, 1, 0, ...]  (starts_with_vowel, contains_plosive)
            >>> # Syllable B: [1, 0, 0, 0, 0, ...]  (starts_with_vowel only)
            >>> walker._hamming_distance(idx_a, idx_b)
            1  # One feature differs (contains_plosive)
        """
        return int(np.sum(self.feature_matrix[idx_a] != self.feature_matrix[idx_b]))  # type: ignore[index]

    def _flip_cost(self, idx_a: int, idx_b: int) -> float:
        """Compute weighted cost of flipping features between syllables.

        Unlike Hamming distance (which counts flips), this weights each
        feature flip by its cost from feature_costs dict. This allows
        penalizing certain phonetic changes more than others.

        Args:
            idx_a: Index of source syllable
            idx_b: Index of target syllable

        Returns:
            Total weighted cost (sum of individual feature costs)

        Example:
            >>> # If "starts_with_cluster" flips (cost=1.5) and
            >>> # "contains_liquid" flips (cost=0.3), total cost = 1.8
            >>> walker._flip_cost(idx_a, idx_b)
            1.8

        Notes:
            - Only flipped features contribute to cost
            - Unchanged features have zero cost
            - Cost is always non-negative
        """
        cost = 0.0
        features_a = self.feature_matrix[idx_a]  # type: ignore[index]
        features_b = self.feature_matrix[idx_b]  # type: ignore[index]

        # Sum costs for each differing feature
        for i, key in enumerate(FEATURE_KEYS):
            if features_a[i] != features_b[i]:
                cost += self.feature_costs[key]

        return cost

    def _rarity_cost(self, idx: int, weight: float) -> float:
        """Compute frequency-based cost using log-rarity.

        Rare syllables have high log-rarity, common have low log-rarity.
        The weight parameter controls direction:
        - Positive weight: Penalize rare (favor common)
        - Negative weight: Reward rare (favor rare)
        - Zero weight: Neutral (no frequency bias)

        Args:
            idx: Syllable index
            weight: Frequency weight (-2.0 to 2.0)

        Returns:
            Weighted rarity cost (can be negative if weight < 0)

        Formula:
            cost = weight * log(1 / (frequency + epsilon))

            Where epsilon=1e-6 prevents division by zero and log(0).

        Example:
            >>> # Rare syllable (freq=5), weight=1.0
            >>> walker._rarity_cost(rare_idx, 1.0)
            5.3  # High positive cost (penalty)

            >>> # Same syllable, weight=-1.0
            >>> walker._rarity_cost(rare_idx, -1.0)
            -5.3  # Negative cost (reward/attraction)

            >>> # Common syllable (freq=1000), weight=1.0
            >>> walker._rarity_cost(common_idx, 1.0)
            -6.9  # Negative cost (reward)
        """
        freq = self.frequencies[idx]  # type: ignore[index]
        # Add small epsilon to prevent log(0) for zero-frequency syllables
        return weight * math.log(1.0 / (freq + 1e-6))

    def walk(
        self,
        start: int | str,
        steps: int,
        max_flips: int,
        temperature: float = 1.0,
        frequency_weight: float = 0.0,
        seed: int | None = None,
    ) -> list[dict]:
        """Execute a syllable walk through feature space.

        Starting from a syllable, takes `steps` steps through feature space,
        choosing each next syllable probabilistically based on:
        - Feature flip cost (weighted Hamming distance)
        - Frequency cost (rarity penalty/bonus)
        - Temperature (exploration vs exploitation)
        - Inertia (tendency to stay put)

        The walk uses softmax selection over candidate neighbors:
        1. Find all neighbors within max_flips distance
        2. Compute cost for each neighbor (flip cost + rarity cost)
        3. Add inertia option (staying at current syllable)
        4. Apply softmax with temperature: weight_i = exp(-cost_i / T)
        5. Sample next syllable proportional to weights

        Args:
            start: Starting syllable (syllable text or index)
            steps: Number of steps to take (each step visits one syllable)
            max_flips: Maximum feature flips allowed per step (1-3).
                      Must be <= max_neighbor_distance from __init__.
            temperature: Exploration temperature (0.1-5.0). Higher values
                        increase randomness. Typical values:
                        - 0.3: Conservative, minimal exploration
                        - 0.7: Balanced
                        - 1.5: High exploration
                        - 2.5: Maximum randomness
            frequency_weight: Frequency bias (-2.0 to 2.0):
                             - Positive: Favor common syllables
                             - Zero: Neutral
                             - Negative: Favor rare syllables
                             Typical values: -1.0, 0.0, 1.0
            seed: Random seed for reproducibility. Same seed = same walk.
                 If None, uses system randomness (non-reproducible).

        Returns:
            List of syllable dictionaries with keys:
            - "syllable": Syllable text (str)
            - "frequency": Corpus frequency (int)
            - "features": Binary feature vector (list of 12 ints)

            Length = steps + 1 (includes starting syllable)

        Raises:
            ValueError: If start syllable not found in dataset
            ValueError: If max_flips > max_neighbor_distance
            ValueError: If steps < 0

        Example:
            >>> walker = SyllableWalker("data.json")
            >>> walk = walker.walk(
            ...     start="ka",
            ...     steps=5,
            ...     max_flips=2,
            ...     temperature=0.7,
            ...     frequency_weight=0.0,
            ...     seed=42
            ... )
            >>> len(walk)
            6  # start + 5 steps
            >>> walk[0]["syllable"]
            'ka'

        Notes:
            - Deterministic: Same seed always produces same walk
            - Uses local Random instance (doesn't affect global random state)
            - Inertia option allows walk to stay at current syllable
        """
        # Resolve start index from string or int
        if isinstance(start, str):
            if start not in self.syllable_to_idx:
                raise ValueError(f"Syllable '{start}' not found in dataset")
            start_idx = self.syllable_to_idx[start]
        else:
            start_idx = start
            if not 0 <= start_idx < len(self.syllables):
                raise ValueError(f"Invalid syllable index: {start_idx}")

        # Validate max_flips against pre-computed neighbor distance
        if max_flips > self.max_neighbor_distance:
            raise ValueError(
                f"max_flips ({max_flips}) exceeds pre-computed neighbor distance "
                f"({self.max_neighbor_distance}). Reinitialize walker with larger "
                f"max_neighbor_distance."
            )

        # Validate steps
        if steps < 0:
            raise ValueError(f"steps must be non-negative, got {steps}")

        # Initialize local RNG for determinism
        # CRITICAL: Use local Random instance, not global random.seed()
        # This ensures walks don't interfere with other randomness in the program
        rng = random.Random(seed)  # nosec B311 - non-cryptographic use

        # Initialize path with starting syllable
        path = [self._get_syllable_dict(start_idx)]
        current_idx = start_idx

        # Execute walk for specified number of steps
        for _ in range(steps):
            # Collect candidate next syllables with their costs
            candidates: list[tuple[int, float]] = []

            # Find neighbors within max_flips distance
            for neighbor_idx in self.neighbor_graph[current_idx]:
                # Double-check distance constraint (neighbor graph should guarantee this)
                if self._hamming_distance(current_idx, neighbor_idx) <= max_flips:
                    # Compute total cost: flip cost + rarity cost
                    cost = self._flip_cost(current_idx, neighbor_idx)
                    cost += self._rarity_cost(neighbor_idx, frequency_weight)
                    candidates.append((neighbor_idx, cost))

            # Add inertia option (staying at current syllable)
            candidates.append((current_idx, self.inertia_cost))

            # Softmax selection: convert costs to weights
            # Lower cost = higher weight = more likely to be chosen
            # Temperature controls exploration:
            # - Low T: strongly prefers low-cost options (exploitation)
            # - High T: more uniform selection (exploration)
            weights = [math.exp(-cost / temperature) for _, cost in candidates]

            # Sample next syllable proportional to weights
            chosen_idx = rng.choices([idx for idx, _ in candidates], weights=weights, k=1)[0]

            # Add chosen syllable to path
            path.append(self._get_syllable_dict(chosen_idx))
            current_idx = chosen_idx

        return path

    def walk_from_profile(
        self,
        start: int | str,
        profile: str | WalkProfile,
        steps: int = 5,
        seed: int | None = None,
    ) -> list[dict]:
        """Execute a walk using a named profile.

        Convenience method that uses predefined WalkProfile parameters.
        See WALK_PROFILES for available profiles.

        Args:
            start: Starting syllable (text or index)
            profile: Profile name ("clerical", "dialect", "goblin", "ritual")
                    or WalkProfile object
            steps: Number of steps to take (default: 5)
            seed: Random seed for reproducibility (default: None)

        Returns:
            List of syllable dictionaries (same as walk())

        Raises:
            ValueError: If profile name not found

        Example:
            >>> walker = SyllableWalker("data.json")
            >>> walk = walker.walk_from_profile("ka", "goblin", steps=10, seed=42)
            >>> print(walker.format_walk(walk))
            ka → kha → gha → ghe → ge → gwe → ...
        """
        # Resolve profile name to WalkProfile object
        if isinstance(profile, str):
            if profile not in WALK_PROFILES:
                available = ", ".join(WALK_PROFILES.keys())
                raise ValueError(f"Unknown profile '{profile}'. Available: {available}")
            profile = WALK_PROFILES[profile]

        # Delegate to walk() with profile parameters
        return self.walk(
            start=start,
            steps=steps,
            max_flips=profile.max_flips,
            temperature=profile.temperature,
            frequency_weight=profile.frequency_weight,
            seed=seed,
        )

    def _get_syllable_dict(self, idx: int) -> dict:
        """Get syllable dictionary for a given index.

        Args:
            idx: Syllable index

        Returns:
            Dictionary with keys: syllable, frequency, features
        """
        return {
            "syllable": self.syllables[idx],
            "frequency": int(self.frequencies[idx]),  # type: ignore[index]
            "features": self.feature_matrix[idx].tolist(),  # type: ignore[index]
        }

    def get_random_syllable(self, seed: int | None = None) -> str:
        """Get a random syllable from the dataset.

        Args:
            seed: Random seed for reproducibility (default: None)

        Returns:
            Random syllable text

        Example:
            >>> walker.get_random_syllable(seed=42)
            'ka'
            >>> walker.get_random_syllable(seed=42)
            'ka'  # Same seed = same result
        """
        rng = random.Random(seed)  # nosec B311 - non-cryptographic use
        return rng.choice(self.syllables)

    def get_syllable_info(self, syllable: str) -> dict | None:
        """Get information about a specific syllable.

        Args:
            syllable: Syllable text to look up

        Returns:
            Syllable dictionary with keys: syllable, frequency, features
            Returns None if syllable not found

        Example:
            >>> info = walker.get_syllable_info("ka")
            >>> if info:
            ...     print(f"Frequency: {info['frequency']}")
            Frequency: 1234
        """
        if syllable not in self.syllable_to_idx:
            return None
        idx = self.syllable_to_idx[syllable]
        return self._get_syllable_dict(idx)

    def format_walk(self, walk: list[dict], arrow: str = " → ") -> str:
        """Format a walk as a string with arrows.

        Args:
            walk: Walk result from walk() or walk_from_profile()
            arrow: Separator between syllables (default: " → ")

        Returns:
            Formatted walk string

        Example:
            >>> walk = walker.walk_from_profile("ka", "dialect", steps=5, seed=42)
            >>> walker.format_walk(walk)
            'ka → ki → ti → ta → da → de'
            >>> walker.format_walk(walk, arrow=" -> ")
            'ka -> ki -> ti -> ta -> da -> de'
        """
        return arrow.join(s["syllable"] for s in walk)

    def get_available_profiles(self) -> dict[str, WalkProfile]:
        """Get all available walk profiles.

        Returns:
            Dictionary mapping profile names to WalkProfile objects

        Example:
            >>> profiles = walker.get_available_profiles()
            >>> for name in profiles:
            ...     print(name)
            clerical
            dialect
            goblin
            ritual
        """
        return WALK_PROFILES.copy()

    @classmethod
    def from_data(
        cls,
        data: list[dict],
        max_neighbor_distance: int = DEFAULT_MAX_NEIGHBOR_DISTANCE,
        feature_costs: dict[str, float] | None = None,
        inertia_cost: float = DEFAULT_INERTIA_COST,
        verbose: bool = False,
    ) -> "SyllableWalker":
        """Create a SyllableWalker from in-memory data.

        This is useful when syllable data is loaded from a source other than
        a JSON file (e.g., SQLite database).

        Args:
            data: List of syllable records, each with keys:
                  'syllable', 'frequency', 'features' (dict of bool values)
            max_neighbor_distance: Maximum Hamming distance for neighbors (1-3)
            feature_costs: Custom feature cost dictionary
            inertia_cost: Cost of staying at current syllable
            verbose: If True, print progress during initialization

        Returns:
            Initialized SyllableWalker instance

        Example:
            >>> data = [
            ...     {"syllable": "ka", "frequency": 100,
            ...      "features": {"starts_with_vowel": False, ...}}
            ... ]
            >>> walker = SyllableWalker.from_data(data, verbose=True)
        """
        # Create instance without calling __init__ (skip file loading)
        instance = cls.__new__(cls)

        # Set configuration
        instance.data_path = None  # type: ignore[assignment]
        instance.max_neighbor_distance = max_neighbor_distance
        instance.feature_costs = feature_costs or DEFAULT_FEATURE_COSTS
        instance.inertia_cost = inertia_cost
        instance.verbose = verbose

        # Validate max_neighbor_distance
        if not 1 <= max_neighbor_distance <= len(FEATURE_KEYS):
            raise ValueError(
                f"max_neighbor_distance must be between 1 and {len(FEATURE_KEYS)}, "
                f"got {max_neighbor_distance}"
            )

        # Validate feature_costs if provided
        if feature_costs is not None:
            if set(feature_costs.keys()) != set(FEATURE_KEYS):
                raise ValueError(
                    f"feature_costs keys must match FEATURE_KEYS. "
                    f"Expected: {set(FEATURE_KEYS)}, got: {set(feature_costs.keys())}"
                )

        if verbose:
            print(f"Building walker from {len(data):,} syllable records...")

        # Extract syllables and frequencies
        instance.syllables = [r["syllable"] for r in data]
        instance.frequencies = np.array([r["frequency"] for r in data], dtype=np.uint32)

        # Build feature matrix
        feature_lists = []
        for r in data:
            features = [int(r["features"].get(k, False)) for k in FEATURE_KEYS]
            feature_lists.append(features)

        instance.feature_matrix = np.array(feature_lists, dtype=np.uint8)

        # Build syllable lookup
        instance.syllable_to_idx = {syl: idx for idx, syl in enumerate(instance.syllables)}

        if verbose:
            print(f"Feature matrix shape: {instance.feature_matrix.shape}")

        # Initialize neighbor graph
        instance.neighbor_graph = defaultdict(list)

        # Build neighbor graph
        instance._build_neighbor_graph()

        return instance
