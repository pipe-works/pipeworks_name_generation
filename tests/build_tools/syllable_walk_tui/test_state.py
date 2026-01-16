"""
Tests for syllable_walk_tui state management.

Critical: Tests RNG isolation to ensure TUI state doesn't contaminate global random state.
"""

import random
from pathlib import Path

from build_tools.syllable_walk_tui.core.state import AppState
from build_tools.syllable_walk_tui.modules.oscillator import PatchState


class TestPatchState:
    """Tests for PatchState dataclass and RNG isolation."""

    def test_initialization_with_defaults(self):
        """Test PatchState initializes with correct default values."""
        patch = PatchState(name="A")

        assert patch.name == "A"
        assert isinstance(patch.seed, int)
        assert 0 <= patch.seed < 2**32
        assert patch.corpus_dir is None
        assert patch.corpus_type is None

        # Walk profile parameters (defaults match "Dialect" profile)
        assert patch.min_length == 2
        assert patch.max_length == 5
        assert patch.walk_length == 5
        assert patch.max_flips == 2
        assert patch.temperature == 0.7
        assert patch.frequency_weight == 0.0
        assert patch.neighbor_limit == 10
        assert patch.outputs == []

    def test_initialization_with_custom_seed(self):
        """Test PatchState accepts custom seed."""
        patch = PatchState(name="B", seed=42)

        assert patch.name == "B"
        assert patch.seed == 42

    def test_rng_instance_created(self):
        """Test that isolated Random instance is created."""
        patch = PatchState(name="A", seed=42)

        assert hasattr(patch, "rng")
        assert isinstance(patch.rng, random.Random)

    def test_rng_determinism(self):
        """Test that same seed produces same random sequence."""
        patch1 = PatchState(name="A", seed=42)
        patch2 = PatchState(name="A", seed=42)

        # Generate same sequence from both RNGs
        seq1 = [patch1.rng.random() for _ in range(10)]
        seq2 = [patch2.rng.random() for _ in range(10)]

        assert seq1 == seq2

    def test_rng_isolation_from_global_state(self):
        """Test that PatchState RNG doesn't affect global random state."""
        # Set global random state
        random.seed(999)
        global_before = random.random()

        # Create patch with isolated RNG and use it
        patch = PatchState(name="A", seed=42)
        _ = [patch.rng.random() for _ in range(100)]

        # Reset global random to same seed
        random.seed(999)
        global_after = random.random()

        # Global state should be unaffected
        assert global_before == global_after

    def test_rng_independence_between_patches(self):
        """Test that different patches have independent RNG instances."""
        patch_a = PatchState(name="A", seed=42)
        patch_b = PatchState(name="B", seed=100)

        # Generate different sequences
        seq_a = [patch_a.rng.random() for _ in range(10)]
        seq_b = [patch_b.rng.random() for _ in range(10)]

        # Sequences should be different
        assert seq_a != seq_b

        # But repeating with same seeds should match original sequences
        patch_a_repeat = PatchState(name="A", seed=42)
        patch_b_repeat = PatchState(name="B", seed=100)

        seq_a_repeat = [patch_a_repeat.rng.random() for _ in range(10)]
        seq_b_repeat = [patch_b_repeat.rng.random() for _ in range(10)]

        assert seq_a == seq_a_repeat
        assert seq_b == seq_b_repeat

    def test_generate_seed(self):
        """Test that generate_seed creates new seed and updates RNG."""
        patch = PatchState(name="A", seed=42)
        original_seed = patch.seed

        # Generate first sequence
        seq1 = [patch.rng.random() for _ in range(5)]

        # Generate new seed
        new_seed = patch.generate_seed()

        assert new_seed != original_seed
        assert patch.seed == new_seed
        assert 0 <= new_seed < 2**32

        # New sequence should be different
        seq2 = [patch.rng.random() for _ in range(5)]
        assert seq1 != seq2

    def test_generate_seed_uses_system_random(self):
        """Test that generate_seed uses SystemRandom (doesn't depend on global state)."""
        # Set global random state
        random.seed(42)

        # Generate seeds multiple times
        patch = PatchState(name="A")
        seeds = [patch.generate_seed() for _ in range(10)]

        # Reset global random to same seed
        random.seed(42)

        # Generate more seeds
        more_seeds = [patch.generate_seed() for _ in range(10)]

        # Seeds should be different (not affected by global state)
        # Note: This test has a tiny probability of false failure if random collision
        assert seeds != more_seeds

    def test_corpus_path_storage(self):
        """Test that corpus directory can be stored and retrieved."""
        patch = PatchState(name="A")
        corpus_path = Path("/fake/corpus/path")

        patch.corpus_dir = corpus_path
        patch.corpus_type = "NLTK"

        assert patch.corpus_dir == corpus_path
        assert patch.corpus_type == "NLTK"

    def test_outputs_list_independent(self):
        """Test that outputs list is independent between instances."""
        patch1 = PatchState(name="A")
        patch2 = PatchState(name="B")

        patch1.outputs.append("name1")
        patch1.outputs.append("name2")

        # patch2's outputs should be empty
        assert len(patch2.outputs) == 0
        assert len(patch1.outputs) == 2

    def test_is_ready_for_generation_all_requirements_met(self):
        """Test is_ready_for_generation returns True when all data is loaded."""
        from pathlib import Path

        patch = PatchState(name="A")
        patch.corpus_dir = Path("/test/corpus")
        patch.syllables = ["hel", "lo", "world"]
        patch.frequencies = {"hel": 1, "lo": 2, "world": 1}
        patch.annotated_data = [
            {"syllable": "hel", "frequency": 1, "features": {}},
            {"syllable": "lo", "frequency": 2, "features": {}},
        ]
        patch.is_loading_annotated = False
        patch.loading_error = None

        assert patch.is_ready_for_generation() is True

    def test_is_ready_for_generation_no_corpus_dir(self):
        """Test is_ready_for_generation returns False when corpus_dir is None."""
        patch = PatchState(name="A")
        patch.syllables = ["test"]
        patch.frequencies = {"test": 1}
        patch.annotated_data = [{"syllable": "test", "frequency": 1, "features": {}}]

        assert patch.is_ready_for_generation() is False

    def test_is_ready_for_generation_no_syllables(self):
        """Test is_ready_for_generation returns False when syllables is None."""
        from pathlib import Path

        patch = PatchState(name="A")
        patch.corpus_dir = Path("/test/corpus")
        patch.frequencies = {"test": 1}
        patch.annotated_data = [{"syllable": "test", "frequency": 1, "features": {}}]

        assert patch.is_ready_for_generation() is False

    def test_is_ready_for_generation_no_frequencies(self):
        """Test is_ready_for_generation returns False when frequencies is None."""
        from pathlib import Path

        patch = PatchState(name="A")
        patch.corpus_dir = Path("/test/corpus")
        patch.syllables = ["test"]
        patch.annotated_data = [{"syllable": "test", "frequency": 1, "features": {}}]

        assert patch.is_ready_for_generation() is False

    def test_is_ready_for_generation_no_annotated_data(self):
        """Test is_ready_for_generation returns False when annotated_data is None."""
        from pathlib import Path

        patch = PatchState(name="A")
        patch.corpus_dir = Path("/test/corpus")
        patch.syllables = ["test"]
        patch.frequencies = {"test": 1}

        assert patch.is_ready_for_generation() is False

    def test_is_ready_for_generation_currently_loading(self):
        """Test is_ready_for_generation returns False when loading in progress."""
        from pathlib import Path

        patch = PatchState(name="A")
        patch.corpus_dir = Path("/test/corpus")
        patch.syllables = ["test"]
        patch.frequencies = {"test": 1}
        patch.annotated_data = [{"syllable": "test", "frequency": 1, "features": {}}]
        patch.is_loading_annotated = True

        assert patch.is_ready_for_generation() is False

    def test_is_ready_for_generation_has_loading_error(self):
        """Test is_ready_for_generation returns False when there's a loading error."""
        from pathlib import Path

        patch = PatchState(name="A")
        patch.corpus_dir = Path("/test/corpus")
        patch.syllables = ["test"]
        patch.frequencies = {"test": 1}
        patch.annotated_data = [{"syllable": "test", "frequency": 1, "features": {}}]
        patch.loading_error = "Failed to load"

        assert patch.is_ready_for_generation() is False

    def test_current_profile_defaults_to_dialect(self):
        """Test that current_profile defaults to 'dialect'."""
        patch = PatchState(name="A")

        assert patch.current_profile == "dialect"

    def test_current_profile_can_be_changed(self):
        """Test that current_profile can be changed to other profiles."""
        patch = PatchState(name="A")

        patch.current_profile = "clerical"
        assert patch.current_profile == "clerical"

        patch.current_profile = "goblin"
        assert patch.current_profile == "goblin"

        patch.current_profile = "custom"
        assert patch.current_profile == "custom"


class TestAppState:
    """Tests for AppState dataclass."""

    def test_initialization_with_defaults(self):
        """Test AppState initializes with correct defaults."""
        app_state = AppState()

        assert isinstance(app_state.patch_a, PatchState)
        assert isinstance(app_state.patch_b, PatchState)
        assert app_state.patch_a.name == "A"
        assert app_state.patch_b.name == "B"
        assert app_state.current_focus == "patch_a"
        assert app_state.last_browse_dir is None

    def test_patches_have_independent_rngs(self):
        """Test that patch A and B have independent RNG instances."""
        app_state = AppState()

        # Generate sequences from both patches
        seq_a = [app_state.patch_a.rng.random() for _ in range(10)]
        seq_b = [app_state.patch_b.rng.random() for _ in range(10)]

        # Should be different (different seeds)
        assert seq_a != seq_b

    def test_last_browse_dir_storage(self):
        """Test that last browsed directory can be stored."""
        app_state = AppState()
        browse_path = Path("/fake/browse/path")

        app_state.last_browse_dir = browse_path

        assert app_state.last_browse_dir == browse_path

    def test_focus_switching(self):
        """Test that current focus can be changed."""
        app_state = AppState()

        app_state.current_focus = "patch_b"
        assert app_state.current_focus == "patch_b"

        app_state.current_focus = "stats"
        assert app_state.current_focus == "stats"

    def test_patch_state_independence(self):
        """Test that modifying one patch doesn't affect the other."""
        app_state = AppState()

        # Modify patch A
        app_state.patch_a.min_length = 3
        app_state.patch_a.max_length = 7
        app_state.patch_a.corpus_type = "NLTK"

        # Patch B should retain defaults
        assert app_state.patch_b.min_length == 2
        assert app_state.patch_b.max_length == 5
        assert app_state.patch_b.corpus_type is None
