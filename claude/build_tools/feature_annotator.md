# Syllable Feature Annotator

A build-time tool for annotating syllables with phonetic feature detection. This tool sits
between the syllable normalizer and pattern development, attaching structural features to each
canonical syllable for downstream use.

## 3-Layer Architecture

1. **Data Models** - AnnotatedSyllable, AnnotationStatistics, AnnotationResult
2. **Core Logic** - Pure annotation functions (no I/O, no side effects)
3. **Pipeline** - End-to-end orchestration with file I/O

## Key Features

- Pure observation (tool observes patterns, never interprets or filters)
- Deterministic feature detection (same syllable = same features)
- Feature independence (12 independent boolean detectors)
- Language-agnostic structural patterns
- Conservative approximation (no linguistic overthinking)

## Feature Set (12 features)

### Onset Features (3)

- `starts_with_vowel` - Open onset (vowel-initial)
- `starts_with_cluster` - Initial consonant cluster (2+ consonants)
- `starts_with_heavy_cluster` - Heavy initial cluster (3+ consonants)

### Internal Features (4)

- `contains_plosive` - Contains plosive consonant (p, t, k, b, d, g)
- `contains_fricative` - Contains fricative consonant (f, s, z, v, h)
- `contains_liquid` - Contains liquid consonant (l, r, w)
- `contains_nasal` - Contains nasal consonant (m, n)

### Nucleus Features (2)

- `short_vowel` - Exactly one vowel (weight proxy)
- `long_vowel` - Two or more vowels (weight proxy)

### Coda Features (3)

- `ends_with_vowel` - Open syllable (vowel-final)
- `ends_with_nasal` - Nasal coda
- `ends_with_stop` - Stop coda

## Basic Usage

```bash
# Annotate syllables with default paths (normalizer output)
python -m build_tools.syllable_feature_annotator

# Annotate with custom paths
python -m build_tools.syllable_feature_annotator \
  --syllables data/normalized/syllables_unique.txt \
  --frequencies data/normalized/syllables_frequencies.json \
  --output data/annotated/syllables_annotated.json

# Enable verbose output
python -m build_tools.syllable_feature_annotator --verbose
```

## Input/Output Contract

### Inputs

- `syllables_unique.txt` - One canonical syllable per line (from normalizer)
- `syllables_frequencies.json` - `{"syllable": count}` mapping (from normalizer)

### Output

- `syllables_annotated.json` - Array of syllable records with features

## Output Format

```json
[
  {
    "syllable": "kran",
    "frequency": 7,
    "features": {
      "starts_with_vowel": false,
      "starts_with_cluster": true,
      "starts_with_heavy_cluster": false,
      "contains_plosive": true,
      "contains_fricative": false,
      "contains_liquid": true,
      "contains_nasal": true,
      "short_vowel": true,
      "long_vowel": false,
      "ends_with_vowel": false,
      "ends_with_nasal": true,
      "ends_with_stop": false
    }
  }
]
```

## Programmatic API Usage

```python
from pathlib import Path
from build_tools.syllable_feature_annotator import run_annotation_pipeline

# Run full pipeline
result = run_annotation_pipeline(
    syllables_path=Path("data/normalized/syllables_unique.txt"),
    frequencies_path=Path("data/normalized/syllables_frequencies.json"),
    output_path=Path("data/annotated/syllables_annotated.json"),
    verbose=True
)

print(f"Annotated {result.statistics.syllable_count} syllables")
print(f"Processing time: {result.statistics.processing_time:.2f}s")
```

## Annotate Syllables in Code

```python
from build_tools.syllable_feature_annotator import (
    annotate_corpus,
    annotate_syllable,
    FEATURE_DETECTORS
)

# Annotate a corpus
syllables = ["ka", "kran", "spla"]
frequencies = {"ka": 187, "kran": 7, "spla": 2}
result = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)

# Annotate a single syllable
record = annotate_syllable("kran", 7, FEATURE_DETECTORS)
print(f"{record.syllable}: {sum(record.features.values())} features active")
```

## Module Structure

```text
build_tools/syllable_feature_annotator/
├── __init__.py              # Public API exports
├── __main__.py              # Module entry point
├── cli.py                   # Argument parsing and CLI
├── annotator.py             # Core orchestration and data models
├── feature_rules.py         # 12 feature detector functions
├── phoneme_sets.py          # Character class definitions
└── file_io.py               # I/O helper functions
```

## Design Principles

1. **Pure Observation**: Tool never asks "should we...", only "is this true/false?"
2. **No Filtering**: Processes all syllables without exclusion or validation
3. **Feature Independence**: No detector depends on another detector's output
4. **Conservative Detection**: Structural patterns without linguistic interpretation
5. **Deterministic**: Same input always produces same output

## Important Notes

- This is a **build-time tool only** (not used during runtime name generation)
- Features are structural observations, not linguistic interpretations
- All 12 features are applied to every syllable (no selective detection)
- Processing is fast: typically <1 second for 1,000-10,000 syllables
- Designed to integrate seamlessly with syllable normalizer output

## Testing

```bash
# Run all feature annotator tests (80 tests)
pytest tests/test_syllable_feature_annotator.py -v

# Test coverage includes:
# - Phoneme sets (7 tests)
# - Onset features (9 tests)
# - Internal features (12 tests)
# - Nucleus features (5 tests)
# - Coda features (9 tests)
# - Feature registry (4 tests)
# - Annotation logic (7 tests)
# - File I/O (8 tests)
# - CLI (6 tests)
# - Integration (3 tests)
# - Determinism (4 tests)
# - Real-world examples (5 tests)
```

## Pipeline Integration

The feature annotator sits between the normalizer and pattern development:

```bash
# Step 1: Normalize syllables from corpus
python -m build_tools.pyphen_syllable_normaliser \
  --source data/corpus/ \
  --output data/normalized/

# Step 2: Annotate normalized syllables with features
python -m build_tools.syllable_feature_annotator \
  --syllables data/normalized/syllables_unique.txt \
  --frequencies data/normalized/syllables_frequencies.json \
  --output data/annotated/syllables_annotated.json

# Step 3: Use annotated syllables for pattern generation (future)
```

## Analysis Tools

Post-annotation analysis utilities are available for exploring and visualizing syllable feature
data. See [Analysis Tools](analysis_tools.md) for details.
