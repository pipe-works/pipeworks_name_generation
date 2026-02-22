"""Tests for the syllable walker web service layer.

This module tests the thin service wrappers:
- corpus_loader: delegates to build_tools.syllable_walk.db.load_syllables
- combiner_runner: delegates to build_tools.name_combiner.combiner
- selector_runner: policy caching, listing, and selection
- walk_generator: walk generation with profiles and seeds
"""

from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_annotated_data():
    """Minimal annotated syllable records."""
    return [
        {"syllable": "ka", "frequency": 100, "features": {"short_vowel": True}},
        {"syllable": "ri", "frequency": 80, "features": {"long_vowel": True}},
        {"syllable": "ta", "frequency": 60, "features": {"short_vowel": True}},
    ]


@pytest.fixture
def mock_walker():
    """Mock SyllableWalker that returns predictable walks."""
    walker = MagicMock()

    def get_random(seed=None, **kwargs):
        return "ka"

    walker.get_random_syllable = get_random

    def walk(**kwargs):
        return [
            {"syllable": "ka", "distance": 0},
            {"syllable": "ri", "distance": 1},
        ]

    walker.walk = walk

    def walk_from_profile(**kwargs):
        return [
            {"syllable": "ka", "distance": 0},
            {"syllable": "ta", "distance": 2},
        ]

    walker.walk_from_profile = walk_from_profile

    return walker


# ============================================================
# corpus_loader
# ============================================================


class TestCorpusLoader:
    """Test corpus_loader.load_corpus service."""

    def test_delegates_to_load_syllables(self):
        """Test load_corpus delegates with correct parameters."""
        from pathlib import Path

        from build_tools.syllable_walk_web.services.corpus_loader import load_corpus

        mock_data = [{"syllable": "ka", "frequency": 10}]
        with patch(
            "build_tools.syllable_walk.db.load_syllables",
            return_value=(mock_data, "from db"),
        ) as mock_load:
            result_data, result_source = load_corpus(
                corpus_db_path=Path("/test/corpus.db"),
                annotated_json_path=Path("/test/annotated.json"),
            )

        mock_load.assert_called_once_with(
            db_path=Path("/test/corpus.db"),
            json_path=Path("/test/annotated.json"),
        )
        assert result_data == mock_data
        assert result_source == "from db"


# ============================================================
# combiner_runner
# ============================================================


class TestCombinerRunner:
    """Test combiner_runner.run_combiner service."""

    def test_delegates_to_combine_syllables(self, sample_annotated_data):
        """Test run_combiner passes all parameters through."""
        from build_tools.syllable_walk_web.services.combiner_runner import run_combiner

        mock_candidates = [{"name": "Kari", "syllables": ["ka", "ri"]}]
        with patch(
            "build_tools.name_combiner.combiner.combine_syllables",
            return_value=mock_candidates,
        ) as mock_combine:
            result = run_combiner(
                sample_annotated_data,
                syllable_count=2,
                count=500,
                seed=42,
                frequency_weight=0.5,
            )

        mock_combine.assert_called_once_with(
            annotated_data=sample_annotated_data,
            syllable_count=2,
            count=500,
            seed=42,
            frequency_weight=0.5,
        )
        assert result == mock_candidates

    def test_default_parameters(self, sample_annotated_data):
        """Test run_combiner uses correct defaults."""
        from build_tools.syllable_walk_web.services.combiner_runner import run_combiner

        with patch(
            "build_tools.name_combiner.combiner.combine_syllables",
            return_value=[],
        ) as mock_combine:
            run_combiner(sample_annotated_data)

        _, kwargs = mock_combine.call_args
        assert kwargs["syllable_count"] == 2
        assert kwargs["count"] == 10000
        assert kwargs["seed"] is None
        assert kwargs["frequency_weight"] == 1.0


# ============================================================
# selector_runner
# ============================================================


class TestSelectorRunner:
    """Test selector_runner service."""

    def test_list_name_classes(self):
        """Test list_name_classes returns dicts with expected keys."""
        from build_tools.syllable_walk_web.services import selector_runner

        # Reset the module-level cache so our mock takes effect
        selector_runner._policies = None

        mock_policy = MagicMock()
        mock_policy.description = "Test class"
        mock_policy.syllable_range = (2, 3)

        with patch(
            "build_tools.name_selector.name_class.load_name_classes",
            return_value={"test_class": mock_policy},
        ):
            result = selector_runner.list_name_classes()

        assert len(result) == 1
        assert result[0]["name"] == "test_class"
        assert result[0]["description"] == "Test class"
        assert result[0]["syllable_range"] == [2, 3]

        # Clean up cache
        selector_runner._policies = None

    def test_run_selector_unknown_class(self):
        """Test run_selector returns error for unknown name class."""
        from build_tools.syllable_walk_web.services import selector_runner

        selector_runner._policies = None

        with patch(
            "build_tools.name_selector.name_class.load_name_classes",
            return_value={},
        ):
            result = selector_runner.run_selector(
                [{"name": "Kari"}],
                name_class="nonexistent",
            )

        assert "error" in result
        selector_runner._policies = None

    def test_run_selector_success(self):
        """Test run_selector delegates to select_names correctly."""
        from build_tools.syllable_walk_web.services import selector_runner

        selector_runner._policies = None

        mock_policy = MagicMock()
        mock_policy.description = "First names"
        mock_policy.syllable_range = (2, 3)

        candidates = [{"name": "Kari", "features": {}}]
        selected = [{"name": "Kari", "score": 1.0}]

        with (
            patch(
                "build_tools.name_selector.name_class.load_name_classes",
                return_value={"first_name": mock_policy},
            ),
            patch(
                "build_tools.name_selector.selector.select_names",
                return_value=selected,
            ) as mock_select,
        ):
            result = selector_runner.run_selector(
                candidates,
                name_class="first_name",
                count=50,
                mode="hard",
                order="alphabetical",
                seed=42,
            )

        assert "error" not in result
        assert result["name_class"] == "first_name"
        assert result["count"] == 1
        mock_select.assert_called_once()
        selector_runner._policies = None

    def test_policy_caching(self):
        """Test that policies are loaded once and cached."""
        from build_tools.syllable_walk_web.services import selector_runner

        selector_runner._policies = None

        mock_policy = MagicMock()
        mock_policy.description = "Test"
        mock_policy.syllable_range = (2, 3)

        with patch(
            "build_tools.name_selector.name_class.load_name_classes",
            return_value={"test": mock_policy},
        ) as mock_load:
            selector_runner.list_name_classes()
            selector_runner.list_name_classes()

        # Should only be called once due to caching
        mock_load.assert_called_once()
        selector_runner._policies = None


# ============================================================
# walk_generator
# ============================================================


class TestWalkGenerator:
    """Test walk_generator.generate_walks service."""

    def test_single_walk(self, mock_walker):
        """Test generating a single walk."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        results = generate_walks(mock_walker, count=1)
        assert len(results) == 1
        assert "formatted" in results[0]
        assert "syllables" in results[0]
        assert "steps" in results[0]

    def test_multiple_walks(self, mock_walker):
        """Test generating multiple walks."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        results = generate_walks(mock_walker, count=3)
        assert len(results) == 3

    def test_formatted_uses_middle_dot(self, mock_walker):
        """Test formatted string uses middle dot separator."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        results = generate_walks(mock_walker, count=1)
        assert "\u00b7" in results[0]["formatted"]

    def test_profile_routing(self, mock_walker):
        """Test that named profile uses walk_from_profile."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        results = generate_walks(mock_walker, count=1, profile="clerical")
        # walk_from_profile returns ka·ta
        assert results[0]["syllables"] == ["ka", "ta"]

    def test_custom_profile_uses_explicit_params(self, mock_walker):
        """Test that 'custom' profile uses walk() with explicit params."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        results = generate_walks(mock_walker, count=1, profile="custom")
        # walk() returns ka·ri
        assert results[0]["syllables"] == ["ka", "ri"]

    def test_seed_offset(self, mock_walker):
        """Test each walk in a batch gets seed+i for determinism."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        # Track seeds passed to get_random_syllable
        seeds_seen = []

        def tracking_get(seed=None, **kwargs):
            seeds_seen.append(seed)
            return "ka"

        mock_walker.get_random_syllable = tracking_get

        generate_walks(mock_walker, count=3, seed=100)
        assert seeds_seen == [100, 101, 102]

    def test_no_seed_passes_none(self, mock_walker):
        """Test that no seed passes None for each walk."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        seeds_seen = []

        def tracking_get(seed=None, **kwargs):
            seeds_seen.append(seed)
            return "ka"

        mock_walker.get_random_syllable = tracking_get

        generate_walks(mock_walker, count=2, seed=None)
        assert seeds_seen == [None, None]

    def test_custom_walk_receives_neighbor_and_length_constraints(self, mock_walker):
        """Custom walk path forwards neighbor/length controls."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        mock_walk = MagicMock(
            return_value=[
                {"syllable": "ka", "distance": 0},
                {"syllable": "ri", "distance": 1},
            ]
        )
        mock_walker.walk = mock_walk

        generate_walks(
            mock_walker,
            count=1,
            profile="custom",
            neighbor_limit=7,
            min_length=2,
            max_length=4,
        )

        _, kwargs = mock_walk.call_args
        assert kwargs["neighbor_limit"] == 7
        assert kwargs["min_length"] == 2
        assert kwargs["max_length"] == 4

    def test_profile_walk_receives_neighbor_and_length_constraints(self, mock_walker):
        """Named profile path forwards neighbor/length controls."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        mock_profile_walk = MagicMock(
            return_value=[
                {"syllable": "ka", "distance": 0},
                {"syllable": "ta", "distance": 2},
            ]
        )
        mock_walker.walk_from_profile = mock_profile_walk

        generate_walks(
            mock_walker,
            count=1,
            profile="clerical",
            neighbor_limit=11,
            min_length=1,
            max_length=5,
        )

        _, kwargs = mock_profile_walk.call_args
        assert kwargs["neighbor_limit"] == 11
        assert kwargs["min_length"] == 1
        assert kwargs["max_length"] == 5

    def test_walk_allows_disabled_optional_constraints(self, mock_walker):
        """None neighbor/min/max values are treated as disabled constraints."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        mock_walk = MagicMock(
            return_value=[
                {"syllable": "ka", "distance": 0},
                {"syllable": "ri", "distance": 1},
            ]
        )
        mock_walker.walk = mock_walk

        generate_walks(
            mock_walker,
            count=1,
            profile="custom",
            neighbor_limit=None,
            min_length=None,
            max_length=None,
        )

        _, kwargs = mock_walk.call_args
        assert kwargs["neighbor_limit"] is None
        assert kwargs["min_length"] is None
        assert kwargs["max_length"] is None

    def test_invalid_length_constraints_raise_value_error(self, mock_walker):
        """min_length > max_length is rejected before walk execution."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        with pytest.raises(ValueError, match="min_length .* must be <= max_length"):
            generate_walks(mock_walker, count=1, min_length=5, max_length=2)

    def test_invalid_neighbor_limit_raises_value_error(self, mock_walker):
        """neighbor_limit must be >= 1."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        with pytest.raises(ValueError, match="neighbor_limit must be >= 1"):
            generate_walks(mock_walker, count=1, neighbor_limit=0)

    def test_invalid_min_length_raises_value_error(self, mock_walker):
        """min_length must be >= 1."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        with pytest.raises(ValueError, match="min_length must be >= 1"):
            generate_walks(mock_walker, count=1, min_length=0)

    def test_invalid_max_length_raises_value_error(self, mock_walker):
        """max_length must be >= 1."""
        from build_tools.syllable_walk_web.services.walk_generator import generate_walks

        with pytest.raises(ValueError, match="max_length must be >= 1"):
            generate_walks(mock_walker, count=1, max_length=0)


# ============================================================
# metrics
# ============================================================


class TestComputeAnalysis:
    """Test metrics.compute_analysis service."""

    def test_output_structure(self, sample_annotated_data):
        """Test compute_analysis returns expected keys."""
        from build_tools.syllable_walk_web.services.metrics import compute_analysis

        # Build a mock CorpusShapeMetrics return value matching the
        # dataclass structure from syllable_walk_tui.services.metrics
        mock_inv = MagicMock()
        mock_inv.total_count = 3
        mock_inv.length_distribution = {2: 3}

        mock_freq = MagicMock()
        mock_freq.hapax_count = 1

        mock_terrain = MagicMock()
        mock_terrain.shape_score = 0.5
        mock_terrain.shape_label = "balanced"
        mock_terrain.shape_exemplars = None
        mock_terrain.craft_score = 0.6
        mock_terrain.craft_label = "moderate"
        mock_terrain.craft_exemplars = None
        mock_terrain.space_score = 0.4
        mock_terrain.space_label = "sparse"
        mock_terrain.space_exemplars = None

        mock_metrics = MagicMock()
        mock_metrics.inventory = mock_inv
        mock_metrics.frequency = mock_freq
        mock_metrics.terrain = mock_terrain

        freqs = {"ka": 100, "ri": 80, "ta": 60}

        with patch(
            "build_tools.syllable_walk_tui.services.metrics.compute_corpus_shape_metrics",
            return_value=mock_metrics,
        ):
            result = compute_analysis(sample_annotated_data, freqs)

        assert result["total"] == 3
        assert result["unique"] == 3
        assert result["hapax"] == 1
        assert "length_distribution" in result
        assert "terrain" in result
        assert "shape" in result["terrain"]
        assert "craft" in result["terrain"]
        assert "space" in result["terrain"]

    def test_length_distribution_bucketing(self, sample_annotated_data):
        """Test 5+ length bucket merges correctly."""
        from build_tools.syllable_walk_web.services.metrics import compute_analysis

        mock_inv = MagicMock()
        mock_inv.total_count = 10
        mock_inv.length_distribution = {2: 4, 3: 3, 5: 2, 6: 1}

        mock_freq = MagicMock()
        mock_freq.hapax_count = 0

        mock_terrain = MagicMock()
        mock_terrain.shape_score = 0.5
        mock_terrain.shape_label = "balanced"
        mock_terrain.shape_exemplars = None
        mock_terrain.craft_score = 0.5
        mock_terrain.craft_label = "balanced"
        mock_terrain.craft_exemplars = None
        mock_terrain.space_score = 0.5
        mock_terrain.space_label = "balanced"
        mock_terrain.space_exemplars = None

        mock_metrics = MagicMock()
        mock_metrics.inventory = mock_inv
        mock_metrics.frequency = mock_freq
        mock_metrics.terrain = mock_terrain

        with patch(
            "build_tools.syllable_walk_tui.services.metrics.compute_corpus_shape_metrics",
            return_value=mock_metrics,
        ):
            result = compute_analysis(sample_annotated_data, {"ka": 100})

        ld = result["length_distribution"]
        assert "2" in ld
        assert "3" in ld
        # Lengths 5 and 6 should be merged into "5+"
        assert "5+" in ld
        assert ld["5+"][0] == 3  # 2 + 1

    def test_terrain_exemplars_flattening(self, sample_annotated_data):
        """Test terrain exemplars from both poles are merged."""
        from build_tools.syllable_walk_web.services.metrics import compute_analysis

        mock_inv = MagicMock()
        mock_inv.total_count = 3
        mock_inv.length_distribution = {2: 3}

        mock_freq = MagicMock()
        mock_freq.hapax_count = 0

        # Set up exemplars with low and high poles
        mock_shape_ex = MagicMock()
        mock_shape_ex.low_pole_exemplars = ["ka", "ta"]
        mock_shape_ex.high_pole_exemplars = ["bri", "stra"]

        mock_terrain = MagicMock()
        mock_terrain.shape_score = 0.5
        mock_terrain.shape_label = "balanced"
        mock_terrain.shape_exemplars = mock_shape_ex
        mock_terrain.craft_score = 0.5
        mock_terrain.craft_label = "balanced"
        mock_terrain.craft_exemplars = None
        mock_terrain.space_score = 0.5
        mock_terrain.space_label = "balanced"
        mock_terrain.space_exemplars = None

        mock_metrics = MagicMock()
        mock_metrics.inventory = mock_inv
        mock_metrics.frequency = mock_freq
        mock_metrics.terrain = mock_terrain

        with patch(
            "build_tools.syllable_walk_tui.services.metrics.compute_corpus_shape_metrics",
            return_value=mock_metrics,
        ):
            result = compute_analysis(sample_annotated_data, {"ka": 100})

        shape_ex = result["terrain"]["shape"]["exemplars"]
        assert "ka" in shape_ex
        assert "bri" in shape_ex
        assert len(shape_ex) == 4
