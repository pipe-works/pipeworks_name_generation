"""Tests for selector orchestration logic."""

from build_tools.name_selector.name_class import NameClassPolicy
from build_tools.name_selector.selector import compute_selection_statistics, select_names


def make_policy(**feature_policies) -> NameClassPolicy:
    """Helper to create a policy."""
    return NameClassPolicy(
        name="test",
        description="Test policy",
        syllable_range=(2, 3),
        features=feature_policies,
    )


def make_candidate(name: str, syllables: list[str], **features: bool) -> dict:
    """Helper to create a candidate."""
    all_features = {
        "starts_with_vowel": False,
        "starts_with_cluster": False,
        "starts_with_heavy_cluster": False,
        "contains_plosive": False,
        "contains_fricative": False,
        "contains_liquid": False,
        "contains_nasal": False,
        "short_vowel": False,
        "long_vowel": False,
        "ends_with_vowel": False,
        "ends_with_nasal": False,
        "ends_with_stop": False,
    }
    all_features.update(features)
    return {
        "name": name,
        "syllables": syllables,
        "features": all_features,
    }


class TestSelectNames:
    """Test select_names function."""

    def test_returns_requested_count(self):
        """Should return at most the requested count."""
        policy = make_policy()
        candidates = [make_candidate(f"name{i}", ["na", "me"]) for i in range(100)]

        result = select_names(candidates, policy, count=10)

        assert len(result) == 10

    def test_returns_less_if_not_enough_admitted(self):
        """Should return fewer if not enough candidates are admitted."""
        policy = make_policy(ends_with_stop="discouraged")
        # All candidates have discouraged feature
        candidates = [
            make_candidate(f"kalt{i}", ["kal", "t"], ends_with_stop=True) for i in range(10)
        ]

        result = select_names(candidates, policy, count=100, mode="hard")

        assert len(result) == 0  # All rejected

    def test_ranked_by_score_descending(self):
        """Results should be ranked by score, highest first."""
        policy = make_policy(
            ends_with_vowel="preferred",
            contains_liquid="preferred",
        )
        candidates = [
            make_candidate("low", ["lo", "w"]),  # No preferred features
            make_candidate("kali", ["ka", "li"], ends_with_vowel=True, contains_liquid=True),  # 2
            make_candidate("sola", ["me", "da"], ends_with_vowel=True),  # 1
        ]

        result = select_names(candidates, policy, count=10)

        assert result[0]["name"] == "kali"  # Score 2
        assert result[1]["name"] == "sola"  # Score 1
        assert result[2]["name"] == "low"  # Score 0

    def test_candidates_augmented_with_metadata(self):
        """Selected candidates should have score, rank, and evaluation."""
        policy = make_policy()
        candidates = [make_candidate("kali", ["ka", "li"])]

        result = select_names(candidates, policy, count=10)

        assert "score" in result[0]
        assert "rank" in result[0]
        assert "evaluation" in result[0]

    def test_rank_starts_at_one(self):
        """Rank should start at 1, not 0."""
        policy = make_policy()
        candidates = [
            make_candidate("a", ["a", "b"]),
            make_candidate("b", ["b", "c"]),
            make_candidate("c", ["c", "d"]),
        ]

        result = select_names(candidates, policy, count=10)

        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 3

    def test_syllable_count_filtering(self):
        """Should filter by syllable count."""
        policy = NameClassPolicy(
            name="test",
            description="Test",
            syllable_range=(2, 2),  # Only 2 syllables allowed
            features={},
        )
        candidates = [
            make_candidate("ka", ["ka"]),  # 1 syllable - rejected
            make_candidate("kali", ["ka", "li"]),  # 2 syllables - admitted
            make_candidate("kalira", ["ka", "li", "ra"]),  # 3 syllables - rejected
        ]

        result = select_names(candidates, policy, count=10)

        assert len(result) == 1
        assert result[0]["name"] == "kali"


class TestComputeSelectionStatistics:
    """Test compute_selection_statistics function."""

    def test_counts_total_evaluated(self):
        """Should count total candidates evaluated."""
        policy = make_policy()
        candidates = [make_candidate(f"n{i}", ["n", str(i)]) for i in range(50)]

        stats = compute_selection_statistics(candidates, policy)

        assert stats["total_evaluated"] == 50

    def test_counts_admitted_and_rejected(self):
        """Should correctly count admitted and rejected."""
        policy = make_policy(ends_with_stop="discouraged")
        candidates = [
            make_candidate("kali", ["ka", "li"]),  # Admitted
            make_candidate("kalt", ["kal", "t"], ends_with_stop=True),  # Rejected
            make_candidate("sola", ["me", "da"]),  # Admitted
        ]

        stats = compute_selection_statistics(candidates, policy, mode="hard")

        assert stats["admitted"] == 2
        assert stats["rejected"] == 1

    def test_tracks_rejection_reasons(self):
        """Should track why candidates were rejected."""
        policy = make_policy(
            ends_with_stop="discouraged",
            starts_with_heavy_cluster="discouraged",
        )
        candidates = [
            make_candidate("kalt", ["kal", "t"], ends_with_stop=True),
            make_candidate("sprak", ["spra", "k"], starts_with_heavy_cluster=True),
            make_candidate("kali", ["ka", "li"]),  # Admitted
        ]

        stats = compute_selection_statistics(candidates, policy, mode="hard")

        assert "ends_with_stop" in stats["rejection_reasons"]
        assert "starts_with_heavy_cluster" in stats["rejection_reasons"]

    def test_tracks_score_distribution(self):
        """Should track distribution of scores."""
        policy = make_policy(
            ends_with_vowel="preferred",
            contains_liquid="preferred",
        )
        candidates = [
            make_candidate("a", ["a", "b"]),  # Score 0
            make_candidate("b", ["b", "c"], ends_with_vowel=True),  # Score 1
            make_candidate("c", ["c", "d"], ends_with_vowel=True, contains_liquid=True),  # Score 2
        ]

        stats = compute_selection_statistics(candidates, policy)

        assert 0 in stats["score_distribution"]
        assert 1 in stats["score_distribution"]
        assert 2 in stats["score_distribution"]

    def test_syllable_count_rejection_tracked(self):
        """Should track syllable count rejections."""
        policy = NameClassPolicy(
            name="test",
            description="Test",
            syllable_range=(2, 2),  # Only 2 syllables
            features={},
        )
        candidates = [
            make_candidate("ka", ["ka"]),  # 1 syllable - rejected
            make_candidate("kali", ["ka", "li"]),  # 2 syllables - admitted
            make_candidate("kalira", ["ka", "li", "ra"]),  # 3 syllables - rejected
        ]

        stats = compute_selection_statistics(candidates, policy)

        assert stats["rejected"] == 2
        assert stats["admitted"] == 1
        assert "syllable_count_out_of_range" in stats["rejection_reasons"]
        assert stats["rejection_reasons"]["syllable_count_out_of_range"] == 2


class TestDeterminism:
    """Test deterministic behavior."""

    def test_same_input_same_output(self):
        """Same input should produce identical output."""
        policy = make_policy(ends_with_vowel="preferred")
        candidates = [
            make_candidate(f"name{i}", ["na", "me"], ends_with_vowel=(i % 2 == 0))
            for i in range(100)
        ]

        result1 = select_names(candidates, policy, count=50)
        result2 = select_names(candidates, policy, count=50)

        # Names should be in same order
        names1 = [r["name"] for r in result1]
        names2 = [r["name"] for r in result2]
        assert names1 == names2

    def test_ordering_is_stable(self):
        """Candidates with same score should be ordered deterministically."""
        policy = make_policy()  # All tolerated, so all score 0
        candidates = [
            make_candidate("zebra", ["ze", "bra"]),
            make_candidate("alpha", ["al", "pha"]),
            make_candidate("mango", ["man", "go"]),
        ]

        result = select_names(candidates, policy, count=10)

        # Should be alphabetical (secondary sort by name)
        names = [r["name"] for r in result]
        assert names == sorted(names)


class TestOrderParameter:
    """Test order parameter behavior."""

    def test_alphabetical_order_is_deterministic(self):
        """Alphabetical order should produce same results every time."""
        policy = make_policy()  # All score 0
        candidates = [
            make_candidate("zebra", ["ze", "bra"]),
            make_candidate("alpha", ["al", "pha"]),
            make_candidate("mango", ["man", "go"]),
        ]

        result1 = select_names(candidates, policy, count=10, order="alphabetical")
        result2 = select_names(candidates, policy, count=10, order="alphabetical")

        names1 = [r["name"] for r in result1]
        names2 = [r["name"] for r in result2]
        assert names1 == names2
        assert names1 == ["alpha", "mango", "zebra"]

    def test_random_order_with_seed_is_deterministic(self):
        """Random order with same seed should produce same results."""
        policy = make_policy()  # All score 0
        candidates = [make_candidate(f"name{i}", ["na", "me"]) for i in range(20)]

        result1 = select_names(candidates, policy, count=10, order="random", seed=42)
        result2 = select_names(candidates, policy, count=10, order="random", seed=42)

        names1 = [r["name"] for r in result1]
        names2 = [r["name"] for r in result2]
        assert names1 == names2

    def test_random_order_different_seeds_differ(self):
        """Random order with different seeds should produce different results."""
        policy = make_policy()  # All score 0
        candidates = [make_candidate(f"name{i}", ["na", "me"]) for i in range(20)]

        result1 = select_names(candidates, policy, count=10, order="random", seed=42)
        result2 = select_names(candidates, policy, count=10, order="random", seed=123)

        names1 = [r["name"] for r in result1]
        names2 = [r["name"] for r in result2]
        # With enough candidates, different seeds should produce different order
        assert names1 != names2

    def test_random_order_preserves_score_ranking(self):
        """Random order should only shuffle within same score groups."""
        policy = make_policy(ends_with_vowel="preferred", contains_liquid="preferred")
        candidates = [
            make_candidate("low1", ["lo", "w1"]),  # Score 0
            make_candidate("low2", ["lo", "w2"]),  # Score 0
            make_candidate("mid1", ["mi", "da"], ends_with_vowel=True),  # Score 1
            make_candidate("mid2", ["mi", "db"], ends_with_vowel=True),  # Score 1
            make_candidate("high1", ["ka", "li"], ends_with_vowel=True, contains_liquid=True),  # 2
            make_candidate("high2", ["sa", "li"], ends_with_vowel=True, contains_liquid=True),  # 2
        ]

        result = select_names(candidates, policy, count=10, order="random", seed=42)

        # Verify score ordering is preserved (descending)
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

        # First 2 should be score 2
        assert result[0]["score"] == 2
        assert result[1]["score"] == 2
        # Next 2 should be score 1
        assert result[2]["score"] == 1
        assert result[3]["score"] == 1
        # Last 2 should be score 0
        assert result[4]["score"] == 0
        assert result[5]["score"] == 0

    def test_random_order_without_seed_varies(self):
        """Random order without seed should produce variety (non-deterministic)."""
        policy = make_policy()  # All score 0
        candidates = [make_candidate(f"name{i:02d}", ["na", "me"]) for i in range(50)]

        # Run multiple times and collect unique orderings
        orderings = set()
        for _ in range(5):
            result = select_names(candidates, policy, count=20, order="random")
            names = tuple(r["name"] for r in result)
            orderings.add(names)

        # Should have gotten at least 2 different orderings (very likely with 50 candidates)
        # Note: There's a tiny chance this could fail, but extremely unlikely
        assert len(orderings) > 1


class TestShuffleWithinScoreGroups:
    """Test _shuffle_within_score_groups helper function."""

    def test_empty_list_returns_empty(self):
        """Empty input should return empty list."""
        import random

        from build_tools.name_selector.selector import _shuffle_within_score_groups

        rng = random.Random(42)
        result = _shuffle_within_score_groups([], rng)
        assert result == []

    def test_single_group_shuffled(self):
        """Single score group should be shuffled."""
        import random

        from build_tools.name_selector.selector import _shuffle_within_score_groups

        candidates = [
            {"name": "a", "score": 5},
            {"name": "b", "score": 5},
            {"name": "c", "score": 5},
            {"name": "d", "score": 5},
        ]

        rng = random.Random(42)
        result = _shuffle_within_score_groups(candidates, rng)

        # All candidates should still be present
        assert len(result) == 4
        result_names = {c["name"] for c in result}
        assert result_names == {"a", "b", "c", "d"}

    def test_multiple_groups_preserved(self):
        """Multiple score groups should maintain group boundaries."""
        import random

        from build_tools.name_selector.selector import _shuffle_within_score_groups

        candidates = [
            {"name": "high1", "score": 10},
            {"name": "high2", "score": 10},
            {"name": "mid1", "score": 5},
            {"name": "mid2", "score": 5},
            {"name": "low1", "score": 0},
            {"name": "low2", "score": 0},
        ]

        rng = random.Random(42)
        result = _shuffle_within_score_groups(candidates, rng)

        # Score order should be preserved
        scores = [c["score"] for c in result]
        assert scores == [10, 10, 5, 5, 0, 0]

    def test_deterministic_with_seed(self):
        """Same seed should produce same shuffle result."""
        import random

        from build_tools.name_selector.selector import _shuffle_within_score_groups

        candidates = [{"name": f"n{i}", "score": 5} for i in range(10)]

        rng1 = random.Random(42)
        result1 = _shuffle_within_score_groups(candidates.copy(), rng1)

        rng2 = random.Random(42)
        result2 = _shuffle_within_score_groups(candidates.copy(), rng2)

        names1 = [c["name"] for c in result1]
        names2 = [c["name"] for c in result2]
        assert names1 == names2
