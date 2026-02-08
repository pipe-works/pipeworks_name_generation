Database Model
==============

The webapp uses SQLite with two metadata tables plus dynamically created text
value tables.

Metadata tables:

- ``imported_packages``
  Tracks each imported metadata/zip pair.
- ``package_tables``
  Tracks source txt filenames and associated physical SQLite table names.

Dynamic tables:

- One physical table per imported ``*.txt`` file.
- Schema: ``id``, ``line_number``, ``value``.

Import behavior summary:

- Metadata ``files_included`` (when present) limits which ``*.txt`` entries are
  imported from the ZIP.
- JSON files in the ZIP are currently ignored by importer persistence.
- Duplicate metadata+zip imports are rejected via uniqueness constraints.
