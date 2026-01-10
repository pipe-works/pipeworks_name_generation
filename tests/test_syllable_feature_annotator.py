"""
Comprehensive test suite for syllable feature annotator.

This test module covers all components of the syllable_feature_annotator build tool:
- Phoneme sets and character classes
- Individual feature detector functions
- Core annotation logic
- File I/O operations
- CLI argument parsing
- End-to-end integration
- Determinism and reproducibility

Test Organization
-----------------
1. TestPhonemeSets: Character class membership tests
2. TestOnsetFeatures: Syllable-initial pattern detection
3. TestInternalFeatures: Manner of articulation detection
4. TestNucleusFeatures: Vowel structure detection
5. TestCodaFeatures: Syllable-final pattern detection
6. TestFeatureDetectorRegistry: Feature registry completeness
7. TestAnnotationLogic: Core annotation functions
8. TestFileIO: Loading and saving data
9. TestCLI: Argument parsing and error handling
10. TestIntegration: End-to-end pipeline tests
11. TestDeterminism: Reproducibility verification

Running Tests
-------------
Run all tests::

    $ pytest tests/test_syllable_feature_annotator.py -v

Run specific test class::

    $ pytest tests/test_syllable_feature_annotator.py::TestOnsetFeatures -v

Run with coverage::

    $ pytest tests/test_syllable_feature_annotator.py --cov=build_tools.syllable_feature_annotator
"""

import json
from pathlib import Path

import pytest

from build_tools.syllable_feature_annotator import (
    FEATURE_DETECTORS,
    FRICATIVES,
    LIQUIDS,
    NASALS,
    PLOSIVES,
    STOPS,
    VOWELS,
    AnnotatedSyllable,
    AnnotationResult,
    annotate_corpus,
    annotate_syllable,
    contains_fricative,
    contains_liquid,
    contains_nasal,
    contains_plosive,
    ends_with_nasal,
    ends_with_stop,
    ends_with_vowel,
    load_frequencies,
    load_syllables,
    long_vowel,
    run_annotation_pipeline,
    save_annotated_syllables,
    short_vowel,
    starts_with_cluster,
    starts_with_heavy_cluster,
    starts_with_vowel,
)
from build_tools.syllable_feature_annotator.cli import (
    compute_output_path,
    detect_extractor_type,
    main,
    parse_arguments,
)

# =========================================================================
# Test Phoneme Sets
# =========================================================================


class TestPhonemeSets:
    """Test character class definitions and membership."""

    def test_vowel_set_membership(self):
        """Test that vowels are correctly defined."""
        assert "a" in VOWELS
        assert "e" in VOWELS
        assert "i" in VOWELS
        assert "o" in VOWELS
        assert "u" in VOWELS
        assert "b" not in VOWELS
        assert "x" not in VOWELS

    def test_plosive_set_membership(self):
        """Test that plosives are correctly defined."""
        assert "p" in PLOSIVES
        assert "t" in PLOSIVES
        assert "k" in PLOSIVES
        assert "b" in PLOSIVES
        assert "d" in PLOSIVES
        assert "g" in PLOSIVES
        assert "f" not in PLOSIVES
        assert "a" not in PLOSIVES

    def test_fricative_set_membership(self):
        """Test that fricatives are correctly defined."""
        assert "f" in FRICATIVES
        assert "s" in FRICATIVES
        assert "z" in FRICATIVES
        assert "v" in FRICATIVES
        assert "h" in FRICATIVES
        assert "p" not in FRICATIVES

    def test_nasal_set_membership(self):
        """Test that nasals are correctly defined."""
        assert "m" in NASALS
        assert "n" in NASALS
        assert "p" not in NASALS

    def test_liquid_set_membership(self):
        """Test that liquids are correctly defined."""
        assert "l" in LIQUIDS
        assert "r" in LIQUIDS
        assert "w" in LIQUIDS
        assert "m" not in LIQUIDS

    def test_stops_includes_plosives(self):
        """Test that STOPS includes all PLOSIVES."""
        assert PLOSIVES.issubset(STOPS)

    def test_stops_includes_q(self):
        """Test that STOPS includes 'q' for terminal closure."""
        assert "q" in STOPS
        assert "q" not in PLOSIVES  # But not in PLOSIVES


# =========================================================================
# Test Onset Features
# =========================================================================


class TestOnsetFeatures:
    """Test syllable-initial pattern detection."""

    def test_starts_with_vowel_positive_cases(self):
        """Test vowel-initial syllables."""
        assert starts_with_vowel("apple") is True
        assert starts_with_vowel("egg") is True
        assert starts_with_vowel("ink") is True
        assert starts_with_vowel("orange") is True
        assert starts_with_vowel("umbrella") is True
        assert starts_with_vowel("a") is True

    def test_starts_with_vowel_negative_cases(self):
        """Test consonant-initial syllables."""
        assert starts_with_vowel("bat") is False
        assert starts_with_vowel("cat") is False
        assert starts_with_vowel("kran") is False

    def test_starts_with_vowel_edge_cases(self):
        """Test edge cases for vowel onset detection."""
        assert starts_with_vowel("") is False  # Empty string

    def test_starts_with_cluster_positive_cases(self):
        """Test consonant cluster detection."""
        assert starts_with_cluster("kran") is True
        assert starts_with_cluster("train") is True
        assert starts_with_cluster("stop") is True
        assert starts_with_cluster("black") is True
        assert starts_with_cluster("tr") is True

    def test_starts_with_cluster_negative_cases(self):
        """Test non-cluster onsets."""
        assert starts_with_cluster("na") is False
        assert starts_with_cluster("apple") is False
        assert starts_with_cluster("bat") is False
        assert starts_with_cluster("a") is False

    def test_starts_with_cluster_edge_cases(self):
        """Test edge cases for cluster detection."""
        assert starts_with_cluster("") is False  # Empty string
        assert starts_with_cluster("k") is False  # Too short

    def test_starts_with_heavy_cluster_positive_cases(self):
        """Test heavy cluster (3+ consonants) detection."""
        assert starts_with_heavy_cluster("spla") is True
        assert starts_with_heavy_cluster("stra") is True
        assert starts_with_heavy_cluster("scr") is True

    def test_starts_with_heavy_cluster_negative_cases(self):
        """Test non-heavy clusters."""
        assert starts_with_heavy_cluster("kran") is False  # Only 2 consonants
        assert starts_with_heavy_cluster("na") is False
        assert starts_with_heavy_cluster("apple") is False

    def test_starts_with_heavy_cluster_edge_cases(self):
        """Test edge cases for heavy cluster detection."""
        assert starts_with_heavy_cluster("") is False
        assert starts_with_heavy_cluster("st") is False  # Too short


# =========================================================================
# Test Internal Features
# =========================================================================


class TestInternalFeatures:
    """Test manner of articulation detection."""

    def test_contains_plosive_positive_cases(self):
        """Test syllables containing plosives."""
        assert contains_plosive("takt") is True
        assert contains_plosive("pat") is True
        assert contains_plosive("kran") is True
        assert contains_plosive("bug") is True

    def test_contains_plosive_negative_cases(self):
        """Test syllables without plosives."""
        assert contains_plosive("sal") is False
        assert contains_plosive("fish") is False
        assert contains_plosive("mom") is False

    def test_contains_plosive_edge_cases(self):
        """Test edge cases for plosive detection."""
        assert contains_plosive("") is False

    def test_contains_fricative_positive_cases(self):
        """Test syllables containing fricatives."""
        assert contains_fricative("fish") is True
        assert contains_fricative("zone") is True
        assert contains_fricative("have") is True

    def test_contains_fricative_negative_cases(self):
        """Test syllables without fricatives."""
        assert contains_fricative("bat") is False
        assert contains_fricative("kran") is False
        assert contains_fricative("mom") is False

    def test_contains_fricative_edge_cases(self):
        """Test edge cases for fricative detection."""
        assert contains_fricative("") is False

    def test_contains_liquid_positive_cases(self):
        """Test syllables containing liquids."""
        assert contains_liquid("kran") is True
        assert contains_liquid("slow") is True
        assert contains_liquid("wall") is True

    def test_contains_liquid_negative_cases(self):
        """Test syllables without liquids."""
        assert contains_liquid("bat") is False
        assert contains_liquid("fish") is False
        assert contains_liquid("mom") is False

    def test_contains_liquid_edge_cases(self):
        """Test edge cases for liquid detection."""
        assert contains_liquid("") is False

    def test_contains_nasal_positive_cases(self):
        """Test syllables containing nasals."""
        assert contains_nasal("kran") is True
        assert contains_nasal("man") is True
        assert contains_nasal("mom") is True

    def test_contains_nasal_negative_cases(self):
        """Test syllables without nasals."""
        assert contains_nasal("bat") is False
        assert contains_nasal("fish") is False
        assert contains_nasal("slow") is False

    def test_contains_nasal_edge_cases(self):
        """Test edge cases for nasal detection."""
        assert contains_nasal("") is False


# =========================================================================
# Test Nucleus Features
# =========================================================================


class TestNucleusFeatures:
    """Test vowel structure detection (length proxies)."""

    def test_short_vowel_positive_cases(self):
        """Test syllables with exactly one vowel."""
        assert short_vowel("bat") is True
        assert short_vowel("kran") is True
        assert short_vowel("stop") is True
        assert short_vowel("a") is True

    def test_short_vowel_negative_cases(self):
        """Test syllables without exactly one vowel."""
        assert short_vowel("beat") is False  # Two vowels (ea)
        assert short_vowel("aura") is False  # Three vowels
        assert short_vowel("") is False  # No vowels

    def test_long_vowel_positive_cases(self):
        """Test syllables with two or more vowels."""
        assert long_vowel("beat") is True  # 'ea' = 2 vowels
        assert long_vowel("aura") is True  # 'au' + 'a' = 3 vowels
        assert long_vowel("ae") is True
        assert long_vowel("eau") is True

    def test_long_vowel_negative_cases(self):
        """Test syllables without multiple vowels."""
        assert long_vowel("bat") is False  # Only 1 vowel
        assert long_vowel("kran") is False
        assert long_vowel("") is False  # No vowels

    def test_short_and_long_mutually_exclusive(self):
        """Test that short_vowel and long_vowel are mutually exclusive."""
        test_cases = ["bat", "beat", "kran", "aura", "a", "ae", ""]
        for syllable in test_cases:
            # A syllable can't be both short and long
            assert not (short_vowel(syllable) and long_vowel(syllable))


# =========================================================================
# Test Coda Features
# =========================================================================


class TestCodaFeatures:
    """Test syllable-final pattern detection."""

    def test_ends_with_vowel_positive_cases(self):
        """Test vowel-final (open) syllables."""
        assert ends_with_vowel("na") is True
        assert ends_with_vowel("hello") is True
        assert ends_with_vowel("tuna") is True
        assert ends_with_vowel("a") is True

    def test_ends_with_vowel_negative_cases(self):
        """Test consonant-final (closed) syllables."""
        assert ends_with_vowel("bat") is False
        assert ends_with_vowel("turn") is False
        assert ends_with_vowel("kran") is False

    def test_ends_with_vowel_edge_cases(self):
        """Test edge cases for vowel coda detection."""
        assert ends_with_vowel("") is False

    def test_ends_with_nasal_positive_cases(self):
        """Test syllables ending with nasals."""
        assert ends_with_nasal("turn") is True
        assert ends_with_nasal("man") is True
        assert ends_with_nasal("mom") is True
        assert ends_with_nasal("kran") is True

    def test_ends_with_nasal_negative_cases(self):
        """Test syllables not ending with nasals."""
        assert ends_with_nasal("bat") is False
        assert ends_with_nasal("fish") is False
        assert ends_with_nasal("na") is False

    def test_ends_with_nasal_edge_cases(self):
        """Test edge cases for nasal coda detection."""
        assert ends_with_nasal("") is False

    def test_ends_with_stop_positive_cases(self):
        """Test syllables ending with stops."""
        assert ends_with_stop("takt") is True
        assert ends_with_stop("bat") is True
        assert ends_with_stop("sick") is True

    def test_ends_with_stop_negative_cases(self):
        """Test syllables not ending with stops."""
        assert ends_with_stop("man") is False  # Ends with nasal
        assert ends_with_stop("fish") is False  # Ends with fricative
        assert ends_with_stop("na") is False  # Ends with vowel

    def test_ends_with_stop_edge_cases(self):
        """Test edge cases for stop coda detection."""
        assert ends_with_stop("") is False


# =========================================================================
# Test Feature Detector Registry
# =========================================================================


class TestFeatureDetectorRegistry:
    """Test the feature detector registry completeness."""

    def test_registry_has_all_features(self):
        """Test that registry contains all 12 features."""
        expected_features = {
            # Onset (3)
            "starts_with_vowel",
            "starts_with_cluster",
            "starts_with_heavy_cluster",
            # Internal (4)
            "contains_plosive",
            "contains_fricative",
            "contains_liquid",
            "contains_nasal",
            # Nucleus (2)
            "short_vowel",
            "long_vowel",
            # Coda (3)
            "ends_with_vowel",
            "ends_with_nasal",
            "ends_with_stop",
        }
        assert set(FEATURE_DETECTORS.keys()) == expected_features

    def test_registry_count(self):
        """Test that registry has exactly 12 features."""
        assert len(FEATURE_DETECTORS) == 12

    def test_all_detectors_are_callable(self):
        """Test that all registry values are callable functions."""
        for name, detector in FEATURE_DETECTORS.items():
            assert callable(detector), f"{name} is not callable"

    def test_all_detectors_return_bool(self):
        """Test that all detectors return boolean values."""
        test_syllable = "kran"
        for name, detector in FEATURE_DETECTORS.items():
            result = detector(test_syllable)
            assert isinstance(result, bool), f"{name} returned {type(result)}, not bool"


# =========================================================================
# Test Annotation Logic
# =========================================================================


class TestAnnotationLogic:
    """Test core annotation functions."""

    def test_annotate_syllable_basic(self):
        """Test basic syllable annotation."""
        record = annotate_syllable("kran", 7, FEATURE_DETECTORS)
        assert record.syllable == "kran"
        assert record.frequency == 7
        assert isinstance(record.features, dict)
        assert len(record.features) == 12

    def test_annotate_syllable_feature_values(self):
        """Test that annotated features have correct values."""
        record = annotate_syllable("kran", 7, FEATURE_DETECTORS)
        # Check expected feature values for "kran"
        assert record.features["starts_with_cluster"] is True
        assert record.features["contains_plosive"] is True
        assert record.features["contains_liquid"] is True
        assert record.features["contains_nasal"] is True
        assert record.features["short_vowel"] is True
        assert record.features["ends_with_nasal"] is True

    def test_annotate_syllable_all_false(self):
        """Test syllable with mostly false features."""
        record = annotate_syllable("a", 1, FEATURE_DETECTORS)
        assert record.features["starts_with_vowel"] is True
        assert record.features["short_vowel"] is True
        assert record.features["ends_with_vowel"] is True
        # Most other features should be False
        assert record.features["starts_with_cluster"] is False
        assert record.features["contains_plosive"] is False

    def test_annotate_corpus_basic(self):
        """Test basic corpus annotation."""
        syllables = ["ka", "kran", "spla"]
        frequencies = {"ka": 187, "kran": 7, "spla": 2}
        result = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)

        assert isinstance(result, AnnotationResult)
        assert len(result.annotated_syllables) == 3
        assert result.statistics.syllable_count == 3
        assert result.statistics.feature_count == 12

    def test_annotate_corpus_preserves_order(self):
        """Test that corpus annotation preserves syllable order."""
        syllables = ["ka", "kran", "spla"]
        frequencies = {"ka": 187, "kran": 7, "spla": 2}
        result = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)

        assert result.annotated_syllables[0].syllable == "ka"
        assert result.annotated_syllables[1].syllable == "kran"
        assert result.annotated_syllables[2].syllable == "spla"

    def test_annotate_corpus_missing_frequency(self):
        """Test that missing frequencies default to 1."""
        syllables = ["xyz"]
        frequencies: dict[str, int] = {}  # Empty
        result = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)

        assert result.annotated_syllables[0].frequency == 1

    def test_annotate_corpus_statistics(self):
        """Test that statistics are calculated correctly."""
        syllables = ["ka", "kran", "spla"]
        frequencies = {"ka": 187, "kran": 7, "spla": 2}
        result = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)

        stats = result.statistics
        assert stats.syllable_count == 3
        assert stats.feature_count == 12
        assert stats.total_frequency == 196  # 187 + 7 + 2
        assert stats.processing_time > 0  # Should take some time

    def test_annotated_syllable_dataclass(self):
        """Test AnnotatedSyllable dataclass structure."""
        record = AnnotatedSyllable(syllable="test", frequency=5, features={"feature1": True})
        assert record.syllable == "test"
        assert record.frequency == 5
        assert record.features == {"feature1": True}


# =========================================================================
# Test File I/O
# =========================================================================


class TestFileIO:
    """Test file loading and saving operations."""

    def test_load_syllables_basic(self, tmp_path):
        """Test loading syllables from text file."""
        # Create test file
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("ka\nkran\nspla\n")

        # Load syllables
        syllables = load_syllables(syllables_file)
        assert syllables == ["ka", "kran", "spla"]

    def test_load_syllables_filters_empty_lines(self, tmp_path):
        """Test that empty lines are filtered out."""
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("ka\n\nkran\n\nspla\n")

        syllables = load_syllables(syllables_file)
        assert syllables == ["ka", "kran", "spla"]

    def test_load_syllables_strips_whitespace(self, tmp_path):
        """Test that whitespace is stripped from lines."""
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("  ka  \n  kran  \n  spla  \n")

        syllables = load_syllables(syllables_file)
        assert syllables == ["ka", "kran", "spla"]

    def test_load_syllables_missing_file(self, tmp_path):
        """Test error handling for missing file."""
        missing_file = tmp_path / "nonexistent.txt"
        with pytest.raises(FileNotFoundError):
            load_syllables(missing_file)

    def test_load_frequencies_basic(self, tmp_path):
        """Test loading frequencies from JSON file."""
        # Create test file
        frequencies_file = tmp_path / "frequencies.json"
        frequencies_file.write_text('{"ka": 187, "kran": 7, "spla": 2}')

        # Load frequencies
        frequencies = load_frequencies(frequencies_file)
        assert frequencies == {"ka": 187, "kran": 7, "spla": 2}

    def test_load_frequencies_missing_file(self, tmp_path):
        """Test error handling for missing frequencies file."""
        missing_file = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_frequencies(missing_file)

    def test_save_annotated_syllables_basic(self, tmp_path):
        """Test saving annotated syllables to JSON."""
        output_file = tmp_path / "annotated.json"
        annotated = [
            {
                "syllable": "ka",
                "frequency": 187,
                "features": {"starts_with_vowel": False, "short_vowel": True},
            }
        ]

        save_annotated_syllables(annotated, output_file)

        # Verify file was created and contains valid JSON
        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert loaded == annotated

    def test_save_annotated_syllables_creates_directory(self, tmp_path):
        """Test that parent directories are created automatically."""
        output_file = tmp_path / "subdir" / "nested" / "annotated.json"
        annotated = [{"syllable": "ka", "frequency": 1, "features": {}}]

        save_annotated_syllables(annotated, output_file)

        assert output_file.exists()
        assert output_file.parent.exists()


# =========================================================================
# Test CLI
# =========================================================================


class TestCLI:
    """Test command-line interface."""

    def test_parse_arguments_defaults(self):
        """Test default argument values."""
        args = parse_arguments([])
        assert args.syllables == Path("data/normalized/syllables_unique.txt")
        assert args.frequencies == Path("data/normalized/syllables_frequencies.json")
        assert args.output is None  # Changed: now defaults to None for auto-detection
        assert args.verbose is False

    def test_parse_arguments_custom_paths(self):
        """Test parsing custom path arguments."""
        args = parse_arguments(
            [
                "--syllables",
                "custom/syllables.txt",
                "--frequencies",
                "custom/frequencies.json",
                "--output",
                "output/annotated.json",
            ]
        )
        assert args.syllables == Path("custom/syllables.txt")
        assert args.frequencies == Path("custom/frequencies.json")
        assert args.output == Path("output/annotated.json")

    def test_parse_arguments_verbose_flag(self):
        """Test verbose flag parsing."""
        args = parse_arguments(["--verbose"])
        assert args.verbose is True

    def test_parse_arguments_verbose_short_flag(self):
        """Test verbose short flag (-v)."""
        args = parse_arguments(["-v"])
        assert args.verbose is True

    def test_main_missing_input_file(self, tmp_path):
        """Test main function with missing input file."""
        missing_file = tmp_path / "missing.txt"
        exit_code = main(["--syllables", str(missing_file)])
        assert exit_code == 1  # Error exit code

    def test_main_success(self, tmp_path):
        """Test successful main execution."""
        # Create test input files
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("ka\nkran\n")

        frequencies_file = tmp_path / "frequencies.json"
        frequencies_file.write_text('{"ka": 187, "kran": 7}')

        output_file = tmp_path / "output.json"

        # Run main
        exit_code = main(
            [
                "--syllables",
                str(syllables_file),
                "--frequencies",
                str(frequencies_file),
                "--output",
                str(output_file),
            ]
        )

        assert exit_code == 0  # Success
        assert output_file.exists()


# =========================================================================
# Test Path Detection
# =========================================================================


class TestPathDetection:
    """Test automatic path detection for output files."""

    def test_detect_extractor_type_from_filename_pyphen(self):
        """Test detecting pyphen from filename prefix."""
        path = Path("_working/output/20260110_115453_pyphen/pyphen_syllables_unique.txt")
        assert detect_extractor_type(path) == "pyphen"

    def test_detect_extractor_type_from_filename_nltk(self):
        """Test detecting NLTK from filename prefix."""
        path = Path("_working/output/20260110_115601_nltk/nltk_syllables_unique.txt")
        assert detect_extractor_type(path) == "nltk"

    def test_detect_extractor_type_from_directory_pyphen(self):
        """Test detecting pyphen from directory name."""
        path = Path("_working/output/20260110_115453_pyphen/syllables_unique.txt")
        assert detect_extractor_type(path) == "pyphen"

    def test_detect_extractor_type_from_directory_nltk(self):
        """Test detecting NLTK from directory name."""
        path = Path("_working/output/20260110_115601_nltk/syllables_unique.txt")
        assert detect_extractor_type(path) == "nltk"

    def test_detect_extractor_type_no_match(self):
        """Test that non-normalizer paths return None."""
        path = Path("data/custom/syllables.txt")
        assert detect_extractor_type(path) is None

    def test_detect_extractor_type_no_match_similar_name(self):
        """Test that similar but incorrect names return None."""
        path = Path("data/pyphenated/syllables.txt")  # Contains "pyphen" but not "_pyphen"
        assert detect_extractor_type(path) is None

    def test_compute_output_path_pyphen(self):
        """Test computing output path for pyphen extractor."""
        syllables_path = Path("_working/output/20260110_115453_pyphen/pyphen_syllables_unique.txt")
        expected = Path(
            "_working/output/20260110_115453_pyphen/data/pyphen_syllables_annotated.json"
        )
        assert compute_output_path(syllables_path, "pyphen") == expected

    def test_compute_output_path_nltk(self):
        """Test computing output path for NLTK extractor."""
        syllables_path = Path("_working/output/20260110_115601_nltk/nltk_syllables_unique.txt")
        expected = Path("_working/output/20260110_115601_nltk/data/nltk_syllables_annotated.json")
        assert compute_output_path(syllables_path, "nltk") == expected

    def test_compute_output_path_different_filename(self):
        """Test that output path is computed from parent directory."""
        syllables_path = Path(
            "_working/output/20260110_115601_nltk/nltk_syllables_canonicalised.txt"
        )
        expected = Path("_working/output/20260110_115601_nltk/data/nltk_syllables_annotated.json")
        assert compute_output_path(syllables_path, "nltk") == expected

    def test_main_auto_detect_output_path_pyphen(self, tmp_path):
        """Test that main() auto-detects output path for pyphen files."""
        # Create test directory structure mimicking pyphen normalizer output
        run_dir = tmp_path / "20260110_115453_pyphen"
        run_dir.mkdir()

        # Create input files
        syllables_file = run_dir / "pyphen_syllables_unique.txt"
        syllables_file.write_text("ka\nkran\n")

        frequencies_file = run_dir / "pyphen_syllables_frequencies.json"
        frequencies_file.write_text('{"ka": 187, "kran": 7}')

        # Run main WITHOUT specifying --output
        exit_code = main(
            [
                "--syllables",
                str(syllables_file),
                "--frequencies",
                str(frequencies_file),
            ]
        )

        # Check that output was created in auto-detected location
        expected_output = run_dir / "data" / "pyphen_syllables_annotated.json"
        assert exit_code == 0
        assert expected_output.exists()

    def test_main_auto_detect_output_path_nltk(self, tmp_path):
        """Test that main() auto-detects output path for NLTK files."""
        # Create test directory structure mimicking NLTK normalizer output
        run_dir = tmp_path / "20260110_115601_nltk"
        run_dir.mkdir()

        # Create input files
        syllables_file = run_dir / "nltk_syllables_unique.txt"
        syllables_file.write_text("ka\nkran\n")

        frequencies_file = run_dir / "nltk_syllables_frequencies.json"
        frequencies_file.write_text('{"ka": 187, "kran": 7}')

        # Run main WITHOUT specifying --output
        exit_code = main(
            [
                "--syllables",
                str(syllables_file),
                "--frequencies",
                str(frequencies_file),
            ]
        )

        # Check that output was created in auto-detected location
        expected_output = run_dir / "data" / "nltk_syllables_annotated.json"
        assert exit_code == 0
        assert expected_output.exists()

    def test_main_explicit_output_overrides_auto_detection(self, tmp_path):
        """Test that explicit --output overrides auto-detection."""
        # Create test directory structure
        run_dir = tmp_path / "20260110_115601_nltk"
        run_dir.mkdir()

        # Create input files
        syllables_file = run_dir / "nltk_syllables_unique.txt"
        syllables_file.write_text("ka\n")

        frequencies_file = run_dir / "nltk_syllables_frequencies.json"
        frequencies_file.write_text('{"ka": 187}')

        # Specify explicit output path
        explicit_output = tmp_path / "custom" / "output.json"

        # Run main WITH explicit --output
        exit_code = main(
            [
                "--syllables",
                str(syllables_file),
                "--frequencies",
                str(frequencies_file),
                "--output",
                str(explicit_output),
            ]
        )

        # Check that output was created in explicit location, NOT auto-detected
        assert exit_code == 0
        assert explicit_output.exists()
        auto_detected = run_dir / "data" / "nltk_syllables_annotated.json"
        assert not auto_detected.exists()


# =========================================================================
# Test Integration
# =========================================================================


class TestIntegration:
    """Test end-to-end pipeline integration."""

    def test_full_pipeline_execution(self, tmp_path):
        """Test complete annotation pipeline from files to output."""
        # Create input files
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("ka\nkran\nspla\n")

        frequencies_file = tmp_path / "frequencies.json"
        frequencies_file.write_text('{"ka": 187, "kran": 7, "spla": 2}')

        output_file = tmp_path / "annotated.json"

        # Run pipeline
        result = run_annotation_pipeline(
            syllables_path=syllables_file,
            frequencies_path=frequencies_file,
            output_path=output_file,
            verbose=False,
        )

        # Verify result
        assert result.statistics.syllable_count == 3
        assert result.statistics.feature_count == 12
        assert len(result.annotated_syllables) == 3

        # Verify output file
        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert len(loaded) == 3
        assert loaded[0]["syllable"] == "ka"
        assert "features" in loaded[0]
        assert len(loaded[0]["features"]) == 12

    def test_pipeline_output_format(self, tmp_path):
        """Test that pipeline output matches expected JSON format."""
        # Create input files
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("kran\n")

        frequencies_file = tmp_path / "frequencies.json"
        frequencies_file.write_text('{"kran": 7}')

        output_file = tmp_path / "annotated.json"

        # Run pipeline
        run_annotation_pipeline(
            syllables_path=syllables_file,
            frequencies_path=frequencies_file,
            output_path=output_file,
        )

        # Load and verify output format
        loaded = json.loads(output_file.read_text())
        record = loaded[0]

        # Check structure
        assert "syllable" in record
        assert "frequency" in record
        assert "features" in record

        # Check values
        assert record["syllable"] == "kran"
        assert record["frequency"] == 7
        assert isinstance(record["features"], dict)

        # Check specific features for "kran"
        assert record["features"]["starts_with_cluster"] is True
        assert record["features"]["contains_plosive"] is True
        assert record["features"]["contains_liquid"] is True
        assert record["features"]["contains_nasal"] is True
        assert record["features"]["short_vowel"] is True
        assert record["features"]["ends_with_nasal"] is True

    def test_pipeline_verbose_mode(self, tmp_path, capsys):
        """Test that verbose mode produces output."""
        # Create input files
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("ka\n")

        frequencies_file = tmp_path / "frequencies.json"
        frequencies_file.write_text('{"ka": 187}')

        output_file = tmp_path / "annotated.json"

        # Run with verbose=True
        run_annotation_pipeline(
            syllables_path=syllables_file,
            frequencies_path=frequencies_file,
            output_path=output_file,
            verbose=True,
        )

        # Check that something was printed
        captured = capsys.readouterr()
        assert "Loading syllables" in captured.out
        assert "Annotating" in captured.out
        assert "Saving" in captured.out
        assert "complete" in captured.out


# =========================================================================
# Test Determinism
# =========================================================================


class TestDeterminism:
    """Test that annotation is deterministic and reproducible."""

    def test_single_syllable_determinism(self):
        """Test that annotating the same syllable twice produces same result."""
        record1 = annotate_syllable("kran", 7, FEATURE_DETECTORS)
        record2 = annotate_syllable("kran", 7, FEATURE_DETECTORS)

        assert record1.syllable == record2.syllable
        assert record1.frequency == record2.frequency
        assert record1.features == record2.features

    def test_corpus_annotation_determinism(self):
        """Test that annotating corpus twice produces same results."""
        syllables = ["ka", "kran", "spla", "turn", "au"]
        frequencies = {"ka": 187, "kran": 7, "spla": 2, "turn": 5, "au": 12}

        result1 = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)
        result2 = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)

        # Compare syllable records
        assert len(result1.annotated_syllables) == len(result2.annotated_syllables)
        for rec1, rec2 in zip(result1.annotated_syllables, result2.annotated_syllables):
            assert rec1.syllable == rec2.syllable
            assert rec1.frequency == rec2.frequency
            assert rec1.features == rec2.features

    def test_pipeline_determinism(self, tmp_path):
        """Test that full pipeline produces identical output on repeated runs."""
        # Create input files
        syllables_file = tmp_path / "syllables.txt"
        syllables_file.write_text("ka\nkran\nspla\n")

        frequencies_file = tmp_path / "frequencies.json"
        frequencies_file.write_text('{"ka": 187, "kran": 7, "spla": 2}')

        output_file1 = tmp_path / "output1.json"
        output_file2 = tmp_path / "output2.json"

        # Run pipeline twice
        run_annotation_pipeline(syllables_file, frequencies_file, output_file1)
        run_annotation_pipeline(syllables_file, frequencies_file, output_file2)

        # Compare outputs
        output1 = json.loads(output_file1.read_text())
        output2 = json.loads(output_file2.read_text())

        assert output1 == output2

    def test_feature_independence(self):
        """Test that features are truly independent (order doesn't matter)."""
        syllable = "kran"

        # Apply features in different orders (shouldn't matter with dict)
        features1 = {name: detector(syllable) for name, detector in FEATURE_DETECTORS.items()}

        # Create reversed dict (Python 3.7+ maintains insertion order)
        reversed_detectors = dict(reversed(list(FEATURE_DETECTORS.items())))
        features2 = {name: detector(syllable) for name, detector in reversed_detectors.items()}

        # Features should be identical regardless of application order
        assert features1 == features2


# =========================================================================
# Test Real-World Example Syllables
# =========================================================================


class TestRealWorldExamples:
    """Test annotation with real-world example syllables from spec."""

    def test_example_syllable_na(self):
        """Test annotation of 'na' (simple CV syllable)."""
        record = annotate_syllable("na", 1, FEATURE_DETECTORS)
        assert record.features["starts_with_cluster"] is False
        assert record.features["short_vowel"] is True
        assert record.features["ends_with_vowel"] is True  # Ends with 'a' (vowel)

    def test_example_syllable_turn(self):
        """Test annotation of 'turn' (nasal coda - note: 'turn' = t-u-r-n, no initial cluster)."""
        record = annotate_syllable("turn", 1, FEATURE_DETECTORS)
        # 'turn' starts with 't' then 'u' (vowel), so NO cluster
        assert record.features["starts_with_cluster"] is False
        # But it does end with nasal 'n'
        assert record.features["ends_with_nasal"] is True

    def test_example_syllable_spla(self):
        """Test annotation of 'spla' (heavy cluster)."""
        record = annotate_syllable("spla", 1, FEATURE_DETECTORS)
        assert record.features["starts_with_heavy_cluster"] is True

    def test_example_syllable_au(self):
        """Test annotation of 'au' (vowel-initial, diphthong)."""
        record = annotate_syllable("au", 1, FEATURE_DETECTORS)
        assert record.features["starts_with_vowel"] is True
        assert record.features["long_vowel"] is True

    def test_example_syllable_takt(self):
        """Test annotation of 'takt' (plosives + stop coda)."""
        record = annotate_syllable("takt", 1, FEATURE_DETECTORS)
        assert record.features["contains_plosive"] is True
        assert record.features["ends_with_stop"] is True
