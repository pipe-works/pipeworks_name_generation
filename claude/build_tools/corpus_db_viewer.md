# Corpus Database Viewer

## Interactive TUI for Build Provenance Inspection

An interactive terminal user interface (TUI) for viewing corpus database provenance records. This
tool provides a keyboard-driven interface for browsing extraction run history, inspecting schemas,
and exporting data.

## Overview

The corpus database viewer is a **build-time inspection tool** that provides read-only access to
the syllable extractor's provenance database (`data/raw/syllable_extractor.db`). It replaced the
Flask-based web viewer to eliminate web server overhead and better integrate with the build tools
ecosystem.

**Key Features:**

- Interactive table browsing with pagination
- Schema inspection (columns, types, indexes, CREATE statements)
- Data export to CSV and JSON formats
- Keyboard-driven navigation
- Read-only database access (safe inspection)

**Technology:** Built with [Textual](https://textual.textualize.io/), a modern Python TUI
framework.

## Installation

The viewer is installed as part of the development dependencies:

```bash
pip install -r requirements-dev.txt
```

This installs the `textual` library (>=0.50.0) and all other build tool dependencies.

## Basic Usage

### Launching the Viewer

**With default database:**

```bash
python -m build_tools.corpus_db_viewer
```

**With custom database:**

```bash
python -m build_tools.corpus_db_viewer --db /path/to/other.db
```

**With custom export directory:**

```bash
python -m build_tools.corpus_db_viewer --export-dir _working/my_exports/
```

**With custom page size:**

```bash
python -m build_tools.corpus_db_viewer --page-size 100
```

### Interface Layout

```text
┌─ Corpus Database Viewer ────────────────────────────────────────┐
│                                                                   │
│  Tables          │ Table: runs | Page 1/3 | Total rows: 127     │
│  ────────        ├───────────────────────────────────────────────│
│  inputs          │ id │ timestamp      │ tool    │ status       │
│  outputs         │ 1  │ 2024-01-05...  │ pyphen  │ completed    │
│  runs            │ 2  │ 2024-01-06...  │ pyphen  │ completed    │
│  sqlite_sequence │ 3  │ 2024-01-07...  │ pyphen  │ failed       │
│                  │ ... (50 rows per page)                        │
│                  │                                               │
└───────────────────────────────────────────────────────────────────┘
 q quit  ? help  i schema  e export
```

**Three main areas:**

1. **Left sidebar:** List of database tables
2. **Top bar:** Current table name, page info, row count
3. **Main area:** Data table with current page

## Keyboard Shortcuts

### Navigation

| Key(s)           | Action                          |
|------------------|---------------------------------|
| `↑` / `↓`        | Navigate rows                   |
| `←` / `→`        | Previous/Next page              |
| `PageUp`/`PageDn`| Jump 10 pages back/forward      |
| `Home` / `End`   | Go to first/last page           |

### Actions

| Key | Action                               |
|-----|--------------------------------------|
| `t` | Switch table (focuses table list)   |
| `i` | Show schema information              |
| `e` | Export current table                 |
| `r` | Refresh data                         |
| `?` | Show help screen                     |
| `q` | Quit application                     |

### In Table Selector

| Key     | Action          |
|---------|-----------------|
| `↑`/`↓` | Navigate tables |
| `Enter` | Select table    |
| `Esc`   | Cancel/Return   |

## Feature Walkthrough

### 1. Browsing Tables

When the app launches, it automatically loads the first table. Use the sidebar to switch between
tables:

1. Press `t` to focus the table list
2. Use `↑`/`↓` arrows to navigate
3. Press `Enter` to select a table

Or simply click on a table name in the sidebar.

**Pagination:**

- Press `←`/`→` to move one page at a time
- Press `PageUp`/`PageDn` to jump 10 pages
- Press `Home`/`End` to go to first/last page

### 2. Viewing Schema Information

Press `i` (info) to view detailed schema information for the current table.

**Schema modal shows:**

- **Columns:** Name, type, PRIMARY KEY, NOT NULL, DEFAULT values
- **Indexes:** Index names, columns, UNIQUE constraints
- **CREATE TABLE statement:** Original SQL used to create the table

**Example:**

```text
Schema: runs

Columns:
  • id: INTEGER [PRIMARY KEY]
  • run_timestamp: TEXT NOT NULL
  • extractor_tool: TEXT NOT NULL
  • extractor_version: TEXT
  • status: TEXT
  • exit_code: INTEGER
  • ...

Indexes:
  • idx_extractor_tool (extractor_tool)
  • idx_status (status)

CREATE TABLE Statement:
CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,
    ...
);
```

Press the "Close" button or `Esc` to return to the main view.

### 3. Exporting Data

Press `e` (export) to export the current table to a file.

**Export modal shows:**

- Default filename: `<table_name>_<timestamp>`
- Format choices: CSV or JSON
- Editable filename field

**Export process:**

1. Press `e` to open export modal
2. Edit filename if desired (without extension)
3. Click "Export CSV" or "Export JSON"
4. File is saved to export directory (default: `_working/exports/`)
5. Success notification appears

**Note:** Export always includes ALL rows, not just the current page.

**Output files:**

```bash
_working/exports/
├── runs_20240109_143022.csv
├── runs_20240109_143022.json
├── outputs_20240109_143145.csv
└── ...
```

**CSV format:**

```csv
id,run_timestamp,extractor_tool,status,exit_code
1,2024-01-05 14:30:22,pyphen,completed,0
2,2024-01-06 09:15:43,pyphen,completed,0
3,2024-01-07 11:22:11,pyphen,failed,1
```

**JSON format:**

```json
[
  {
    "id": 1,
    "run_timestamp": "2024-01-05 14:30:22",
    "extractor_tool": "pyphen",
    "status": "completed",
    "exit_code": 0
  },
  ...
]
```

### 4. Refreshing Data

Press `r` (refresh) to reload data for the current table. Useful if the database has been updated
by another process while the viewer is running.

### 5. Help Screen

Press `?` to show the help screen with all keyboard shortcuts. Press any key (or click "Close") to
return to the main view.

## Command-Line Options

### `--db PATH`

Path to SQLite database file.

**Default:** `data/raw/syllable_extractor.db`

**Example:**

```bash
python -m build_tools.corpus_db_viewer --db /tmp/test.db
```

### `--export-dir PATH`

Directory where exported files will be saved.

**Default:** `_working/exports/`

The directory is created automatically if it doesn't exist.

**Example:**

```bash
python -m build_tools.corpus_db_viewer --export-dir /tmp/exports/
```

### `--page-size N`

Number of rows to display per page.

**Default:** `50`

**Example:**

```bash
python -m build_tools.corpus_db_viewer --page-size 100
```

## Python API

You can also use the query functions and formatters programmatically:

### Querying Tables

```python
from build_tools.corpus_db_viewer import queries
from pathlib import Path

db_path = Path("data/raw/syllable_extractor.db")

# Get list of tables
tables = queries.get_tables_list(db_path)
for table in tables:
    print(table['name'])

# Get schema
schema = queries.get_table_schema(db_path, "runs")
print(f"Columns: {len(schema['columns'])}")
print(f"Indexes: {len(schema['indexes'])}")

# Get paginated data
data = queries.get_table_data(
    db_path,
    "runs",
    page=1,
    limit=10,
    sort_by="run_timestamp",
    sort_order="DESC"
)
print(f"Total rows: {data['total']}")
print(f"Page {data['page']} of {data['total_pages']}")
for row in data['rows']:
    print(row)
```

### Exporting Data

```python
from build_tools.corpus_db_viewer import formatters
from pathlib import Path

rows = [
    {'id': 1, 'name': 'Alice', 'age': 30},
    {'id': 2, 'name': 'Bob', 'age': 25}
]

# Export to CSV
formatters.export_to_csv(rows, Path("_working/exports/data.csv"))

# Export to JSON
formatters.export_to_json(rows, Path("_working/exports/data.json"))

# Format helpers
print(formatters.format_row_count(1234))  # "1,234 rows"
print(formatters.format_file_size(1048576))  # "1.0 MB"
```

## Database Structure

The corpus database (`syllable_extractor.db`) tracks syllable extraction run provenance:

### Tables

| Table     | Purpose                                  |
|-----------|------------------------------------------|
| `runs`    | Extraction run metadata (tool, version, status, timestamps) |
| `inputs`  | Input files used in each run             |
| `outputs` | Output files produced by each run        |

### Key Queries

**Find runs by status:**

```sql
SELECT * FROM runs WHERE status = 'completed' ORDER BY run_timestamp DESC;
```

**Find outputs for a specific run:**

```sql
SELECT o.* FROM outputs o WHERE o.run_id = 5;
```

**Find which run produced a file:**

```sql
SELECT r.* FROM runs r
JOIN outputs o ON r.id = o.run_id
WHERE o.output_path LIKE '%corpus.syllables';
```

**Get statistics:**

```sql
SELECT status, COUNT(*) as count FROM runs GROUP BY status;
```

## Troubleshooting

### Database Not Found

```text
Error: Database not found: data/raw/syllable_extractor.db
```

**Solution:** Ensure the database file exists, or specify a different path with `--db`:

```bash
python -m build_tools.corpus_db_viewer --db /path/to/your/database.db
```

### Textual Not Installed

```text
Error: Textual library not found. Please install dependencies:
  pip install textual
```

**Solution:** Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Export Directory Permission Error

```text
Error: Could not create export directory: _working/exports/
```

**Solution:** Ensure you have write permissions, or specify a different directory:

```bash
python -m build_tools.corpus_db_viewer --export-dir /tmp/exports/
```

### Terminal Too Small

If the TUI layout looks broken, your terminal window may be too small. Textual recommends a minimum
of 80 columns × 24 rows. Resize your terminal and the app will automatically reflow.

## Comparison with Flask Version

The original Flask-based viewer (`_working/_archived/pipeworks_db_viewer_flask/`) has been replaced
by this TUI version.

### Why the Change?

**Textual TUI advantages:**

- ✅ No web server overhead (runs directly in terminal)
- ✅ Better integration with build tools ecosystem
- ✅ Simpler deployment (no HTML/CSS/JavaScript)
- ✅ Reduced dependencies (removed Flask, pandas, Werkzeug)
- ✅ Single-language codebase (Python only)
- ✅ Native keyboard navigation

**Flask version advantages:**

- ✅ SQL query interface (custom SELECT queries)
- ✅ Search across all tables
- ✅ Browser-based (familiar UI paradigm)

**Decision:** The TUI better matches the "build tool" philosophy and reduces complexity. The SQL
query interface and search features may be added in future if requested.

## Future Enhancements

Potential improvements:

1. **Search functionality** - Full-text search across tables
2. **SQL query interface** - Execute custom SELECT queries in TUI
3. **Run comparison** - Side-by-side comparison of extraction runs
4. **Visualization** - Charts for run statistics using Rich rendering
5. **Column filtering** - Filter rows by column values
6. **Saved views** - Store frequently-used queries
7. **Multiple databases** - Switch between databases without restarting

## Design Philosophy

### Read-Only Access

The viewer opens the database in **read-only mode** (`?mode=ro`) to prevent accidental
modifications. This ensures safe inspection of build provenance without risk of corruption.

### Observational Tool

Like the `corpus_db` ledger itself, the viewer is **observational only**. It displays what
happened during extraction runs but does not control or modify any build processes.

### Lightweight and Focused

The viewer provides core inspection capabilities (browse, schema, export) without attempting to be
a full database administration tool. For advanced use cases (complex queries, analysis), use
standard SQLite tools (`sqlite3`, DBeaver, etc.) or the Python API.

## Integration with Corpus Database

The viewer is designed specifically for the corpus database schema (see
[Corpus Database](corpus_db.md)), but works with any SQLite database. It automatically:

- Discovers all tables
- Infers column types and constraints
- Displays indexes and foreign keys
- Handles NULL values gracefully

## Related Documentation

- [Corpus Database (corpus_db)](corpus_db.md) - Build provenance ledger
- [Syllable Extractor](syllable_extractor.md) - The tool that populates the database
- [Development Guide](../development.md) - Build tool patterns and conventions

## Questions?

If you encounter issues or have feature requests:

1. Check this documentation first
2. Review the Python API for programmatic access
3. For advanced queries, use `sqlite3` CLI or database tools
4. For bugs or enhancements, file an issue

---

**Version:** 0.1.0
**Status:** Stable (replaces Flask viewer)
**Dependencies:** textual >= 0.50.0
