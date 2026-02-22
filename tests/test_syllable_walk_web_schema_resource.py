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

SCHEMA_PACKAGE = "build_tools.syllable_walk_web"
SCHEMA_RELATIVE_PATH = "schemas/walker_profile_reaches.v1.schema.json"
SCHEMA_URN = "urn:pipeworks:schema:walker-profile-reaches-cache:v1"


def _load_schema_payload() -> dict[str, Any]:
    """Load the walker profile reaches schema from package resources."""
    schema_ref = resources.files(SCHEMA_PACKAGE).joinpath(SCHEMA_RELATIVE_PATH)
    payload = json.loads(schema_ref.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_walker_profile_reaches_schema_is_packaged_resource() -> None:
    """Schema file should be discoverable via importlib.resources.

    This validates that setuptools package-data rules include the schema,
    which is required for installed environments that rely on schema access.
    """
    schema_ref = resources.files(SCHEMA_PACKAGE).joinpath(SCHEMA_RELATIVE_PATH)
    assert schema_ref.is_file()


def test_walker_profile_reaches_schema_has_expected_identity_fields() -> None:
    """Schema should preserve stable identity fields for tooling compatibility."""
    payload = _load_schema_payload()

    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert payload["$id"] == SCHEMA_URN
    assert payload["properties"]["schema_version"]["const"] == 1


def test_walker_profile_reaches_schema_includes_core_required_sections() -> None:
    """Schema must retain required top-level sections used by IPC cache flow."""
    payload = _load_schema_payload()

    required = set(payload["required"])
    assert {
        "schema_version",
        "cache_kind",
        "run_id",
        "manifest",
        "graph_settings",
        "reach_settings",
        "ipc",
        "profile_reaches",
    }.issubset(required)

    profiles = payload["properties"]["profile_reaches"]["required"]
    assert profiles == ["clerical", "dialect", "goblin", "ritual"]
