#!/usr/bin/env python3
"""Restore a name_packages SQLite database from a local file.

This script is designed for server-side use. A typical workflow is:

1. Export the database on a local machine via the web UI.
2. Copy the exported ``.sqlite3`` file to the server (for example with scp).
3. Run this script on the server to replace the live database.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for database restore."""
    parser = argparse.ArgumentParser(
        description="Restore the Pipeworks name_packages SQLite database from a backup file."
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Destination database path used by the webapp.",
    )
    parser.add_argument(
        "--import",
        dest="import_path",
        required=True,
        help="Path to the exported SQLite database file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing the destination database if it already exists.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a pre-restore backup of the destination database.",
    )
    parser.add_argument(
        "--backup-path",
        default=None,
        help="Optional path for the pre-restore backup file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for restoring a database file."""
    # Allow running the script from a repo checkout without installing the package.
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from pipeworks_name_generation.webapp.db.backup import restore_database

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.backup_path and args.no_backup:
        parser.error("--backup-path cannot be used with --no-backup.")

    result = restore_database(
        Path(args.db),
        import_path=Path(args.import_path),
        overwrite=bool(args.overwrite),
        create_backup=not args.no_backup,
        backup_path=Path(args.backup_path) if args.backup_path else None,
    )

    print("Restore completed.")
    print(f"  Restored DB: {result.restored_path}")
    if result.backup_path:
        print(f"  Pre-restore backup: {result.backup_path}")
    print(f"  Bytes written: {result.bytes_written}")
    print(f"  SHA-256: {result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
