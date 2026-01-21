"""Tests for name class policy loading and validation."""

import tempfile
from pathlib import Path

import pytest

from build_tools.name_selector.name_class import (
    FEATURE_NAMES,
    NameClassPolicy,
    load_name_classes,
)


class TestFeatureNames:
    """Test feature name constants."""

    def test_feature_count(self):
        """Should have exactly 12 features."""
        assert len(FEATURE_NAMES) == 12

    def test_feature_names_are_strings(self):
        """All feature names should be strings."""
        for name in FEATURE_NAMES:
            assert isinstance(name, str)


class TestNameClassPolicy:
    """Test NameClassPolicy dataclass."""

    def test_valid_policy_creation(self):
        """Should create policy with valid inputs."""
        policy = NameClassPolicy(
            name="test_class",
            description="A test class",
            syllable_range=(2, 3),
            features={"ends_with_vowel": "preferred"},
        )
        assert policy.name == "test_class"
        assert policy.description == "A test class"
        assert policy.syllable_range == (2, 3)
        assert policy.features["ends_with_vowel"] == "preferred"

    def test_default_features(self):
        """Features should default to empty dict."""
        policy = NameClassPolicy(
            name="test",
            description="Test",
            syllable_range=(2, 3),
        )
        assert policy.features == {}

    def test_invalid_syllable_range_length(self):
        """Should reject syllable_range with wrong length."""
        with pytest.raises(ValueError, match="2 elements"):
            NameClassPolicy(
                name="test",
                description="Test",
                syllable_range=(2,),  # type: ignore[arg-type]
            )

    def test_invalid_syllable_range_order(self):
        """Should reject syllable_range where min > max."""
        with pytest.raises(ValueError, match="min > max"):
            NameClassPolicy(
                name="test",
                description="Test",
                syllable_range=(5, 2),
            )

    def test_unknown_feature_rejected(self):
        """Should reject unknown feature names."""
        with pytest.raises(ValueError, match="Unknown features"):
            NameClassPolicy(
                name="test",
                description="Test",
                syllable_range=(2, 3),
                features={"not_a_real_feature": "preferred"},
            )

    def test_invalid_policy_value_rejected(self):
        """Should reject invalid policy values."""
        with pytest.raises(ValueError, match="Invalid policy value"):
            NameClassPolicy(
                name="test",
                description="Test",
                syllable_range=(2, 3),
                features={"ends_with_vowel": "invalid_value"},  # type: ignore[dict-item]
            )

    def test_all_valid_policy_values(self):
        """Should accept all three valid policy values."""
        policy = NameClassPolicy(
            name="test",
            description="Test",
            syllable_range=(2, 3),
            features={
                "starts_with_vowel": "preferred",
                "contains_liquid": "tolerated",
                "ends_with_stop": "discouraged",
            },
        )
        assert policy.features["starts_with_vowel"] == "preferred"
        assert policy.features["contains_liquid"] == "tolerated"
        assert policy.features["ends_with_stop"] == "discouraged"


class TestLoadNameClasses:
    """Test YAML loading functionality."""

    def test_load_valid_yaml(self):
        """Should load valid YAML file."""
        yaml_content = """
version: "1.0"
name_classes:
  first_name:
    description: "Test first name"
    syllable_range: [2, 3]
    features:
      ends_with_vowel: preferred
      ends_with_stop: discouraged
  last_name:
    description: "Test last name"
    syllable_range: [2, 4]
    features:
      ends_with_stop: preferred
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            policies = load_name_classes(f.name)

            assert "first_name" in policies
            assert "last_name" in policies
            assert policies["first_name"].syllable_range == (2, 3)
            assert policies["last_name"].syllable_range == (2, 4)

    def test_file_not_found(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_name_classes("/nonexistent/path/to/file.yml")

    def test_missing_name_classes_key(self):
        """Should raise ValueError if name_classes key is missing."""
        yaml_content = """
version: "1.0"
other_key: value
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            with pytest.raises(ValueError, match="Missing 'name_classes'"):
                load_name_classes(f.name)

    def test_load_project_name_classes(self):
        """Should be able to load the project's name_classes.yml."""
        # This test assumes the file exists at data/name_classes.yml
        project_path = Path(__file__).parent.parent.parent.parent / "data" / "name_classes.yml"
        if project_path.exists():
            policies = load_name_classes(project_path)
            assert len(policies) >= 1
            # Verify at least one expected class exists
            assert any(name in policies for name in ["first_name", "last_name", "place_name"])

    def test_invalid_top_level_yaml(self):
        """Should raise ValueError if top-level is not a dict."""
        yaml_content = "- list_item"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            with pytest.raises(ValueError, match="Expected dict"):
                load_name_classes(f.name)

    def test_invalid_name_classes_value(self):
        """Should raise ValueError if name_classes is not a dict."""
        yaml_content = """
version: "1.0"
name_classes:
  - item1
  - item2
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            with pytest.raises(ValueError, match="must be a dict"):
                load_name_classes(f.name)

    def test_invalid_name_class_config(self):
        """Should raise ValueError if individual name class is not a dict."""
        yaml_content = """
version: "1.0"
name_classes:
  first_name: "not a dict"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            with pytest.raises(ValueError, match="Name class 'first_name' must be a dict"):
                load_name_classes(f.name)

    def test_invalid_syllable_range_type(self):
        """Should raise ValueError if syllable_range is not a list."""
        yaml_content = """
version: "1.0"
name_classes:
  first_name:
    description: "Test"
    syllable_range: 2
    features: {}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            with pytest.raises(ValueError, match="must be a list"):
                load_name_classes(f.name)


class TestGetDefaultPolicyPath:
    """Test default policy path resolution."""

    def test_returns_path(self):
        """Should return a Path object."""
        from build_tools.name_selector.name_class import get_default_policy_path

        result = get_default_policy_path()
        assert isinstance(result, Path)

    def test_path_ends_with_name_classes(self):
        """Should return path ending with data/name_classes.yml."""
        from build_tools.name_selector.name_class import get_default_policy_path

        result = get_default_policy_path()
        assert result.name == "name_classes.yml"
        assert result.parent.name == "data"
