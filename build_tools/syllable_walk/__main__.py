"""
Entry point for running syllable_walk as a module.

This module enables the package to be run directly with:
    python -m build_tools.syllable_walk

It simply delegates to the CLI main function, which handles all
argument parsing, error handling, and walk execution.

Usage
-----
Run as module::

    $ python -m build_tools.syllable_walk data.json --start ka --profile dialect

This is equivalent to::

    $ python -m build_tools.syllable_walk.cli

Notes
-----
- This follows Python's standard pattern for executable packages
- The __main__.py file makes the package directly executable
- All functionality is in cli.py; this is just a thin wrapper
- Exit codes are passed through from cli.main()
"""

from build_tools.syllable_walk.cli import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
