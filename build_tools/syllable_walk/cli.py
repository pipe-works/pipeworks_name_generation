"""Command-line interface for syllable walker.

This module provides both interactive and batch processing functionality
for exploring syllable feature space through random walks.

Usage::

    python -m build_tools.syllable_walk [options]

Examples::

    # Generate a single walk
    python -m build_tools.syllable_walk data.json --start ka --profile dialect

    # Compare all profiles
    python -m build_tools.syllable_walk data.json --start bak --compare-profiles

    # Generate batch of walks
    python -m build_tools.syllable_walk data.json --batch 50 --output walks.json

    # Start interactive web interface
    python -m build_tools.syllable_walk data.json --web
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from build_tools.syllable_walk.profiles import WALK_PROFILES
from build_tools.syllable_walk.server import run_server
from build_tools.syllable_walk.walker import SyllableWalker


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for syllable walker.

    This function creates the ArgumentParser with all CLI options but does not
    parse arguments. This separation allows Sphinx documentation tools to
    introspect the parser and auto-generate CLI documentation.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments

    Examples:
        Create parser and inspect options::

            >>> parser = create_argument_parser()
            >>> parser.prog
            'cli.py'

        Use parser to parse arguments::

            >>> parser = create_argument_parser()
            >>> args = parser.parse_args(["data.json", "--start", "ka"])
            >>> args.start
            'ka'

    Notes:
        - This function is used by both the CLI and documentation generation
        - For normal CLI usage, use main() which calls this internally
        - Sphinx-argparse can introspect this function to generate docs
    """
    parser = argparse.ArgumentParser(
        description="Explore syllable feature space via cost-based random walks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Generate a single walk with default profile (dialect)
   python -m build_tools.syllable_walk data.json --start ka

   # Use specific profile
   python -m build_tools.syllable_walk data.json --start bak --profile goblin --steps 10

   # Compare all profiles from same starting point
   python -m build_tools.syllable_walk data.json --start ka --compare-profiles

   # Generate batch of 50 walks and save to JSON
   python -m build_tools.syllable_walk data.json --batch 50 --profile ritual --output walks.json

   # Search for syllables containing "th"
   python -m build_tools.syllable_walk data.json --search "th"

   # Custom walk parameters (overrides profile)
   python -m build_tools.syllable_walk data.json --start ka --steps 10 \\
       --max-flips 2 --temperature 1.5 --frequency-weight -0.8 --seed 42

   # Start interactive web interface (auto-discovers port starting at 8000)
   python -m build_tools.syllable_walk --web

   # Start web interface on specific port
   python -m build_tools.syllable_walk --web --port 9000

For detailed documentation, see: claude/build_tools/syllable_walk.md
        """,
    )

    # Optional positional argument (required for CLI modes, optional for web mode)
    parser.add_argument(
        "data_file",
        nargs="?",  # Make optional
        type=Path,
        help=(
            "Path to syllables_annotated.json file (output of "
            "syllable_feature_annotator). This file contains syllables with "
            "phonetic features and frequency information. "
            "Example: data/annotated/syllables_annotated.json. "
            "Optional in --web mode: if not specified, auto-discovers the most recent "
            "dataset from _working/output/ directories."
        ),
    )

    # Walk parameters group
    walk_group = parser.add_argument_group(
        "walk parameters",
        "Parameters controlling syllable walk behavior. These work with any mode "
        "except --search.",
    )

    walk_group.add_argument(
        "--start",
        type=str,
        metavar="SYLLABLE",
        help=(
            "Starting syllable for the walk. If not specified, a random "
            "syllable will be chosen. Must be a syllable present in the "
            "data file. Use --search to find valid syllables. "
            "Examples: 'ka', 'bak', 'the'. "
            "Default: random syllable"
        ),
    )

    walk_group.add_argument(
        "--profile",
        type=str,
        choices=list(WALK_PROFILES.keys()),
        default="dialect",
        metavar="NAME",
        help=(
            "Walk profile preset defining behavior characteristics. "
            "Available profiles: "
            "clerical (conservative, favors common syllables), "
            "dialect (balanced exploration, neutral frequency), "
            "goblin (chaotic, favors rare syllables), "
            "ritual (maximum exploration, very rare syllables). "
            "Each profile has predefined max_flips, temperature, and "
            "frequency_weight values. Can be overridden with custom parameters. "
            "Default: dialect"
        ),
    )

    walk_group.add_argument(
        "--steps",
        type=int,
        default=5,
        metavar="N",
        help=(
            "Number of steps to take in the walk. Each step visits one "
            "syllable. Output length will be steps + 1 (includes starting "
            "syllable). Valid range: 0-1000. "
            "Examples: 5 (quick walk), 20 (longer exploration). "
            "Default: 5"
        ),
    )

    walk_group.add_argument(
        "--seed",
        type=int,
        metavar="SEED",
        help=(
            "Random seed for reproducible walks. Same seed with same "
            "parameters always produces identical walks. This is useful for "
            "testing, debugging, or generating consistent examples. "
            "If not specified, uses system randomness (non-reproducible). "
            "Examples: 42, 12345. "
            "Default: None (random)"
        ),
    )

    # Custom parameters group (overrides profile)
    custom_group = parser.add_argument_group(
        "custom parameters",
        "Advanced parameters that override profile settings. Use these to "
        "fine-tune walk behavior beyond predefined profiles.",
    )

    custom_group.add_argument(
        "--max-flips",
        type=int,
        metavar="N",
        choices=[1, 2, 3],
        help=(
            "Maximum number of phonetic features that can change per step. "
            "This controls the Hamming distance constraint between consecutive "
            "syllables. Higher values allow more dramatic phonetic changes. "
            "Valid values: 1 (very conservative), 2 (moderate), 3 (maximum). "
            "Must be <= max-neighbor-distance. Overrides profile setting. "
            "Examples: 1 for minimal change, 3 for maximum variation. "
            "Default: determined by profile"
        ),
    )

    custom_group.add_argument(
        "--temperature",
        type=float,
        metavar="T",
        help=(
            "Exploration temperature controlling randomness (0.1-5.0). "
            "Higher values increase randomness and exploration, making the "
            "walk more likely to choose high-cost transitions. Lower values "
            "make walks more deterministic, strongly preferring low-cost moves. "
            "Overrides profile setting. "
            "Typical values: 0.3 (conservative), 0.7 (balanced), "
            "1.5 (exploratory), 2.5 (chaotic). "
            "Default: determined by profile"
        ),
    )

    custom_group.add_argument(
        "--frequency-weight",
        type=float,
        metavar="W",
        help=(
            "Frequency bias weight (-2.0 to 2.0). Controls whether the walk "
            "favors common or rare syllables. "
            "Positive values: Favor common syllables (e.g., 1.0 strongly favors common). "
            "Zero: Neutral, no frequency bias. "
            "Negative values: Favor rare syllables (e.g., -1.0 strongly favors rare). "
            "Overrides profile setting. "
            "Examples: 1.0 (prefer common), 0.0 (neutral), -1.0 (prefer rare). "
            "Default: determined by profile"
        ),
    )

    # Operation modes group
    mode_group = parser.add_argument_group(
        "operation modes",
        "Different modes of operation. These modes are mutually exclusive. "
        "If no mode is specified, performs a single walk.",
    )

    mode_group.add_argument(
        "--compare-profiles",
        action="store_true",
        help=(
            "Compare all four walk profiles from the same starting syllable. "
            "Generates one walk for each profile (clerical, dialect, goblin, "
            "ritual) using the same seed (if specified), allowing direct "
            "comparison of different behaviors. The --profile argument is "
            "ignored in this mode. Output shows walks side-by-side with "
            "profile descriptions. Useful for understanding profile differences."
        ),
    )

    mode_group.add_argument(
        "--batch",
        type=int,
        metavar="N",
        help=(
            "Generate N walks in batch mode. Each walk starts from a random "
            "syllable (unless --start is specified, then all walks start from "
            "the same syllable). Useful for statistical analysis, corpus "
            "exploration, or generating large datasets. Combine with --output "
            "to save results to JSON file. Progress is shown during generation. "
            "Examples: --batch 100 for analysis, --batch 1000 for corpus stats. "
            "Valid range: 1-10000"
        ),
    )

    mode_group.add_argument(
        "--search",
        type=str,
        metavar="QUERY",
        help=(
            "Search for syllables matching the query string. Performs "
            "case-insensitive substring match against all syllables in the "
            "dataset. Shows up to 20 matches with frequency information. "
            "Useful for finding valid starting syllables or exploring corpus "
            "contents. Does not perform walk generation. "
            "Examples: --search 'th' finds 'the', 'thi', 'tha', etc. "
            "          --search 'ka' finds 'ka', 'kan', 'kaf', etc."
        ),
    )

    mode_group.add_argument(
        "--web",
        action="store_true",
        help=(
            "Start simplified web interface for browsing name selections and "
            "generating walks. Auto-discovers pipeline runs from _working/output/. "
            "The interface provides: run selection dropdown, tabbed selections "
            "browser (first_name, last_name, place_name), and quick walk generator. "
            "Auto-discovers an available port starting at 8000, or use --port to "
            "specify a port. The server runs until stopped with Ctrl+C. "
            "Other CLI arguments are ignored in web mode."
        ),
    )

    # Output options group
    output_group = parser.add_argument_group(
        "output options",
        "Control output format, destination, and verbosity.",
    )

    output_group.add_argument(
        "--output",
        type=Path,
        metavar="FILE",
        help=(
            "Save results to JSON file instead of printing to console. "
            "Parent directories will be created if they don't exist. "
            "Output format depends on mode: single walk saves walk details with "
            "profile and seed info; batch mode saves array of walks with "
            "metadata. File can be used for further analysis or visualization. "
            "Examples: --output results/walks.json, --output batch_data.json"
        ),
    )

    output_group.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Suppress progress messages and verbose output. Only prints "
            "final results or errors. Useful for scripting, piping output, "
            "or when running in automated environments. Cannot be combined "
            "with --verbose. Progress bars and initialization messages are "
            "hidden in quiet mode."
        ),
    )

    output_group.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "Enable verbose output showing initialization progress, neighbor "
            "graph construction details, and detailed walk information. Shows "
            "memory usage, processing time, and intermediate steps. Useful for "
            "understanding performance, debugging, or learning how the walker "
            "works. Cannot be combined with --quiet. Significantly increases "
            "output volume."
        ),
    )

    # Walker configuration group
    config_group = parser.add_argument_group(
        "walker configuration",
        "Advanced configuration for the walker engine. These settings affect "
        "initialization time and memory usage.",
    )

    config_group.add_argument(
        "--max-neighbor-distance",
        type=int,
        default=3,
        metavar="N",
        choices=[1, 2, 3],
        help=(
            "Maximum Hamming distance for pre-computing neighbor graph "
            "(1-3). During initialization, the walker computes which syllables "
            "are 'neighbors' (similar in phonetic features). Higher values "
            "allow larger --max-flips but significantly increase initialization "
            "time and memory usage. Should be >= largest --max-flips you plan "
            "to use. "
            "Initialization time (500k syllables): ~30 sec (1), ~1 min (2), ~3 min (3). "
            "Memory impact: ~50MB (1), ~150MB (2), ~300MB (3). "
            "Default: 3 (recommended for maximum flexibility)"
        ),
    )

    config_group.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORT",
        help=(
            "Port number for web server when using --web mode. Only applies "
            "when --web flag is specified, otherwise ignored. "
            "If not specified, auto-discovers an available port starting at 8000. "
            "If specified, uses that exact port (fails if unavailable). "
            "Valid range: 1024-65535 (ports below 1024 require root/admin). "
            "Default: auto-discover starting at 8000"
        ),
    )

    return parser


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: List of argument strings to parse. If None, uses sys.argv[1:].
              This parameter is useful for testing.

    Returns:
        Parsed arguments as argparse.Namespace object

    Example:
        >>> args = parse_arguments(["data.json", "--start", "ka"])
        >>> args.start
        'ka'
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def single_walk_mode(walker: SyllableWalker, args: argparse.Namespace) -> int:
    """
    Handle single walk generation mode.

    Args:
        walker: Initialized SyllableWalker instance
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Determine starting syllable
    if args.start:
        start = args.start
        # Validate starting syllable exists
        if start not in walker.syllable_to_idx:
            print(f"Error: Syllable '{start}' not found in dataset", file=sys.stderr)
            print(f"Use --search '{start}' to find similar syllables", file=sys.stderr)
            return 1
    else:
        start = walker.get_random_syllable(seed=args.seed)

    # Generate walk with profile or custom parameters
    if args.max_flips or args.temperature or args.frequency_weight:
        # Custom parameters mode
        profile_name = "Custom"
        walk = walker.walk(
            start=start,
            steps=args.steps,
            max_flips=args.max_flips or 2,
            temperature=args.temperature or 0.7,
            frequency_weight=args.frequency_weight or 0.0,
            seed=args.seed,
        )
    else:
        # Use profile
        profile_name = WALK_PROFILES[args.profile].name
        walk = walker.walk_from_profile(
            start=start, profile=args.profile, steps=args.steps, seed=args.seed
        )

    # Display or save walk
    if args.output:
        # Save to file
        output_data = {
            "profile": (
                args.profile
                if not (args.max_flips or args.temperature or args.frequency_weight)
                else "custom"
            ),
            "start": start,
            "steps": args.steps,
            "seed": args.seed,
            "path": " → ".join(s["syllable"] for s in walk),
            "syllables": walk,
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        if not args.quiet:
            print(f"✓ Walk saved to: {args.output}")
    else:
        # Print to console
        print(f"\n{profile_name}")
        print("=" * len(profile_name))
        print("\nPath:")
        print("  " + " → ".join(s["syllable"] for s in walk))
        print("\nDetails:")
        for i, s in enumerate(walk, 1):
            print(f"  {i:2d}. {s['syllable']:>10}  (frequency: {s['frequency']:>6})")

    return 0


def compare_profiles_mode(walker: SyllableWalker, args: argparse.Namespace) -> int:
    """
    Handle profile comparison mode.

    Args:
        walker: Initialized SyllableWalker instance
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Determine starting syllable
    if args.start:
        start = args.start
        if start not in walker.syllable_to_idx:
            print(f"Error: Syllable '{start}' not found in dataset", file=sys.stderr)
            return 1
    else:
        start = walker.get_random_syllable(seed=args.seed)

    print("\n" + "=" * 70)
    print(f"Profile Comparison - Starting from: {start}")
    if args.seed is not None:
        print(f"Random seed: {args.seed}")
    print("=" * 70)

    # Generate walk for each profile
    for profile_name, profile in walker.get_available_profiles().items():
        walk = walker.walk_from_profile(
            start=start, profile=profile_name, steps=args.steps, seed=args.seed
        )

        print(f"\n{profile.name}")
        print("-" * len(profile.name))
        print(f"Description: {profile.description}")
        print("\nPath:")
        print("  " + " → ".join(s["syllable"] for s in walk))
        print("\nDetails:")
        for i, s in enumerate(walk, 1):
            print(f"  {i:2d}. {s['syllable']:>10}  (frequency: {s['frequency']:>6})")

    return 0


def batch_mode(walker: SyllableWalker, args: argparse.Namespace) -> int:
    """
    Handle batch walk generation mode.

    Args:
        walker: Initialized SyllableWalker instance
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if not args.quiet:
        print(f"\nGenerating {args.batch} walks using '{args.profile}' profile...")

    walks = []
    for i in range(args.batch):
        # Determine starting syllable for this walk
        if args.start:
            start = args.start
        else:
            # Use different seed for each walk if seed is provided
            walk_seed = (args.seed + i) if args.seed is not None else None
            start = walker.get_random_syllable(seed=walk_seed)

        # Generate walk
        walk = walker.walk_from_profile(
            start=start, profile=args.profile, steps=args.steps, seed=args.seed
        )
        walks.append(walk)

        # Progress indicator
        if not args.quiet and ((i + 1) % 10 == 0 or (i + 1) == args.batch):
            print(f"  Progress: {i + 1}/{args.batch} walks generated")

    # Save or display results
    if args.output:
        output_data = {
            "profile": args.profile,
            "steps": args.steps,
            "count": args.batch,
            "seed": args.seed,
            "walks": [
                {"path": " → ".join(s["syllable"] for s in walk), "syllables": walk}
                for walk in walks
            ],
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        if not args.quiet:
            print(f"\n✓ Saved {args.batch} walks to: {args.output}")
    else:
        # Print summary
        if not args.quiet:
            print("\nBatch Summary:")
            print(f"  Total walks: {len(walks)}")
            avg_length = sum(len(w) for w in walks) / len(walks)
            print(f"  Average path length: {avg_length:.1f}")
            unique_syllables = len(set(s["syllable"] for walk in walks for s in walk))
            print(f"  Unique syllables visited: {unique_syllables}")

    return 0


def search_mode(walker: SyllableWalker, args: argparse.Namespace) -> int:
    """
    Handle syllable search mode.

    Args:
        walker: Initialized SyllableWalker instance
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success)
    """
    query_lower = args.search.lower()
    matches = [s for s in walker.syllables if query_lower in s.lower()]

    if not matches:
        print(f"\nNo syllables found matching '{args.search}'")
        return 0

    print(f"\nFound {len(matches)} syllable(s) matching '{args.search}':")
    print("-" * 70)

    # Show first 20 matches
    for syllable in matches[:20]:
        info = walker.get_syllable_info(syllable)
        if info:
            print(f"  {syllable:>15}  (frequency: {info['frequency']:>8})")

    if len(matches) > 20:
        print(f"\n  ... and {len(matches) - 20} more")
        print("\nTip: Narrow your search query to see all results")

    return 0


def web_mode(args: argparse.Namespace) -> int:
    """
    Handle web server mode.

    Starts the simplified web interface for browsing name selections and
    exploring syllable walks. The server auto-discovers pipeline runs from
    _working/output/ and provides a selections browser with walk generation.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, 1 = error)

    Notes:
        - Server auto-discovers available ports starting at 8000 if --port not specified
        - Walker initialization is lazy (happens when user selects a run)
        - The server runs until stopped with Ctrl+C
    """
    try:
        # run_server handles run discovery and server lifecycle
        # Port is None means auto-discover starting at 8000
        run_server(
            port=args.port,
            verbose=not args.quiet,
        )
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        if args.port:
            print(f"\nPort {args.port} may already be in use.", file=sys.stderr)
            print("Try using a different port with --port option.", file=sys.stderr)
        else:
            print("\nCould not find an available port.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """
    Main entry point for syllable walker CLI.

    Parses arguments, validates inputs, initializes walker, and executes
    requested operation mode.

    Returns:
        Exit code:
        - 0: Success
        - 1: Error (file not found, invalid arguments, etc.)
        - 2: Validation error (incompatible arguments)
        - 130: Keyboard interrupt (Ctrl+C)

    Notes:
        - Errors are printed to stderr
        - Normal output goes to stdout
        - Keyboard interrupt (Ctrl+C) exits cleanly with code 130
    """
    args = parse_arguments()

    try:
        # Validate argument combinations
        if args.quiet and args.verbose:
            print(
                "Error: --quiet and --verbose are mutually exclusive",
                file=sys.stderr,
            )
            return 2

        # Handle web mode early (may not need data_file)
        if args.web:
            # data_file is optional in web mode (will auto-discover)
            return web_mode(args)

        # For CLI modes, data_file is required
        if not args.data_file:
            print("Error: data_file is required for CLI mode", file=sys.stderr)
            print(
                "\nUsage: python -m build_tools.syllable_walk <data_file> [options]",
                file=sys.stderr,
            )
            print(
                "\nFor web mode with auto-discovery, use: python -m build_tools.syllable_walk --web",
                file=sys.stderr,
            )
            return 1

        # Validate data file exists
        if not args.data_file.exists():
            print(f"Error: Data file not found: {args.data_file}", file=sys.stderr)
            print(
                "\nThe data file should be the output from syllable_feature_annotator:",
                file=sys.stderr,
            )
            print("  python -m build_tools.syllable_feature_annotator", file=sys.stderr)
            return 1

        # Initialize walker
        if not args.quiet:
            print("=" * 70)
            print("Syllable Walker")
            print("=" * 70)
            print(f"\nInitializing from: {args.data_file}")
            if args.max_neighbor_distance == 3:
                print("This may take 2-3 minutes for large datasets (500k+ syllables)...")
            print()

        walker = SyllableWalker(
            args.data_file,
            max_neighbor_distance=args.max_neighbor_distance,
            verbose=args.verbose,
        )

        if not args.quiet:
            print("\n" + "=" * 70)
            print("✓ Walker ready!")
            print("=" * 70)
            print(f"Total syllables: {len(walker.syllables):,}")
            print(f"Available profiles: {', '.join(WALK_PROFILES.keys())}")
            print()

        # Execute mode
        if args.search:
            return search_mode(walker, args)
        elif args.compare_profiles:
            return compare_profiles_mode(walker, args)
        elif args.batch:
            return batch_mode(walker, args)
        else:
            return single_walk_mode(walker, args)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
