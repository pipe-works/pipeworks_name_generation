"""
Command-line interface for the name combiner.

This module provides the CLI for generating name candidates from an
annotated syllable corpus. It follows the project's CLI documentation
standards with sphinx-argparse compatible argument parser.

Usage
-----
Generate 2-syllable candidates::

    python -m build_tools.name_combiner \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --syllables 2 \\
        --count 10000 \\
        --seed 42

Generate 3-syllable candidates with uniform sampling::

    python -m build_tools.name_combiner \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --syllables 3 \\
        --count 5000 \\
        --frequency-weight 0.0
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for the name combiner.

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser ready to parse command-line arguments.

    Notes
    -----
    This function follows the project's CLI documentation standards,
    enabling sphinx-argparse to auto-generate documentation.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Generate N-syllable name candidates from an annotated syllable corpus. "
            "Combines syllables structurally and aggregates features to the name level. "
            "This is a build-time tool for the Selection Policy Layer."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples::

    # Generate 2-syllable candidates with default settings
    python -m build_tools.name_combiner \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --syllables 2

    # Generate 10000 3-syllable candidates with fixed seed
    python -m build_tools.name_combiner \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --syllables 3 \\
        --count 10000 \\
        --seed 42

    # Generate with uniform sampling (no frequency weighting)
    python -m build_tools.name_combiner \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --syllables 2 \\
        --frequency-weight 0.0

Output:
    Creates ``candidates/{prefix}_candidates_{N}syl.json`` in the run directory.
    The prefix (pyphen\\_ or nltk\\_) is auto-detected from the run directory name.
        """,
    )

    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help=(
            "Path to extraction run directory containing annotated JSON. "
            "Example: _working/output/20260110_115453_pyphen/"
        ),
    )

    parser.add_argument(
        "--syllables",
        type=int,
        required=True,
        choices=[2, 3, 4],
        help="Number of syllables per candidate name. Choices: 2, 3, 4.",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=10000,
        help="Number of candidates to generate. Default: 10000.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "RNG seed for deterministic output. If not specified, uses system entropy. "
            "Same seed always produces identical candidates."
        ),
    )

    parser.add_argument(
        "--frequency-weight",
        type=float,
        default=1.0,
        help=(
            "Weight for frequency-biased sampling. "
            "0.0 = uniform sampling, 1.0 = fully frequency-weighted. "
            "Values between 0 and 1 interpolate. Default: 1.0."
        ),
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Parameters
    ----------
    args : list[str] | None, optional
        Arguments to parse. If None, uses sys.argv.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def discover_annotated_json(run_dir: Path) -> tuple[Path, str]:
    """
    Discover the annotated JSON file in a run directory.

    Parameters
    ----------
    run_dir : Path
        Path to extraction run directory.

    Returns
    -------
    tuple[Path, str]
        (path_to_annotated_json, prefix) where prefix is 'pyphen' or 'nltk'.

    Raises
    ------
    FileNotFoundError
        If no annotated JSON is found.
    ValueError
        If run directory structure is unexpected.
    """
    data_dir = run_dir / "data"
    if not data_dir.exists():
        raise FileNotFoundError(f"No data/ directory in {run_dir}")

    # Check for pyphen or nltk annotated file
    pyphen_path = data_dir / "pyphen_syllables_annotated.json"
    nltk_path = data_dir / "nltk_syllables_annotated.json"

    if pyphen_path.exists():
        return pyphen_path, "pyphen"
    elif nltk_path.exists():
        return nltk_path, "nltk"
    else:
        raise FileNotFoundError(
            f"No annotated JSON found in {data_dir}. "
            "Expected pyphen_syllables_annotated.json or nltk_syllables_annotated.json"
        )


def main(args: list[str] | None = None) -> int:
    """
    Main entry point for the name combiner CLI.

    Parameters
    ----------
    args : list[str] | None, optional
        Command-line arguments. If None, uses sys.argv.

    Returns
    -------
    int
        Exit code (0 for success, non-zero for error).
    """
    # Import here to avoid circular imports and speed up --help
    from build_tools.name_combiner.combiner import combine_syllables

    parsed = parse_arguments(args)

    # Validate run directory
    run_dir = parsed.run_dir.resolve()
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    # Discover annotated JSON
    try:
        annotated_path, prefix = discover_annotated_json(run_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Loading annotated data from: {annotated_path}")

    # Load annotated data
    try:
        with open(annotated_path) as f:
            annotated_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {annotated_path}: {e}", file=sys.stderr)
        return 1

    print(f"Loaded {len(annotated_data):,} syllables")

    # Generate candidates
    print(
        f"Generating {parsed.count:,} {parsed.syllables}-syllable candidates "
        f"(seed={parsed.seed}, frequency_weight={parsed.frequency_weight})"
    )

    candidates = combine_syllables(
        annotated_data=annotated_data,
        syllable_count=parsed.syllables,
        count=parsed.count,
        seed=parsed.seed,
        frequency_weight=parsed.frequency_weight,
    )

    print(f"Generated {len(candidates):,} candidates")

    # Prepare output
    candidates_dir = run_dir / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"{prefix}_candidates_{parsed.syllables}syl.json"
    output_path = candidates_dir / output_filename

    # Build output structure
    output = {
        "metadata": {
            "source_run": run_dir.name,
            "source_annotated": annotated_path.name,
            "syllable_count": parsed.syllables,
            "total_candidates": len(candidates),
            "seed": parsed.seed,
            "frequency_weight": parsed.frequency_weight,
            "aggregation_rule": "majority",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "candidates": candidates,
    }

    # Write output
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote candidates to: {output_path}")

    # Summary stats
    unique_names = len(set(c["name"] for c in candidates))
    print(f"Unique names: {unique_names:,} ({unique_names / len(candidates) * 100:.1f}%)")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
