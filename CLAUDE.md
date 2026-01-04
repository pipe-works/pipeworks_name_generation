# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`pipeworks_name_generation` is a phonetic name generator that produces pronounceable, neutral names without imposing semantic meaning. The system is designed to be context-free, deterministic, and lightweight.

**Critical Design Principle**: Determinism is paramount. The same seed must always produce the same name. This is essential for games where entity IDs need to map to consistent names across sessions.

## Development Commands

### Setup
```bash
# Create virtual environment (Python 3.12+)
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
pip install -e .
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_minimal_generation.py

# Run specific test
pytest tests/test_minimal_generation.py::TestBasicGeneration::test_generator_creates_deterministic_names

# Run tests verbose
pytest -v

# Run tests with coverage report
pytest --cov=pipeworks_name_generation --cov-report=html
```

### Code Quality
```bash
# Lint with ruff
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Type checking with mypy
mypy pipeworks_name_generation/

# Format with black (line length: 100)
black pipeworks_name_generation/ tests/
```

### Running Examples
```bash
python examples/minimal_proof_of_concept.py
```

### Build Tools
```bash
# Extract syllables from text (build-time tool)
python -m build_tools.syllable_extractor

# Run syllable extraction example
python examples/syllable_extraction_example.py
```

### Documentation
```bash
# Build documentation (fully automated from code docstrings)
cd docs
make html

# View documentation (macOS)
open build/html/index.html

# Clean and rebuild
make clean && make html

# Documentation is automatically generated from code using sphinx-autoapi
# No manual .rst files needed - just write good docstrings!
# The docs are also built automatically on ReadTheDocs when pushed to GitHub
```

## Architecture

### Current State (Phase 1 - Proof of Concept)

The project is in **Phase 1**: a minimal working proof of concept with hardcoded syllables.

**Core Components:**
- `pipeworks_name_generation/generator.py` - Contains `NameGenerator` class with hardcoded syllables
- Currently supports only the "simple" pattern
- No external dependencies at runtime (intentional design choice)

**Key Methods:**
- `NameGenerator.generate(seed, syllables=None)` - Generate single name deterministically
- `NameGenerator.generate_batch(count, base_seed, unique=True)` - Batch generation

### Critical Implementation Details

**Deterministic RNG:**
```python
# ALWAYS use Random(seed), NOT random.seed()
rng = random.Random(seed)  # Creates isolated RNG instance
# This avoids global state contamination
```

**Syllable Selection:**
- Currently uses `rng.sample()` without replacement to prevent repetition (e.g., "kakaka")
- Hardcoded syllables in `_SIMPLE_SYLLABLES` list
- Names are capitalized with `.capitalize()` (first letter only)

### Planned Architecture (Future Phases)

**Phase 2+** will add:
1. YAML pattern loading from `data/` directory
2. Multiple pattern sets beyond "simple"
3. Additional build tools in `build_tools/` (syllable extractor already implemented)
4. Phonotactic constraints
5. CLI interface

**Important**: Natural language toolkits (NLTK, etc.) are **build-time only**. They should never be runtime dependencies. The runtime generator must remain fast and lightweight.

## Directory Structure

```
pipeworks_name_generation/    # Core library code
tests/                         # pytest test suite
examples/                      # Usage examples
data/                          # Pattern files (future: YAML configs)
build_tools/                   # Build-time corpus analysis tools
  syllable_extractor.py        # Syllable extraction using pyphen (build-time only)
scripts/                       # Utility scripts
docs/                          # Documentation
_working/                      # Local scratch workspace (not committed)
```

## Design Philosophy

### What This System Is
- A phonetically-plausible name generator
- Deterministic and seedable
- Context-free and domain-agnostic
- Zero runtime dependencies (by design)

### What This System Is NOT
- A lore or narrative system
- Genre-specific (fantasy/sci-fi/etc.)
- Semantically aware
- Culturally or historically affiliated

The generator produces **structural** names. Meaning and interpretation are applied by consuming applications.

## Testing Requirements

All changes must maintain determinism. The following test **must always pass**:

```python
gen = NameGenerator(pattern="simple")
assert gen.generate(seed=42) == gen.generate(seed=42)
```

Batch generation must also be deterministic:
```python
batch1 = gen.generate_batch(count=5, base_seed=42)
batch2 = gen.generate_batch(count=5, base_seed=42)
assert batch1 == batch2
```

## Project Configuration

- **Python Version**: 3.12+
- **License**: GPL-3.0-or-later (all contributions must remain GPL)
- **Line Length**: 100 characters (black/ruff)
- **Type Checking**: mypy enabled but lenient in Phase 1 (`disallow_untyped_defs = false`)
- **Test Framework**: pytest with coverage reporting

## Current Phase Limitations

Phase 1 is intentionally minimal. The following are **hardcoded** and expected:
- Only "simple" pattern exists
- Syllables are hardcoded in generator.py
- No YAML loading
- No phonotactic constraints
- No CLI

Do not treat these as bugs or missing features in Phase 1. They are intentional scope limitations.

## Adding New Features

When extending beyond Phase 1:
1. Maintain determinism at all costs
2. Keep runtime dependencies minimal
3. Reserve heavy processing (NLP, corpus analysis) for build-time tools
4. Pattern data should be in `data/` directory
5. Build tools should be in `build_tools/` directory
6. All patterns must be loadable, not hardcoded
