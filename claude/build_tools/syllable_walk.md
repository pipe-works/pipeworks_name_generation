# Syllable Walker

A simplified web interface for exploring syllable walks and browsing name selections
from pipeline run directories. Uses SQLite for fast data loading.

## Overview

The Syllable Walker provides:

1. **Run Discovery** - Auto-discovers pipeline runs from `_working/output/`
2. **Selections Browser** - Browse first_name, last_name, place_name selections
3. **Quick Walk** - Generate syllable walks with preset profiles

This tool is a **build-time analysis tool** for exploring phonetic space, not a runtime component
of the name generator.

## Quick Start

### Web Interface (Recommended)

```bash
# Start the web server (auto-discovers port starting at 8000)
python -m build_tools.syllable_walk --web

# Specify exact port
python -m build_tools.syllable_walk --web --port 9000

# Verbose mode
python -m build_tools.syllable_walk --web --verbose
```

The web interface provides:

- Run selector dropdown showing folder names and metadata
- Tabbed selections browser (First Names, Last Names, Place Names)
- Quick walk generator with four preset profiles

### Run Directory Structure

The walker discovers runs from `_working/output/` matching the pattern:

```text
_working/output/YYYYMMDD_HHMMSS_{extractor}/
├── data/
│   ├── corpus.db                    # SQLite database (preferred)
│   └── {prefix}_syllables_annotated.json  # JSON fallback
└── selections/
    ├── {prefix}_first_name_2syl.json
    ├── {prefix}_last_name_2syl.json
    └── {prefix}_place_name_2syl.json
```

## Web Interface Features

### Run Selector

Displays all discovered pipeline runs with:

- **Folder name** (e.g., `20260121_084017_nltk`)
- **Syllable count** from database or JSON
- **Selection count** (number of selection files)

Example: `20260121_084017_nltk (3,135 syllables, 3 selections)`

### Selections Browser

When a run has selections, tabbed categories appear:

- **First Names** - Names optimized for addressability
- **Last Names** - Names optimized for durability
- **Place Names** - Names optimized for stability

Each selection table shows:

- Name (combined syllables)
- Component syllables
- Admission score

### Quick Walk Generator

Generate syllable walks with preset profiles:

| Profile | Description | Temperature | Freq Weight |
|---------|-------------|-------------|-------------|
| **clerical** | Conservative, minimal change | 0.3 | 1.0 |
| **dialect** | Balanced exploration | 0.7 | 0.0 |
| **goblin** | Chaotic, high variation | 1.5 | -0.5 |
| **ritual** | Maximum exploration | 2.5 | -1.0 |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/runs` | GET | List all discovered run directories |
| `/api/runs/{id}/selections/{class}` | GET | Get selection data for a name class |
| `/api/select-run` | POST | Switch to a different run |
| `/api/walk` | POST | Generate a syllable walk |

### Example: List Runs

```bash
curl http://localhost:8000/api/runs
```

Response:

```json
{
  "runs": [
    {
      "path": "/path/to/_working/output/20260121_084017_nltk",
      "extractor_type": "nltk",
      "timestamp": "20260121_084017",
      "display_name": "20260121_084017_nltk (3,135 syllables, 3 selections)",
      "syllable_count": 3135,
      "selection_count": 3
    }
  ]
}
```

### Example: Get Selections

```bash
curl http://localhost:8000/api/runs/20260121_084017_nltk/selections/first_name
```

Response:

```json
{
  "metadata": {
    "name_class": "first_name",
    "admitted": 91,
    "rejected": 9,
    "total_evaluated": 100
  },
  "selections": [
    {"name": "andka", "syllables": ["and", "ka"], "score": 3},
    {"name": "andno", "syllables": ["and", "no"], "score": 3}
  ]
}
```

### Example: Generate Walk

```bash
curl -X POST http://localhost:8000/api/walk \
  -H "Content-Type: application/json" \
  -d '{"start": "ka", "profile": "dialect", "seed": 42}'
```

## Data Sources

The walker prefers SQLite for performance:

| Source | Load Time | Notes |
|--------|-----------|-------|
| SQLite `corpus.db` | <100ms | Preferred, indexed |
| Annotated JSON | 2-3 min | Fallback for older runs |

### SQLite Database Schema

The `corpus.db` contains a `syllables` table with:

- `syllable` - The syllable text
- `frequency` - Occurrence count in corpus
- 12 phonetic feature columns (boolean)

## Port Discovery

The server auto-discovers available ports:

```bash
# Auto-discover starting at 8000
python -m build_tools.syllable_walk --web
# Output: Server running at http://localhost:8000

# If 8000 is in use, tries 8001, 8002, etc.
# Output: Server running at http://localhost:8001
```

To use a specific port:

```bash
python -m build_tools.syllable_walk --web --port 9000
# Fails with error if port 9000 is unavailable
```

## Core Concepts

### Phonetic Distance (Hamming Distance)

Each syllable has 12 binary phonetic features. The distance between two syllables
is the number of features that differ:

```text
ka:    [0,0,0,1,0,0,0,1,0,1,0,0]
pai:   [0,0,0,1,0,0,0,0,1,1,0,0]
       ─────────────────↑───────
Distance = 1 (very similar)
```

### Walk Profiles

The walker includes four pre-configured profiles:

- **clerical** - Conservative, favors common syllables
- **dialect** - Balanced, neutral frequency bias
- **goblin** - Chaotic, favors rare syllables
- **ritual** - Maximum exploration, very rare syllables

### Determinism

The same seed always produces the same walk:

```python
# Same seed = same walk
walk1 = walker.walk("ka", seed=42)
walk2 = walker.walk("ka", seed=42)
assert walk1 == walk2  # Always true
```

## Troubleshooting

### No Runs Found

Ensure pipeline output directories exist:

```bash
ls _working/output/
# Should show: 20260121_084017_nltk/, etc.
```

### No Selections Shown

Run the name selector to generate selection files:

```bash
python -m build_tools.name_selector \
  --run-dir _working/output/20260121_084017_nltk/ \
  --candidates candidates/nltk_candidates_2syl.json \
  --name-class first_name \
  --count 100
```

### Port Already in Use

With `--port`, the server fails if the port is unavailable. Without `--port`,
it auto-discovers starting at 8000.

### Walker Not Loading

Check that the run has valid data:

```bash
# Check for database
ls _working/output/20260121_084017_nltk/data/corpus.db

# Or check for JSON
ls _working/output/20260121_084017_nltk/data/*_syllables_annotated.json
```

## Module Structure

```text
build_tools/syllable_walk/
├── __init__.py       # Package exports
├── __main__.py       # CLI entry point
├── cli.py            # Argument parser
├── server.py         # HTTP server and handlers
├── run_discovery.py  # Run directory discovery
├── db.py             # SQLite database access
├── walker.py         # Core walk algorithm
├── profiles.py       # Walk profile definitions
└── web_assets.py     # HTML/CSS/JS templates
```

## Related Tools

- **syllable_feature_annotator** - Generates input data with phonetic features
- **corpus_sqlite_builder** - Builds SQLite database for fast loading
- **name_combiner** - Generates name candidates from syllables
- **name_selector** - Selects names by policy (first_name, last_name, place_name)
- **syllable_walk_tui** - Full-featured terminal UI for detailed exploration
