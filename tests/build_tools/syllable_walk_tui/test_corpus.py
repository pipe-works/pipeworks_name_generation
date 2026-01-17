"""
Tests for syllable_walk_tui corpus validation.

Tests validation logic for NLTK and Pyphen corpus directories without loading data.
"""

import json

import pytest

from build_tools.syllable_walk_tui.services.corpus import (
    get_corpus_info,
    load_annotated_data,
    load_corpus_data,
    validate_corpus_directory,
)


class TestValidateCorpusDirectory:
    """Tests for corpus directory validation."""

    def test_valid_nltk_corpus(self, tmp_path):
        """Test validation of valid NLTK corpus directory."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        # Create required NLTK files
        (corpus_dir / "nltk_syllables_unique.txt").write_text("hel\nlo\nworld\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(
            json.dumps({"hel": 1, "lo": 2, "world": 1})
        )

        is_valid, corpus_type, message = validate_corpus_directory(corpus_dir)

        assert is_valid is True
        assert corpus_type == "NLTK"
        assert "Valid NLTK corpus" in message

    def test_valid_pyphen_corpus(self, tmp_path):
        """Test validation of valid Pyphen corpus directory."""
        corpus_dir = tmp_path / "pyphen_corpus"
        corpus_dir.mkdir()

        # Create required Pyphen files
        (corpus_dir / "pyphen_syllables_unique.txt").write_text("hel\nlo\nworld\n")
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(
            json.dumps({"hel": 1, "lo": 2, "world": 1})
        )

        is_valid, corpus_type, message = validate_corpus_directory(corpus_dir)

        assert is_valid is True
        assert corpus_type == "Pyphen"
        assert "Valid Pyphen corpus" in message

    def test_both_corpus_types_present_prefers_nltk(self, tmp_path):
        """Test that NLTK is preferred when both corpus types exist."""
        corpus_dir = tmp_path / "mixed_corpus"
        corpus_dir.mkdir()

        # Create both NLTK and Pyphen files
        (corpus_dir / "nltk_syllables_unique.txt").write_text("nltk\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"nltk": 1}))
        (corpus_dir / "pyphen_syllables_unique.txt").write_text("pyphen\n")
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(json.dumps({"pyphen": 1}))

        is_valid, corpus_type, message = validate_corpus_directory(corpus_dir)

        assert is_valid is True
        assert corpus_type == "NLTK"  # Should prefer NLTK
        assert "Valid NLTK corpus" in message

    def test_missing_unique_file_nltk(self, tmp_path):
        """Test invalid corpus with missing NLTK unique file."""
        corpus_dir = tmp_path / "incomplete_nltk"
        corpus_dir.mkdir()

        # Only frequencies file, missing unique file
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        is_valid, corpus_type, error = validate_corpus_directory(corpus_dir)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "No corpus files found" in error

    def test_missing_frequencies_file_nltk(self, tmp_path):
        """Test invalid corpus with missing NLTK frequencies file."""
        corpus_dir = tmp_path / "incomplete_nltk"
        corpus_dir.mkdir()

        # Only unique file, missing frequencies file
        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")

        is_valid, corpus_type, error = validate_corpus_directory(corpus_dir)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "No corpus files found" in error

    def test_missing_unique_file_pyphen(self, tmp_path):
        """Test invalid corpus with missing Pyphen unique file."""
        corpus_dir = tmp_path / "incomplete_pyphen"
        corpus_dir.mkdir()

        # Only frequencies file
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        is_valid, corpus_type, error = validate_corpus_directory(corpus_dir)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "No corpus files found" in error

    def test_missing_frequencies_file_pyphen(self, tmp_path):
        """Test invalid corpus with missing Pyphen frequencies file."""
        corpus_dir = tmp_path / "incomplete_pyphen"
        corpus_dir.mkdir()

        # Only unique file
        (corpus_dir / "pyphen_syllables_unique.txt").write_text("test\n")

        is_valid, corpus_type, error = validate_corpus_directory(corpus_dir)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "No corpus files found" in error

    def test_nonexistent_directory(self, tmp_path):
        """Test validation of nonexistent directory."""
        nonexistent = tmp_path / "does_not_exist"

        is_valid, corpus_type, error = validate_corpus_directory(nonexistent)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "does not exist" in error.lower()

    def test_file_instead_of_directory(self, tmp_path):
        """Test validation when path points to a file instead of directory."""
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("content")

        is_valid, corpus_type, error = validate_corpus_directory(file_path)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "not a directory" in error.lower()

    def test_empty_directory(self, tmp_path):
        """Test validation of empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        is_valid, corpus_type, error = validate_corpus_directory(empty_dir)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "No corpus files found" in error

    def test_directory_with_wrong_files(self, tmp_path):
        """Test validation of directory with unrelated files."""
        corpus_dir = tmp_path / "wrong_files"
        corpus_dir.mkdir()

        # Create unrelated files
        (corpus_dir / "readme.txt").write_text("readme")
        (corpus_dir / "data.csv").write_text("data")

        is_valid, corpus_type, error = validate_corpus_directory(corpus_dir)

        assert is_valid is False
        assert corpus_type == ""
        assert error is not None
        assert "No corpus files found" in error

    def test_invalid_json_in_frequencies(self, tmp_path):
        """Test that validation still passes even if JSON is malformed (validation doesn't parse)."""
        corpus_dir = tmp_path / "bad_json"
        corpus_dir.mkdir()

        # Create files but with invalid JSON
        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text("not valid json {{{")

        # Validation only checks file existence, not content
        is_valid, corpus_type, message = validate_corpus_directory(corpus_dir)

        assert is_valid is True
        assert corpus_type == "NLTK"
        assert "Valid NLTK corpus" in message

    def test_empty_unique_file(self, tmp_path):
        """Test validation with empty unique syllables file."""
        corpus_dir = tmp_path / "empty_unique"
        corpus_dir.mkdir()

        # Create empty files
        (corpus_dir / "nltk_syllables_unique.txt").write_text("")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text("{}")

        # Validation only checks existence, not content
        is_valid, corpus_type, message = validate_corpus_directory(corpus_dir)

        assert is_valid is True
        assert corpus_type == "NLTK"
        assert "Valid NLTK corpus" in message


class TestGetCorpusInfo:
    """Tests for corpus info string generation."""

    def test_nltk_corpus_info(self, tmp_path):
        """Test corpus info string for NLTK corpus."""
        corpus_dir = tmp_path / "20260110_115601_nltk"
        corpus_dir.mkdir()

        # Create NLTK files
        (corpus_dir / "nltk_syllables_unique.txt").write_text("hel\nlo\nworld\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"hel": 5}))

        info = get_corpus_info(corpus_dir)

        assert "NLTK" in info
        assert "20260110_115601_nltk" in info

    def test_pyphen_corpus_info(self, tmp_path):
        """Test corpus info string for Pyphen corpus."""
        corpus_dir = tmp_path / "20260110_143022_pyphen"
        corpus_dir.mkdir()

        # Create Pyphen files
        (corpus_dir / "pyphen_syllables_unique.txt").write_text("py\nphen\n")
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(json.dumps({"py": 100}))

        info = get_corpus_info(corpus_dir)

        assert "Pyphen" in info
        assert "20260110_143022_pyphen" in info

    def test_corpus_info_format(self, tmp_path):
        """Test corpus info format matches expected pattern."""
        corpus_dir = tmp_path / "test_corpus"
        corpus_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        info = get_corpus_info(corpus_dir)

        # Format: "NLTK (dir_name)"
        assert info == "NLTK (test_corpus)"

    def test_corpus_info_invalid_directory(self, tmp_path):
        """Test corpus info for invalid directory returns error message."""
        invalid_dir = tmp_path / "invalid"
        invalid_dir.mkdir()

        info = get_corpus_info(invalid_dir)

        assert "Invalid" in info
        assert "No corpus files found" in info


class TestLoadCorpusData:
    """Tests for corpus data loading."""

    def test_load_nltk_corpus_data(self, tmp_path):
        """Test loading NLTK corpus data successfully."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        # Create test corpus files
        syllables_content = "hel\nlo\nworld\ntest\n"
        frequencies_content = json.dumps({"hel": 10, "lo": 20, "world": 5, "test": 3})

        (corpus_dir / "nltk_syllables_unique.txt").write_text(syllables_content)
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(frequencies_content)

        syllables, frequencies = load_corpus_data(corpus_dir)

        assert len(syllables) == 4
        assert syllables == ["hel", "lo", "world", "test"]
        assert len(frequencies) == 4
        assert frequencies["hel"] == 10
        assert frequencies["lo"] == 20
        assert frequencies["world"] == 5
        assert frequencies["test"] == 3

    def test_load_pyphen_corpus_data(self, tmp_path):
        """Test loading Pyphen corpus data successfully."""
        corpus_dir = tmp_path / "pyphen_corpus"
        corpus_dir.mkdir()

        # Create test corpus files
        syllables_content = "py\nphen\nsyl\nla\nble\n"
        frequencies_content = json.dumps({"py": 100, "phen": 50, "syl": 30, "la": 40, "ble": 60})

        (corpus_dir / "pyphen_syllables_unique.txt").write_text(syllables_content)
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(frequencies_content)

        syllables, frequencies = load_corpus_data(corpus_dir)

        assert len(syllables) == 5
        assert syllables == ["py", "phen", "syl", "la", "ble"]
        assert len(frequencies) == 5
        assert frequencies["py"] == 100
        assert frequencies["ble"] == 60

    def test_load_corpus_data_strips_whitespace(self, tmp_path):
        """Test that syllable loading strips whitespace correctly."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        # Create test with various whitespace
        syllables_content = "  hel  \n\nlo\n\n  world  \n\n"
        frequencies_content = json.dumps({"hel": 1, "lo": 2, "world": 3})

        (corpus_dir / "nltk_syllables_unique.txt").write_text(syllables_content)
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(frequencies_content)

        syllables, frequencies = load_corpus_data(corpus_dir)

        # Should have 3 syllables (empty lines filtered)
        assert len(syllables) == 3
        assert syllables == ["hel", "lo", "world"]

    def test_load_corpus_data_invalid_directory(self, tmp_path):
        """Test loading from invalid directory raises ValueError."""
        invalid_dir = tmp_path / "invalid"
        invalid_dir.mkdir()

        with pytest.raises(ValueError, match="Invalid corpus directory"):
            load_corpus_data(invalid_dir)

    def test_load_corpus_data_missing_syllables_file(self, tmp_path):
        """Test loading with missing syllables file raises ValueError (caught by validation)."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        # Only create frequencies file
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        # Validation will catch this before file loading
        with pytest.raises(ValueError, match="Invalid corpus directory"):
            load_corpus_data(corpus_dir)

    def test_load_corpus_data_missing_frequencies_file(self, tmp_path):
        """Test loading with missing frequencies file raises ValueError (caught by validation)."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        # Only create syllables file
        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")

        # Validation will catch this before file loading
        with pytest.raises(ValueError, match="Invalid corpus directory"):
            load_corpus_data(corpus_dir)

    def test_load_corpus_data_invalid_json(self, tmp_path):
        """Test loading with invalid JSON raises JSONDecodeError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text("not valid json {{{")

        with pytest.raises(json.JSONDecodeError):
            load_corpus_data(corpus_dir)

    def test_load_corpus_data_empty_syllables_file(self, tmp_path):
        """Test loading with empty syllables file raises ValueError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        with pytest.raises(ValueError, match="Syllables file is empty"):
            load_corpus_data(corpus_dir)

    def test_load_corpus_data_empty_frequencies_file(self, tmp_path):
        """Test loading with empty frequencies file raises ValueError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text("{}")

        with pytest.raises(ValueError, match="Frequencies file is empty"):
            load_corpus_data(corpus_dir)

    def test_load_corpus_data_missing_frequency_entries(self, tmp_path, capsys):
        """Test loading with missing frequency entries shows warning."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        # Create syllables with some missing frequency data
        syllables_content = "hel\nlo\nworld\nmissing\n"
        frequencies_content = json.dumps({"hel": 10, "lo": 20, "world": 5})

        (corpus_dir / "nltk_syllables_unique.txt").write_text(syllables_content)
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(frequencies_content)

        syllables, frequencies = load_corpus_data(corpus_dir)

        # Should still load successfully
        assert len(syllables) == 4
        assert len(frequencies) == 3

        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "missing frequency data" in captured.out

    def test_load_corpus_data_prefers_nltk_when_both_exist(self, tmp_path):
        """Test that NLTK corpus is loaded when both types exist."""
        corpus_dir = tmp_path / "mixed_corpus"
        corpus_dir.mkdir()

        # Create both NLTK and Pyphen files
        (corpus_dir / "nltk_syllables_unique.txt").write_text("nltk\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"nltk": 100}))
        (corpus_dir / "pyphen_syllables_unique.txt").write_text("pyphen\n")
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(json.dumps({"pyphen": 50}))

        syllables, frequencies = load_corpus_data(corpus_dir)

        # Should load NLTK (preferred)
        assert syllables == ["nltk"]
        assert frequencies == {"nltk": 100}

    def test_load_corpus_data_utf8_encoding(self, tmp_path):
        """Test loading corpus data with UTF-8 characters."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()

        # Create test with UTF-8 characters
        syllables_content = "café\nnaïve\nrésumé\n"
        frequencies_content = json.dumps({"café": 5, "naïve": 3, "résumé": 2})

        (corpus_dir / "nltk_syllables_unique.txt").write_text(syllables_content, encoding="utf-8")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(
            frequencies_content, encoding="utf-8"
        )

        syllables, frequencies = load_corpus_data(corpus_dir)

        assert len(syllables) == 3
        assert "café" in syllables
        assert "naïve" in syllables
        assert "résumé" in syllables
        assert frequencies["café"] == 5


class TestLoadAnnotatedData:
    """Tests for annotated data loading."""

    def test_load_nltk_annotated_data(self, tmp_path):
        """Test loading NLTK annotated data successfully."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        # Create corpus files
        (corpus_dir / "nltk_syllables_unique.txt").write_text("hel\nlo\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(
            json.dumps({"hel": 10, "lo": 20})
        )

        # Create annotated data file
        annotated = [
            {
                "syllable": "hel",
                "frequency": 10,
                "features": {
                    "starts_with_vowel": False,
                    "ends_with_vowel": False,
                    "contains_plosive": False,
                },
            },
            {
                "syllable": "lo",
                "frequency": 20,
                "features": {
                    "starts_with_vowel": False,
                    "ends_with_vowel": True,
                    "contains_plosive": False,
                },
            },
        ]
        (data_dir / "nltk_syllables_annotated.json").write_text(json.dumps(annotated))

        data, metadata = load_annotated_data(corpus_dir)

        assert len(data) == 2
        assert data[0]["syllable"] == "hel"
        assert data[0]["frequency"] == 10
        assert "features" in data[0]
        assert isinstance(data[0]["features"], dict)

        # Verify metadata is returned
        assert metadata["source"] in ("sqlite", "json")
        assert "file_name" in metadata
        assert "load_time_ms" in metadata

    def test_load_pyphen_annotated_data(self, tmp_path):
        """Test loading Pyphen annotated data successfully."""
        corpus_dir = tmp_path / "pyphen_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        # Create corpus files
        (corpus_dir / "pyphen_syllables_unique.txt").write_text("py\nphen\n")
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(
            json.dumps({"py": 100, "phen": 50})
        )

        # Create annotated data file
        annotated = [
            {
                "syllable": "py",
                "frequency": 100,
                "features": {
                    "starts_with_vowel": False,
                    "ends_with_vowel": True,
                },
            },
            {
                "syllable": "phen",
                "frequency": 50,
                "features": {
                    "starts_with_vowel": False,
                    "ends_with_vowel": False,
                },
            },
        ]
        (data_dir / "pyphen_syllables_annotated.json").write_text(json.dumps(annotated))

        data, metadata = load_annotated_data(corpus_dir)

        assert len(data) == 2
        assert data[0]["syllable"] == "py"
        assert data[1]["syllable"] == "phen"

        # Verify metadata
        assert metadata["source"] in ("sqlite", "json")
        assert "file_name" in metadata

    def test_load_annotated_data_invalid_directory(self, tmp_path):
        """Test loading from invalid directory raises ValueError."""
        invalid_dir = tmp_path / "invalid"
        invalid_dir.mkdir()

        with pytest.raises(ValueError, match="Invalid corpus directory"):
            load_annotated_data(invalid_dir)

    def test_load_annotated_data_missing_file(self, tmp_path):
        """Test loading with missing annotated file raises FileNotFoundError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        # Create corpus files but no annotated file
        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        with pytest.raises(FileNotFoundError, match="No annotated data found"):
            load_annotated_data(corpus_dir)

    def test_load_annotated_data_invalid_json(self, tmp_path):
        """Test loading with invalid JSON raises JSONDecodeError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))
        (data_dir / "nltk_syllables_annotated.json").write_text("not valid json {{{")

        with pytest.raises(json.JSONDecodeError):
            load_annotated_data(corpus_dir)

    def test_load_annotated_data_empty_list(self, tmp_path):
        """Test loading with empty JSON list raises ValueError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))
        (data_dir / "nltk_syllables_annotated.json").write_text("[]")

        with pytest.raises(ValueError, match="Annotated data file is empty"):
            load_annotated_data(corpus_dir)

    def test_load_annotated_data_not_list(self, tmp_path):
        """Test loading with non-list JSON raises ValueError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))
        (data_dir / "nltk_syllables_annotated.json").write_text('{"not": "a list"}')

        with pytest.raises(ValueError, match="should be a JSON array"):
            load_annotated_data(corpus_dir)

    def test_load_annotated_data_missing_keys(self, tmp_path):
        """Test loading with missing required keys raises ValueError."""
        corpus_dir = tmp_path / "nltk_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        (corpus_dir / "nltk_syllables_unique.txt").write_text("test\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"test": 1}))

        # Missing 'features' key
        annotated = [{"syllable": "test", "frequency": 1}]
        (data_dir / "nltk_syllables_annotated.json").write_text(json.dumps(annotated))

        with pytest.raises(ValueError, match="missing required keys"):
            load_annotated_data(corpus_dir)

    def test_load_annotated_data_prefers_nltk_when_both_exist(self, tmp_path):
        """Test that NLTK annotated data is loaded when both types exist."""
        corpus_dir = tmp_path / "mixed_corpus"
        corpus_dir.mkdir()
        data_dir = corpus_dir / "data"
        data_dir.mkdir()

        # Create both NLTK and Pyphen corpus files
        (corpus_dir / "nltk_syllables_unique.txt").write_text("nltk\n")
        (corpus_dir / "nltk_syllables_frequencies.json").write_text(json.dumps({"nltk": 100}))
        (corpus_dir / "pyphen_syllables_unique.txt").write_text("pyphen\n")
        (corpus_dir / "pyphen_syllables_frequencies.json").write_text(json.dumps({"pyphen": 50}))

        # Create both annotated files
        nltk_annotated = [
            {"syllable": "nltk", "frequency": 100, "features": {"starts_with_vowel": False}}
        ]
        pyphen_annotated = [
            {"syllable": "pyphen", "frequency": 50, "features": {"starts_with_vowel": False}}
        ]
        (data_dir / "nltk_syllables_annotated.json").write_text(json.dumps(nltk_annotated))
        (data_dir / "pyphen_syllables_annotated.json").write_text(json.dumps(pyphen_annotated))

        data, metadata = load_annotated_data(corpus_dir)

        # Should load NLTK (preferred)
        assert len(data) == 1
        assert data[0]["syllable"] == "nltk"
        assert metadata["source"] in ("sqlite", "json")
