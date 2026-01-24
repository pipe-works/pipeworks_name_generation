"""Feature Signature Analysis Tool

This build-time analysis tool examines the annotated syllable corpus to identify
which feature combinations actually exist in the data and how frequently each
combination appears.

A "feature signature" is the set of all active (True) features for a syllable.
For example, a syllable with only "starts_with_vowel" and "ends_with_vowel" active
would have the signature: ('ends_with_vowel', 'starts_with_vowel').

This analysis helps answer questions like:
- What feature patterns are most common in natural language?
- Are certain feature combinations rare or impossible?
- How diverse is the feature space in the corpus?

Output is saved to _working/analysis/feature_signatures/ for review.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Counter as CounterType

from build_tools.syllable_analysis.common import (
    default_paths,
    ensure_output_dir,
    generate_timestamped_path,
    load_annotated_syllables,
)


def extract_signature(features: dict[str, bool]) -> tuple[str, ...]:
    """Extract the feature signature from a feature dictionary.

    A signature is a sorted tuple of feature names where the feature value is True.
    This creates a canonical representation of the active feature set.

    Args:
        features: Dictionary mapping feature names to boolean values

    Returns:
        Sorted tuple of feature names that are active (True)

    Example:
        >>> extract_signature({"starts_with_vowel": True, "ends_with_vowel": False})
        ('starts_with_vowel',)
    """
    return tuple(sorted(feature_name for feature_name, is_active in features.items() if is_active))


def analyze_feature_signatures(records: list[dict]) -> Counter:
    """Analyze feature signatures across all syllable records.

    Counts how many syllables share each unique feature signature.

    Args:
        records: List of syllable records from syllables_annotated.json
                Each record should have "syllable", "frequency", and "features" keys

    Returns:
        Counter mapping feature signatures to occurrence counts

    Example:
        >>> records = [
        ...     {"syllable": "ka", "features": {"starts_with_vowel": False}},
        ...     {"syllable": "a", "features": {"starts_with_vowel": True}}
        ... ]
        >>> counter = analyze_feature_signatures(records)
        >>> counter[('starts_with_vowel',)]
        1
    """
    signature_counter: CounterType[tuple[str, ...]] = Counter()

    for record in records:
        sig = extract_signature(record["features"])
        signature_counter[sig] += 1

    return signature_counter


def format_signature_report(
    signature_counter: Counter, total_syllables: int, limit: int | None = None
) -> str:
    """Format the signature analysis results as a human-readable report.

    Args:
        signature_counter: Counter of signatures to their occurrence counts
        total_syllables: Total number of syllables in the corpus
        limit: Maximum number of signatures to include (None = all)

    Returns:
        Formatted multi-line string report
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("FEATURE SIGNATURE ANALYSIS")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total syllables analyzed: {total_syllables:,}")
    lines.append(f"Unique feature signatures: {len(signature_counter):,}")
    lines.append("")

    # Summary statistics (moved before rankings)
    lines.append("SUMMARY STATISTICS")
    lines.append("-" * 80)

    if signature_counter:
        most_common_sig, most_common_count = signature_counter.most_common(1)[0]
        lines.append(
            f"Most common signature: {most_common_count} syllables ({(most_common_count/total_syllables)*100:.1f}%)"
        )
        lines.append(f"  Features: {', '.join(most_common_sig) if most_common_sig else '(none)'}")
        lines.append("")

        # Calculate feature cardinality distribution
        cardinality_dist = Counter(len(sig) for sig in signature_counter.keys())
        lines.append("Feature cardinality distribution:")
        for num_features in sorted(cardinality_dist.keys()):
            sig_count = cardinality_dist[num_features]
            lines.append(f"  {num_features} features: {sig_count} unique signatures")

    lines.append("")
    lines.append("=" * 80)

    # Signature details (moved after summary)
    lines.append("SIGNATURE RANKINGS")
    lines.append("-" * 80)
    lines.append(f"{'Rank':<6} {'Count':<8} {'Pct':<8} {'Features'}")
    lines.append("-" * 80)

    signatures_to_show = (
        signature_counter.most_common(limit) if limit else signature_counter.most_common()
    )

    for rank, (signature, count) in enumerate(signatures_to_show, start=1):
        percentage = (count / total_syllables) * 100
        feature_count = len(signature)

        # Format the feature list for readability
        if feature_count == 0:
            feature_str = "(no features active)"
        else:
            feature_str = f"[{feature_count}] " + ", ".join(signature)

        lines.append(f"{rank:<6} {count:<8} {percentage:>6.2f}%  {feature_str}")

    lines.append("=" * 80)

    return "\n".join(lines)


def save_report(report: str, output_dir: Path) -> Path:
    """Save the formatted report to the output directory.

    Args:
        report: Formatted report string
        output_dir: Directory to save the report in

    Returns:
        Path to the saved report file
    """
    # Ensure output directory exists
    ensure_output_dir(output_dir)

    # Generate timestamped output path
    output_path = generate_timestamped_path(output_dir, "feature_signatures", "txt")

    # Write report
    output_path.write_text(report, encoding="utf-8")

    return output_path


def run_analysis(input_path: Path, output_dir: Path, limit: int | None = None) -> dict:
    """Run the complete feature signature analysis pipeline.

    Args:
        input_path: Path to syllables_annotated.json
        output_dir: Directory to save analysis results
        limit: Maximum number of signatures to include in report (None = all)

    Returns:
        Dictionary with analysis results including:
        - total_syllables: Total number of syllables analyzed
        - unique_signatures: Number of unique feature signatures
        - output_path: Path to the saved report
    """
    # Load annotated syllables
    records = load_annotated_syllables(input_path)

    # Analyze signatures
    signature_counter = analyze_feature_signatures(records)

    # Generate report
    report = format_signature_report(signature_counter, len(records), limit)

    # Save report
    output_path = save_report(report, output_dir)

    return {
        "total_syllables": len(records),
        "unique_signatures": len(signature_counter),
        "output_path": output_path,
        "signature_counter": signature_counter,
    }


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for feature signature analysis.

    This function creates the ArgumentParser with all CLI options but does not
    parse arguments. This separation allows Sphinx documentation tools to
    introspect the parser and auto-generate CLI documentation.

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Analyze feature signatures in annotated syllable corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Analyze with default paths
   python -m build_tools.syllable_analysis.feature_signatures

   # Show only top 50 signatures
   python -m build_tools.syllable_analysis.feature_signatures --limit 50

   # Custom input/output paths
   python -m build_tools.syllable_analysis.feature_signatures \\
     --input data/annotated/syllables_annotated.json \\
     --output _working/my_analysis/
        """,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=default_paths.annotated_syllables,
        help=f"Path to syllables_annotated.json (default: {default_paths.annotated_syllables})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=default_paths.analysis_output_dir("feature_signatures"),
        help=f"Output directory for analysis results (default: {default_paths.analysis_output_dir('feature_signatures')})",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of signatures in report (default: show all)",
    )

    return parser


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_argument_parser()
    return parser.parse_args()


def main() -> None:
    """Main entry point for the feature signature analysis tool."""
    args = parse_args()

    # Validate input file exists
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        print("Have you run the syllable feature annotator yet?")
        return

    print(f"Analyzing feature signatures from: {args.input}")
    print(f"Output directory: {args.output}")
    if args.limit:
        print(f"Showing top {args.limit} signatures")
    print()

    # Run analysis
    result = run_analysis(args.input, args.output, args.limit)

    # Display summary
    print(f"✓ Analyzed {result['total_syllables']:,} syllables")
    print(f"✓ Found {result['unique_signatures']:,} unique feature signatures")
    print(f"✓ Report saved to: {result['output_path']}")


if __name__ == "__main__":
    main()
