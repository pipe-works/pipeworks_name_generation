# pipeworks_name_generation

> A lightweight, phonetic name generator that produces names which *sound right*,
> without imposing what they *mean*.

[![CI](https://github.com/aa-parky/pipeworks_name_generation/actions/workflows/ci.yml/badge.svg)](https://github.com/aa-parky/pipeworks_name_generation/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/aa-parky/pipeworks_name_generation/branch/main/graph/badge.svg)](https://codecov.io/gh/aa-parky/pipeworks_name_generation)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/aa-parky/pipeworks_name_generation)

`pipeworks_name_generation` is a standalone, GPL-3 licensed name generation system based on phonetic and syllabic recombination.

It generates **pronounceable, neutral names** intended to act purely as labels.  
Any narrative, cultural, or semantic meaning is deliberately left to downstream systems.

This project is designed to stand on its own and can be used independently of Pipeworks in
games, simulations, world-building tools, or other generative systems.

---

## Design Goals

- Generate names that are **linguistically plausible**, not random strings
- Avoid direct copying of real names or source material
- Support **deterministic generation** via seeding
- Remain **context-free** and reusable across domains
- Keep runtime dependencies lightweight, predictable, and stable
- Allow different consumers to apply their own meaning and interpretation

---

## Table of Contents

- [Installation](#installation)
  - [Requirements](#requirements)
  - [From Source](#from-source)
  - [From PyPI](#from-pypi)
  - [Verify Installation](#verify-installation)
- [Quick Start](#quick-start)
- [Build Tools](#build-tools)
  - [Syllable Extractor](#syllable-extractor)
  - [Syllable Normaliser](#syllable-normaliser)
  - [Syllable Feature Annotator](#syllable-feature-annotator)
  - [Feature Signature Analysis](#feature-signature-analysis)
  - [t-SNE Visualization](#t-sne-visualization)
- [Documentation](#documentation)
- [Non-Goals](#non-goals)
- [Architecture Overview](#architecture-overview)
- [Usage](#usage)
- [Design Philosophy](#design-philosophy)
- [Licence](#licence)
- [Status](#status)

---

## Installation

### Requirements

- Python 3.12 or higher
- No runtime dependencies (by design)

### From Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/aa-parky/pipeworks_name_generation.git
cd pipeworks_name_generation
pip install -e .
```

For development with testing and documentation tools:

```bash
pip install -e ".[dev]"
```

### From PyPI

> **Note:** Package not yet published to PyPI. Currently in Phase 1 (proof of concept).

Once published, installation will be:

```bash
pip install pipeworks-name-generation
```

### Verify Installation

Run the proof of concept example:

```bash
python examples/minimal_proof_of_concept.py
```

[↑ Back to Table of Contents](#table-of-contents)

---

## Quick Start

```python
from pipeworks_name_generation import NameGenerator

# Create a generator
gen = NameGenerator(pattern="simple")

# Generate a name deterministically
name = gen.generate(seed=42)
print(name)  # "Kawyn"

# Same seed = same name (always!)
assert gen.generate(seed=42) == name

# Generate multiple unique names
names = gen.generate_batch(count=10, base_seed=1000, unique=True)
print(names)
# ['Borkragmar', 'Kragso', 'Thrakrain', 'Alisra', ...]
```

**Key Feature:** Determinism is guaranteed. The same seed will always produce the same name,
making this ideal for games where entity IDs need consistent names across sessions.

[↑ Back to Table of Contents](#table-of-contents)

---

## Build Tools

The project includes build-time tools for analyzing and extracting phonetic patterns from text.

### Syllable Extractor

The syllable extractor uses dictionary-based hyphenation to extract syllables from text files.
This is a **build-time tool only** - not used during runtime name generation.

The tool supports two modes:

- **Interactive Mode** - Guided prompts for single-file processing
- **Batch Mode** - Automated processing of multiple files via command-line arguments

#### Interactive Mode

Run the interactive syllable extractor with no arguments:

```bash
python -m build_tools.syllable_extractor
```

The CLI will guide you through:

1. Selecting a language (40+ supported via pyphen) or auto-detection
2. Configuring syllable length constraints (default: 2-8 characters)
3. Choosing an input text file (with tab completion)
4. Extracting and saving syllables with metadata

#### Batch Mode

Process multiple files automatically using command-line arguments:

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
```

**Batch Mode Features:**

- Sequential processing with deterministic file ordering
- Continue-on-error with comprehensive error reporting
- Progress indicators and detailed summaries
- Support for automatic language detection
- Flexible input: single file, multiple files, or directory scanning

**Available Options:**

- `--file PATH` - Process a single file
- `--files PATH [PATH ...]` - Process multiple specific files
- `--source DIR` - Scan a directory for files
- `--lang CODE` - Use specific language code (e.g., en_US, de_DE)
- `--auto` - Automatically detect language from text
- `--pattern PATTERN` - File pattern for directory scanning (default: `*.txt`)
- `--recursive` - Scan directories recursively
- `--min N` - Minimum syllable length (default: 2)
- `--max N` - Maximum syllable length (default: 8)
- `--output DIR` - Output directory (default: `_working/output/`)
- `--quiet` - Suppress progress indicators
- `--verbose` - Show detailed processing information

#### Output Format

Output files are saved to `_working/output/` with timestamped names including language codes:

- `YYYYMMDD_HHMMSS.syllables.LANG.txt` - Unique syllables (one per line, sorted)
- `YYYYMMDD_HHMMSS.meta.LANG.txt` - Extraction metadata and statistics

Examples:

- `20260105_143022.syllables.en_US.txt`
- `20260105_143022.meta.en_US.txt`
- `20260105_143045.syllables.de_DE.txt`

The language code in filenames enables easy sorting and organization when processing
multiple files in different languages.

#### Programmatic Usage

Use the syllable extractor in your own scripts:

**Single-File Extraction:**

```python
from pathlib import Path
from build_tools.syllable_extractor import SyllableExtractor

# Initialize extractor for English (US)
extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)

# Extract syllables from text
syllables = extractor.extract_syllables_from_text("Hello wonderful world")
print(sorted(syllables))
# ['der', 'ful', 'hel', 'lo', 'won', 'world']

# Extract from a file
syllables = extractor.extract_syllables_from_file(Path('input.txt'))

# Save results
extractor.save_syllables(syllables, Path('output.txt'))
```

**Automatic Language Detection:**

```python
from build_tools.syllable_extractor import SyllableExtractor

# Automatic language detection from text
text = "Bonjour le monde, comment allez-vous?"
syllables, stats, detected_lang = SyllableExtractor.extract_with_auto_language(text)
print(f"Detected language: {detected_lang}")  # "fr"
print(f"Extracted {len(syllables)} syllables")

# Automatic detection from file
syllables, stats, detected_lang = SyllableExtractor.extract_file_with_auto_language(
    Path('german_text.txt')
)
print(f"Detected language: {detected_lang}")  # "de_DE"
```

**Batch Processing:**

```python
from pathlib import Path
from build_tools.syllable_extractor import discover_files, process_batch

# Discover files in a directory
files = discover_files(
    source=Path("~/documents"),
    pattern="*.txt",
    recursive=True
)

# Process batch with automatic language detection
result = process_batch(
    files=files,
    language_code="auto",  # or specific code like "en_US"
    min_len=2,
    max_len=8,
    output_dir=Path("_working/output"),
    quiet=False,
    verbose=False
)

# Check results
print(f"Processed {result.total_files} files")
print(f"Successful: {result.successful}")
print(f"Failed: {result.failed}")
print(result.format_summary())  # Detailed summary report
```

#### Supported Languages

The extractor supports 40+ languages through pyphen's LibreOffice dictionaries:

```python
from build_tools.syllable_extractor import SUPPORTED_LANGUAGES

print(f"{len(SUPPORTED_LANGUAGES)} languages available")
# English (US/UK), German, French, Spanish, Russian, and many more...
```

**Language Auto-Detection:**

The tool includes automatic language detection (requires `langdetect`):

```python
from build_tools.syllable_extractor import (
    detect_language_code,
    is_detection_available,
    list_supported_languages
)

# Check if detection is available
if is_detection_available():
    # Detect language from text
    lang_code = detect_language_code("Hello world, this is a test")
    print(lang_code)  # "en_US"

    # List all supported languages with detection
    languages = list_supported_languages()
    print(f"{len(languages)} languages available")
```

**Key Features:**

- Dictionary-based hyphenation using pyphen (LibreOffice dictionaries)
- Support for 40+ languages
- Automatic language detection (optional, via langdetect)
- Configurable syllable length constraints
- Deterministic extraction (same input = same output)
- Unicode support for accented characters
- Comprehensive metadata and statistics

For complete examples, see `examples/syllable_extraction_example.py`.

### Syllable Normaliser

The syllable normaliser transforms raw syllable files into canonical form through a 3-step pipeline,
creating the authoritative syllable inventory for pattern development. This is a **build-time tool only** -
not used during runtime name generation.

**3-Step Normalization Pipeline:**

1. **Aggregation** - Combine multiple input files while preserving all occurrences
2. **Canonicalization** - Unicode normalization, diacritic stripping, charset validation
3. **Frequency Analysis** - Count occurrences and generate frequency intelligence

#### Basic Usage

Process all .txt files in a directory through the complete pipeline:

```bash
# Basic usage - process directory with default settings
python -m build_tools.syllable_normaliser --source data/corpus/ --output _working/normalized/

# Recursive directory scan
python -m build_tools.syllable_normaliser --source data/ --recursive --output results/

# Custom syllable length constraints
python -m build_tools.syllable_normaliser --source data/ --min 3 --max 10

# Custom charset and Unicode normalization form
python -m build_tools.syllable_normaliser \
  --source data/ \
  --charset "abcdefghijklmnopqrstuvwxyz" \
  --unicode-form NFKD

# Verbose output with detailed statistics
python -m build_tools.syllable_normaliser --source data/ --verbose
```

#### Command-Line Options

**Input options (required):**

- `--source DIR` - Source directory containing input .txt files

**Directory scanning:**

- `--pattern PATTERN` - File pattern for discovery (default: `*.txt`)
- `--recursive` - Scan directories recursively

**Output options:**

- `--output DIR` - Output directory (default: `_working/normalized`)

**Normalization parameters:**

- `--min N` - Minimum syllable length (default: 2)
- `--max N` - Maximum syllable length (default: 20)
- `--charset STR` - Allowed character set (default: `abcdefghijklmnopqrstuvwxyz`)
- `--unicode-form FORM` - Unicode normalization: NFC, NFD, NFKC, NFKD (default: NFKD)

**Display options:**

- `--verbose` - Show detailed processing information

#### Output Files

The pipeline generates 5 output files:

1. **`syllables_raw.txt`** - Aggregated raw syllables (all occurrences preserved)
2. **`syllables_canonicalised.txt`** - Normalized canonical syllables
3. **`syllables_frequencies.json`** - Frequency intelligence (syllable → count)
4. **`syllables_unique.txt`** - Deduplicated canonical syllable inventory
5. **`normalization_meta.txt`** - Detailed statistics and metadata report

#### Pipeline Details

Step 1 - Aggregation:

- Combines all input files into `syllables_raw.txt`
- Preserves ALL occurrences (no deduplication)
- Maintains raw counts for frequency analysis
- Empty lines filtered during file reading

Step 2 - Canonicalization:

- Unicode normalization (NFKD - compatibility decomposition)
- Strip diacritics: café → cafe, résumé → resume
- Lowercase conversion
- Trim whitespace
- Charset validation (reject invalid characters)
- Length constraint enforcement
- Outputs to `syllables_canonicalised.txt`

Step 3 - Frequency Analysis:

- Count occurrences of each canonical syllable
- Generate frequency rankings and percentages
- Create deduplicated unique list (alphabetically sorted)
- Outputs:
  - `syllables_frequencies.json` - Frequency counts before deduplication
  - `syllables_unique.txt` - Authoritative syllable inventory
  - `normalization_meta.txt` - Comprehensive statistics report

#### Programmatic API Usage

**Full Pipeline:**

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

# Access frequency data
top_syllable = max(result.frequencies.items(), key=lambda x: x[1])
print(f"Most frequent: {top_syllable[0]} ({top_syllable[1]} occurrences)")
```

**Working with Individual Pipeline Steps:**

```python
from pathlib import Path
from build_tools.syllable_normaliser import (
    FileAggregator,
    SyllableNormalizer,
    FrequencyAnalyzer,
    NormalizationConfig,
    normalize_batch
)

# Step 1: Aggregation
aggregator = FileAggregator()
raw_syllables = aggregator.aggregate_files([Path("file1.txt"), Path("file2.txt")])
aggregator.save_raw_syllables(raw_syllables, Path("syllables_raw.txt"))

# Step 2: Normalization
config = NormalizationConfig(min_length=2, max_length=8)
canonical_syllables, rejection_stats = normalize_batch(raw_syllables, config)

# Save canonicalized syllables
with open("syllables_canonicalised.txt", "w", encoding="utf-8") as f:
    for syllable in canonical_syllables:
        f.write(f"{syllable}\n")

# Step 3: Frequency analysis
analyzer = FrequencyAnalyzer()
frequencies = analyzer.calculate_frequencies(canonical_syllables)
unique_syllables = analyzer.extract_unique_syllables(canonical_syllables)

# Save outputs
analyzer.save_frequencies(frequencies, Path("syllables_frequencies.json"))
analyzer.save_unique_syllables(unique_syllables, Path("syllables_unique.txt"))
```

**Single Syllable Normalization:**

```python
from build_tools.syllable_normaliser import SyllableNormalizer, NormalizationConfig

config = NormalizationConfig(min_length=2, max_length=20)
normalizer = SyllableNormalizer(config)

# Basic normalization
normalizer.normalize("Café")       # → "cafe"
normalizer.normalize("  HELLO  ")  # → "hello"
normalizer.normalize("résumé")     # → "resume"
normalizer.normalize("Zürich")     # → "zurich"

# Rejections return None
normalizer.normalize("x")          # → None (too short)
normalizer.normalize("hello123")   # → None (invalid characters)
normalizer.normalize("   ")        # → None (empty after normalization)
```

#### Frequency Intelligence

The frequency data captures how often each canonical syllable occurs **before** deduplication.
This intelligence is essential for understanding natural language patterns:

```json
{
  "ka": 187,
  "ra": 162,
  "mi": 145,
  "ta": 98
}
```

This shows "ka" appears 187 times in the canonical syllables, providing valuable frequency information
for weighted name generation patterns.

#### Key Features

- Unicode normalization (NFKD, NFC, NFD, NFKC)
- Diacritic stripping using unicodedata
- Configurable charset and length constraints
- Frequency intelligence capture (pre-deduplication counts)
- Deterministic processing (same input = same output)
- Comprehensive metadata reporting
- 5 output files for complete analysis

#### Important Notes

- This is a **build-time tool only** - not used during runtime name generation
- The normalizer is deterministic (same input always produces same output)
- Empty lines are filtered during aggregation (not counted as rejections)
- Frequency counts capture occurrences BEFORE deduplication
- All syllable processing is case-insensitive (output is lowercase)
- Unicode normalization form NFKD provides maximum compatibility decomposition

### Syllable Feature Annotator

The syllable feature annotator attaches phonetic features to normalized syllables, creating a feature-annotated
dataset for downstream pattern generation. This tool sits between the syllable normaliser and pattern development.
This is a **build-time tool only** - not used during runtime name generation.

**Design Philosophy:**

- Pure observation (observes patterns, never interprets or filters)
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

#### Running the Annotator

Annotate syllables with default paths (normalizer output):

```bash
# Basic usage with default paths
python -m build_tools.syllable_feature_annotator

# Annotate with custom paths
python -m build_tools.syllable_feature_annotator \
  --syllables data/normalized/syllables_unique.txt \
  --frequencies data/normalized/syllables_frequencies.json \
  --output data/annotated/syllables_annotated.json

# Enable verbose output
python -m build_tools.syllable_feature_annotator --verbose
```

#### Options

**Input options:**

- `--syllables PATH` - Path to syllables text file (default: `data/normalized/syllables_unique.txt`)
- `--frequencies PATH` - Path to frequencies JSON file (default: `data/normalized/syllables_frequencies.json`)

**Output options:**

- `--output PATH` - Path for annotated output JSON (default: `data/annotated/syllables_annotated.json`)

**Display options:**

- `--verbose`, `-v` - Show detailed progress information

#### Input/Output Contract

**Inputs** (from syllable normaliser):

- `syllables_unique.txt` - One canonical syllable per line
- `syllables_frequencies.json` - `{"syllable": count}` mapping

**Output**:

- `syllables_annotated.json` - Array of syllable records with features

#### Output Structure

The annotator produces JSON with this structure:

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

#### API Reference

**Full Pipeline:**

```python
from pathlib import Path
from build_tools.syllable_feature_annotator import run_annotation_pipeline

# Run complete annotation pipeline
result = run_annotation_pipeline(
    syllables_path=Path("data/normalized/syllables_unique.txt"),
    frequencies_path=Path("data/normalized/syllables_frequencies.json"),
    output_path=Path("data/annotated/syllables_annotated.json"),
    verbose=True
)

# Access results
print(f"Annotated {result.statistics.syllable_count} syllables")
print(f"Processing time: {result.statistics.processing_time:.2f}s")
```

**Annotate Syllables in Code:**

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

# Access feature detection results
print(f"Starts with cluster: {record.features['starts_with_cluster']}")
print(f"Contains plosive: {record.features['contains_plosive']}")
```

**Import Individual Components:**

```python
from build_tools.syllable_feature_annotator import (
    # Core functions
    run_annotation_pipeline,
    annotate_corpus,
    annotate_syllable,
    # Data models
    AnnotatedSyllable,
    AnnotationStatistics,
    AnnotationResult,
    # Feature detection
    FEATURE_DETECTORS,
    starts_with_vowel,
    contains_plosive,
    # Phoneme sets
    VOWELS,
    PLOSIVES,
    FRICATIVES,
    # File I/O
    load_syllables,
    load_frequencies,
    save_annotated_syllables
)
```

#### Random Sampling Tool

The syllable feature annotator includes a random sampling utility for quality assurance and inspection
of annotated syllables. This tool helps you examine random samples of the annotation output.

**Basic Usage:**

```bash
# Sample 100 syllables (default)
python -m build_tools.syllable_analysis.random_sampler

# Sample specific number of syllables
python -m build_tools.syllable_analysis.random_sampler --samples 50

# Use custom input/output paths
python -m build_tools.syllable_analysis.random_sampler \
    --input data/annotated/syllables_annotated.json \
    --output _working/my_samples.json \
    --samples 200

# Use a specific seed for reproducibility
python -m build_tools.syllable_analysis.random_sampler --samples 50 --seed 42
```

**Options:**

- `--input PATH` - Path to annotated syllables JSON (default: `data/annotated/syllables_annotated.json`)
- `--output PATH` - Path for output samples JSON (default: `_working/random_samples.json`)
- `--samples N` - Number of syllables to sample (default: 100)
- `--seed N` - Random seed for reproducibility (default: None, uses system randomness)

**Programmatic Usage:**

```python
from pathlib import Path
from build_tools.syllable_analysis.random_sampler import (
    load_annotated_syllables,
    sample_syllables,
    save_samples
)

# Load annotated syllables
records = load_annotated_syllables(Path("data/annotated/syllables_annotated.json"))

# Sample with deterministic seed
samples = sample_syllables(records, sample_count=50, seed=42)

# Save samples
save_samples(samples, Path("_working/samples.json"))
```

**Features:**

- Deterministic sampling with optional seed (reproducibility)
- Validates input and provides clear error messages
- Progress feedback during execution
- Outputs properly formatted JSON for easy inspection

#### Pipeline Integration

The feature annotator sits between the normaliser and pattern development:

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

#### Features

- Pure observation (tool observes patterns, never interprets or filters)
- Deterministic feature detection (same syllable = same features)
- Feature independence (12 independent boolean detectors)
- Language-agnostic structural patterns
- Conservative approximation (no linguistic overthinking)
- Processing speed: <1 second for 1,000-10,000 syllables
- Full type safety with comprehensive error handling

#### Notes

- This is a **build-time tool only** - not used during runtime name generation
- Features are structural observations, not linguistic interpretations
- All 12 features are applied to every syllable (no selective detection)
- Processing is fast and deterministic (same input = same output)
- Designed to integrate seamlessly with syllable normalizer output

### Feature Signature Analysis

The feature signature analysis tool examines annotated syllables to identify which feature combinations
actually exist in the data and how frequently each combination appears. This analysis helps understand
the diversity and distribution of phonetic patterns in your syllable corpus.

A "feature signature" is the set of all active (True) features for a syllable. For example, a syllable
with only `starts_with_vowel` and `ends_with_vowel` active would have the signature:
`('ends_with_vowel', 'starts_with_vowel')`.

This analysis answers questions like:

- What feature patterns are most common in natural language?
- Are certain feature combinations rare or impossible?
- How diverse is the feature space in the corpus?

#### Running the Analysis Tool

```bash
# Analyze with default paths (uses data/annotated/syllables_annotated.json)
python -m build_tools.syllable_analysis.feature_signatures

# Show only top 20 signatures
python -m build_tools.syllable_analysis.feature_signatures --limit 20

# Custom input/output paths
python -m build_tools.syllable_analysis.feature_signatures \
  --input data/annotated/syllables_annotated.json \
  --output _working/my_analysis/
```

#### Analysis Options

**Input options:**

- `--input PATH` - Path to syllables_annotated.json (default: `data/annotated/syllables_annotated.json`)

**Output options:**

- `--output PATH` - Output directory for analysis results (default: `_working/analysis/feature_signatures/`)

**Display options:**

- `--limit N` - Limit number of signatures in report (default: show all)

#### Report Format

The tool generates timestamped plain text reports (`YYYYMMDD_HHMMSS.feature_signatures.txt`) with:

```text
================================================================================
FEATURE SIGNATURE ANALYSIS
================================================================================
Generated: 2026-01-06 13:55:56
Total syllables analyzed: 23,160
Unique feature signatures: 361

SUMMARY STATISTICS
--------------------------------------------------------------------------------
Most common signature: 661 syllables (2.9%)
  Features: contains_liquid, contains_plosive, ends_with_vowel, long_vowel

Feature cardinality distribution:
  1 features: 3 unique signatures
  2 features: 17 unique signatures
  3 features: 54 unique signatures
  4 features: 86 unique signatures
  5 features: 96 unique signatures
  6 features: 70 unique signatures
  7 features: 30 unique signatures
  8 features: 5 unique signatures

================================================================================
SIGNATURE RANKINGS
--------------------------------------------------------------------------------
Rank   Count    Pct      Features
--------------------------------------------------------------------------------
1      661        2.85%  [4] contains_liquid, contains_plosive, ends_with_vowel, long_vowel
2      506        2.18%  [3] contains_plosive, ends_with_vowel, long_vowel
...
```

The report includes:

- **Header** - Generation timestamp, total syllables, unique signatures count
- **Summary Statistics** - Most common signature and feature cardinality distribution
- **Signature Rankings** - Detailed list of signatures with counts, percentages, and feature lists

#### Analysis API Reference

```python
from pathlib import Path
from build_tools.syllable_analysis.feature_signatures import run_analysis

# Run full analysis
result = run_analysis(
    input_path=Path("data/annotated/syllables_annotated.json"),
    output_dir=Path("_working/analysis/feature_signatures/"),
    limit=None  # Show all signatures
)

# Access results
print(f"Analyzed {result['total_syllables']:,} syllables")
print(f"Found {result['unique_signatures']:,} unique feature signatures")
print(f"Report saved to: {result['output_path']}")

# Access signature counter
for signature, count in result['signature_counter'].most_common(10):
    print(f"{count:4d} syllables: {', '.join(signature)}")
```

**Working with Individual Functions:**

```python
from build_tools.syllable_analysis.feature_signatures import (
    extract_signature,
    analyze_feature_signatures,
    format_signature_report
)

# Extract signature from a feature dict
features = {"starts_with_vowel": True, "ends_with_vowel": True, "short_vowel": True}
sig = extract_signature(features)
print(sig)  # ('ends_with_vowel', 'short_vowel', 'starts_with_vowel')

# Analyze signatures across records
records = [
    {"syllable": "ka", "features": {"ends_with_vowel": True}},
    {"syllable": "an", "features": {"starts_with_vowel": True, "ends_with_nasal": True}}
]
counter = analyze_feature_signatures(records)
print(f"Found {len(counter)} unique signatures")

# Format a report
report = format_signature_report(counter, total_syllables=len(records), limit=10)
print(report)
```

#### Analysis Tool Features

- Deterministic analysis (same input = same output)
- Human-readable plain text reports with formatted tables
- Timestamped output files for historical tracking
- Feature cardinality distribution analysis
- Configurable result limits for large datasets
- Comprehensive statistics (counts, percentages, rankings)

#### Analysis Tool Notes

- This is a **build-time analysis tool** - not used during runtime name generation
- Analyzes the output from the syllable feature annotator
- Results help inform pattern generation and syllable selection strategies
- Processing is fast: typically <1 second for 20,000+ syllables
- Reports are saved to `_working/analysis/feature_signatures/` by default

### t-SNE Visualization

The t-SNE (t-distributed Stochastic Neighbor Embedding) visualization tool creates 2D visualizations of the
high-dimensional feature signature space. This helps identify clustering patterns, syllable similarity, and
natural groupings in the annotated syllable corpus.

t-SNE is a dimensionality reduction technique that projects 12-dimensional feature vectors into 2D space while
preserving local structure. The visualization uses:

- **Position (x, y)**: t-SNE projection coordinates
- **Size**: Syllable frequency (larger points = more common)
- **Color**: Syllable frequency (warmer colors = more common)

**Output Formats:**

- **Static PNG**: High-resolution matplotlib visualization (always generated)
- **Interactive HTML**: Plotly-based interactive visualization with hover tooltips, zoom, pan, and export (optional)

This visualization helps answer questions like:

- Are there natural clusters in the feature space?
- Which syllables are similar based on phonetic features?
- Are there outliers or unique feature combinations?
- How does frequency relate to feature patterns?

#### Running the Visualizer

Generate a t-SNE visualization with default settings:

```bash
# Basic usage with default paths (static PNG only)
python -m build_tools.syllable_analysis.tsne_visualizer

# Generate both static PNG and interactive HTML
python -m build_tools.syllable_analysis.tsne_visualizer \
  --interactive \
  --save-mapping

# Custom input/output paths with interactive visualization
python -m build_tools.syllable_analysis.tsne_visualizer \
  --input data/annotated/syllables_annotated.json \
  --output _working/analysis/tsne/ \
  --interactive

# Adjust t-SNE parameters with interactive output
python -m build_tools.syllable_analysis.tsne_visualizer \
  --perplexity 50 \
  --random-state 123 \
  --interactive

# High-resolution output with interactive HTML
python -m build_tools.syllable_analysis.tsne_visualizer \
  --dpi 600 \
  --interactive \
  --save-mapping

# Verbose output
python -m build_tools.syllable_analysis.tsne_visualizer --verbose
```

#### Visualization Options

**Input options:**

- `--input PATH` - Path to syllables_annotated.json (default: `data/annotated/syllables_annotated.json`)

**Output options:**

- `--output PATH` - Output directory for visualizations (default: `_working/analysis/tsne/`)
- `--dpi N` - Output resolution in DPI for static PNG (default: 300)
- `--save-mapping` - Save syllable→features→coordinates mapping as JSON (default: False)
- `--interactive` - Generate interactive HTML visualization in addition to static PNG (requires Plotly)

**Algorithm parameters:**

- `--perplexity N` - t-SNE perplexity parameter (default: 30, range: 5-50)
- `--random-state N` - Random seed for reproducibility (default: 42)

**Display options:**

- `--verbose` - Show detailed progress information

#### Visualization Output Files

The visualizer generates timestamped files in the output directory:

1. **`YYYYMMDD_HHMMSS.tsne_visualization.png`** - High-resolution static visualization (PNG, always generated)
2. **`YYYYMMDD_HHMMSS.tsne_metadata.txt`** - Detailed metadata and interpretation guide
3. **`YYYYMMDD_HHMMSS.tsne_mapping.json`** - Syllable→features→coordinates mapping (optional, requires `--save-mapping`)
4. **`YYYYMMDD_HHMMSS.tsne_interactive.html`** - Interactive Plotly visualization (optional, requires `--interactive`)

Example output files:

- `20260106_143022.tsne_visualization.png` (static PNG)
- `20260106_143022.tsne_metadata.txt` (metadata)
- `20260106_143022.tsne_mapping.json` (when using `--save-mapping`)
- `20260106_143022.tsne_interactive.html` (when using `--interactive`)

**Static PNG metadata file includes:**

- Algorithm parameters (method, perplexity, random seed, dimensions, distance metric, features)
- Visualization encoding (axis meanings, point size/color)
- Interpretation guide (how to read the visualization)
- Technical details (DPI, generation timestamp)

**Interactive HTML features:**

- Hover tooltips showing syllable text, frequency, and active features
- Interactive zoom, pan, and exploration controls
- Export to high-resolution PNG directly from browser
- Self-contained HTML file with embedded metadata
- Works in any modern web browser without additional dependencies

The mapping file (optional) contains:

- Syllable text and frequency for each point
- 2D t-SNE coordinates (tsne_x, tsne_y)
- Complete feature dictionary for each syllable
- Useful for post-hoc cluster analysis and cross-referencing visualizations

#### Visualization API Reference

**Full Pipeline:**

```python
from pathlib import Path
from build_tools.syllable_analysis import run_tsne_visualization

# Run complete visualization pipeline with interactive output
result = run_tsne_visualization(
    input_path=Path("data/annotated/syllables_annotated.json"),
    output_dir=Path("_working/analysis/tsne/"),
    perplexity=30,
    random_state=42,
    dpi=300,
    verbose=True,
    save_mapping=True,  # Optional: save mapping file
    interactive=True    # Optional: generate interactive HTML (requires Plotly)
)

# Access results
print(f"Visualized {result['syllable_count']:,} syllables")
print(f"Projected {result['feature_count']} features into 2D")
print(f"Static visualization: {result['output_path']}")
print(f"Metadata saved to: {result['metadata_path']}")

# Access mapping file (if save_mapping=True)
if result['mapping_path']:
    print(f"Mapping saved to: {result['mapping_path']}")

# Access interactive HTML (if interactive=True)
if result['interactive_path']:
    print(f"Interactive HTML: {result['interactive_path']}")

# Access t-SNE coordinates
coords = result['tsne_coordinates']  # numpy array (n_syllables, 2)
```

**Working with Individual Functions:**

```python
from pathlib import Path
from build_tools.syllable_analysis.tsne_visualizer import (
    load_annotated_data,
    extract_feature_matrix,
    create_tsne_visualization,
    save_visualization,
    create_interactive_visualization,
    save_interactive_visualization
)

# Load data
records = load_annotated_data(Path("data/annotated/syllables_annotated.json"))

# Extract feature matrix
feature_matrix, frequencies = extract_feature_matrix(records)
print(f"Feature matrix shape: {feature_matrix.shape}")  # (n_syllables, 12)

# Create static visualization
fig, tsne_coords = create_tsne_visualization(
    feature_matrix,
    frequencies,
    perplexity=30,
    random_state=42
)

# Save static PNG (includes parameter logging in metadata)
viz_path, meta_path = save_visualization(
    fig,
    Path("_working/tsne/"),
    dpi=300,
    perplexity=30,
    random_state=42
)
print(f"Static PNG saved to: {viz_path}")

# Create interactive visualization (requires Plotly)
interactive_fig = create_interactive_visualization(records, tsne_coords)

# Save interactive HTML
html_path = save_interactive_visualization(
    interactive_fig,
    Path("_working/tsne/"),
    perplexity=30,
    random_state=42
)
print(f"Interactive HTML saved to: {html_path}")
```

#### Understanding t-SNE Parameters

**Perplexity** (default: 30):

- Balances attention between local and global structure
- Typical range: 5-50
- Lower values: emphasize local clusters
- Higher values: preserve global structure
- Rule of thumb: should be less than number of syllables
- Default of 30 works well for most corpus sizes (100-10,000 syllables)

**Random State** (default: 42):

- Controls random initialization of t-SNE
- Same value = reproducible visualizations
- Different values = different (but valid) layouts
- Use fixed value (e.g., 42) for consistent results

**Distance Metric**:

- Uses Hamming distance (optimal for binary feature vectors)
- Automatically configured for 12-dimensional binary features
- Not configurable via command-line (intentional design choice)

#### Visualization Features

- **Deterministic**: Same input + same seed = same visualization
- **High Resolution**: Default 300 DPI for publication quality
- **Reproducible**: Fixed random seeds for consistent results
- **Fast Processing**: Typically <10 seconds for 1,000-10,000 syllables
- **Comprehensive Metadata**: Detailed interpretation guide included
- **Integration**: Works seamlessly with syllable feature annotator output

#### Visualization Notes

- This is a **build-time analysis tool** - not used during runtime name generation
- **Required dependencies** (install with `pip install -e ".[build-tools]"`):
  - scikit-learn, matplotlib, numpy, pandas (for static PNG generation)
  - plotly (for interactive HTML generation, optional)
- t-SNE is non-deterministic by default, but we use fixed random seeds for reproducibility
- Processing time scales roughly O(n²) with corpus size
- For very large datasets (>50,000 syllables), consider sampling first
- Static visualizations saved as PNG files for easy sharing and embedding
- Interactive visualizations saved as self-contained HTML files (work in any modern browser)

#### Interpreting the Visualization

**What to look for:**

- **Nearby points**: Syllables with similar phonetic features
- **Clusters**: Natural groupings in the feature space
- **Large/bright points**: High-frequency syllables (common patterns)
- **Small/dark points**: Low-frequency syllables (rare patterns)
- **Isolated points**: Unique or rare feature combinations
- **Dense regions**: Common feature patterns
- **Sparse regions**: Less common feature patterns

**Example insights:**

- Vowel-initial syllables might cluster together
- Heavy consonant clusters might form distinct groups
- Frequency might correlate with certain feature patterns
- Outliers might indicate unusual phonetic combinations

[↑ Back to Table of Contents](#table-of-contents)

---

## Documentation

Full documentation is available and includes:

- **Installation Guide** - Setup instructions
- **Quick Start** - Get started in 5 minutes
- **User Guide** - Comprehensive usage patterns and examples
- **API Reference** - Complete API documentation
- **Development Guide** - Contributing and development setup

### Building Documentation Locally

To build and view the documentation on your machine:

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build the HTML documentation
cd docs
make html

# View the documentation
open build/html/index.html  # macOS
xdg-open build/html/index.html  # Linux
start build/html/index.html  # Windows
```

To clean and rebuild:

```bash
make clean && make html
```

### Online Documentation

> **Coming Soon:** Documentation will be automatically hosted on ReadTheDocs when the repository is public.

[↑ Back to Table of Contents](#table-of-contents)

---

## Non-Goals

This project deliberately does **not**:

- Encode lore, narrative meaning, or symbolism
- Distinguish between characters, places, organisations, or objects
- Imply cultural, regional, or historical identity
- Enforce genre-specific naming conventions
- Perform runtime natural-language processing
- Act as a world-building or storytelling system

All such concerns are expected to be handled by consuming applications.

[↑ Back to Table of Contents](#table-of-contents)

---

## Architecture Overview

At a high level, the system works as follows:

1. Phonetic or syllabic units are derived from language corpora  
   *(analysis and build-time only)*
2. These units are stored as neutral, reusable data
3. Names are generated by recombining units using weighted rules and constraints
4. The system emits pronounceable name strings, without semantic awareness

Natural language toolkits (such as NLTK) may be used during **analysis or build phases**,
but are intentionally excluded from the runtime generation path.

This keeps generation fast, deterministic, and easy to embed.

[↑ Back to Table of Contents](#table-of-contents)

---

## Usage

`pipeworks_name_generation` is intended to be consumed programmatically.

Typical use cases include:

- Character name generation
- Place and location naming
- Organisation or faction names
- Artefact or object labels
- Procedural or generative world systems

The generator itself does not distinguish between these uses.

[↑ Back to Table of Contents](#table-of-contents)

---

## Design Philosophy

Names generated by this system are **structural**, not narrative.

They are designed to feel:

- plausible
- consistent
- pronounceable

…but not authoritative.

Meaning, history, and interpretation are applied later, elsewhere.

[↑ Back to Table of Contents](#table-of-contents)

---

## Licence

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

You are free to use, modify, and distribute this software under the terms of the GPL.  
Improvements and derivative works must remain open under the same licence.

See the `LICENSE` file for full details.

[↑ Back to Table of Contents](#table-of-contents)

---

## Status

This project is under active development.  
APIs and internal structures may change as the system stabilises.
