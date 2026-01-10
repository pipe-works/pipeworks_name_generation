"""
Command-line interface for syllable feature annotator.

This module provides argument parsing and CLI orchestration for the
syllable feature annotation tool. It handles user input, validates
arguments, and provides clear error messages.

Design Principles
-----------------
1. **Clear Contract**: Explicit required and optional arguments
2. **Helpful Defaults**: Sensible default paths matching normalizer output
3. **User-Friendly Errors**: Clear messages when things go wrong
4. **Clean Exit**: Proper exit codes for shell scripting

Functions
---------
parse_arguments(args: list[str] | None) -> argparse.Namespace
    Parse command-line arguments
main(args: list[str] | None) -> int
    Main CLI entry point with error handling

Usage
-----
Run from command line::

    $ python -m build_tools.syllable_feature_annotator \\
        --syllables data/normalized/syllables_unique.txt \\
        --frequencies data/normalized/syllables_frequencies.json \\
        --output data/annotated/syllables_annotated.json

Use default paths::

    $ python -m build_tools.syllable_feature_annotator

Enable verbose output::

    $ python -m build_tools.syllable_feature_annotator --verbose

Get help::

    $ python -m build_tools.syllable_feature_annotator --help

CLI Arguments
-------------
--syllables PATH
    Path to syllables text file (one per line)
    Default: data/normalized/syllables_unique.txt

--frequencies PATH
    Path to frequencies JSON file (syllable → count mapping)
    Default: data/normalized/syllables_frequencies.json

--output PATH
    Path where annotated JSON should be written
    Default: data/annotated/syllables_annotated.json

--verbose, -v
    Show detailed progress information

--help, -h
    Show help message and exit

Exit Codes
----------
0 : Success
    Annotation completed successfully
1 : Error
    File not found, invalid input, or other error

Examples
--------
Process normalized syllables with default paths::

    $ python -m build_tools.syllable_feature_annotator
    Annotation complete!
      Syllables annotated: 1,523
      Features per syllable: 12
      Processing time: 0.342s

Custom paths with verbose output::

    $ python -m build_tools.syllable_feature_annotator \\
        --syllables custom/syllables.txt \\
        --frequencies custom/frequencies.json \\
        --output output/annotated.json \\
        --verbose
    Loading syllables from custom/syllables.txt...
    Loading frequencies from custom/frequencies.json...
    Annotating 1523 syllables...
    Saving annotated syllables to output/annotated.json...

    Annotation complete!
      Syllables annotated: 1,523
      Features per syllable: 12
      Total corpus frequency: 8,472
      Processing time: 0.342s
      Output saved to: output/annotated.json

Error Handling
--------------
The CLI catches common errors and provides user-friendly messages:

File not found::

    $ python -m build_tools.syllable_feature_annotator --syllables missing.txt
    Error: Input file not found: missing.txt
    Please ensure the file exists and is readable.

Invalid JSON::

    $ python -m build_tools.syllable_feature_annotator --frequencies bad.json
    Error: Invalid JSON in frequencies file: bad.json
    Expecting property name enclosed in double quotes: line 1 column 2 (char 1)

Permission error::

    $ python -m build_tools.syllable_feature_annotator --output /readonly/output.json
    Error: Permission denied: /readonly/output.json
    Please check file permissions.

Integration with Pipeline
-------------------------
This CLI is designed to work seamlessly with the syllable normalizer:

1. Run syllable normalizer to create normalized syllables
2. Run feature annotator to add features to syllables
3. Use annotated syllables for pattern development

Example workflow::

    # Step 1: Normalize syllables from corpus
    $ python -m build_tools.pyphen_syllable_normaliser \\
        --source data/corpus/ \\
        --output data/normalized/

    # Step 2: Annotate normalized syllables with features
    $ python -m build_tools.syllable_feature_annotator \\
        --syllables data/normalized/syllables_unique.txt \\
        --frequencies data/normalized/syllables_frequencies.json \\
        --output data/annotated/syllables_annotated.json

    # Step 3: Use annotated syllables for pattern generation
    # (future tools will consume syllables_annotated.json)

Notes
-----
- All paths can be absolute or relative to current working directory
- Output directory is created automatically if it doesn't exist
- Existing output files are overwritten without warning
- Verbose mode is recommended for first-time users
- Exit codes follow Unix conventions (0=success, 1=error)
"""

import argparse
import sys
from pathlib import Path

from build_tools.syllable_feature_annotator.annotator import run_annotation_pipeline


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for syllable feature annotator.

    This function creates the ArgumentParser with all CLI options but does not
    parse arguments. This separation allows Sphinx documentation tools to
    introspect the parser and auto-generate CLI documentation.

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser ready to parse command-line arguments

    Examples
    --------
    Create parser and inspect options::

        >>> parser = create_argument_parser()
        >>> parser.prog
        'cli.py'

    Use parser to parse arguments::

        >>> parser = create_argument_parser()
        >>> args = parser.parse_args(["--syllables", "data/syllables.txt"])
        >>> args.syllables
        PosixPath('data/syllables.txt')

    Notes
    -----
    - This function is used by both the CLI and documentation generation
    - For normal CLI usage, use parse_arguments() instead
    - Sphinx-argparse can introspect this function to generate docs
    """
    parser = argparse.ArgumentParser(
        description="Annotate syllables with phonetic feature detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Annotate with default paths (normalizer output)
   python -m build_tools.syllable_feature_annotator

   # Annotate with custom paths
   python -m build_tools.syllable_feature_annotator \\
     --syllables data/normalized/syllables_unique.txt \\
     --frequencies data/normalized/syllables_frequencies.json \\
     --output data/annotated/syllables_annotated.json

   # Enable verbose output
   python -m build_tools.syllable_feature_annotator --verbose

For more information, see the documentation in CLAUDE.md
        """,
    )

    parser.add_argument(
        "--syllables",
        type=Path,
        default=Path("data/normalized/syllables_unique.txt"),
        help="Path to syllables text file (one per line). Default: data/normalized/syllables_unique.txt",
    )

    parser.add_argument(
        "--frequencies",
        type=Path,
        default=Path("data/normalized/syllables_frequencies.json"),
        help="Path to frequencies JSON file. Default: data/normalized/syllables_frequencies.json",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/annotated/syllables_annotated.json"),
        help="Path for annotated output JSON. Default: data/annotated/syllables_annotated.json",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress information",
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments for syllable feature annotator.

    Creates an argument parser with all CLI options and parses the
    provided arguments (or sys.argv if none provided).

    Parameters
    ----------
    args : list[str] | None, optional
        List of argument strings to parse. If None, uses sys.argv[1:]
        This parameter exists primarily for testing purposes.

    Returns
    -------
    argparse.Namespace
        Parsed arguments with attributes:
        - syllables (Path): Path to syllables file
        - frequencies (Path): Path to frequencies file
        - output (Path): Path to output file
        - verbose (bool): Whether to show progress

    Examples
    --------
    Parse command-line arguments::

        >>> args = parse_arguments(["--syllables", "data/syllables.txt"])
        >>> args.syllables
        PosixPath('data/syllables.txt')

    Parse with all arguments::

        >>> args = parse_arguments([
        ...     "--syllables", "input/syllables.txt",
        ...     "--frequencies", "input/frequencies.json",
        ...     "--output", "output/annotated.json",
        ...     "--verbose"
        ... ])
        >>> args.verbose
        True

    Use default values::

        >>> args = parse_arguments([])
        >>> args.syllables
        PosixPath('data/normalized/syllables_unique.txt')

    Notes
    -----
    - All path arguments are automatically converted to Path objects
    - Default paths match standard normalizer output locations
    - Help message is automatically generated from argument definitions
    - Invalid arguments trigger help message and exit
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """
    Main CLI entry point with error handling.

    Parses arguments, runs annotation pipeline, and handles errors
    gracefully with user-friendly messages.

    Parameters
    ----------
    args : list[str] | None, optional
        List of argument strings to parse. If None, uses sys.argv[1:]
        This parameter exists primarily for testing purposes.

    Returns
    -------
    int
        Exit code (0 for success, 1 for error)

    Examples
    --------
    Run with default arguments::

        >>> exit_code = main([])  # doctest: +SKIP
        >>> exit_code
        0

    Run with custom arguments::

        >>> exit_code = main([
        ...     "--syllables", "data/syllables.txt",
        ...     "--output", "output/annotated.json",
        ...     "--verbose"
        ... ])  # doctest: +SKIP
        >>> exit_code
        0

    Handle error case::

        >>> exit_code = main(["--syllables", "missing.txt"])  # doctest: +SKIP
        Error: Input file not found: missing.txt
        >>> exit_code
        1

    Notes
    -----
    - Catches common errors and provides user-friendly messages
    - Exit code 0 indicates success, 1 indicates error
    - Verbose output is controlled by --verbose flag
    - All exceptions are caught and converted to error messages
    """
    try:
        # Parse arguments
        parsed_args = parse_arguments(args)

        # Run annotation pipeline
        result = run_annotation_pipeline(
            syllables_path=parsed_args.syllables,
            frequencies_path=parsed_args.frequencies,
            output_path=parsed_args.output,
            verbose=parsed_args.verbose,
        )

        # Print summary if not verbose (verbose mode already prints)
        if not parsed_args.verbose:
            print("Annotation complete!")
            print(f"  Syllables annotated: {result.statistics.syllable_count:,}")
            print(f"  Features per syllable: {result.statistics.feature_count}")
            print(f"  Processing time: {result.statistics.processing_time:.3f}s")
            print(f"  Output saved to: {parsed_args.output}")

        return 0  # Success

    except FileNotFoundError as e:
        print(f"Error: Input file not found: {e.filename}", file=sys.stderr)
        print("Please ensure the file exists and is readable.", file=sys.stderr)
        return 1

    except ValueError as e:
        print(f"Error: Invalid input data: {e}", file=sys.stderr)
        print("Please check that input files are properly formatted.", file=sys.stderr)
        return 1

    except PermissionError as e:
        print(f"Error: Permission denied: {e.filename}", file=sys.stderr)
        print("Please check file permissions.", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        print("An unexpected error occurred. Please check your inputs.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
