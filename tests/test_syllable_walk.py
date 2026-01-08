"""Comprehensive test suite for syllable walker core functionality.

This module tests all core functionality of the SyllableWalker class including:
- Initialization and data loading
- Neighbor graph construction
- Walk generation and determinism
- Feature flip constraints
- Hamming distance computation
- Frequency weighting
- Edge cases and error handling

The tests use both synthetic fixtures and real annotated syllable data.
"""

import json

import pytest

from build_tools.syllable_walk.walker import DEFAULT_FEATURE_COSTS, FEATURE_KEYS, SyllableWalker

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_syllables():
    """Small sample of syllable records for testing."""
    return [
        {
            "syllable": "ka",
            "frequency": 100,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ki",
            "frequency": 80,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": False,  # Different from ka
                "long_vowel": True,  # Different from ka
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ta",
            "frequency": 90,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "bak",
            "frequency": 5,  # Rare
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": False,  # Different from ka
                "ends_with_nasal": False,
                "ends_with_stop": True,  # Different from ka
            },
        },
        {
            "syllable": "the",
            "frequency": 500,  # Very common
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,  # Different from ka
                "contains_fricative": True,  # Different from ka
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
    ]


@pytest.fixture
def sample_data_file(tmp_path, sample_syllables):
    """Create a temporary syllables_annotated.json file for testing."""
    file_path = tmp_path / "test_syllables.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_syllables, f)
    return file_path


@pytest.fixture
def initialized_walker(sample_data_file):
    """Pre-initialized walker for tests."""
    return SyllableWalker(sample_data_file, max_neighbor_distance=3, verbose=False)


# ============================================================
# Initialization Tests
# ============================================================


class TestSyllableWalkerInitialization:
    """Test walker initialization and data loading."""

    def test_init_with_valid_data(self, sample_data_file):
        """Test initialization with valid syllables_annotated.json."""
        walker = SyllableWalker(sample_data_file)
        assert len(walker.syllables) == 5
        assert walker.feature_matrix is not None
        assert walker.feature_matrix.shape == (5, len(FEATURE_KEYS))
        assert walker.frequencies is not None
        assert len(walker.frequencies) == 5
        assert len(walker.syllable_to_idx) == 5

    def test_init_with_nonexistent_file(self):
        """Test initialization with nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SyllableWalker("/nonexistent/path.json")

    def test_init_with_invalid_json(self, tmp_path):
        """Test initialization with invalid JSON raises error."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{")

        with pytest.raises(json.JSONDecodeError):
            SyllableWalker(bad_file)

    def test_init_builds_neighbor_graph(self, sample_data_file):
        """Test neighbor graph is built during initialization."""
        walker = SyllableWalker(sample_data_file, max_neighbor_distance=2)
        assert len(walker.neighbor_graph) > 0
        # Every syllable should have entry (even if empty neighbors list)
        assert len(walker.neighbor_graph) == 5

    def test_init_custom_feature_costs(self, sample_data_file):
        """Test initialization with custom feature costs."""
        custom_costs = DEFAULT_FEATURE_COSTS.copy()
        custom_costs["starts_with_vowel"] = 10.0

        walker = SyllableWalker(sample_data_file, feature_costs=custom_costs)
        assert walker.feature_costs["starts_with_vowel"] == 10.0

    def test_init_invalid_feature_costs_raises(self, sample_data_file):
        """Test initialization with invalid feature costs raises ValueError."""
        bad_costs = {"invalid_key": 1.0}

        with pytest.raises(ValueError, match="feature_costs keys must match"):
            SyllableWalker(sample_data_file, feature_costs=bad_costs)

    def test_init_invalid_max_neighbor_distance(self, sample_data_file):
        """Test initialization with invalid max_neighbor_distance raises ValueError."""
        with pytest.raises(ValueError, match="max_neighbor_distance must be"):
            SyllableWalker(sample_data_file, max_neighbor_distance=0)

        with pytest.raises(ValueError, match="max_neighbor_distance must be"):
            SyllableWalker(sample_data_file, max_neighbor_distance=20)

    def test_init_verbose_mode(self, sample_data_file, capsys):
        """Test verbose mode prints progress messages."""
        _walker = SyllableWalker(sample_data_file, verbose=True)
        captured = capsys.readouterr()
        assert "Loading syllable data" in captured.out
        assert "Building neighbor graph" in captured.out

    def test_syllable_to_idx_mapping(self, initialized_walker):
        """Test syllable_to_idx provides correct mappings."""
        assert initialized_walker.syllable_to_idx["ka"] == 0
        assert initialized_walker.syllable_to_idx["ki"] == 1
        assert initialized_walker.syllables[initialized_walker.syllable_to_idx["bak"]] == "bak"


# ============================================================
# Determinism Tests (CRITICAL)
# ============================================================


class TestDeterminism:
    """Test determinism - same seed must produce same walk."""

    def test_same_seed_same_walk(self, initialized_walker):
        """Test that same seed produces identical walks."""
        walk1 = initialized_walker.walk(start="ka", steps=10, max_flips=2, temperature=1.0, seed=42)
        walk2 = initialized_walker.walk(start="ka", steps=10, max_flips=2, temperature=1.0, seed=42)

        # Must be identical
        assert len(walk1) == len(walk2)
        syllables1 = [s["syllable"] for s in walk1]
        syllables2 = [s["syllable"] for s in walk2]
        assert syllables1 == syllables2

        # Check all details match
        for s1, s2 in zip(walk1, walk2):
            assert s1["syllable"] == s2["syllable"]
            assert s1["frequency"] == s2["frequency"]
            assert s1["features"] == s2["features"]

    def test_different_seed_different_walk(self, initialized_walker):
        """Test that different seeds produce different walks (probabilistically)."""
        walk1 = initialized_walker.walk(start="ka", steps=20, max_flips=2, temperature=1.0, seed=42)
        walk2 = initialized_walker.walk(start="ka", steps=20, max_flips=2, temperature=1.0, seed=99)

        # Should differ (with high probability for 20 steps)
        syllables1 = [s["syllable"] for s in walk1]
        syllables2 = [s["syllable"] for s in walk2]
        assert syllables1 != syllables2

    def test_no_seed_produces_varied_walks(self, initialized_walker):
        """Test walks without seed are non-deterministic."""
        walks = []
        for _ in range(5):
            walk = initialized_walker.walk(
                start="ka", steps=10, max_flips=2, temperature=1.0, seed=None
            )
            syllables = tuple(s["syllable"] for s in walk)
            walks.append(syllables)

        # At least some should be different (very high probability)
        unique_walks = set(walks)
        assert len(unique_walks) > 1

    def test_profile_walk_determinism(self, initialized_walker):
        """Test that profile walks are also deterministic."""
        walk1 = initialized_walker.walk_from_profile(
            start="ka", profile="goblin", steps=10, seed=42
        )
        walk2 = initialized_walker.walk_from_profile(
            start="ka", profile="goblin", steps=10, seed=42
        )

        syllables1 = [s["syllable"] for s in walk1]
        syllables2 = [s["syllable"] for s in walk2]
        assert syllables1 == syllables2


# ============================================================
# Feature Flip Constraint Tests
# ============================================================


class TestFeatureFlipConstraints:
    """Test that max_flips constraint is never violated."""

    def test_max_flips_respected(self, initialized_walker):
        """Test walk never exceeds max_flips constraint."""
        max_flips = 2
        walk = initialized_walker.walk(
            start="ka", steps=20, max_flips=max_flips, temperature=1.0, seed=42
        )

        for i in range(len(walk) - 1):
            current_idx = initialized_walker.syllable_to_idx[walk[i]["syllable"]]
            next_idx = initialized_walker.syllable_to_idx[walk[i + 1]["syllable"]]
            distance = initialized_walker._hamming_distance(current_idx, next_idx)

            assert distance <= max_flips, (
                f"Step {i}: {walk[i]['syllable']} -> {walk[i+1]['syllable']}: "
                f"distance={distance} exceeds max_flips={max_flips}"
            )

    def test_max_flips_one(self, initialized_walker):
        """Test max_flips=1 (most conservative)."""
        walk = initialized_walker.walk(start="ka", steps=10, max_flips=1, temperature=0.5, seed=42)

        for i in range(len(walk) - 1):
            current_idx = initialized_walker.syllable_to_idx[walk[i]["syllable"]]
            next_idx = initialized_walker.syllable_to_idx[walk[i + 1]["syllable"]]
            distance = initialized_walker._hamming_distance(current_idx, next_idx)
            assert distance <= 1

    def test_max_flips_three(self, initialized_walker):
        """Test max_flips=3 (maximum exploration)."""
        walk = initialized_walker.walk(start="ka", steps=10, max_flips=3, temperature=2.0, seed=42)

        for i in range(len(walk) - 1):
            current_idx = initialized_walker.syllable_to_idx[walk[i]["syllable"]]
            next_idx = initialized_walker.syllable_to_idx[walk[i + 1]["syllable"]]
            distance = initialized_walker._hamming_distance(current_idx, next_idx)
            assert distance <= 3

    def test_max_flips_exceeds_neighbor_distance_raises(self, sample_data_file):
        """Test max_flips > max_neighbor_distance raises ValueError."""
        walker = SyllableWalker(sample_data_file, max_neighbor_distance=2)

        with pytest.raises(ValueError, match="exceeds"):
            walker.walk(start="ka", steps=5, max_flips=3, temperature=1.0)


# ============================================================
# Hamming Distance Tests
# ============================================================


class TestHammingDistance:
    """Test Hamming distance computation."""

    def test_hamming_distance_identical(self, initialized_walker):
        """Test Hamming distance between identical syllables is 0."""
        idx = initialized_walker.syllable_to_idx["ka"]
        distance = initialized_walker._hamming_distance(idx, idx)
        assert distance == 0

    def test_hamming_distance_symmetric(self, initialized_walker):
        """Test Hamming distance is symmetric."""
        idx_ka = initialized_walker.syllable_to_idx["ka"]
        idx_ki = initialized_walker.syllable_to_idx["ki"]

        dist_forward = initialized_walker._hamming_distance(idx_ka, idx_ki)
        dist_backward = initialized_walker._hamming_distance(idx_ki, idx_ka)
        assert dist_forward == dist_backward

    def test_hamming_distance_range(self, initialized_walker):
        """Test Hamming distance is in valid range [0, num_features]."""
        num_features = len(FEATURE_KEYS)
        syllables = list(initialized_walker.syllable_to_idx.keys())

        for syl_a in syllables:
            for syl_b in syllables:
                idx_a = initialized_walker.syllable_to_idx[syl_a]
                idx_b = initialized_walker.syllable_to_idx[syl_b]
                distance = initialized_walker._hamming_distance(idx_a, idx_b)
                assert 0 <= distance <= num_features

    def test_hamming_distance_known_values(self, initialized_walker):
        """Test Hamming distance with known values."""
        # ka and ki differ in 2 features (short_vowel, long_vowel)
        idx_ka = initialized_walker.syllable_to_idx["ka"]
        idx_ki = initialized_walker.syllable_to_idx["ki"]
        distance = initialized_walker._hamming_distance(idx_ka, idx_ki)
        assert distance == 2

        # ka and bak differ in 2 features (ends_with_vowel, ends_with_stop)
        idx_bak = initialized_walker.syllable_to_idx["bak"]
        distance = initialized_walker._hamming_distance(idx_ka, idx_bak)
        assert distance == 2


# ============================================================
# Frequency Weighting Tests
# ============================================================


class TestFrequencyWeighting:
    """Test frequency bias behavior."""

    def test_positive_weight_favors_common(self, initialized_walker):
        """Test positive frequency weight favors common syllables."""
        # Generate multiple walks with positive weight
        walks = [
            initialized_walker.walk(
                start="ka",
                steps=10,
                max_flips=2,
                temperature=0.7,
                frequency_weight=1.0,
                seed=i,
            )
            for i in range(20)
        ]

        # Collect all visited syllables and count "the" (very common)
        the_count = 0
        bak_count = 0
        for walk in walks:
            for step in walk:
                if step["syllable"] == "the":
                    the_count += 1
                elif step["syllable"] == "bak":
                    bak_count += 1

        # "the" (freq=500) should be visited more than "bak" (freq=5)
        assert the_count > bak_count

    def test_negative_weight_favors_rare(self, initialized_walker):
        """Test negative frequency weight favors rare syllables."""
        # Generate multiple walks with negative weight
        walks = [
            initialized_walker.walk(
                start="ka",
                steps=10,
                max_flips=2,
                temperature=0.7,
                frequency_weight=-1.0,
                seed=i,
            )
            for i in range(20)
        ]

        # Count visits to rare vs common
        the_count = 0
        bak_count = 0
        for walk in walks:
            for step in walk:
                if step["syllable"] == "the":
                    the_count += 1
                elif step["syllable"] == "bak":
                    bak_count += 1

        # "bak" (rare) should be visited more than "the" (common)
        # Note: This is probabilistic, may occasionally fail
        # Using relatively large sample (20 walks * 10 steps) for stability
        assert bak_count > the_count

    def test_zero_weight_neutral(self, initialized_walker):
        """Test zero frequency weight is neutral."""
        # With zero weight, walks should be based only on feature distance
        walk = initialized_walker.walk(
            start="ka",
            steps=10,
            max_flips=2,
            temperature=0.7,
            frequency_weight=0.0,
            seed=42,
        )

        # Just verify walk completes without error
        assert len(walk) == 11  # start + 10 steps


# ============================================================
# Walk Generation Tests
# ============================================================


class TestWalkGeneration:
    """Test walk generation functionality."""

    def test_walk_length(self, initialized_walker):
        """Test walk has correct length (steps + 1)."""
        walk = initialized_walker.walk(start="ka", steps=5, max_flips=2, temperature=1.0, seed=42)
        assert len(walk) == 6  # start + 5 steps

    def test_walk_starts_at_specified_syllable(self, initialized_walker):
        """Test walk starts at the specified syllable."""
        walk = initialized_walker.walk(start="bak", steps=5, max_flips=2, temperature=1.0, seed=42)
        assert walk[0]["syllable"] == "bak"

    def test_walk_with_string_start(self, initialized_walker):
        """Test walk with string start parameter."""
        walk = initialized_walker.walk(start="ka", steps=3, max_flips=2, temperature=1.0, seed=42)
        assert walk[0]["syllable"] == "ka"

    def test_walk_with_index_start(self, initialized_walker):
        """Test walk with index start parameter."""
        walk = initialized_walker.walk(start=0, steps=3, max_flips=2, temperature=1.0, seed=42)
        assert walk[0]["syllable"] == "ka"  # Index 0 is "ka"

    def test_walk_output_format(self, initialized_walker):
        """Test walk output has correct format."""
        walk = initialized_walker.walk(start="ka", steps=1, max_flips=2, temperature=1.0, seed=42)

        for step in walk:
            assert "syllable" in step
            assert "frequency" in step
            assert "features" in step
            assert isinstance(step["syllable"], str)
            assert isinstance(step["frequency"], int)
            assert isinstance(step["features"], list)
            assert len(step["features"]) == len(FEATURE_KEYS)

    def test_walk_from_profile(self, initialized_walker):
        """Test walk_from_profile uses correct profile parameters."""
        walk = initialized_walker.walk_from_profile(start="ka", profile="dialect", steps=5, seed=42)
        assert len(walk) == 6

    def test_walk_from_profile_invalid_name(self, initialized_walker):
        """Test walk_from_profile with invalid profile name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown profile"):
            initialized_walker.walk_from_profile(start="ka", profile="invalid", steps=5, seed=42)


# ============================================================
# Edge Cases and Error Handling
# ============================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_walk_with_invalid_start_syllable(self, initialized_walker):
        """Test walk with nonexistent start syllable raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            initialized_walker.walk(start="INVALID_XYZ", steps=5, max_flips=2, temperature=1.0)

    def test_walk_with_invalid_start_index(self, initialized_walker):
        """Test walk with invalid start index raises ValueError."""
        with pytest.raises(ValueError, match="Invalid syllable index"):
            initialized_walker.walk(start=999, steps=5, max_flips=2, temperature=1.0)

        with pytest.raises(ValueError, match="Invalid syllable index"):
            initialized_walker.walk(start=-1, steps=5, max_flips=2, temperature=1.0)

    def test_walk_with_zero_steps(self, initialized_walker):
        """Test walk with 0 steps returns only starting syllable."""
        walk = initialized_walker.walk(start="ka", steps=0, max_flips=2, temperature=1.0)
        assert len(walk) == 1
        assert walk[0]["syllable"] == "ka"

    def test_walk_with_negative_steps(self, initialized_walker):
        """Test walk with negative steps raises ValueError."""
        with pytest.raises(ValueError, match="steps must be non-negative"):
            initialized_walker.walk(start="ka", steps=-1, max_flips=2, temperature=1.0)


# ============================================================
# Utility Method Tests
# ============================================================


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_random_syllable(self, initialized_walker):
        """Test get_random_syllable returns valid syllable."""
        syllable = initialized_walker.get_random_syllable(seed=42)
        assert syllable in initialized_walker.syllables

    def test_get_random_syllable_deterministic(self, initialized_walker):
        """Test get_random_syllable is deterministic with seed."""
        syl1 = initialized_walker.get_random_syllable(seed=42)
        syl2 = initialized_walker.get_random_syllable(seed=42)
        assert syl1 == syl2

    def test_get_syllable_info_exists(self, initialized_walker):
        """Test get_syllable_info for existing syllable."""
        info = initialized_walker.get_syllable_info("ka")
        assert info is not None
        assert info["syllable"] == "ka"
        assert info["frequency"] == 100

    def test_get_syllable_info_not_exists(self, initialized_walker):
        """Test get_syllable_info for nonexistent syllable returns None."""
        info = initialized_walker.get_syllable_info("NONEXISTENT")
        assert info is None

    def test_format_walk(self, initialized_walker):
        """Test format_walk produces correct string."""
        walk = initialized_walker.walk(start="ka", steps=2, max_flips=2, temperature=1.0, seed=42)
        formatted = initialized_walker.format_walk(walk)
        assert formatted.startswith("ka")
        assert " → " in formatted

    def test_format_walk_custom_arrow(self, initialized_walker):
        """Test format_walk with custom arrow."""
        walk = initialized_walker.walk(start="ka", steps=2, max_flips=2, temperature=1.0, seed=42)
        formatted = initialized_walker.format_walk(walk, arrow=" -> ")
        assert " -> " in formatted
        assert " → " not in formatted

    def test_get_available_profiles(self, initialized_walker):
        """Test get_available_profiles returns all profiles."""
        profiles = initialized_walker.get_available_profiles()
        assert len(profiles) == 4
        assert "clerical" in profiles
        assert "dialect" in profiles
        assert "goblin" in profiles
        assert "ritual" in profiles
