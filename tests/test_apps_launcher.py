"""Tests for the unified pipeworks-app launcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeworks_name_generation.apps import main


def test_dispatches_name_gen_with_expected_arguments() -> None:
    """name-gen subcommand should forward compatible args to webapp server CLI."""
    captured: list[list[str]] = []

    def fake_run_name_gen(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    result = main(
        [
            "name-gen",
            "--config",
            "server.ini",
            "--host",
            "0.0.0.0",
            "--port",
            "8012",
            "--quiet",
            "--api-only",
        ],
        run_name_gen=fake_run_name_gen,
        run_syllable_walk=lambda _argv: 1,
    )

    assert result == 0
    assert captured == [
        [
            "--config",
            "server.ini",
            "--host",
            "0.0.0.0",
            "--port",
            "8012",
            "--quiet",
            "--api-only",
        ]
    ]


def test_dispatches_syllable_walk_with_expected_arguments(tmp_path: Path) -> None:
    """syllable-walk subcommand should forward compatible args to its CLI."""
    captured: list[list[str]] = []

    def fake_run_syllable_walk(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    result = main(
        [
            "syllable-walk",
            "--config",
            "server.ini",
            "--port",
            "8009",
            "--quiet",
            "--output-base",
            str(tmp_path / "output"),
            "--sessions-dir",
            str(tmp_path / "sessions"),
        ],
        run_name_gen=lambda _argv: 1,
        run_syllable_walk=fake_run_syllable_walk,
    )

    assert result == 0
    assert captured == [
        [
            "--config",
            "server.ini",
            "--port",
            "8009",
            "--quiet",
            "--output-base",
            str(tmp_path / "output"),
            "--sessions-dir",
            str(tmp_path / "sessions"),
        ]
    ]


def test_dispatches_both_with_expected_arguments(tmp_path: Path) -> None:
    """both subcommand should build and forward args for both child launchers."""
    captured: list[tuple[list[str], list[str]]] = []

    def fake_run_both(name_gen_argv: list[str], syllable_walk_argv: list[str]) -> int:
        captured.append((name_gen_argv, syllable_walk_argv))
        return 0

    result = main(
        [
            "both",
            "--config",
            "server.ini",
            "--quiet",
            "--name-gen-host",
            "0.0.0.0",
            "--name-gen-port",
            "8007",
            "--syllable-walk-port",
            "8008",
            "--output-base",
            str(tmp_path / "output"),
            "--sessions-dir",
            str(tmp_path / "sessions"),
        ],
        run_name_gen=lambda _argv: 1,
        run_syllable_walk=lambda _argv: 1,
        run_both=fake_run_both,
    )

    assert result == 0
    assert captured == [
        (
            [
                "--config",
                "server.ini",
                "--host",
                "0.0.0.0",
                "--port",
                "8007",
                "--quiet",
            ],
            [
                "--config",
                "server.ini",
                "--port",
                "8008",
                "--quiet",
                "--output-base",
                str(tmp_path / "output"),
                "--sessions-dir",
                str(tmp_path / "sessions"),
            ],
        )
    ]


def test_requires_app_subcommand() -> None:
    """Launcher should require explicit target app selection."""
    with pytest.raises(SystemExit):
        main([])
