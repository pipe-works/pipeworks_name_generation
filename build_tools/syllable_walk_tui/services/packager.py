"""
Selection packaging service for the Syllable Walker TUI.

This module provides a focused utility for bundling selection outputs
from a pipeline run directory into a single distributable archive.
The output is a ZIP file containing the selection files and a manifest
that summarizes what was included.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class SelectionInventory:
    """
    Inventory of selection files discovered in a run directory.

    Attributes:
        run_dir: Root run directory containing the selections folder
        selections_dir: Path to the selections directory
        selection_json: JSON selection outputs (excluding meta)
        selection_txt: TXT exports associated with selections
        meta_json: Meta JSON files (selector metadata)
    """

    run_dir: Path
    selections_dir: Path
    selection_json: list[Path]
    selection_txt: list[Path]
    meta_json: list[Path]


@dataclass
class PackageOptions:
    """
    Configuration for packaging selection outputs.

    Attributes:
        run_dir: Run directory containing the selections folder
        output_dir: Destination directory for the package (default: run_dir/packages)
        package_name: Optional filename for the ZIP (default: <run_dir>_selections.zip)
        include_json: Whether to include JSON selection outputs
        include_txt: Whether to include TXT exports
        include_meta: Whether to include selector meta JSON files
        include_manifest: Whether to include a generated manifest in the ZIP
    """

    run_dir: Path
    output_dir: Path | None = None
    package_name: str | None = None
    include_json: bool = True
    include_txt: bool = True
    include_meta: bool = True
    include_manifest: bool = True


@dataclass
class PackageResult:
    """
    Result from packaging selections.

    Attributes:
        package_path: Path to the created ZIP archive
        included_files: Files written into the archive
        manifest: Manifest payload that was written (if enabled)
        error: Error message if the operation failed
    """

    package_path: Path
    included_files: list[Path]
    manifest: dict | None
    error: str | None = None


def _extract_extractor_type(run_dir: Path) -> str | None:
    """
    Extract extractor type (pyphen, nltk, etc.) from the run directory name.

    Expected format: YYYYMMDD_HHMMSS_<extractor>

    Args:
        run_dir: Path to run directory

    Returns:
        Extractor type string, or None if not parseable
    """
    # Split the run directory name into timestamp + extractor parts
    parts = run_dir.name.split("_")
    if len(parts) < 3:
        return None
    # Re-join anything after the timestamp to support multi-word extractors
    return "_".join(parts[2:])


def _is_meta_file(path: Path) -> bool:
    """
    Determine if a JSON file is a selector metadata file.

    Args:
        path: Path to a JSON file

    Returns:
        True if the file appears to be selector metadata
    """
    # Selector metadata files always end with "_meta.json" in this project
    return path.name.endswith("_meta.json")


def _parse_selection_filename(filename: str) -> tuple[str | None, str | None]:
    """
    Parse name class and syllable label from a selection filename.

    Examples::
        pyphen_first_name_2syl.json -> ("first_name", "2syl")
        nltk_last_name_all.txt      -> ("last_name", "all")

    Args:
        filename: File name to parse (no directory)

    Returns:
        Tuple of (name_class, syllable_label). Returns (None, None) if parsing fails.
    """
    # Strip extension to make token parsing uniform for .json/.txt
    stem = Path(filename).stem
    parts = stem.split("_")
    # Expected: <prefix>_<name_class...>_<syllable_label>
    if len(parts) < 3:
        return (None, None)
    syllable_label = parts[-1]
    # Syllable labels we expect: 2syl, 3syl, 4syl, all
    if not (syllable_label.endswith("syl") or syllable_label == "all"):
        return (None, None)
    name_class = "_".join(parts[1:-1])
    return (name_class or None, syllable_label)


def collect_included_files(
    run_dir: Path,
    include_json: bool,
    include_txt: bool,
    include_meta: bool,
) -> tuple[list[Path], str | None]:
    """
    Collect selection files to include based on include flags.

    Args:
        run_dir: Run directory containing selections/ (or selections/ itself)
        include_json: Include JSON selection outputs
        include_txt: Include TXT exports
        include_meta: Include selector metadata JSON

    Returns:
        Tuple of (included_files, error_message_or_none)
    """
    # Scan the run directory for selection outputs first
    inventory, error = scan_selections(run_dir)
    if error or inventory is None:
        return ([], error or "Unable to scan selections")

    included: list[Path] = []

    # Add JSON selections when requested
    if include_json:
        included.extend(inventory.selection_json)

    # Add TXT exports when requested
    if include_txt:
        included.extend(inventory.selection_txt)

    # Add metadata JSON outputs when requested
    if include_meta:
        included.extend(inventory.meta_json)

    return (included, None)


def build_package_metadata(
    run_dir: Path,
    metadata_inputs: dict,
    included_files: Iterable[Path],
    include_flags: dict[str, bool],
) -> dict:
    """
    Build a JSON-serializable metadata payload for the package.

    Args:
        run_dir: Run directory that sourced the selections
        metadata_inputs: User-supplied metadata fields from the editor
            (intended_use should be a list of name class identifiers,
            examples should be a dict keyed by name class)
        included_files: Files included in the package
        include_flags: Include flags for json/txt/meta/manifest

    Returns:
        Metadata dictionary ready for JSON serialization
    """
    # Normalize the list to deterministic ordering for tests and output stability
    included_list = sorted({Path(path) for path in included_files}, key=lambda p: p.name)

    # Convert file list into relative, human-friendly names
    included_names = [path.name for path in included_list]

    return {
        "schema_version": 1,
        "created_at": metadata_inputs.get("created_at", ""),
        "author": metadata_inputs.get("author", ""),
        "version": metadata_inputs.get("version", ""),
        "common_name": metadata_inputs.get("common_name", ""),
        "intended_use": metadata_inputs.get("intended_use", []),
        "source_run": run_dir.name,
        "source_dir": str(run_dir),
        "examples": metadata_inputs.get("examples", {}),
        "include": include_flags,
        "files_included": included_names,
    }


def write_metadata_json(
    output_dir: Path,
    package_name: str,
    metadata: dict,
) -> tuple[Path, str | None]:
    """
    Write metadata JSON to disk next to the package archive.

    Args:
        output_dir: Directory where the package ZIP is stored
        package_name: Package ZIP filename (used to derive JSON filename)
        metadata: Metadata dictionary to serialize

    Returns:
        Tuple of (metadata_path, error_message_or_none)
    """
    # Derive the metadata filename from the package name for traceability
    stem = Path(package_name).stem
    metadata_path = output_dir / f"{stem}_metadata.json"

    try:
        # Ensure the output directory exists before writing
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)
        return (metadata_path, None)
    except OSError as exc:
        return (metadata_path, f"Failed to write metadata: {exc}")


def scan_selections(run_dir: Path) -> tuple[SelectionInventory | None, str | None]:
    """
    Scan a run directory and return an inventory of selection outputs.

    Args:
        run_dir: Run directory containing a selections/ subfolder

    Returns:
        Tuple of (SelectionInventory or None, error message or None)
    """
    # Accept either a run directory or the selections directory itself
    if not run_dir.exists():
        return (None, f"Run directory does not exist: {run_dir}")

    # If the user pointed directly at selections/, normalize to the parent run dir
    if run_dir.name == "selections":
        selections_dir = run_dir
        run_dir = run_dir.parent
    else:
        selections_dir = run_dir / "selections"

    if not selections_dir.exists():
        return (None, f"Selections directory not found: {selections_dir}")

    # Gather JSON and TXT files in a stable order for deterministic packaging
    json_files = sorted(selections_dir.glob("*.json"))
    txt_files = sorted(selections_dir.glob("*.txt"))

    # Separate selector meta files from selection JSON outputs
    meta_files = [path for path in json_files if _is_meta_file(path)]
    selection_json = [path for path in json_files if path not in meta_files]

    inventory = SelectionInventory(
        run_dir=run_dir,
        selections_dir=selections_dir,
        selection_json=selection_json,
        selection_txt=txt_files,
        meta_json=meta_files,
    )
    return (inventory, None)


def _build_manifest(
    run_dir: Path,
    included_files: Iterable[Path],
    include_flags: dict[str, bool],
) -> dict:
    """
    Build a manifest describing the packaged selection files.

    Args:
        run_dir: Run directory being packaged
        included_files: Iterable of files added to the archive
        include_flags: Dictionary of include flags used for packaging

    Returns:
        Manifest dictionary ready to be serialized as JSON
    """
    extractor_type = _extract_extractor_type(run_dir)
    created_at = datetime.now(timezone.utc).isoformat()

    manifest_files: list[dict] = []
    selection_index: dict[str, list[str]] = {}

    for path in included_files:
        # Build a consistent archive path for manifest entries
        archive_path = f"selections/{path.name}"

        # Identify file type for clarity in the manifest
        if _is_meta_file(path):
            file_type = "meta"
        elif path.suffix == ".txt":
            file_type = "txt"
        else:
            file_type = "json"

        name_class, syllable_label = _parse_selection_filename(path.name)
        if name_class and syllable_label and file_type == "json":
            selection_index.setdefault(name_class, [])
            if syllable_label not in selection_index[name_class]:
                selection_index[name_class].append(syllable_label)

        manifest_files.append(
            {
                "path": archive_path,
                "file_type": file_type,
                "bytes": path.stat().st_size,
                "name_class": name_class,
                "syllables": syllable_label,
            }
        )

    # Keep syllable labels sorted for deterministic output
    for labels in selection_index.values():
        labels.sort()

    return {
        "schema_version": 1,
        "created_at": created_at,
        "run_name": run_dir.name,
        "run_dir": str(run_dir),
        "extractor_type": extractor_type,
        "include": include_flags,
        "file_count": len(manifest_files),
        "selection_index": selection_index,
        "files": manifest_files,
    }


def package_selections(options: PackageOptions) -> PackageResult:
    """
    Package selection outputs from a run directory into a ZIP archive.

    Args:
        options: Packaging configuration

    Returns:
        PackageResult with archive path and manifest, or error populated
    """
    # Scan for selection outputs before attempting packaging
    inventory, error = scan_selections(options.run_dir)
    if error or inventory is None:
        return PackageResult(package_path=Path(), included_files=[], manifest=None, error=error)

    # Assemble the file list based on include flags
    included_files: list[Path] = []
    if options.include_json:
        included_files.extend(inventory.selection_json)
    if options.include_txt:
        included_files.extend(inventory.selection_txt)
    if options.include_meta:
        included_files.extend(inventory.meta_json)

    # Fail early if there is nothing to package
    if not included_files:
        return PackageResult(
            package_path=Path(),
            included_files=[],
            manifest=None,
            error="No selection files matched the current include options.",
        )

    # Determine output directory and ensure it exists
    output_dir = options.output_dir or (inventory.run_dir / "packages")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Default package name uses the run directory for traceability
    package_name = options.package_name or f"{inventory.run_dir.name}_selections.zip"
    if not package_name.endswith(".zip"):
        package_name = f"{package_name}.zip"

    package_path = output_dir / package_name

    # Prevent accidental overwrites to protect existing artifacts
    if package_path.exists():
        return PackageResult(
            package_path=package_path,
            included_files=[],
            manifest=None,
            error=f"Package already exists: {package_path.name}",
        )

    include_flags = {
        "json": options.include_json,
        "txt": options.include_txt,
        "meta": options.include_meta,
        "manifest": options.include_manifest,
    }

    manifest: dict | None = None

    # Create the ZIP archive and write the selection files
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in included_files:
            # Always place selection files under a selections/ folder in the archive
            archive_path = f"selections/{path.name}"
            archive.write(path, arcname=archive_path)

        # Optionally add a manifest file that describes the package contents
        if options.include_manifest:
            manifest = _build_manifest(inventory.run_dir, included_files, include_flags)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))

    return PackageResult(
        package_path=package_path,
        included_files=included_files,
        manifest=manifest,
        error=None,
    )
