"""Tests for syllable walker profiles.

This module tests the WalkProfile dataclass and predefined profile definitions
to ensure all profiles have valid parameters and the profile accessors work correctly.
"""

import pytest

from build_tools.syllable_walk.profiles import (
    WALK_PROFILES,
    WalkProfile,
    get_profile,
    list_profiles,
)


class TestWalkProfile:
    """Test WalkProfile dataclass."""

    def test_profile_creation(self):
        """Test creating a custom profile."""
        profile = WalkProfile(
            name="Test Profile",
            description="Test description",
            max_flips=2,
            temperature=1.0,
            frequency_weight=0.0,
        )
        assert profile.name == "Test Profile"
        assert profile.description == "Test description"
        assert profile.max_flips == 2
        assert profile.temperature == 1.0
        assert profile.frequency_weight == 0.0

    def test_profile_str(self):
        """Test profile string representation."""
        profile = WALK_PROFILES["dialect"]
        str_repr = str(profile)
        assert "Dialect Walk" in str_repr
        assert "Moderate exploration" in str_repr


class TestPredefinedProfiles:
    """Test predefined walk profiles."""

    def test_all_profiles_exist(self):
        """Test all expected profiles are defined."""
        expected = ["clerical", "dialect", "goblin", "ritual"]
        for name in expected:
            assert name in WALK_PROFILES, f"Profile '{name}' missing"

    def test_profile_count(self):
        """Test correct number of profiles defined."""
        assert len(WALK_PROFILES) == 4, "Expected exactly 4 profiles"

    def test_profile_parameters_valid(self):
        """Test all profile parameters are in valid ranges."""
        for name, profile in WALK_PROFILES.items():
            # max_flips should be 1-3
            assert 1 <= profile.max_flips <= 3, f"{name}: invalid max_flips={profile.max_flips}"

            # temperature should be positive and reasonable (0.1-5.0)
            assert (
                0.1 <= profile.temperature <= 5.0
            ), f"{name}: invalid temperature={profile.temperature}"

            # frequency_weight should be reasonable (-2.0 to 2.0)
            assert (
                -2.0 <= profile.frequency_weight <= 2.0
            ), f"{name}: invalid frequency_weight={profile.frequency_weight}"

    def test_clerical_profile(self):
        """Test clerical profile has expected conservative parameters."""
        profile = WALK_PROFILES["clerical"]
        assert profile.name == "Clerical Walk"
        assert profile.max_flips == 1  # Most conservative
        assert profile.temperature == 0.3  # Low temperature
        assert profile.frequency_weight == 1.0  # Favors common

    def test_dialect_profile(self):
        """Test dialect profile has expected balanced parameters."""
        profile = WALK_PROFILES["dialect"]
        assert profile.name == "Dialect Walk"
        assert profile.max_flips == 2  # Moderate
        assert profile.temperature == 0.7  # Moderate
        assert profile.frequency_weight == 0.0  # Neutral

    def test_goblin_profile(self):
        """Test goblin profile has expected chaotic parameters."""
        profile = WALK_PROFILES["goblin"]
        assert profile.name == "Goblin Walk"
        assert profile.max_flips == 2  # Moderate
        assert profile.temperature == 1.5  # High temperature
        assert profile.frequency_weight == -0.5  # Favors rare

    def test_ritual_profile(self):
        """Test ritual profile has expected extreme parameters."""
        profile = WALK_PROFILES["ritual"]
        assert profile.name == "Ritual Walk"
        assert profile.max_flips == 3  # Maximum
        assert profile.temperature == 2.5  # Very high
        assert profile.frequency_weight == -1.0  # Strongly favors rare


class TestGetProfile:
    """Test get_profile function."""

    def test_get_profile_lowercase(self):
        """Test get_profile with lowercase name."""
        profile = get_profile("goblin")
        assert profile.name == "Goblin Walk"
        assert profile.temperature == 1.5

    def test_get_profile_uppercase(self):
        """Test get_profile is case-insensitive (uppercase)."""
        profile = get_profile("GOBLIN")
        assert profile.name == "Goblin Walk"

    def test_get_profile_mixedcase(self):
        """Test get_profile is case-insensitive (mixed case)."""
        profile = get_profile("GoBLiN")
        assert profile.name == "Goblin Walk"

    def test_get_profile_invalid_raises(self):
        """Test get_profile with invalid name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown profile"):
            get_profile("invalid_profile_name")

    def test_get_profile_error_message_shows_available(self):
        """Test error message includes available profiles."""
        with pytest.raises(ValueError, match="clerical.*dialect.*goblin.*ritual"):
            get_profile("nonexistent")


class TestListProfiles:
    """Test list_profiles function."""

    def test_list_profiles_returns_all(self):
        """Test list_profiles returns all profiles."""
        profiles = list_profiles()
        assert len(profiles) == 4
        assert "clerical" in profiles
        assert "dialect" in profiles
        assert "goblin" in profiles
        assert "ritual" in profiles

    def test_list_profiles_returns_copy(self):
        """Test list_profiles returns a copy (not original)."""
        profiles1 = list_profiles()
        profiles2 = list_profiles()

        # Should be different objects
        assert profiles1 is not profiles2

        # But same content
        assert profiles1 == profiles2

    def test_list_profiles_modification_safe(self):
        """Test modifying returned dict doesn't affect original."""
        profiles = list_profiles()
        original_count = len(WALK_PROFILES)

        # Add something to returned dict
        profiles["test"] = WalkProfile("Test", "Test", 1, 1.0, 0.0)

        # Original should be unchanged
        assert len(WALK_PROFILES) == original_count
        assert "test" not in WALK_PROFILES
