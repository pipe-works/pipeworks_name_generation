"""Shared constants for the webapp server and UI behavior.

Keeping these values in one module makes it easier to reuse route-level limits and
Generation tab metadata across HTTP handlers and service modules as refactoring
continues.
"""

from __future__ import annotations

# Keep pagination intentionally small so database browsing is readable.
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 200

# Canonical class keys and labels used by the Generation tab card layout.
GENERATION_NAME_CLASSES: list[tuple[str, str]] = [
    ("first_name", "First Name"),
    ("last_name", "Last Name"),
    ("place_name", "Place Name"),
    ("location_name", "Location Name"),
    ("object_item", "Object Item"),
    ("organisation", "Organisation"),
    ("title_epithet", "Title Epithet"),
]

# Filename pattern hints used to map imported txt source files to generation
# classes. Patterns are compared against a normalized lowercase stem.
GENERATION_CLASS_PATTERNS: dict[str, tuple[str, ...]] = {
    "first_name": ("first_name",),
    "last_name": ("last_name",),
    "place_name": ("place_name",),
    "location_name": ("location_name",),
    "object_item": ("object_item", "object_name"),
    "organisation": ("organisation", "organization", "org_name"),
    "title_epithet": ("title_epithet", "epithet"),
}

GENERATION_CLASS_KEYS: set[str] = {key for key, _ in GENERATION_NAME_CLASSES}

# Display labels for normalized syllable mode keys presented in the UI.
GENERATION_SYLLABLE_LABELS: dict[str, str] = {
    "2syl": "2 syllables",
    "3syl": "3 syllables",
    "4syl": "4 syllables",
    "all": "All syllables",
}

__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "MAX_PAGE_LIMIT",
    "GENERATION_NAME_CLASSES",
    "GENERATION_CLASS_PATTERNS",
    "GENERATION_CLASS_KEYS",
    "GENERATION_SYLLABLE_LABELS",
]
