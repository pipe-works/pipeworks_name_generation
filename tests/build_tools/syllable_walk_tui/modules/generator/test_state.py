"""
Tests for CombinerState and SelectorState.

Tests that states mirror the CLI options exactly for name_combiner and name_selector.
"""

from __future__ import annotations

from build_tools.syllable_walk_tui.modules.generator.state import (
    NAME_CLASSES,
    CombinerState,
    SelectorState,
)


class TestCombinerStateDefaults:
    """Test default values match CLI defaults."""

    def test_default_source_patch(self) -> None:
        """Default source patch is A."""
        state = CombinerState()
        assert state.source_patch == "A"

    def test_default_syllables(self) -> None:
        """Default syllables is 2."""
        state = CombinerState()
        assert state.syllables == 2

    def test_default_count(self) -> None:
        """Default count is 10000 (matches CLI --count default)."""
        state = CombinerState()
        assert state.count == 10000

    def test_default_seed(self) -> None:
        """Default seed is None (matches CLI --seed default = system entropy)."""
        state = CombinerState()
        assert state.seed is None

    def test_default_frequency_weight(self) -> None:
        """Default frequency_weight is 1.0 (matches CLI --frequency-weight default)."""
        state = CombinerState()
        assert state.frequency_weight == 1.0

    def test_default_outputs_empty(self) -> None:
        """Default outputs is empty list."""
        state = CombinerState()
        assert state.outputs == []

    def test_default_last_output_path_none(self) -> None:
        """Default last_output_path is None."""
        state = CombinerState()
        assert state.last_output_path is None


class TestCombinerStateValues:
    """Test setting various values."""

    def test_set_source_patch_b(self) -> None:
        """Can set source patch to B."""
        state = CombinerState()
        state.source_patch = "B"
        assert state.source_patch == "B"

    def test_set_syllables_2(self) -> None:
        """Can set syllables to 2."""
        state = CombinerState()
        state.syllables = 2
        assert state.syllables == 2

    def test_set_syllables_3(self) -> None:
        """Can set syllables to 3."""
        state = CombinerState()
        state.syllables = 3
        assert state.syllables == 3

    def test_set_syllables_4(self) -> None:
        """Can set syllables to 4."""
        state = CombinerState()
        state.syllables = 4
        assert state.syllables == 4

    def test_set_count(self) -> None:
        """Can set count to various values."""
        state = CombinerState()
        state.count = 5000
        assert state.count == 5000

    def test_set_seed(self) -> None:
        """Can set seed to specific value."""
        state = CombinerState()
        state.seed = 42
        assert state.seed == 42

    def test_set_frequency_weight(self) -> None:
        """Can set frequency_weight in range 0.0-1.0."""
        state = CombinerState()
        state.frequency_weight = 0.5
        assert state.frequency_weight == 0.5

    def test_set_frequency_weight_zero(self) -> None:
        """Frequency weight 0.0 means uniform sampling."""
        state = CombinerState()
        state.frequency_weight = 0.0
        assert state.frequency_weight == 0.0


class TestCombinerStateCliMapping:
    """Test that state maps to CLI options correctly."""

    def test_maps_to_cli_run_dir(self) -> None:
        """source_patch maps to --run-dir via patch.corpus_dir."""
        state = CombinerState(source_patch="A")
        assert state.source_patch == "A"

    def test_maps_to_cli_syllables(self) -> None:
        """syllables maps to --syllables."""
        state = CombinerState(syllables=3)
        assert state.syllables == 3

    def test_maps_to_cli_count(self) -> None:
        """count maps to --count."""
        state = CombinerState(count=5000)
        assert state.count == 5000

    def test_maps_to_cli_seed(self) -> None:
        """seed maps to --seed."""
        state = CombinerState(seed=42)
        assert state.seed == 42

    def test_maps_to_cli_frequency_weight(self) -> None:
        """frequency_weight maps to --frequency-weight."""
        state = CombinerState(frequency_weight=0.5)
        assert state.frequency_weight == 0.5


class TestCombinerStateTyping:
    """Tests for type annotations."""

    def test_source_patch_accepts_a_or_b(self) -> None:
        """source_patch should accept 'A' or 'B'."""
        state_a = CombinerState(source_patch="A")
        state_b = CombinerState(source_patch="B")
        assert state_a.source_patch == "A"
        assert state_b.source_patch == "B"

    def test_syllables_accepts_valid_values(self) -> None:
        """syllables should accept 2, 3, or 4."""
        for count in [2, 3, 4]:
            state = CombinerState(syllables=count)
            assert state.syllables == count

    def test_frequency_weight_accepts_range(self) -> None:
        """frequency_weight should accept values 0.0 to 1.0."""
        state_min = CombinerState(frequency_weight=0.0)
        state_max = CombinerState(frequency_weight=1.0)
        state_mid = CombinerState(frequency_weight=0.5)

        assert state_min.frequency_weight == 0.0
        assert state_max.frequency_weight == 1.0
        assert state_mid.frequency_weight == 0.5


# =============================================================================
# SelectorState Tests
# =============================================================================


class TestNameClasses:
    """Tests for NAME_CLASSES constant."""

    def test_name_classes_is_list(self) -> None:
        """NAME_CLASSES should be a list."""
        assert isinstance(NAME_CLASSES, list)

    def test_name_classes_contains_expected_values(self) -> None:
        """NAME_CLASSES should contain all expected name class options."""
        expected = [
            "first_name",
            "last_name",
            "place_name",
            "location_name",
            "object_item",
            "organisation",
            "title_epithet",
        ]
        assert NAME_CLASSES == expected

    def test_name_classes_has_seven_items(self) -> None:
        """NAME_CLASSES should have exactly 7 items."""
        assert len(NAME_CLASSES) == 7


class TestSelectorStateDefaults:
    """Test default values match CLI defaults."""

    def test_default_name_class(self) -> None:
        """Default name_class is first_name."""
        state = SelectorState()
        assert state.name_class == "first_name"

    def test_default_count(self) -> None:
        """Default count is 100 (matches CLI --count default)."""
        state = SelectorState()
        assert state.count == 100

    def test_default_mode(self) -> None:
        """Default mode is 'hard' (matches CLI --mode default)."""
        state = SelectorState()
        assert state.mode == "hard"

    def test_default_outputs_empty(self) -> None:
        """Default outputs is empty list."""
        state = SelectorState()
        assert state.outputs == []

    def test_default_last_output_path_none(self) -> None:
        """Default last_output_path is None."""
        state = SelectorState()
        assert state.last_output_path is None

    def test_default_last_candidates_path_none(self) -> None:
        """Default last_candidates_path is None."""
        state = SelectorState()
        assert state.last_candidates_path is None


class TestSelectorStateValues:
    """Test setting various values."""

    def test_set_name_class_last_name(self) -> None:
        """Can set name_class to last_name."""
        state = SelectorState()
        state.name_class = "last_name"
        assert state.name_class == "last_name"

    def test_set_name_class_place_name(self) -> None:
        """Can set name_class to place_name."""
        state = SelectorState()
        state.name_class = "place_name"
        assert state.name_class == "place_name"

    def test_set_count(self) -> None:
        """Can set count to various values."""
        state = SelectorState()
        state.count = 50
        assert state.count == 50

    def test_set_mode_soft(self) -> None:
        """Can set mode to soft."""
        state = SelectorState()
        state.mode = "soft"
        assert state.mode == "soft"

    def test_set_mode_hard(self) -> None:
        """Can set mode to hard."""
        state = SelectorState()
        state.mode = "hard"
        assert state.mode == "hard"

    def test_set_last_candidates_path(self) -> None:
        """Can set last_candidates_path."""
        state = SelectorState()
        state.last_candidates_path = "/path/to/candidates.json"
        assert state.last_candidates_path == "/path/to/candidates.json"


class TestSelectorStateCliMapping:
    """Test that state maps to CLI options correctly."""

    def test_maps_to_cli_name_class(self) -> None:
        """name_class maps to --name-class."""
        state = SelectorState(name_class="organisation")
        assert state.name_class == "organisation"

    def test_maps_to_cli_count(self) -> None:
        """count maps to --count."""
        state = SelectorState(count=200)
        assert state.count == 200

    def test_maps_to_cli_mode(self) -> None:
        """mode maps to --mode."""
        state = SelectorState(mode="soft")
        assert state.mode == "soft"


class TestSelectorStateTyping:
    """Tests for type annotations."""

    def test_name_class_accepts_all_valid_values(self) -> None:
        """name_class should accept all values from NAME_CLASSES."""
        for nc in NAME_CLASSES:
            state = SelectorState(name_class=nc)
            assert state.name_class == nc

    def test_mode_accepts_hard_or_soft(self) -> None:
        """mode should accept 'hard' or 'soft'."""
        state_hard = SelectorState(mode="hard")
        state_soft = SelectorState(mode="soft")
        assert state_hard.mode == "hard"
        assert state_soft.mode == "soft"

    def test_count_accepts_range(self) -> None:
        """count should accept positive integers."""
        state_min = SelectorState(count=10)
        state_mid = SelectorState(count=100)
        state_max = SelectorState(count=1000)

        assert state_min.count == 10
        assert state_mid.count == 100
        assert state_max.count == 1000
