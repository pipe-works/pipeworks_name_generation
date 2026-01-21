"""
Command-line interface for the name selector.

This module provides the CLI for filtering and ranking name candidates
against a name class policy. It follows the project's CLI documentation
standards with sphinx-argparse compatible argument parser.

Usage
-----
Select first names from 2-syllable candidates::

    python -m build_tools.name_selector \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --candidates candidates/pyphen_candidates_2syl.json \\
        --name-class first_name \\
        --count 100

Use soft mode (penalties instead of hard rejection)::

    python -m build_tools.name_selector \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --candidates candidates/pyphen_candidates_2syl.json \\
        --name-class first_name \\
        --mode soft
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for the name selector.

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
            "Filter and rank name candidates against a name class policy. "
            "Evaluates candidates using the 12-feature policy matrix and produces "
            "ranked, admissible name lists. This is a build-time tool for the "
            "Selection Policy Layer."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples::

    # Select first names from 2-syllable candidates
    python -m build_tools.name_selector \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --candidates candidates/pyphen_candidates_2syl.json \\
        --name-class first_name \\
        --count 100

    # Select place names with soft mode (penalties instead of rejection)
    python -m build_tools.name_selector \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --candidates candidates/pyphen_candidates_3syl.json \\
        --name-class place_name \\
        --mode soft

    # Use a custom policy file
    python -m build_tools.name_selector \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --candidates candidates/pyphen_candidates_2syl.json \\
        --name-class first_name \\
        --policy-file custom_policies.yml

Output:
    Creates ``selections/{prefix}_{name_class}_{N}syl.json`` in the run directory.
    The prefix and syllable count are extracted from the candidates filename.
        """,
    )

    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help=(
            "Path to extraction run directory. " "Example: _working/output/20260110_115453_pyphen/"
        ),
    )

    parser.add_argument(
        "--candidates",
        type=Path,
        required=True,
        help=(
            "Path to candidates JSON file, relative to run-dir. "
            "Example: candidates/pyphen_candidates_2syl.json"
        ),
    )

    parser.add_argument(
        "--name-class",
        type=str,
        required=True,
        help=(
            "Name class identifier from name_classes.yml. "
            "Examples: first_name, last_name, place_name"
        ),
    )

    parser.add_argument(
        "--policy-file",
        type=Path,
        default=None,
        help=(
            "Path to name_classes.yml. If not specified, uses data/name_classes.yml "
            "from project root. Default: data/name_classes.yml"
        ),
    )

    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Maximum number of names to output. Default: 100.",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["hard", "soft"],
        default="hard",
        help=(
            "Evaluation mode. 'hard' rejects candidates with discouraged features. "
            "'soft' applies -10 penalty instead. Default: hard."
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


def extract_prefix_and_syllables(candidates_filename: str) -> tuple[str, int]:
    """
    Extract prefix and syllable count from candidates filename.

    Parameters
    ----------
    candidates_filename : str
        Filename like "pyphen_candidates_2syl.json"

    Returns
    -------
    tuple[str, int]
        (prefix, syllable_count) e.g., ("pyphen", 2)

    Raises
    ------
    ValueError
        If filename doesn't match expected pattern.
    """
    # Expected: {prefix}_candidates_{N}syl.json
    stem = Path(candidates_filename).stem  # pyphen_candidates_2syl
    parts = stem.split("_")

    if len(parts) < 3 or parts[1] != "candidates":
        raise ValueError(f"Unexpected candidates filename format: {candidates_filename}")

    prefix = parts[0]

    # Extract syllable count from last part (e.g., "2syl" -> 2)
    syl_part = parts[-1]
    if not syl_part.endswith("syl"):
        raise ValueError(f"Cannot extract syllable count from: {candidates_filename}")

    try:
        syllables = int(syl_part[:-3])  # Remove "syl" suffix
    except ValueError as err:
        raise ValueError(f"Cannot parse syllable count from: {syl_part}") from err

    return prefix, syllables


def main(args: list[str] | None = None) -> int:
    """
    Main entry point for the name selector CLI.

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
    from build_tools.name_selector.name_class import get_default_policy_path, load_name_classes
    from build_tools.name_selector.selector import compute_selection_statistics, select_names

    parsed = parse_arguments(args)

    # Validate run directory
    run_dir = parsed.run_dir.resolve()
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    # Resolve candidates path
    candidates_path = run_dir / parsed.candidates
    if not candidates_path.exists():
        print(f"Error: Candidates file not found: {candidates_path}", file=sys.stderr)
        return 1

    # Load candidates
    print(f"Loading candidates from: {candidates_path}")
    try:
        with open(candidates_path) as f:
            candidates_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {candidates_path}: {e}", file=sys.stderr)
        return 1

    candidates = candidates_data.get("candidates", [])
    print(f"Loaded {len(candidates):,} candidates")

    # Resolve policy file
    policy_path = parsed.policy_file or get_default_policy_path()
    if not policy_path.exists():
        print(f"Error: Policy file not found: {policy_path}", file=sys.stderr)
        return 1

    # Load policies
    print(f"Loading policies from: {policy_path}")
    try:
        policies = load_name_classes(policy_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error loading policies: {e}", file=sys.stderr)
        return 1

    # Get target policy
    if parsed.name_class not in policies:
        available = ", ".join(sorted(policies.keys()))
        print(
            f"Error: Unknown name class '{parsed.name_class}'. " f"Available: {available}",
            file=sys.stderr,
        )
        return 1

    policy = policies[parsed.name_class]
    print(f"Using policy: {parsed.name_class} - {policy.description}")

    # Compute statistics
    print(f"Evaluating candidates (mode={parsed.mode})...")
    stats = compute_selection_statistics(candidates, policy, mode=parsed.mode)  # type: ignore[arg-type]

    print(f"  Evaluated: {stats['total_evaluated']:,}")
    print(
        f"  Admitted: {stats['admitted']:,} ({stats['admitted']/stats['total_evaluated']*100:.1f}%)"
    )
    print(f"  Rejected: {stats['rejected']:,}")

    if stats["rejection_reasons"]:
        print("  Rejection reasons:")
        for reason, count in sorted(stats["rejection_reasons"].items(), key=lambda x: -x[1]):
            print(f"    {reason}: {count:,}")

    # Select top names
    selected = select_names(candidates, policy, count=parsed.count, mode=parsed.mode)  # type: ignore[arg-type]
    print(f"Selected top {len(selected):,} names")

    # Prepare output
    try:
        prefix, syllables = extract_prefix_and_syllables(parsed.candidates.name)
    except ValueError as e:
        print(f"Warning: {e}. Using defaults.", file=sys.stderr)
        prefix = "unknown"
        syllables = candidates_data.get("metadata", {}).get("syllable_count", 0)

    selections_dir = run_dir / "selections"
    selections_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"{prefix}_{parsed.name_class}_{syllables}syl.json"
    output_path = selections_dir / output_filename

    # Build output structure
    output = {
        "metadata": {
            "source_candidates": parsed.candidates.name,
            "name_class": parsed.name_class,
            "policy_description": policy.description,
            "policy_file": str(policy_path),
            "mode": parsed.mode,
            "total_evaluated": stats["total_evaluated"],
            "admitted": stats["admitted"],
            "rejected": stats["rejected"],
            "rejection_reasons": stats["rejection_reasons"],
            "score_distribution": stats["score_distribution"],
            "output_count": len(selected),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "selections": selected,
    }

    # Write output
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote selections to: {output_path}")

    # Show top 5 samples
    if selected:
        print("\nTop 5 selections:")
        for s in selected[:5]:
            features_summary = len([f for f, v in s["features"].items() if v])
            print(
                f"  {s['rank']:3d}. {s['name']:15s} score={s['score']:2d} "
                f"({features_summary} features)"
            )

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
