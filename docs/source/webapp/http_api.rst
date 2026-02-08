HTTP API
========

Routes currently exposed by the webapp:

- ``GET /``
  Serves the main tabbed web UI shell.
- ``GET /static/app.css``
  Serves UI stylesheet.
- ``GET /static/app.js``
  Serves UI client script.
- ``GET /favicon.ico``
  Returns ``204``.
- ``GET /api/health``
  Liveness check.
- ``GET /api/generation/package-options``
  Returns generation package options grouped by name class.
- ``GET /api/generation/package-syllables?class_key=...&package_id=...``
  Returns available syllable options for a class+package.
- ``GET /api/generation/selection-stats?class_key=...&package_id=...&syllable_key=...``
  Returns ``max_items`` and ``max_unique_combinations``.
- ``POST /api/generate``
  Generates names from imported SQLite tables.
- ``GET /api/database/packages``
  Lists imported packages.
- ``GET /api/database/package-tables?package_id=...``
  Lists imported txt-backed tables for a package.
- ``GET /api/database/table-rows?table_id=...&offset=...&limit=...``
  Returns paginated table rows.
- ``POST /api/import``
  Imports a metadata JSON + ZIP package pair.

Error shape:

- API validation/runtime failures return JSON with an ``error`` key.
- Unknown routes return standard HTTP ``404``.
