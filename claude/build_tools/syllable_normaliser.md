# Syllable Normaliser

A build-time tool for normalizing and analyzing syllable corpuses through a 3-step pipeline.
This tool transforms raw syllable files into canonical form with frequency intelligence,
creating the authoritative syllable inventory for pattern development and feature annotation.

## 3-Step Normalization Pipeline

1. **Aggregation** - Combine multiple input files while preserving all occurrences
2. **Canonicalization** - Unicode normalization, diacritic stripping, charset validation
3. **Frequency Analysis** - Count occurrences and generate frequency intelligence

## Key Features

- Unicode normalization (NFKD, NFC, NFD, NFKC)
- Diacritic stripping using unicodedata
- Configurable charset and length constraints
- Frequency intelligence capture (pre-deduplication counts)
- Deterministic processing (same input = same output)
- 5 output files for comprehensive analysis

## Basic Usage

```bash
# Process all .txt files in a directory
python -m build_tools.pyphen_syllable_normaliser --source data/corpus/ --output _working/normalized/

# Recursive directory scan
python -m build_tools.pyphen_syllable_normaliser --source data/ --recursive --output results/

# Custom syllable length constraints
python -m build_tools.pyphen_syllable_normaliser --source data/ --min 3 --max 10

# Custom charset and Unicode form
python -m build_tools.pyphen_syllable_normaliser \
  --source data/ \
  --charset "abcdefghijklmnopqrstuvwxyz" \
  --unicode-form NFKD

# Verbose output with detailed statistics
python -m build_tools.pyphen_syllable_normaliser --source data/ --verbose
```

## Command-Line Options

### Input Options (required)

- `--source DIR` - Source directory containing input .txt files

### Directory Scanning Options

- `--pattern PATTERN` - File pattern for discovery (default: `*.txt`)
- `--recursive` - Scan directories recursively

### Output Options

- `--output DIR` - Output directory (default: `_working/normalized`)

### Normalization Parameters

- `--min N` - Minimum syllable length (default: 2)
- `--max N` - Maximum syllable length (default: 20)
- `--charset STR` - Allowed character set (default: `abcdefghijklmnopqrstuvwxyz`)
- `--unicode-form FORM` - Unicode normalization form: NFC, NFD, NFKC, NFKD (default: NFKD)

### Display Options

- `--verbose` - Show detailed processing information

## Output Files

The pipeline generates 5 output files in the specified output directory:

1. `syllables_raw.txt` - Aggregated raw syllables (all occurrences preserved)
2. `syllables_canonicalised.txt` - Normalized canonical syllables
3. `syllables_frequencies.json` - Frequency intelligence (syllable → count mapping)
4. `syllables_unique.txt` - Deduplicated canonical syllable inventory
5. `normalization_meta.txt` - Detailed statistics and metadata report

## Pipeline Details

### Step 1 - Aggregation

- Combines all input files into a single raw file
- Preserves ALL occurrences (no deduplication)
- Maintains raw counts intact for frequency analysis
- Empty lines are filtered during file reading

### Step 2 - Canonicalization

- Unicode normalization (NFKD by default - compatibility decomposition)
- Strip diacritics (remove combining marks using unicodedata)
- Lowercase conversion
- Trim whitespace
- Enforce allowed charset (reject syllables with invalid characters)
- Check length constraints (reject syllables outside min/max range)
- Track rejection reasons (empty, charset, length)

### Step 3 - Frequency Analysis

- Calculate occurrence counts for each canonical syllable
- Generate frequency rankings and percentages
- Create deduplicated unique syllable list (sorted alphabetically)
- Save frequency intelligence as JSON
- Generate comprehensive metadata report

## Programmatic API Usage

```python
from pathlib import Path
from build_tools.pyphen_syllable_normaliser import (
    NormalizationConfig,
    run_full_pipeline,
    discover_input_files
)

# Discover input files
files = discover_input_files(
    source_dir=Path("data/corpus/"),
    pattern="*.txt",
    recursive=False
)

# Create configuration
config = NormalizationConfig(
    min_length=2,
    max_length=20,
    allowed_charset="abcdefghijklmnopqrstuvwxyz",
    unicode_form="NFKD"
)

# Run full pipeline
result = run_full_pipeline(
    input_files=files,
    output_dir=Path("_working/normalized"),
    config=config,
    verbose=True
)

# Access results
print(f"Processed {result.stats.raw_count:,} raw syllables")
print(f"Canonical: {result.stats.after_canonicalization:,}")
print(f"Unique: {result.stats.unique_canonical:,}")
print(f"Rejection rate: {result.stats.rejection_rate:.1f}%")
print(f"Processing time: {result.stats.processing_time:.2f}s")

# Access frequency data
top_syllable = max(result.frequencies.items(), key=lambda x: x[1])
print(f"Most frequent: {top_syllable[0]} ({top_syllable[1]} occurrences)")
```

## Working with Individual Components

```python
from build_tools.pyphen_syllable_normaliser import (
    SyllableNormalizer,
    FileAggregator,
    FrequencyAnalyzer,
    NormalizationConfig
)

# Step 1: Aggregation
aggregator = FileAggregator()
raw_syllables = aggregator.aggregate_files([Path("file1.txt"), Path("file2.txt")])
aggregator.save_raw_syllables(raw_syllables, Path("syllables_raw.txt"))

# Step 2: Normalization
from build_tools.pyphen_syllable_normaliser import normalize_batch
config = NormalizationConfig(min_length=2, max_length=8)
canonical_syllables, rejection_stats = normalize_batch(raw_syllables, config)

# Step 3: Frequency analysis
analyzer = FrequencyAnalyzer()
frequencies = analyzer.calculate_frequencies(canonical_syllables)
unique_syllables = analyzer.extract_unique_syllables(canonical_syllables)

# Save outputs
analyzer.save_frequencies(frequencies, Path("syllables_frequencies.json"))
analyzer.save_unique_syllables(unique_syllables, Path("syllables_unique.txt"))

# Access rejection statistics
print(f"Rejected (empty): {rejection_stats['rejected_empty']}")
print(f"Rejected (charset): {rejection_stats['rejected_charset']}")
print(f"Rejected (length): {rejection_stats['rejected_length']}")
```

## Normalization Examples

```python
from build_tools.pyphen_syllable_normaliser import SyllableNormalizer, NormalizationConfig

config = NormalizationConfig(min_length=2, max_length=20)
normalizer = SyllableNormalizer(config)

# Basic normalization
normalizer.normalize("Café")       # → "cafe"
normalizer.normalize("  HELLO  ")  # → "hello"
normalizer.normalize("résumé")     # → "resume"
normalizer.normalize("Zürich")     # → "zurich"

# Rejections
normalizer.normalize("x")          # → None (too short)
normalizer.normalize("hello123")   # → None (invalid characters)
normalizer.normalize("   ")        # → None (empty after normalization)
normalizer.normalize("verylongword")  # → None (too long with default max_length=20)
```

## Frequency Intelligence

The frequency data captures how often each canonical syllable occurs *before* deduplication.
This intelligence is essential for understanding natural language patterns in the source corpus:

```json
{
  "ka": 187,
  "ra": 162,
  "mi": 145,
  "ta": 98
}
```

This shows "ka" appears 187 times in the canonical syllables before we create the unique list.

## Metadata Report

The `normalization_meta.txt` file includes:

- Processing timestamp and input file count
- Raw syllables count
- Canonicalized syllables count
- Rejection breakdown (empty, charset, length)
- Rejection rate percentage
- Unique canonical syllables count
- Processing time
- Top 20 most frequent syllables with percentages
- Normalization configuration (min/max length, charset, Unicode form)
- Output file listing

## Important Notes

- This is a **build-time tool only** - not used during runtime name generation
- The normalizer is deterministic (same input always produces same output)
- Empty lines are filtered during aggregation (not counted as rejections)
- Frequency counts capture occurrences BEFORE deduplication (intelligence capture)
- All syllable processing is case-insensitive (output is lowercase)
- Unicode normalization form NFKD provides compatibility decomposition for maximum normalization

## Testing

```bash
# Run all syllable normaliser tests (40 tests)
pytest tests/test_syllable_normaliser.py -v

# Test coverage includes:
# - Data models (configuration, statistics, results) - 11 tests
# - Core normalization (Unicode, diacritics, charset, length) - 8 tests
# - File aggregation (discovery, reading, combining) - 10 tests
# - Frequency analysis (counting, ranking, deduplication) - 6 tests
# - Full pipeline integration (end-to-end, rejections, determinism) - 3 tests
```

## Test Coverage

### Data Models Tests

- Configuration validation (min/max length, Unicode form)
- Statistics calculation (rejection counts, rates)
- Result formatting (metadata generation)

### Normalization Tests

- Unicode NFKD normalization
- Diacritic stripping (café → cafe, résumé → resume)
- Charset validation (reject numbers, symbols)
- Length constraint enforcement
- Batch processing with rejection tracking

### Aggregation Tests

- Multi-file aggregation preserving duplicates
- Empty line filtering
- File discovery (recursive, patterns, sorting)
- Deterministic file ordering

### Frequency Analysis Tests

- Frequency counting from duplicates
- Ranked entry generation with percentages
- Unique syllable extraction (sorted)
- JSON and text file I/O

### Integration Tests

- Full pipeline end-to-end workflow
- Rejection statistics accuracy
- Output file generation
- Deterministic processing (same input = same output)
