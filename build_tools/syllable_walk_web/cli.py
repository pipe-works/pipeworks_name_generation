"""
Command-line interface for the Pipe-Works Build Tools web application.

Provides ``python -m build_tools.syllable_walk_web`` entry point.
"""

from __future__ import annotations

import argparse
import sys
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildToolsSettings:
    """Settings loaded from the ``[build_tools]`` INI section.

    Attributes:
        output_base: Base directory for pipeline run discovery.
        sessions_dir: Optional explicit session storage directory.
        corpus_dir_a: Directory containing runs to auto-load into Patch A.
        corpus_dir_b: Directory containing runs to auto-load into Patch B.
        port: Optional explicit port. ``None`` means auto-select.
        verbose: Print startup/runtime messages when True.
    """

    output_base: Path | None = None
    sessions_dir: Path | None = None
    corpus_dir_a: str | None = None
    corpus_dir_b: str | None = None
    port: int | None = None
    verbose: bool = True


def load_build_tools_settings(config_path: Path | None) -> BuildToolsSettings:
    """Load build-tools settings from the ``[build_tools]`` INI section.

    Args:
        config_path: Path to INI file. If missing/None, defaults are used.

    Returns:
        Parsed ``BuildToolsSettings`` instance.
    """
    settings = BuildToolsSettings()

    if config_path is None or not config_path.exists():
        return settings

    parser = ConfigParser()
    parser.read(config_path, encoding="utf-8")

    if not parser.has_section("build_tools"):
        return settings

    raw_output = parser.get("build_tools", "output_base", fallback=None)
    output_base: Path | None = None
    if raw_output is not None:
        stripped = raw_output.strip()
        if stripped:
            output_base = Path(stripped).expanduser()

    raw_sessions = parser.get("build_tools", "sessions_dir", fallback=None)
    sessions_dir: Path | None = None
    if raw_sessions is not None:
        stripped = raw_sessions.strip()
        if stripped:
            sessions_dir = Path(stripped).expanduser()

    raw_corpus_a = parser.get("build_tools", "corpus_dir_a", fallback=None)
    corpus_dir_a: str | None = None
    if raw_corpus_a is not None:
        stripped = raw_corpus_a.strip()
        if stripped:
            corpus_dir_a = stripped

    raw_corpus_b = parser.get("build_tools", "corpus_dir_b", fallback=None)
    corpus_dir_b: str | None = None
    if raw_corpus_b is not None:
        stripped = raw_corpus_b.strip()
        if stripped:
            corpus_dir_b = stripped

    raw_port = parser.get("build_tools", "port", fallback=None)
    port: int | None = None
    if raw_port is not None:
        stripped = raw_port.strip()
        if stripped:
            port = int(stripped)

    verbose = parser.getboolean("build_tools", "verbose", fallback=settings.verbose)

    return BuildToolsSettings(
        output_base=output_base,
        sessions_dir=sessions_dir,
        corpus_dir_a=corpus_dir_a,
        corpus_dir_b=corpus_dir_b,
        port=port,
        verbose=verbose,
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for the web server.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Launch the Pipe-Works Build Tools web application. "
            "Combines Pipeline (extraction/normalization/annotation) and "
            "Walker (dual-patch syllable walking, name generation) tools "
            "in a browser-based interface."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples::

  # Launch on auto-detected port (default)
  python -m build_tools.syllable_walk_web

  # Launch on a specific port
  python -m build_tools.syllable_walk_web --port 9000

  # Launch in quiet mode (suppress HTTP request logs)
  python -m build_tools.syllable_walk_web --quiet

  # Use a custom config file
  python -m build_tools.syllable_walk_web --config server.ini
        """,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "Port to serve on. If not specified, automatically finds an "
            "available port (checks 8000-8099 first, then 8100-8999). "
            "Default: auto-detect"
        ),
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress HTTP request logging. Default: False",
    )

    parser.add_argument(
        "--output-base",
        type=str,
        default=None,
        help=("Base directory for pipeline run discovery. " "Default: _working/output"),
    )

    parser.add_argument(
        "--sessions-dir",
        type=str,
        default=None,
        help=("Optional directory for saved walker sessions. " "Default: <output_base>/sessions"),
    )

    parser.add_argument(
        "--config",
        type=str,
        default="server.ini",
        help=(
            "Path to INI config file. Reads the [build_tools] section for "
            "output_base, sessions_dir, corpus_dir_a, corpus_dir_b, port, "
            "and verbose. CLI arguments override INI values. "
            "Default: server.ini"
        ),
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """CLI entry point.

    Returns:
        Exit code: 0 for success, 1 for error, 130 for keyboard interrupt.
    """
    parsed = parse_arguments(args)

    try:
        from build_tools.syllable_walk_web.server import run_server

        # Load INI settings, then let CLI args override.
        ini_settings = load_build_tools_settings(Path(parsed.config))

        # Resolve output_base: CLI > INI > None
        if parsed.output_base is not None:
            output_base = Path(parsed.output_base)
        elif ini_settings.output_base is not None:
            output_base = ini_settings.output_base
        else:
            output_base = None

        # Resolve sessions_dir: CLI > INI > None
        if parsed.sessions_dir is not None:
            sessions_dir = Path(parsed.sessions_dir)
        elif ini_settings.sessions_dir is not None:
            sessions_dir = ini_settings.sessions_dir
        else:
            sessions_dir = None

        # Resolve port: CLI > INI > None
        port = parsed.port if parsed.port is not None else ini_settings.port

        # Resolve verbose: --quiet CLI flag overrides INI
        verbose = not parsed.quiet if parsed.quiet else ini_settings.verbose

        return run_server(
            port=port,
            verbose=verbose,
            output_base=output_base,
            sessions_dir=sessions_dir,
            corpus_dir_a=ini_settings.corpus_dir_a,
            corpus_dir_b=ini_settings.corpus_dir_b,
        )
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
