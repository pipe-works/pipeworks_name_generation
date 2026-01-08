# Corpus Database (Build Provenance Ledger)

An observational SQLite database for tracking all syllable extraction runs across different
extractor tools. Records who ran what extraction, when, with which settings, and what outputs
were produced. Solves the "build provenance drift" problem where you can't remember which corpus
file came from which extraction run.

## Overview

The corpus database is a **build-time observational tool** - it watches and records extraction
runs but never influences extraction behavior. All extractors remain pure, deterministic functions.
The ledger just remembers what happened.

### Key Design Principles

1. **Observational Only**: Records outcomes, doesn't control behavior
2. **Append-Only**: Runs are never modified, only added
3. **Tool-Agnostic**: Works for pyphen, NLTK, eSpeak, or future extractors
4. **Cross-Platform**: Paths stored in POSIX format for Windows/Mac/Linux compatibility

### What Problem Does This Solve?

Without a ledger, you end up with:

```text
data/raw/output_english_v2/
data/raw/output_english_v2_final/
data/raw/output_english_v2_final_real/
```

Questions become impossible:

- "Which one used --min 2 again?"
- "Which corpus was recursive?"
- "Was this auto-lang or forced?"
- "Which run produced corpus.syllables?"

The ledger answers: "Run #42 on 2026-01-05 at 14:30 using syllable_extractor v0.2.0 with en_US, --min 2 --max 8, from /data/corpus/english.txt"

## Database Schema

Three simple tables:

### `runs` - One row per extractor invocation

Records all configuration and execution details:

- Extractor tool name (syllable_extractor, syllable_extractor_nltk, etc.)
- Version/git SHA
- Hostname
- Exit code and status (running/completed/failed/interrupted)
- Language settings (pyphen_lang, auto_lang_detected)
- Length constraints (min_len, max_len)
- Flags (recursive, pattern)
- **Full command-line for reproducibility**
- User notes for manual annotations

### `inputs` - Source files processed (many-to-one with runs)

Tracks what went in:

- Source path (file or directory)
- File count (if directory)

### `outputs` - Generated files (many-to-one with runs)

Tracks what came out:

- Output path (.syllables file)
- Syllable count (total with duplicates)
- Unique syllable count
- Metadata file path (.meta)

## Usage Pattern

### Typical Workflow

```python
from build_tools.corpus_db import CorpusLedger
from pathlib import Path
import sys

ledger = CorpusLedger()  # Defaults to data/raw/syllable_extractor.db

# Start run
run_id = ledger.start_run(
    extractor_tool="syllable_extractor",
    extractor_version="0.2.0",
    pyphen_lang="en_US",
    min_len=2,
    max_len=8,
    command_line=" ".join(sys.argv),
    notes="Production corpus extraction"
)

# Record inputs
ledger.record_input(run_id, Path("data/corpus/english.txt"))

# ... extraction happens (ledger doesn't participate) ...

# Record outputs
ledger.record_output(
    run_id,
    output_path=Path("data/raw/en_US/corpus.syllables"),
    unique_syllable_count=1234,
    meta_path=Path("data/raw/en_US/corpus.meta")
)

# Complete
ledger.complete_run(run_id, exit_code=0, status="completed")
```

### Common Queries

```python
# Reverse lookup: which run produced this file?
run = ledger.find_run_by_output(Path("data/raw/corpus.syllables"))
print(run['command_line'])

# Show all runs using en_GB
runs = ledger.get_runs_by_tool("syllable_extractor")
en_gb = [r for r in runs if r['pyphen_lang'] == 'en_GB']

# Get overall statistics
stats = ledger.get_stats()
print(f"Total runs: {stats['total_runs']}")
print(f"Success rate: {stats['completed_runs']/stats['total_runs']*100:.1f}%")
```

## Integration with Extractors

When building new syllable extractors:

1. Call `start_run()` at the beginning
2. Record all inputs with `record_input()`
3. Record all outputs with `record_output()`
4. Call `complete_run()` in try/finally block

The ledger should **never** be in the critical path - if it fails, extraction should still succeed.

## Database Location

Default: `data/raw/syllable_extractor.db`

The database is small (metadata only, no syllables) and should be committed to version control
by default. It provides valuable build history without bloating the repository.

If it grows too large (unlikely), uncomment the gitignore rule in `.gitignore`:

```gitignore
# Database: commit by default (metadata), uncomment to ignore if too large
# data/raw/syllable_extractor.db
```

## Cross-Platform Compatibility

Paths are stored using `Path.as_posix()` which always uses forward slashes:

- Windows: `C:\data\file.txt` → stored as `C:/data/file.txt`
- Unix: `/data/file.txt` → stored as `/data/file.txt`

This ensures the database can be shared across platforms without path separator issues.

## Multi-Tool Support

The `extractor_tool` field distinguishes between different extraction tools:

- `syllable_extractor` (pyphen-based, current)
- `syllable_extractor_nltk` (NLTK-based, future)
- `syllable_extractor_espeak` (eSpeak-based, future)

All tools use the same ledger API and share the same database, enabling cross-tool comparisons:

```python
# Compare syllable counts across tools
SELECT extractor_tool, AVG(unique_syllable_count) as avg_unique
FROM runs r JOIN outputs o ON r.id = o.run_id
GROUP BY extractor_tool;
```

## File Organization

```text
build_tools/corpus_db/
  __init__.py       # Public API exports
  schema.py         # SQL table definitions and DDL
  ledger.py         # CorpusLedger class (main API)
```

Tests: `tests/test_corpus_db.py` (38 tests, 98% coverage)

## Philosophy

The corpus database embodies the principle: **"Build systems need memory, but they shouldn't have
opinions."**

It remembers what you did without telling you how to do it. It provides situational awareness
without imposing workflow. It's a ledger, not a conductor.
