"""Tests for packaged syllable_walk_web schema resources.

These checks guard the installation contract for walker IPC/cache schema files:
- schema JSON is present under package resources
- schema payload is valid JSON object
- critical identity/contract fields remain stable
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

import pytest

SCHEMA_PACKAGE = "build_tools.syllable_walk_web"
SCHEMA_SPECS = (
    {
        "relative_path": "schemas/walker_profile_reaches.v1.schema.json",
        "urn": "urn:pipeworks:schema:walker-profile-reaches-cache:v1",
        "required": {
            "schema_version",
            "cache_kind",
            "run_id",
            "manifest",
            "graph_settings",
            "reach_settings",
            "ipc",
            "profile_reaches",
        },
    },
    {
        "relative_path": "schemas/walker_patch_output.v1.schema.json",
        "urn": "urn:pipeworks:schema:walker-patch-output:v1",
        "required": {
            "schema_version",
            "artifact_kind",
            "patch",
            "run_id",
            "created_at_utc",
            "ipc",
            "payload",
        },
    },
    {
        "relative_path": "schemas/walker_run_state.v1.schema.json",
        "urn": "urn:pipeworks:schema:walker-run-state:v1",
        "required": {
            "schema_version",
            "state_kind",
            "run_id",
            "created_at_utc",
            "manifest_ipc_output_hash",
            "sidecars",
            "ipc",
        },
    },
    {
        "relative_path": "schemas/walker_patch_session.v1.schema.json",
        "urn": "urn:pipeworks:schema:walker-patch-session:v1",
        "required": {
            "schema_version",
            "session_kind",
            "session_id",
            "created_at_utc",
            "patch_a",
            "patch_b",
            "ipc",
        },
    },
)


def _load_schema_payload(relative_path: str) -> dict[str, Any]:
    """Load one walker schema from package resources."""
    schema_ref = resources.files(SCHEMA_PACKAGE).joinpath(relative_path)
    payload = json.loads(schema_ref.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    ("relative_path",),
    [(spec["relative_path"],) for spec in SCHEMA_SPECS],
)
def test_walker_schema_is_packaged_resource(relative_path: str) -> None:
    """Schema file should be discoverable via importlib.resources.

    This validates that setuptools package-data rules include the schema,
    which is required for installed environments that rely on schema access.
    """
    schema_ref = resources.files(SCHEMA_PACKAGE).joinpath(relative_path)
    assert schema_ref.is_file()


@pytest.mark.parametrize(
    ("relative_path", "schema_urn"),
    [(spec["relative_path"], spec["urn"]) for spec in SCHEMA_SPECS],
)
def test_walker_schema_has_expected_identity_fields(relative_path: str, schema_urn: str) -> None:
    """Schema should preserve stable identity fields for tooling compatibility."""
    payload = _load_schema_payload(relative_path)

    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert payload["$id"] == schema_urn
    assert payload["properties"]["schema_version"]["const"] == 1


@pytest.mark.parametrize(
    ("relative_path", "required_fields"),
    [(spec["relative_path"], spec["required"]) for spec in SCHEMA_SPECS],
)
def test_walker_schema_includes_required_sections(
    relative_path: str,
    required_fields: set[str],
) -> None:
    """Schema must retain required top-level sections used by IPC cache flow."""
    payload = _load_schema_payload(relative_path)

    required = set(payload["required"])
    assert required_fields.issubset(required)


def test_walker_profile_reaches_schema_keeps_profile_required_order() -> None:
    """Profile reach schema should preserve canonical named-profile ordering."""
    payload = _load_schema_payload("schemas/walker_profile_reaches.v1.schema.json")
    profiles = payload["properties"]["profile_reaches"]["required"]
    assert profiles == ["clerical", "dialect", "goblin", "ritual"]
