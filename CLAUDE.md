# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`pipeworks_name_generation` is a phonetic name generator that produces pronounceable, neutral
names without imposing semantic meaning. The system is designed to be context-free,
deterministic, and lightweight.

**Critical Design Principle**: Determinism is paramount. The same seed must always produce
the same name. This is essential for games where entity IDs need to map to consistent names
across sessions.

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

# Run all code quality checks at once
pre-commit run --all-files
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Run hooks manually on staged files
pre-commit run

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks for a commit (use sparingly)
git commit --no-verify
```

### Running Examples

```bash
python examples/minimal_proof_of_concept.py
```

### Build Tool Commands

```bash
# Extract syllables from text (interactive mode)
python -m build_tools.syllable_extractor

# Extract syllables in batch mode - single file
python -m build_tools.syllable_extractor --file input.txt --lang en_US

# Extract syllables in batch mode - multiple files
python -m build_tools.syllable_extractor --files file1.txt file2.txt file3.txt --auto

# Extract syllables in batch mode - directory scan
python -m build_tools.syllable_extractor --source ~/documents/ --pattern "*.txt" --lang en_US

# Extract syllables in batch mode - recursive directory scan with auto-detection
python -m build_tools.syllable_extractor --source ~/corpus/ --recursive --auto

# Extract syllables with custom parameters
python -m build_tools.syllable_extractor --file input.txt --lang de_DE --min 3 --max 6 --output ~/results/

# Run syllable extraction example (programmatic)
python examples/syllable_extraction_example.py

# Test syllable extractor (all tests)
pytest tests/test_syllable_extractor.py tests/test_syllable_extractor_batch.py -v

# Test only batch processing
pytest tests/test_syllable_extractor_batch.py -v

# Normalize syllables through 3-step pipeline (build-time tool)
python -m build_tools.syllable_normaliser --source data/corpus/ --output _working/normalized/

# Normalize syllables recursively with custom parameters
python -m build_tools.syllable_normaliser \
  --source data/ \
  --recursive \
  --min 3 \
  --max 10 \
  --output results/ \
  --verbose

# Test syllable normaliser (40 tests)
pytest tests/test_syllable_normaliser.py -v
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

**Important**: Natural language toolkits (NLTK, etc.) are **build-time only**. They should
never be runtime dependencies. The runtime generator must remain fast and lightweight.

## Directory Structure

```text
pipeworks_name_generation/    # Core library code
tests/                         # pytest test suite
examples/                      # Usage examples
data/                          # Pattern files (future: YAML configs)
build_tools/                   # Build-time corpus analysis tools
  syllable_extractor.py        # Syllable extraction using pyphen (build-time only)
scripts/                       # Utility scripts
docs/                          # Documentation
_working/                      # Local scratch workspace (not committed)
  output/                      # Default output directory for build tools
```

## Build Tools

### Syllable Extractor (`build_tools/syllable_extractor.py`)

A build-time tool for extracting syllables from text files using dictionary-based hyphenation
via pyphen. This tool is used to generate syllable lists for pattern development.

**Key Features:**

- Dictionary-based hyphenation using pyphen (LibreOffice dictionaries)
- Support for 40+ languages
- Configurable syllable length constraints
- Deterministic extraction (same input = same output)
- Unicode support for accented characters
- Timestamped dual-file output (syllables + metadata)

**Interactive Usage:**

```bash
python -m build_tools.syllable_extractor
# Prompts for:
# 1. Language selection (by number, name, or code)
# 2. Min/max syllable length (default: 2-8)
# 3. Input file path (with tab completion)
# Output is automatically saved to _working/output/
```

**Batch Mode Usage:**

The syllable extractor supports batch processing for automated workflows. Batch mode is triggered
by providing command-line arguments (when no arguments are provided, interactive mode is used).

```bash
# Process a single file with manual language selection
python -m build_tools.syllable_extractor --file input.txt --lang en_US

# Process a single file with automatic language detection
python -m build_tools.syllable_extractor --file input.txt --auto

# Process multiple specific files
python -m build_tools.syllable_extractor --files book1.txt book2.txt book3.txt --auto

# Scan a directory for files (non-recursive)
python -m build_tools.syllable_extractor --source ~/documents/ --pattern "*.txt" --lang en_US

# Scan a directory recursively with auto-detection
python -m build_tools.syllable_extractor --source ~/corpus/ --recursive --auto

# Use custom syllable length constraints and output directory
python -m build_tools.syllable_extractor \
  --source ~/texts/ \
  --pattern "*.md" \
  --recursive \
  --auto \
  --min 3 \
  --max 6 \
  --output ~/results/

# Quiet mode (suppress progress indicators)
python -m build_tools.syllable_extractor --files *.txt --lang de_DE --quiet

# Verbose mode (show detailed processing information)
python -m build_tools.syllable_extractor --source ~/data/ --auto --verbose
```

**Batch Mode Options:**

Input options (mutually exclusive):

- `--file PATH` - Process a single file
- `--files PATH [PATH ...]` - Process multiple specific files
- `--source DIR` - Scan a directory for files (requires --pattern)

Language options (mutually exclusive, required):

- `--lang CODE` - Use specific language code (e.g., en_US, de_DE)
- `--auto` - Automatically detect language from text content

Directory scanning options:

- `--pattern PATTERN` - File pattern for directory scanning (default: `*.txt`)
- `--recursive` - Scan directories recursively

Extraction parameters:

- `--min N` - Minimum syllable length (default: 2)
- `--max N` - Maximum syllable length (default: 8)
- `--output DIR` - Output directory (default: `_working/output/`)

Output control:

- `--quiet` - Suppress progress indicators
- `--verbose` - Show detailed processing information

**Batch Mode Behavior:**

- **Sequential Processing:** Files are processed one at a time in sorted order (deterministic)
- **Error Handling:** Processing continues even if individual files fail
- **Summary Report:** Displays statistics, successful files, and failures at the end
- **Exit Codes:** Returns 0 if all files succeed, 1 if any failures occur
- **Flat Output:** All output files are saved to a single directory with language codes in filenames

**Programmatic Batch Usage:**

```python
from pathlib import Path
from build_tools.syllable_extractor import (
    discover_files,
    process_batch,
    process_single_file_batch,
    BatchResult,
    FileProcessingResult
)

# Discover files in a directory
files = discover_files(
    source=Path("~/documents"),
    pattern="*.txt",
    recursive=True
)

# Process batch
result: BatchResult = process_batch(
    files=files,
    language_code="en_US",  # or "auto" for detection
    min_len=2,
    max_len=8,
    output_dir=Path("_working/output"),
    quiet=False,
    verbose=False
)

# Check results
print(f"Total: {result.total_files}")
print(f"Successful: {result.successful}")
print(f"Failed: {result.failed}")
print(result.format_summary())

# Process single file programmatically
file_result: FileProcessingResult = process_single_file_batch(
    input_path=Path("input.txt"),
    language_code="auto",
    min_len=3,
    max_len=6,
    output_dir=Path("output"),
    verbose=False
)

if file_result.success:
    print(f"Extracted {file_result.syllables_count} syllables")
    print(f"Detected language: {file_result.language_code}")
else:
    print(f"Error: {file_result.error_message}")
```

**Programmatic Single-File Usage:**

```python
from pathlib import Path
from build_tools.syllable_extractor import (
    SyllableExtractor,
    ExtractionResult,
    generate_output_filename,
    save_metadata
)

# Initialize extractor
extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)

# Extract syllables from file
syllables = extractor.extract_syllables_from_file(Path('input.txt'))

# Generate timestamped output paths
syllables_path, metadata_path = generate_output_filename()

# Save outputs
extractor.save_syllables(syllables, syllables_path)

# Create and save metadata
result = ExtractionResult(
    syllables=syllables,
    language_code='en_US',
    min_syllable_length=2,
    max_syllable_length=8,
    input_path=Path('input.txt')
)
save_metadata(result, metadata_path)
```

**Output Format:**

Files are saved to `_working/output/` with timestamped names including language codes:

- `YYYYMMDD_HHMMSS.syllables.LANG.txt` - Unique syllables (one per line, sorted, lowercase)
- `YYYYMMDD_HHMMSS.meta.LANG.txt` - Extraction metadata and statistics

Examples:

- `20260105_143022.syllables.en_US.txt`
- `20260105_143022.meta.en_US.txt`
- `20260105_143045.syllables.de_DE.txt`
- `20260105_143045.meta.de_DE.txt`

The language code in filenames enables easy sorting and organization when processing
multiple files in different languages.

Metadata includes:

- Extraction date/time
- Language code
- Syllable length constraints
- Input file path
- Total unique syllables extracted
- Length distribution (with bar chart)
- Sample syllables (first 15)

**Supported Languages:**

The tool supports 40+ languages via pyphen. Common examples:

- `en_US`, `en_GB` - English (US/UK)
- `de_DE`, `de_AT`, `de_CH` - German (Germany/Austria/Switzerland)
- `fr` - French
- `es` - Spanish
- `pt_BR`, `pt_PT` - Portuguese (Brazil/Portugal)
- `ru_RU` - Russian
- Many more (see `SUPPORTED_LANGUAGES` in the code)

**Important Notes:**

- This is a **build-time tool only** - pyphen should NEVER be a runtime dependency
- The extractor is deterministic (same input always produces same output)
- Only extracts syllables from words that pyphen can hyphenate (filters out unsplittable words)
- Case-insensitive processing (all output is lowercase)
- Punctuation and special characters are automatically removed

**Testing:**

```bash
# Run all syllable extractor tests (87 tests total)
pytest tests/test_syllable_extractor.py tests/test_syllable_extractor_batch.py -v

# Run only core extraction tests (33 tests)
pytest tests/test_syllable_extractor.py -v

# Run only batch processing tests (34 tests)
pytest tests/test_syllable_extractor_batch.py -v

# Run only language detection tests (20 tests)
pytest tests/test_language_detection.py -v
```

**Test Coverage:**

Core extraction tests (`test_syllable_extractor.py`):

- Initialization and configuration
- Syllable extraction from text and files
- Length constraint enforcement
- Output file generation
- Metadata formatting
- Edge cases and error handling

Batch processing tests (`test_syllable_extractor_batch.py`):

- File discovery with pattern matching and recursion
- Single file batch processing with error handling
- Multi-file batch processing
- Result aggregation and formatting
- Argument parsing and validation
- Main batch function integration
- End-to-end workflows and determinism

Language detection tests (`test_language_detection.py`):

- ISO code to pyphen locale mapping
- Auto-detection with various languages
- Error handling and fallbacks
- Integration with SyllableExtractor

### Syllable Normaliser (`build_tools/syllable_normaliser/`)

A build-time tool for normalizing and analyzing syllable corpuses through a 3-step pipeline.
This tool transforms raw syllable files into canonical form with frequency intelligence,
creating the authoritative syllable inventory for pattern development and feature annotation.

**3-Step Normalization Pipeline:**

1. **Aggregation** - Combine multiple input files while preserving all occurrences
2. **Canonicalization** - Unicode normalization, diacritic stripping, charset validation
3. **Frequency Analysis** - Count occurrences and generate frequency intelligence

**Key Features:**

- Unicode normalization (NFKD, NFC, NFD, NFKC)
- Diacritic stripping using unicodedata
- Configurable charset and length constraints
- Frequency intelligence capture (pre-deduplication counts)
- Deterministic processing (same input = same output)
- 5 output files for comprehensive analysis

**Basic Usage:**

```bash
# Process all .txt files in a directory
python -m build_tools.syllable_normaliser --source data/corpus/ --output _working/normalized/

# Recursive directory scan
python -m build_tools.syllable_normaliser --source data/ --recursive --output results/

# Custom syllable length constraints
python -m build_tools.syllable_normaliser --source data/ --min 3 --max 10

# Custom charset and Unicode form
python -m build_tools.syllable_normaliser \
  --source data/ \
  --charset "abcdefghijklmnopqrstuvwxyz" \
  --unicode-form NFKD

# Verbose output with detailed statistics
python -m build_tools.syllable_normaliser --source data/ --verbose
```

**Command-Line Options:**

Input options (required):

- `--source DIR` - Source directory containing input .txt files

Directory scanning options:

- `--pattern PATTERN` - File pattern for discovery (default: `*.txt`)
- `--recursive` - Scan directories recursively

Output options:

- `--output DIR` - Output directory (default: `_working/normalized`)

Normalization parameters:

- `--min N` - Minimum syllable length (default: 2)
- `--max N` - Maximum syllable length (default: 20)
- `--charset STR` - Allowed character set (default: `abcdefghijklmnopqrstuvwxyz`)
- `--unicode-form FORM` - Unicode normalization form: NFC, NFD, NFKC, NFKD (default: NFKD)

Display options:

- `--verbose` - Show detailed processing information

**Output Files:**

The pipeline generates 5 output files in the specified output directory:

1. `syllables_raw.txt` - Aggregated raw syllables (all occurrences preserved)
2. `syllables_canonicalised.txt` - Normalized canonical syllables
3. `syllables_frequencies.json` - Frequency intelligence (syllable → count mapping)
4. `syllables_unique.txt` - Deduplicated canonical syllable inventory
5. `normalization_meta.txt` - Detailed statistics and metadata report

**Pipeline Details:**

Step 1 - Aggregation:

- Combines all input files into a single raw file
- Preserves ALL occurrences (no deduplication)
- Maintains raw counts intact for frequency analysis
- Empty lines are filtered during file reading

Step 2 - Canonicalization:

- Unicode normalization (NFKD by default - compatibility decomposition)
- Strip diacritics (remove combining marks using unicodedata)
- Lowercase conversion
- Trim whitespace
- Enforce allowed charset (reject syllables with invalid characters)
- Check length constraints (reject syllables outside min/max range)
- Track rejection reasons (empty, charset, length)

Step 3 - Frequency Analysis:

- Calculate occurrence counts for each canonical syllable
- Generate frequency rankings and percentages
- Create deduplicated unique syllable list (sorted alphabetically)
- Save frequency intelligence as JSON
- Generate comprehensive metadata report

**Programmatic API Usage:**

```python
from pathlib import Path
from build_tools.syllable_normaliser import (
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

**Working with Individual Components:**

```python
from build_tools.syllable_normaliser import (
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
from build_tools.syllable_normaliser import normalize_batch
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

**Normalization Examples:**

```python
from build_tools.syllable_normaliser import SyllableNormalizer, NormalizationConfig

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

**Frequency Intelligence:**

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

**Metadata Report:**

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

**Important Notes:**

- This is a **build-time tool only** - not used during runtime name generation
- The normalizer is deterministic (same input always produces same output)
- Empty lines are filtered during aggregation (not counted as rejections)
- Frequency counts capture occurrences BEFORE deduplication (intelligence capture)
- All syllable processing is case-insensitive (output is lowercase)
- Unicode normalization form NFKD provides compatibility decomposition for maximum normalization

**Testing:**

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

**Test Coverage:**

Data models tests:

- Configuration validation (min/max length, Unicode form)
- Statistics calculation (rejection counts, rates)
- Result formatting (metadata generation)

Normalization tests:

- Unicode NFKD normalization
- Diacritic stripping (café → cafe, résumé → resume)
- Charset validation (reject numbers, symbols)
- Length constraint enforcement
- Batch processing with rejection tracking

Aggregation tests:

- Multi-file aggregation preserving duplicates
- Empty line filtering
- File discovery (recursive, patterns, sorting)
- Deterministic file ordering

Frequency analysis tests:

- Frequency counting from duplicates
- Ranked entry generation with percentages
- Unique syllable extraction (sorted)
- JSON and text file I/O

Integration tests:

- Full pipeline end-to-end workflow
- Rejection statistics accuracy
- Output file generation
- Deterministic processing (same input = same output)

### Syllable Feature Annotator (`build_tools/syllable_feature_annotator/`)

A build-time tool for annotating syllables with phonetic feature detection. This tool sits
between the syllable normalizer and pattern development, attaching structural features to
each canonical syllable for downstream use.

**3-Layer Architecture:**

1. **Data Models** - AnnotatedSyllable, AnnotationStatistics, AnnotationResult
2. **Core Logic** - Pure annotation functions (no I/O, no side effects)
3. **Pipeline** - End-to-end orchestration with file I/O

**Key Features:**

- Pure observation (tool observes patterns, never interprets or filters)
- Deterministic feature detection (same syllable = same features)
- Feature independence (12 independent boolean detectors)
- Language-agnostic structural patterns
- Conservative approximation (no linguistic overthinking)

**Feature Set (12 features):**

Onset Features (3):

- `starts_with_vowel` - Open onset (vowel-initial)
- `starts_with_cluster` - Initial consonant cluster (2+ consonants)
- `starts_with_heavy_cluster` - Heavy initial cluster (3+ consonants)

Internal Features (4):

- `contains_plosive` - Contains plosive consonant (p, t, k, b, d, g)
- `contains_fricative` - Contains fricative consonant (f, s, z, v, h)
- `contains_liquid` - Contains liquid consonant (l, r, w)
- `contains_nasal` - Contains nasal consonant (m, n)

Nucleus Features (2):

- `short_vowel` - Exactly one vowel (weight proxy)
- `long_vowel` - Two or more vowels (weight proxy)

Coda Features (3):

- `ends_with_vowel` - Open syllable (vowel-final)
- `ends_with_nasal` - Nasal coda
- `ends_with_stop` - Stop coda

**Basic Usage:**

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

**Input/Output Contract:**

Inputs:

- `syllables_unique.txt` - One canonical syllable per line (from normalizer)
- `syllables_frequencies.json` - `{"syllable": count}` mapping (from normalizer)

Output:

- `syllables_annotated.json` - Array of syllable records with features

**Output Format:**

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

**Programmatic API Usage:**

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

**Annotate syllables in code:**

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

**Module Structure:**

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

**Design Principles:**

1. **Pure Observation**: Tool never asks "should we...", only "is this true/false?"
2. **No Filtering**: Processes all syllables without exclusion or validation
3. **Feature Independence**: No detector depends on another detector's output
4. **Conservative Detection**: Structural patterns without linguistic interpretation
5. **Deterministic**: Same input always produces same output

**Important Notes:**

- This is a **build-time tool only** (not used during runtime name generation)
- Features are structural observations, not linguistic interpretations
- All 12 features are applied to every syllable (no selective detection)
- Processing is fast: typically <1 second for 1,000-10,000 syllables
- Designed to integrate seamlessly with syllable normalizer output

**Testing:**

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

**Pipeline Integration:**

The feature annotator sits between the normalizer and pattern development:

```bash
# Step 1: Normalize syllables from corpus
python -m build_tools.syllable_normaliser \
  --source data/corpus/ \
  --output data/normalized/

# Step 2: Annotate normalized syllables with features
python -m build_tools.syllable_feature_annotator \
  --syllables data/normalized/syllables_unique.txt \
  --frequencies data/normalized/syllables_frequencies.json \
  --output data/annotated/syllables_annotated.json

# Step 3: Use annotated syllables for pattern generation (future)
```

### Analysis Tools (`build_tools/syllable_feature_annotator/analysis/`)

Post-annotation analysis utilities for exploring and visualizing syllable feature data. These tools help understand feature distributions, patterns, and relationships in the annotated syllable corpus.

**Modular Architecture (Refactored):**

The analysis tools follow a clean modular architecture with shared utilities:

```text
build_tools/syllable_feature_annotator/analysis/
├── common/                      # Shared utilities
│   ├── paths.py                 # Path management and defaults
│   ├── data_io.py               # Data loading/saving functions
│   └── output.py                # Output file management
├── dimensionality/              # Dimensionality reduction
│   ├── feature_matrix.py        # Feature extraction and transformation
│   ├── tsne_core.py             # t-SNE dimensionality reduction
│   └── mapping.py               # Coordinate mapping utilities
├── plotting/                    # Visualization modules
│   ├── styles.py                # Shared styling constants
│   ├── static.py                # Matplotlib static visualizations
│   └── interactive.py           # Plotly interactive visualizations
├── random_sampler.py            # Random sampling utility for QA
├── feature_signatures.py        # Feature combination frequency analysis
└── tsne_visualizer.py           # t-SNE visualization CLI
```

**Key Features:**

- **Modular Design**: Shared utilities eliminate code duplication
- **Reusable Components**: Dimensionality reduction and plotting modules work independently
- **High Test Coverage**: 100% coverage on core modules (common, dimensionality feature_matrix/mapping, plotting static/styles)
- **Optional Dependencies**: Matplotlib, numpy, plotly are optional (gracefully handled)
- **Deterministic**: All tools produce reproducible results with same inputs

**Common Utilities (`common/`):**

Shared functionality used across all analysis tools:

```python
from build_tools.syllable_feature_annotator.analysis.common import (
    default_paths,              # Centralized path configuration
    load_annotated_syllables,   # Load syllables_annotated.json with validation
    load_frequency_data,         # Load syllables_frequencies.json
    save_json_output,            # Save JSON with consistent formatting
    ensure_output_dir,           # Create output directories
    generate_timestamped_path,   # Generate timestamped file paths
)

# Access default paths
input_path = default_paths.annotated_syllables
output_dir = default_paths.analysis_output_dir("tsne")

# Load annotated data
records = load_annotated_syllables(input_path)

# Save results
save_json_output(results, output_path)
```

**Dimensionality Reduction (`dimensionality/`):**

Extract feature matrices and apply dimensionality reduction algorithms:

```python
from build_tools.syllable_feature_annotator.analysis.dimensionality import (
    ALL_FEATURES,              # 12 canonical feature names
    extract_feature_matrix,    # Convert records to numpy matrix
    apply_tsne,                # Apply t-SNE dimensionality reduction
    create_tsne_mapping,       # Map coordinates back to syllables
    save_tsne_mapping,         # Save mapping as JSON
)

# Extract feature matrix
feature_matrix, frequencies = extract_feature_matrix(records)

# Apply t-SNE
tsne_coords = apply_tsne(feature_matrix, perplexity=30, random_state=42)

# Create mapping
mapping = create_tsne_mapping(records, tsne_coords)
save_tsne_mapping(mapping, output_path)
```

**Visualization (`plotting/`):**

Create static (matplotlib) and interactive (Plotly) visualizations:

```python
from build_tools.syllable_feature_annotator.analysis.plotting import (
    # Static plotting (matplotlib)
    create_tsne_scatter,       # Create scatter plot
    save_static_plot,          # Save as PNG
    create_metadata_text,      # Generate metadata

    # Interactive plotting (Plotly) - optional
    PLOTLY_AVAILABLE,          # Check if Plotly installed
    create_interactive_scatter,  # Create interactive plot
    save_interactive_html,       # Save as HTML

    # Styling constants
    DEFAULT_COLORMAP,          # "viridis"
    DEFAULT_FIGURE_SIZE,       # (14, 10)
    DEFAULT_DPI,               # 300
)

# Static visualization
fig = create_tsne_scatter(tsne_coords, frequencies)
save_static_plot(fig, Path("output.png"), dpi=300)

# Interactive visualization (if Plotly available)
if PLOTLY_AVAILABLE:
    fig = create_interactive_scatter(records, tsne_coords)
    save_interactive_html(fig, Path("output.html"), perplexity=30, random_state=42)
```

**Analysis Tools:**

1. **Random Sampler** (`random_sampler.py`)
   - Random sampling of annotated syllables for QA
   - Deterministic sampling with seed support
   - Quick corpus exploration

   ```bash
   python -m build_tools.syllable_feature_annotator.analysis.random_sampler \
     --samples 10 \
     --seed 42 \
     --output _working/analysis/random_sampler/
   ```

2. **Feature Signatures** (`feature_signatures.py`)
   - Analyze frequency of feature combinations
   - Identify common and rare feature patterns
   - Generate detailed reports with statistics

   ```bash
   python -m build_tools.syllable_feature_annotator.analysis.feature_signatures \
     --input data/annotated/syllables_annotated.json \
     --output _working/analysis/feature_signatures/ \
     --limit 20
   ```

3. **t-SNE Visualizer** (`tsne_visualizer.py`)
   - Dimensionality reduction visualization of feature space
   - Generate static (PNG) and interactive (HTML) plots
   - Explore feature clustering and relationships

   ```bash
   python -m build_tools.syllable_feature_annotator.analysis.tsne_visualizer \
     --input data/annotated/syllables_annotated.json \
     --output _working/analysis/tsne/ \
     --perplexity 30 \
     --dpi 300 \
     --interactive \
     --save-mapping
   ```

**Design Principles:**

1. **Modularity**: Shared utilities in `common/`, reusable ML in `dimensionality/`, independent plotting in `plotting/`
2. **Separation of Concerns**: Data loading, ML algorithms, and visualization are independent
3. **Optional Dependencies**: Tools work without matplotlib/numpy/plotly (graceful degradation)
4. **Deterministic**: Same inputs always produce same outputs (reproducible analysis)
5. **Testability**: Pure functions with clear contracts (100% coverage on core modules)
6. **Extensibility**: Easy to add new analysis tools using shared utilities

**Testing:**

```bash
# Run all analysis tests (218 tests)
pytest tests/test_analysis_common.py tests/test_dimensionality.py tests/test_plotting.py \
       tests/test_random_sampler.py tests/test_feature_signatures.py -v

# Test coverage:
# - Common modules: 66 tests (100% coverage on paths, data_io, output)
# - Dimensionality: 43 tests (87-100% coverage on feature_matrix, tsne_core, mapping)
# - Plotting: 40 tests (91-100% coverage on static, interactive, styles)
# - Random sampler: 35 tests (85% coverage)
# - Feature signatures: 34 tests (77% coverage)
```

**Important Notes:**

- These are **build-time analysis tools** (not used during runtime name generation)
- All tools accept custom paths (defaults use `common.default_paths`)
- Output files are timestamped to prevent overwriting
- Tools work independently but share common infrastructure
- Matplotlib/numpy/plotly are optional dependencies (tools check availability)

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
- **Pre-commit Hooks**: Enabled for automated code quality checks
- **CI/CD**: GitHub Actions for testing, linting, security, docs, and builds

## CI/CD Pipeline

### GitHub Actions Workflows

**Main CI Pipeline** (`.github/workflows/ci.yml`):

- **Code Quality**: Ruff linting, Black formatting, mypy type checking
- **Test Suite**: Runs on Ubuntu, macOS, Windows with Python 3.12 and 3.13
- **Security Scan**: Bandit for code security, Safety for dependency vulnerabilities
- **Documentation**: Builds Sphinx docs and checks for excessive warnings
- **Package Build**: Builds distribution packages and validates with twine
- **Coverage**: Uploads coverage reports to Codecov

**Dependency Updates** (`.github/workflows/dependency-update.yml`):

- Runs weekly on Monday at 9:00 AM UTC
- Checks for outdated dependencies
- Creates GitHub issues with update recommendations

### CI Pre-commit Hooks

The project uses pre-commit hooks for automated code quality enforcement:

**File Formatting**:

- Trailing whitespace removal
- End-of-file fixing
- Line ending normalization (LF)

**Code Quality**:

- YAML/TOML/JSON validation
- Python AST checking
- Import sorting (isort)
- Code formatting (Black)
- Linting (Ruff with auto-fix)
- Type checking (mypy for main package)

**Security**:

- Bandit security scanning
- Dependency vulnerability checking (Safety)

**Documentation**:

- Markdown linting (markdownlint)
- Spell checking (codespell)

**Triggers**:

- Pre-commit hooks run automatically on `git commit`
- CI pipeline runs on pushes to `main`/`develop` and on pull requests
- Can be manually triggered via GitHub Actions UI

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
