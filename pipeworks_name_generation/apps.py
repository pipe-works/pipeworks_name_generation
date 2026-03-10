"""Unified launcher for the Pipeworks Name Generation web applications."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Sequence


def create_argument_parser() -> argparse.ArgumentParser:
    """Create a parser with app subcommands and shared launch options."""
    parser = argparse.ArgumentParser(
        prog="pipeworks-app",
        description="Launch Pipeworks Name Generation web applications.",
    )
    subparsers = parser.add_subparsers(dest="app", required=True)

    name_gen = subparsers.add_parser(
        "name-gen",
        help="Launch the Name Generator web app.",
    )
    name_gen.add_argument(
        "--config",
        type=Path,
        default=Path("server.ini"),
        help="Path to INI config file (default: server.ini).",
    )
    name_gen.add_argument("--host", type=str, default=None, help="Override server host.")
    name_gen.add_argument("--port", type=int, default=None, help="Override server port.")
    name_gen.add_argument("--quiet", action="store_true", help="Disable verbose logging.")
    name_gen.add_argument(
        "--api-only",
        action="store_true",
        help="Serve API routes only (no UI/static assets).",
    )

    syllable_walk = subparsers.add_parser(
        "syllable-walk",
        help="Launch the Syllable Walk web app.",
    )
    syllable_walk.add_argument(
        "--config",
        type=Path,
        default=Path("server.ini"),
        help="Path to INI config file (default: server.ini).",
    )
    syllable_walk.add_argument("--port", type=int, default=None, help="Override server port.")
    syllable_walk.add_argument("--quiet", action="store_true", help="Disable verbose logging.")
    syllable_walk.add_argument(
        "--output-base",
        type=Path,
        default=None,
        help="Override corpus output base directory.",
    )
    syllable_walk.add_argument(
        "--sessions-dir",
        type=Path,
        default=None,
        help="Override walker sessions directory.",
    )

    both = subparsers.add_parser(
        "both",
        help="Launch Name Generator and Syllable Walk web apps together.",
    )
    both.add_argument(
        "--config",
        type=Path,
        default=Path("server.ini"),
        help="Path to INI config file (default: server.ini).",
    )
    both.add_argument("--quiet", action="store_true", help="Disable verbose logging in both apps.")
    both.add_argument(
        "--name-gen-host",
        type=str,
        default=None,
        help="Override Name Generator server host.",
    )
    both.add_argument(
        "--name-gen-port",
        type=int,
        default=None,
        help="Override Name Generator server port.",
    )
    both.add_argument(
        "--syllable-walk-port",
        type=int,
        default=None,
        help="Override Syllable Walk server port.",
    )
    both.add_argument(
        "--output-base",
        type=Path,
        default=None,
        help="Override Syllable Walk corpus output base directory.",
    )
    both.add_argument(
        "--sessions-dir",
        type=Path,
        default=None,
        help="Override Syllable Walk sessions directory.",
    )

    return parser


def _run_name_gen(argv: list[str]) -> int:
    """Run the Name Generator web app entrypoint."""
    from pipeworks_name_generation.webapp.server import main as name_gen_main

    return name_gen_main(argv)


def _run_syllable_walk(argv: list[str]) -> int:
    """Run the Syllable Walk web app entrypoint."""
    try:
        from build_tools.syllable_walk_web.cli import main as syllable_walk_main
    except Exception as exc:  # pragma: no cover - defensive import path
        raise RuntimeError(
            "Syllable Walk web app import failed. Install build-tools extras: "
            '`pip install -e ".[build-tools]"`.'
        ) from exc
    return syllable_walk_main(argv)


def _stop_process(process: subprocess.Popen[bytes | str]) -> None:
    """Terminate a subprocess and force-kill if it does not exit quickly."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _run_both(name_gen_argv: list[str], syllable_walk_argv: list[str]) -> int:
    """Run both web apps concurrently and forward their stdout/stderr."""
    name_gen_cmd = [
        sys.executable,
        "-m",
        "pipeworks_name_generation.webapp.server",
        *name_gen_argv,
    ]
    syllable_walk_cmd = [
        sys.executable,
        "-m",
        "build_tools.syllable_walk_web",
        *syllable_walk_argv,
    ]

    name_gen_proc = subprocess.Popen(name_gen_cmd)
    # Stagger process starts to avoid auto-port race conditions.
    time.sleep(0.4)
    if name_gen_proc.poll() not in (None, 0):
        return int(name_gen_proc.returncode or 1)

    syllable_walk_proc = subprocess.Popen(syllable_walk_cmd)

    try:
        while True:
            name_gen_rc = name_gen_proc.poll()
            syllable_walk_rc = syllable_walk_proc.poll()
            if name_gen_rc is not None or syllable_walk_rc is not None:
                _stop_process(name_gen_proc)
                _stop_process(syllable_walk_proc)
                if name_gen_rc not in (None, 0):
                    return int(name_gen_rc)
                if syllable_walk_rc not in (None, 0):
                    return int(syllable_walk_rc)
                return 0
            time.sleep(0.2)
    except KeyboardInterrupt:
        _stop_process(name_gen_proc)
        _stop_process(syllable_walk_proc)
        return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    run_name_gen: Callable[[list[str]], int] = _run_name_gen,
    run_syllable_walk: Callable[[list[str]], int] = _run_syllable_walk,
    run_both: Callable[[list[str], list[str]], int] = _run_both,
) -> int:
    """Dispatch to one of the web app CLIs using a shared command shape."""
    parser = create_argument_parser()
    parsed = parser.parse_args(list(argv) if argv is not None else None)

    config_path = parsed.config if isinstance(parsed.config, Path) else Path(parsed.config)

    if parsed.app == "name-gen":
        command_args: list[str] = ["--config", str(config_path)]
        if parsed.host:
            command_args.extend(["--host", parsed.host])
        if parsed.port is not None:
            command_args.extend(["--port", str(parsed.port)])
        if parsed.quiet:
            command_args.append("--quiet")
        if parsed.api_only:
            command_args.append("--api-only")
        return run_name_gen(command_args)

    if parsed.app == "syllable-walk":
        command_args = ["--config", str(config_path)]
        if parsed.port is not None:
            command_args.extend(["--port", str(parsed.port)])
        if parsed.quiet:
            command_args.append("--quiet")
        if parsed.output_base is not None:
            command_args.extend(["--output-base", str(parsed.output_base)])
        if parsed.sessions_dir is not None:
            command_args.extend(["--sessions-dir", str(parsed.sessions_dir)])
        return run_syllable_walk(command_args)

    if parsed.app == "both":
        name_gen_args = ["--config", str(config_path)]
        if parsed.name_gen_host:
            name_gen_args.extend(["--host", parsed.name_gen_host])
        if parsed.name_gen_port is not None:
            name_gen_args.extend(["--port", str(parsed.name_gen_port)])
        if parsed.quiet:
            name_gen_args.append("--quiet")

        syllable_walk_args = ["--config", str(config_path)]
        if parsed.syllable_walk_port is not None:
            syllable_walk_args.extend(["--port", str(parsed.syllable_walk_port)])
        if parsed.quiet:
            syllable_walk_args.append("--quiet")
        if parsed.output_base is not None:
            syllable_walk_args.extend(["--output-base", str(parsed.output_base)])
        if parsed.sessions_dir is not None:
            syllable_walk_args.extend(["--sessions-dir", str(parsed.sessions_dir)])
        return run_both(name_gen_args, syllable_walk_args)

    parser.error(f"Unsupported app: {parsed.app}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
