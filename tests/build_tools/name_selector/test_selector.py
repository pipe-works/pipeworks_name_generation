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
