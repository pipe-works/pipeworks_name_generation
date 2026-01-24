"""Tests for feature signature analysis tool.

This test suite validates the feature signature analysis functionality,
ensuring correct extraction, counting, formatting, and reporting of
feature combinations in the annotated syllable corpus.
"""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from build_tools.syllable_analysis.feature_signatures import (
    analyze_feature_signatures,
    extract_signature,
    format_signature_report,
    run_analysis,
    save_report,
)


class TestSignatureExtraction:
    """Tests for extract_signature() function."""

    def test_extract_signature_with_all_false(self):
        """Empty signature when all features are False."""
        features = {"starts_with_vowel": False, "ends_with_vowel": False, "contains_plosive": False}
        assert extract_signature(features) == ()

    def test_extract_signature_with_single_feature(self):
        """Single feature creates single-element tuple."""
        features = {"starts_with_vowel": True, "ends_with_vowel": False, "contains_plosive": False}
        assert extract_signature(features) == ("starts_with_vowel",)

    def test_extract_signature_with_multiple_features(self):
        """Multiple features are sorted alphabetically."""
        features = {"ends_with_vowel": True, "starts_with_vowel": True, "contains_plosive": False}
        # Should be alphabetically sorted
        assert extract_signature(features) == ("ends_with_vowel", "starts_with_vowel")

    def test_extract_signature_is_deterministic(self):
        """Same input always produces same output."""
        features = {"contains_liquid": True, "contains_plosive": True, "starts_with_cluster": True}
        sig1 = extract_signature(features)
        sig2 = extract_signature(features)
        assert sig1 == sig2

    def test_extract_signature_sorts_consistently(self):
        """Dictionary order doesn't affect signature order."""
        # Create same features in different dictionary orders
        features1 = {"z_feature": True, "a_feature": True, "m_feature": True}
        features2 = {"a_feature": True, "m_feature": True, "z_feature": True}

        sig1 = extract_signature(features1)
        sig2 = extract_signature(features2)

        assert sig1 == sig2
        assert sig1 == ("a_feature", "m_feature", "z_feature")

    def test_extract_signature_with_empty_dict(self):
        """Empty feature dict produces empty signature."""
        assert extract_signature({}) == ()

    def test_extract_signature_ignores_false_values(self):
        """Only True values are included in signature."""
        features = {"feature_a": True, "feature_b": False, "feature_c": True, "feature_d": False}
        assert extract_signature(features) == ("feature_a", "feature_c")


class TestSignatureAnalysis:
    """Tests for analyze_feature_signatures() function."""

    def test_analyze_empty_records(self):
        """Empty records list produces empty counter."""
        assert analyze_feature_signatures([]) == Counter()

    def test_analyze_single_record(self):
        """Single record produces counter with one entry."""
        records = [
            {"syllable": "ka", "features": {"starts_with_vowel": False, "ends_with_vowel": True}}
        ]
        counter = analyze_feature_signatures(records)
        assert counter[("ends_with_vowel",)] == 1
        assert len(counter) == 1

    def test_analyze_identical_signatures(self):
        """Identical signatures are counted together."""
        records = [
            {"syllable": "ka", "features": {"ends_with_vowel": True}},
            {"syllable": "ra", "features": {"ends_with_vowel": True}},
            {"syllable": "ma", "features": {"ends_with_vowel": True}},
        ]
        counter = analyze_feature_signatures(records)
        assert counter[("ends_with_vowel",)] == 3
        assert len(counter) == 1

    def test_analyze_different_signatures(self):
        """Different signatures are counted separately."""
        records = [
            {"syllable": "a", "features": {"starts_with_vowel": True}},
            {"syllable": "ka", "features": {"ends_with_vowel": True}},
            {"syllable": "an", "features": {"starts_with_vowel": True, "ends_with_nasal": True}},
        ]
        counter = analyze_feature_signatures(records)
        assert counter[("starts_with_vowel",)] == 1
        assert counter[("ends_with_vowel",)] == 1
        assert counter[("ends_with_nasal", "starts_with_vowel")] == 1
        assert len(counter) == 3

    def test_analyze_with_empty_signatures(self):
        """Empty signatures (no active features) are counted."""
        records = [
            {"syllable": "x", "features": {"feature_a": False, "feature_b": False}},
            {"syllable": "y", "features": {"feature_a": False, "feature_b": False}},
        ]
        counter = analyze_feature_signatures(records)
        assert counter[()] == 2

    def test_analyze_preserves_signature_order(self):
        """Signature features are consistently ordered."""
        records = [
            {"syllable": "test", "features": {"z_last": True, "a_first": True, "m_middle": True}}
        ]
        counter = analyze_feature_signatures(records)
        # Should be alphabetically sorted
        assert ("a_first", "m_middle", "z_last") in counter


class TestReportFormatting:
    """Tests for format_signature_report() function."""

    def test_format_basic_report(self):
        """Basic report formatting includes all sections."""
        counter = Counter({("feature_a",): 10, ("feature_b",): 5})
        report = format_signature_report(counter, total_syllables=15)

        assert "FEATURE SIGNATURE ANALYSIS" in report
        assert "Total syllables analyzed: 15" in report
        assert "Unique feature signatures: 2" in report
        assert "SIGNATURE RANKINGS" in report
        assert "SUMMARY STATISTICS" in report

    def test_format_report_with_limit(self):
        """Limit parameter restricts number of signatures shown."""
        counter = Counter({("sig_a",): 100, ("sig_b",): 50, ("sig_c",): 25, ("sig_d",): 10})
        report = format_signature_report(counter, total_syllables=185, limit=2)

        # Should show top 2
        assert "sig_a" in report
        assert "sig_b" in report
        # Should not show bottom 2
        assert "sig_c" not in report
        assert "sig_d" not in report

    def test_format_report_percentages(self):
        """Report includes correct percentages."""
        counter = Counter(
            {
                ("feature_a",): 50,  # 50% of 100
                ("feature_b",): 30,  # 30% of 100
                ("feature_c",): 20,  # 20% of 100
            }
        )
        report = format_signature_report(counter, total_syllables=100)

        assert "50.00%" in report
        assert "30.00%" in report
        assert "20.00%" in report

    def test_format_report_with_empty_signature(self):
        """Empty signature displays as '(no features active)'."""
        counter = Counter({(): 5, ("feature_a",): 10})
        report = format_signature_report(counter, total_syllables=15)

        assert "(no features active)" in report

    def test_format_report_shows_feature_count(self):
        """Report shows feature count in brackets."""
        counter = Counter({("a", "b", "c"): 10})
        report = format_signature_report(counter, total_syllables=10)

        # Should show [3] for 3 features
        assert "[3]" in report

    def test_format_report_cardinality_distribution(self):
        """Report includes feature cardinality distribution."""
        counter = Counter(
            {
                ("a",): 5,  # 1 feature
                ("b",): 3,  # 1 feature
                ("c", "d"): 2,  # 2 features
                ("e", "f", "g"): 1,  # 3 features
            }
        )
        report = format_signature_report(counter, total_syllables=11)

        assert "Feature cardinality distribution:" in report
        assert "1 features: 2 unique signatures" in report
        assert "2 features: 1 unique signatures" in report
        assert "3 features: 1 unique signatures" in report

    def test_format_report_with_empty_counter(self):
        """Report handles empty counter gracefully."""
        counter: Counter = Counter()
        report = format_signature_report(counter, total_syllables=0)

        assert "Total syllables analyzed: 0" in report
        assert "Unique feature signatures: 0" in report


class TestReportSaving:
    """Tests for save_report() function."""

    def test_save_creates_output_directory(self):
        """save_report creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "new_directory" / "nested"
            assert not output_dir.exists()

            save_report("Test report", output_dir)

            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_save_creates_timestamped_file(self):
        """Saved file has timestamped name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            output_path = save_report("Test report", output_dir)

            # Check filename format: YYYYMMDD_HHMMSS.feature_signatures.txt
            assert output_path.suffix == ".txt"
            assert "feature_signatures" in output_path.name
            assert len(output_path.stem.split("_")[0]) == 8  # YYYYMMDD

    def test_save_writes_content(self):
        """Report content is correctly written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            test_content = "Test report content\nLine 2\nLine 3"

            output_path = save_report(test_content, output_dir)

            assert output_path.exists()
            assert output_path.read_text(encoding="utf-8") == test_content

    def test_save_returns_path(self):
        """save_report returns path to saved file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            output_path = save_report("Test", output_dir)

            assert isinstance(output_path, Path)
            assert output_path.exists()
            assert output_path.parent == output_dir


class TestFullPipeline:
    """Integration tests for run_analysis() function."""

    def test_run_analysis_end_to_end(self):
        """Full pipeline from input file to output report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test input file
            input_data = [
                {
                    "syllable": "ka",
                    "frequency": 10,
                    "features": {"starts_with_vowel": False, "ends_with_vowel": True},
                },
                {
                    "syllable": "an",
                    "frequency": 5,
                    "features": {"starts_with_vowel": True, "ends_with_nasal": True},
                },
                {
                    "syllable": "ra",
                    "frequency": 7,
                    "features": {"starts_with_vowel": False, "ends_with_vowel": True},
                },
            ]
            input_path = tmp_path / "syllables_annotated.json"
            input_path.write_text(json.dumps(input_data), encoding="utf-8")

            # Run analysis
            output_dir = tmp_path / "output"
            result = run_analysis(input_path, output_dir)

            # Verify results
            assert result["total_syllables"] == 3
            assert result["unique_signatures"] == 2
            assert result["output_path"].exists()
            assert result["signature_counter"][("ends_with_vowel",)] == 2
            assert result["signature_counter"][("ends_with_nasal", "starts_with_vowel")] == 1

            # Verify output file content
            report_content = result["output_path"].read_text(encoding="utf-8")
            assert "Total syllables analyzed: 3" in report_content
            assert "Unique feature signatures: 2" in report_content

    def test_run_analysis_with_limit(self):
        """Pipeline respects limit parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create input with many signatures
            input_data = [
                {"syllable": f"syl{i}", "frequency": i, "features": {f"feature_{i}": True}}
                for i in range(100)
            ]
            input_path = tmp_path / "syllables_annotated.json"
            input_path.write_text(json.dumps(input_data), encoding="utf-8")

            # Run with limit
            output_dir = tmp_path / "output"
            result = run_analysis(input_path, output_dir, limit=10)

            # Should analyze all but only report top 10
            assert result["total_syllables"] == 100
            assert result["unique_signatures"] == 100

            # Report should be shorter (not all 100 signatures)
            # Just verify it completed without errors

    def test_run_analysis_deterministic(self):
        """Running analysis twice produces consistent results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test input
            input_data = [
                {"syllable": "ka", "frequency": 10, "features": {"feature_a": True}},
                {"syllable": "ra", "frequency": 5, "features": {"feature_b": True}},
            ]
            input_path = tmp_path / "syllables_annotated.json"
            input_path.write_text(json.dumps(input_data), encoding="utf-8")

            # Run twice
            output_dir1 = tmp_path / "output1"
            output_dir2 = tmp_path / "output2"

            result1 = run_analysis(input_path, output_dir1)
            result2 = run_analysis(input_path, output_dir2)

            # Results should be identical (except timestamps and output paths)
            assert result1["total_syllables"] == result2["total_syllables"]
            assert result1["unique_signatures"] == result2["unique_signatures"]
            assert result1["signature_counter"] == result2["signature_counter"]


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_analyze_with_many_features(self):
        """Handles syllables with many active features."""
        records = [{"syllable": "test", "features": {f"feature_{i}": True for i in range(20)}}]
        counter = analyze_feature_signatures(records)
        signature = list(counter.keys())[0]
        assert len(signature) == 20

    def test_analyze_preserves_all_signatures(self):
        """All unique signatures are preserved in counter."""
        # Create 100 unique signatures
        records = [{"syllable": f"syl{i}", "features": {f"feature_{i}": True}} for i in range(100)]
        counter = analyze_feature_signatures(records)
        assert len(counter) == 100

    def test_format_with_large_counts(self):
        """Large syllable counts are formatted with commas."""
        counter = Counter({("feature_a",): 1000000})
        report = format_signature_report(counter, total_syllables=1000000)
        assert "1,000,000" in report

    def test_signature_extraction_unicode_features(self):
        """Feature names with unicode characters work correctly."""
        features = {"café": True, "résumé": False, "naïve": True}
        sig = extract_signature(features)
        assert sig == ("café", "naïve")

    def test_format_report_zero_division_safety(self):
        """Handles edge case of zero total syllables without division error."""
        counter: Counter = Counter()
        # Should not raise ZeroDivisionError
        report = format_signature_report(counter, total_syllables=0)
        assert "Total syllables analyzed: 0" in report


class TestRealWorldScenarios:
    """Tests using realistic feature data."""

    def test_realistic_phonetic_features(self):
        """Test with actual phonetic feature combinations."""
        records: list[dict[str, Any]] = [
            {
                "syllable": "kran",
                "features": {
                    "starts_with_vowel": False,
                    "starts_with_cluster": True,
                    "contains_plosive": True,
                    "contains_liquid": True,
                    "contains_nasal": True,
                    "short_vowel": True,
                    "ends_with_nasal": True,
                },
            },
            {
                "syllable": "ka",
                "features": {
                    "starts_with_vowel": False,
                    "contains_plosive": True,
                    "short_vowel": True,
                    "ends_with_vowel": True,
                },
            },
            {
                "syllable": "an",
                "features": {
                    "starts_with_vowel": True,
                    "contains_nasal": True,
                    "short_vowel": True,
                    "ends_with_nasal": True,
                },
            },
        ]

        counter = analyze_feature_signatures(records)

        # Each should have unique signature
        assert len(counter) == 3

        # Verify specific signatures exist
        kran_sig = extract_signature(records[0]["features"])
        assert counter[kran_sig] == 1
        assert "contains_liquid" in kran_sig
        assert "contains_nasal" in kran_sig

    def test_report_readability_with_real_features(self):
        """Report is readable with actual phonetic feature names."""
        counter = Counter(
            {
                ("contains_plosive", "ends_with_vowel", "short_vowel", "starts_with_vowel"): 50,
                ("contains_nasal", "ends_with_nasal", "short_vowel"): 30,
                ("contains_liquid", "ends_with_vowel", "starts_with_cluster"): 20,
            }
        )

        report = format_signature_report(counter, total_syllables=100)

        # Check that feature names are readable
        assert "contains_plosive" in report
        assert "ends_with_vowel" in report
        assert "short_vowel" in report
        assert "starts_with_vowel" in report
        assert "contains_nasal" in report
        assert "ends_with_nasal" in report
        assert "contains_liquid" in report
        assert "starts_with_cluster" in report
