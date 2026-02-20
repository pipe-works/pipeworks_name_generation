"""
Package builder service for the web application.

Bundles walk results, candidates, and selections from both patches
into a downloadable ZIP archive with a manifest.  Also writes a
companion ``_metadata.json`` file to disk next to the ZIP for
provenance tracking (matching the TUI packager behaviour).
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any

from build_tools.syllable_walk_web.state import PatchState, ServerState


def build_package(
    state: ServerState,
    *,
    name: str = "corpus-package",
    version: str = "0.1.0",
    include_walks_a: bool = True,
    include_walks_b: bool = True,
    include_candidates: bool = True,
    include_selections: bool = True,
) -> tuple[bytes, str | None]:
    """Build a ZIP archive from in-memory walker state.

    Also writes the ZIP and a companion metadata JSON file to disk
    under ``<output_base>/packages/``.

    Args:
        state: Global server state with patch data.
        name: Package name (used in the ZIP filename).
        version: Package version string.
        include_walks_a: Include Patch A walks.
        include_walks_b: Include Patch B walks.
        include_candidates: Include candidates from both patches.
        include_selections: Include selections from both patches.

    Returns:
        Tuple of (zip_bytes, error_message_or_none).
    """
    files_included: list[dict[str, Any]] = []
    buf = io.BytesIO()

    # This dict is passed to both the in-ZIP manifest and the disk-side
    # metadata file so "what was included" is consistent across both.
    include_flags = {
        "walks_a": include_walks_a,
        "walks_b": include_walks_b,
        "candidates": include_candidates,
        "selections": include_selections,
    }

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Patch A walks
        if include_walks_a and state.patch_a.walks:
            data = json.dumps(state.patch_a.walks, indent=2).encode("utf-8")
            zf.writestr("patch_a/walks.json", data)
            files_included.append(
                {
                    "path": "patch_a/walks.json",
                    "type": "walks",
                    "patch": "a",
                    "count": len(state.patch_a.walks),
                    "bytes": len(data),
                }
            )

        # Patch B walks
        if include_walks_b and state.patch_b.walks:
            data = json.dumps(state.patch_b.walks, indent=2).encode("utf-8")
            zf.writestr("patch_b/walks.json", data)
            files_included.append(
                {
                    "path": "patch_b/walks.json",
                    "type": "walks",
                    "patch": "b",
                    "count": len(state.patch_b.walks),
                    "bytes": len(data),
                }
            )

        # Patch A candidates
        if include_candidates and state.patch_a.candidates:
            data = json.dumps(state.patch_a.candidates, indent=2).encode("utf-8")
            zf.writestr("patch_a/candidates.json", data)
            files_included.append(
                {
                    "path": "patch_a/candidates.json",
                    "type": "candidates",
                    "patch": "a",
                    "count": len(state.patch_a.candidates),
                    "bytes": len(data),
                }
            )

        # Patch B candidates
        if include_candidates and state.patch_b.candidates:
            data = json.dumps(state.patch_b.candidates, indent=2).encode("utf-8")
            zf.writestr("patch_b/candidates.json", data)
            files_included.append(
                {
                    "path": "patch_b/candidates.json",
                    "type": "candidates",
                    "patch": "b",
                    "count": len(state.patch_b.candidates),
                    "bytes": len(data),
                }
            )

        # Patch A selections
        if include_selections and state.patch_a.selected_names:
            _write_selections(zf, "a", state.patch_a, files_included)

        # Patch B selections
        if include_selections and state.patch_b.selected_names:
            _write_selections(zf, "b", state.patch_b, files_included)

        # Return an error instead of an empty ZIP — a zero-content archive
        # would be confusing; this nudges the user to generate data first.
        if not files_included:
            return b"", "Nothing to package. Generate walks, candidates, or selections first."

        # Manifest (embedded in the ZIP)
        manifest = _build_manifest(
            name=name,
            version=version,
            state=state,
            files_included=files_included,
            include_flags=include_flags,
        )
        zf.writestr("manifest.json", json.dumps(manifest, indent=2).encode("utf-8"))

    zip_bytes = buf.getvalue()

    # Write ZIP and metadata JSON to disk for provenance
    _persist_to_disk(
        state=state,
        name=name,
        version=version,
        zip_bytes=zip_bytes,
        manifest=manifest,
        include_flags=include_flags,
        files_included=files_included,
    )

    return zip_bytes, None


def _write_selections(
    zf: zipfile.ZipFile,
    patch_key: str,
    patch: PatchState,
    files_included: list[dict[str, Any]],
) -> None:
    """Write selection JSON and TXT into the archive."""
    # JSON preserves full metadata for reimport into the combiner/selector.
    data = json.dumps(patch.selected_names, indent=2).encode("utf-8")
    zf.writestr(f"patch_{patch_key}/selections.json", data)
    files_included.append(
        {
            "path": f"patch_{patch_key}/selections.json",
            "type": "selections",
            "patch": patch_key,
            "count": len(patch.selected_names),
            "bytes": len(data),
        }
    )

    # TXT provides a simple one-name-per-line format for use in other
    # tools or manual review.
    names = [n["name"] if isinstance(n, dict) else n for n in patch.selected_names]
    txt_data = "\n".join(names).encode("utf-8")
    zf.writestr(f"patch_{patch_key}/selections.txt", txt_data)
    files_included.append(
        {
            "path": f"patch_{patch_key}/selections.txt",
            "type": "selections_txt",
            "patch": patch_key,
            "count": len(names),
            "bytes": len(txt_data),
        }
    )


def _build_manifest(
    *,
    name: str,
    version: str,
    state: ServerState,
    files_included: list[dict[str, Any]],
    include_flags: dict[str, bool],
) -> dict[str, Any]:
    """Build manifest.json contents for the package."""
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "package_name": name,
        "version": version,
        "patch_a": _patch_summary(state.patch_a),
        "patch_b": _patch_summary(state.patch_b),
        "include": include_flags,
        "file_count": len(files_included),
        "files": files_included,
    }


def _patch_summary(patch: PatchState) -> dict[str, Any]:
    """Build a summary of a patch's state for the manifest."""
    return {
        "run_id": patch.run_id,
        "corpus_type": patch.corpus_type,
        "syllable_count": patch.syllable_count,
        "walk_count": len(patch.walks),
        "candidate_count": len(patch.candidates) if patch.candidates else 0,
        "selection_count": len(patch.selected_names),
    }


def _persist_to_disk(
    *,
    state: ServerState,
    name: str,
    version: str,
    zip_bytes: bytes,
    manifest: dict[str, Any],
    include_flags: dict[str, bool],
    files_included: list[dict[str, Any]],
) -> None:
    """Write the ZIP and a companion ``_metadata.json`` to disk.

    Files are written under ``<output_base>/packages/``.  Errors are
    logged to stderr but do **not** prevent the in-memory ZIP from
    being returned to the browser — disk persistence is best-effort.
    """
    import sys

    packages_dir = state.output_base / "packages"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stem = f"{name}-{version}_{timestamp}"

    try:
        packages_dir.mkdir(parents=True, exist_ok=True)

        # Write ZIP
        zip_path = packages_dir / f"{stem}.zip"
        zip_path.write_bytes(zip_bytes)

        # Write companion metadata JSON
        metadata = {
            "schema_version": 1,
            "created_at": manifest.get("created_at", ""),
            "package_name": name,
            "version": version,
            "patch_a": manifest.get("patch_a", {}),
            "patch_b": manifest.get("patch_b", {}),
            "include": include_flags,
            "file_count": len(files_included),
            "files_included": [f["path"] for f in files_included],
            "zip_file": zip_path.name,
            "zip_bytes": len(zip_bytes),
        }
        meta_path = packages_dir / f"{stem}_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    except OSError as exc:
        print(f"[packager] warning: failed to persist package to disk: {exc}", file=sys.stderr)
