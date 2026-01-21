"""Tests for name combination logic."""

import pytest

from build_tools.name_combiner.combiner import combine_syllables


def make_annotated_data() -> list[dict]:
    """Create sample annotated data for testing."""
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
            "syllable": "li",
            "frequency": 50,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": True,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ra",
            "frequency": 75,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": True,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
    ]


class TestCombineSyllables:
    """Test combine_syllables function."""

    def test_generates_correct_count(self):
        """Should generate the requested number of candidates."""
        data = make_annotated_data()
        result = combine_syllables(data, syllable_count=2, count=10, seed=42)
        assert len(result) == 10

    def test_candidate_structure(self):
        """Each candidate should have name, syllables, and features."""
        data = make_annotated_data()
        result = combine_syllables(data, syllable_count=2, count=5, seed=42)

        for candidate in result:
            assert "name" in candidate
            assert "syllables" in candidate
            assert "features" in candidate
            assert isinstance(candidate["name"], str)
            assert isinstance(candidate["syllables"], list)
            assert isinstance(candidate["features"], dict)

    def test_name_concatenation(self):
        """Name should be concatenation of syllables."""
        data = make_annotated_data()
        result = combine_syllables(data, syllable_count=2, count=5, seed=42)

        for candidate in result:
            expected_name = "".join(candidate["syllables"])
            assert candidate["name"] == expected_name

    def test_syllable_count_respected(self):
        """Each candidate should have the specified syllable count."""
        data = make_annotated_data()

        for syl_count in [2, 3, 4]:
            result = combine_syllables(data, syllable_count=syl_count, count=5, seed=42)
            for candidate in result:
                assert len(candidate["syllables"]) == syl_count


class TestDeterminism:
    """Test deterministic behavior with seeds."""

    def test_same_seed_same_output(self):
        """Same seed should produce identical results."""
        data = make_annotated_data()

        result1 = combine_syllables(data, syllable_count=2, count=10, seed=42)
        result2 = combine_syllables(data, syllable_count=2, count=10, seed=42)

        assert result1 == result2

    def test_different_seeds_different_output(self):
        """Different seeds should produce different results."""
        data = make_annotated_data()

        result1 = combine_syllables(data, syllable_count=2, count=10, seed=42)
        result2 = combine_syllables(data, syllable_count=2, count=10, seed=123)

        # With small corpus, might occasionally match, but names should differ
        names1 = [c["name"] for c in result1]
        names2 = [c["name"] for c in result2]
        assert names1 != names2


class TestFrequencyWeighting:
    """Test frequency-weighted sampling."""

    def test_uniform_sampling(self):
        """With frequency_weight=0, sampling should be uniform."""
        # Create data with extreme frequency difference
        data = [
            {
                "syllable": "rare",
                "frequency": 1,
                "features": {
                    f: False
                    for f in [
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
                },
            },
            {
                "syllable": "common",
                "frequency": 10000,
                "features": {
                    f: False
                    for f in [
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
                },
            },
        ]

        # With uniform sampling, "rare" should appear roughly 50% of the time
        result = combine_syllables(
            data, syllable_count=1, count=1000, seed=42, frequency_weight=0.0
        )
        rare_count = sum(1 for c in result if "rare" in c["syllables"])

        # Should be roughly 50% (allow 35-65% range for randomness)
        assert 350 < rare_count < 650, f"Expected ~500 rare, got {rare_count}"

    def test_frequency_weighted_sampling(self):
        """With frequency_weight=1, sampling should favor high frequency."""
        # Create data with extreme frequency difference
        data = [
            {
                "syllable": "rare",
                "frequency": 1,
                "features": {
                    f: False
                    for f in [
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
                },
            },
            {
                "syllable": "common",
                "frequency": 10000,
                "features": {
                    f: False
                    for f in [
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
                },
            },
        ]

        # With full frequency weighting, "common" should dominate
        result = combine_syllables(
            data, syllable_count=1, count=1000, seed=42, frequency_weight=1.0
        )
        common_count = sum(1 for c in result if "common" in c["syllables"])

        # Should be ~99.99% common
        assert common_count > 990, f"Expected >990 common, got {common_count}"

    def test_interpolated_weighting(self):
        """With frequency_weight=0.5, sampling should be partially weighted."""
        # Create data with extreme frequency difference
        data = [
            {
                "syllable": "rare",
                "frequency": 1,
                "features": {
                    f: False
                    for f in [
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
                },
            },
            {
                "syllable": "common",
                "frequency": 10000,
                "features": {
                    f: False
                    for f in [
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
                },
            },
        ]

        # With interpolated weighting (0.5), should be between uniform and full
        result = combine_syllables(
            data, syllable_count=1, count=1000, seed=42, frequency_weight=0.5
        )
        common_count = sum(1 for c in result if "common" in c["syllables"])

        # Should be more than uniform (500) but less than full (990+)
        # With weight=0.5 and freq ratio 10000:1, expect ~99.98% common still
        # but testing the interpolation path is the key here
        assert common_count > 600, f"Expected >600 common, got {common_count}"


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_data_raises(self):
        """Empty annotated data should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            combine_syllables([], syllable_count=2, count=10)

    def test_invalid_syllable_count_raises(self):
        """Syllable count < 1 should raise ValueError."""
        data = make_annotated_data()
        with pytest.raises(ValueError, match="syllable_count"):
            combine_syllables(data, syllable_count=0, count=10)

    def test_invalid_count_raises(self):
        """Count < 1 should raise ValueError."""
        data = make_annotated_data()
        with pytest.raises(ValueError, match="count"):
            combine_syllables(data, syllable_count=2, count=0)


class TestFeatureAggregation:
    """Test that features are properly aggregated in candidates."""

    def test_features_are_aggregated(self):
        """Candidate features should be aggregated from syllables."""
        data = make_annotated_data()
        result = combine_syllables(data, syllable_count=2, count=5, seed=42)

        for candidate in result:
            # Should have all 12 features
            assert len(candidate["features"]) == 12

            # All values should be booleans
            for value in candidate["features"].values():
                assert isinstance(value, bool)
