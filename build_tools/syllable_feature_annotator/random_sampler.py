"""Random sampling utility for annotated syllables.

This module provides functionality to randomly sample annotated syllables for inspection
and quality assurance. It reads the output of the syllable feature annotator and generates
a random sample in JSON format.

Usage:
    # Sample 100 syllables (default)
    python -m build_tools.syllable_feature_annotator.random_sampler

    # Sample specific number of syllables
    python -m build_tools.syllable_feature_annotator.random_sampler --samples 50

    # Specify custom input/output paths
    python -m build_tools.syllable_feature_annotator.random_sampler \
        --input data/annotated/syllables_annotated.json \
        --output _working/samples.json \
        --samples 200

    # Use a specific random seed for reproducibility
    python -m build_tools.syllable_feature_annotator.random_sampler --samples 50 --seed 42
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_annotated_syllables(input_path: Path) -> List[Dict[str, Any]]:
    """Load annotated syllables from JSON file.

    Args:
        input_path: Path to the annotated syllables JSON file.

    Returns:
        List of annotated syllable records.

    Raises:
        FileNotFoundError: If input file does not exist.
        json.JSONDecodeError: If input file is not valid JSON.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open() as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"Expected list of records, got {type(records).__name__}")

    return records


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


def save_samples(samples: List[Dict[str, Any]], output_path: Path) -> None:
    """Save sampled syllables to JSON file.

    Args:
        samples: List of sampled syllable records.
        output_path: Path where output JSON file will be saved.
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON with indentation for readability
    with output_path.open("w") as f:
        json.dump(samples, f, indent=2)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Randomly sample annotated syllables for inspection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sample 100 syllables (default)
  python -m build_tools.syllable_feature_annotator.random_sampler

  # Sample 50 syllables
  python -m build_tools.syllable_feature_annotator.random_sampler --samples 50

  # Use custom paths
  python -m build_tools.syllable_feature_annotator.random_sampler \\
      --input data/annotated/syllables_annotated.json \\
      --output _working/my_samples.json \\
      --samples 200

  # Use a specific seed for reproducibility
  python -m build_tools.syllable_feature_annotator.random_sampler --samples 50 --seed 42
        """,
    )

    # Get project root for default paths
    root = Path(__file__).resolve().parent.parent.parent

    parser.add_argument(
        "--input",
        type=Path,
        default=root / "data" / "annotated" / "syllables_annotated.json",
        help="Path to input annotated syllables JSON file (default: data/annotated/syllables_annotated.json)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=root / "_working" / "random_samples.json",
        help="Path to output samples JSON file (default: _working/random_samples.json)",
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

        # Save samples
        print(f"Saving samples to {args.output}...")
        save_samples(samples, args.output)

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
