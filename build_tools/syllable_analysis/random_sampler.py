"""Random sampling utility for annotated syllables.

This module provides functionality to randomly sample annotated syllables for inspection
and quality assurance. It reads the output of the syllable feature annotator and generates
a random sample in JSON format.

This module has been refactored (Phase 2) to use common utilities from the
analysis.common package, eliminating code duplication.

Usage::

    # Sample 100 syllables (default)
    python -m build_tools.syllable_analysis.random_sampler

    # Sample specific number of syllables
    python -m build_tools.syllable_analysis.random_sampler --samples 50

    # Specify custom input/output paths
    python -m build_tools.syllable_analysis.random_sampler \
        --input data/annotated/syllables_annotated.json \
        --output _working/samples.json \
        --samples 200

    # Use a specific random seed for reproducibility
    python -m build_tools.syllable_analysis.random_sampler --samples 50 --seed 42
"""

import argparse
import json  # Still needed for JSONDecodeError in exception handling
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

# Import common utilities (Phase 2 refactoring)
from build_tools.syllable_analysis.common import (
    default_paths,
    load_annotated_syllables,
    save_json_output,
)

# Note: load_annotated_syllables() has been moved to common.data_io (Phase 2 refactoring)


def sample_syllables(
    records: List[Dict[str, Any]], sample_count: int, seed: int | None = None
) -> List[Dict[str, Any]]:
    """Randomly sample syllables from the full corpus.

    Args:
        records: List of annotated syllable records.
        sample_count: Number of samples to draw.
        seed: Optional random seed for reproducibility.

    Returns:
        List of sampled syllable records.

    Raises:
        ValueError: If sample_count is larger than available records.
    """
    if sample_count > len(records):
        raise ValueError(
            f"Cannot sample {sample_count} records from {len(records)} available records"
        )

    # Use a new Random instance to avoid affecting global random state
    rng = random.Random(seed)  # nosec B311 - Not used for cryptographic purposes
    return rng.sample(records, sample_count)


# Note: save_samples() has been replaced with save_json_output() from common.data_io
# (Phase 2 refactoring)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for random sampler.

    This function creates the ArgumentParser with all CLI options but does not
    parse arguments. This separation allows Sphinx documentation tools to
    introspect the parser and auto-generate CLI documentation.

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Randomly sample annotated syllables for inspection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Sample 100 syllables (default)
   python -m build_tools.syllable_analysis.random_sampler

   # Sample 50 syllables
   python -m build_tools.syllable_analysis.random_sampler --samples 50

   # Use custom paths
   python -m build_tools.syllable_analysis.random_sampler \\
       --input data/annotated/syllables_annotated.json \\
       --output _working/my_samples.json \\
       --samples 200

   # Use a specific seed for reproducibility
   python -m build_tools.syllable_analysis.random_sampler --samples 50 --seed 42
        """,
    )

    # Use default_paths from common module (Phase 2 refactoring)
    parser.add_argument(
        "--input",
        type=Path,
        default=default_paths.annotated_syllables,
        help=f"Path to input annotated syllables JSON file (default: {default_paths.annotated_syllables})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=default_paths.root / "_working" / "random_samples.json",
        help=f"Path to output samples JSON file (default: {default_paths.root / '_working' / 'random_samples.json'})",
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of syllables to sample (default: 100)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: None, uses system randomness)",
    )

    return parser


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = create_argument_parser()
    return parser.parse_args()


def main() -> int:
    """Main entry point for random sampling.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    args = parse_arguments()

    try:
        # Load annotated syllables
        print(f"Loading annotated syllables from {args.input}...")
        records = load_annotated_syllables(args.input)
        print(f"Loaded {len(records):,} annotated syllables")

        # Sample syllables
        print(f"Sampling {args.samples} syllables", end="")
        if args.seed is not None:
            print(f" (seed: {args.seed})", end="")
        print("...")

        samples = sample_syllables(records, args.samples, args.seed)

        # Save samples using common.save_json_output() (Phase 2 refactoring)
        print(f"Saving samples to {args.output}...")
        save_json_output(samples, args.output)

        print(f"✓ Successfully saved {len(samples)} random samples to {args.output}")
        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
