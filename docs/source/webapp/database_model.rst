Database Model
==============

The webapp uses SQLite with two metadata tables plus dynamically created text
value tables.

Metadata tables:

- ``imported_packages``
  Tracks each imported metadata/zip pair.
- ``package_tables``
  Tracks source txt filenames and associated physical SQLite table names.

Metadata indexes:

- ``idx_package_tables_package_id``
  Optimizes package-scoped table lookups.
- ``idx_package_tables_package_id_source_txt``
  Optimizes package + source filename lookups.
- ``idx_imported_packages_imported_at``
  Optimizes recency-oriented package browsing.

Dynamic tables:

- One physical table per imported ``*.txt`` file.
- Schema: ``id``, ``line_number``, ``value``.

Connection defaults:

- ``PRAGMA foreign_keys = ON``
- ``PRAGMA journal_mode = WAL``
- ``PRAGMA synchronous = NORMAL``
- ``PRAGMA busy_timeout = 5000``

Import behavior summary:

- Metadata ``files_included`` (when present) limits which ``*.txt`` entries are
  imported from the ZIP.
- JSON files in the ZIP are currently ignored by importer persistence.
- Duplicate metadata+zip imports are rejected via uniqueness constraints.
