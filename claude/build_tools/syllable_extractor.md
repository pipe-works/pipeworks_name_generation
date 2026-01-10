# Syllable Extractor

A build-time tool for extracting syllables from text files using dictionary-based hyphenation
via pyphen. This tool is used to generate syllable lists for pattern development.

## Key Features

- Dictionary-based hyphenation using pyphen (LibreOffice dictionaries)
- Support for 40+ languages
- Configurable syllable length constraints
- Deterministic extraction (same input = same output)
- Unicode support for accented characters
- Timestamped dual-file output (syllables + metadata)

## Interactive Usage

```bash
python -m build_tools.pyphen_syllable_extractor
# Prompts for:
# 1. Language selection (by number, name, or code)
# 2. Min/max syllable length (default: 2-8)
# 3. Input file path (with tab completion)
# Output is automatically saved to _working/output/
```

## Batch Mode Usage

The syllable extractor supports batch processing for automated workflows. Batch mode is
triggered by providing command-line arguments (when no arguments are provided, interactive
mode is used).

```bash
# Process a single file with manual language selection
python -m build_tools.pyphen_syllable_extractor --file input.txt --lang en_US

# Process a single file with automatic language detection
python -m build_tools.pyphen_syllable_extractor --file input.txt --auto

# Process multiple specific files
python -m build_tools.pyphen_syllable_extractor --files book1.txt book2.txt book3.txt --auto

# Scan a directory for files (non-recursive)
python -m build_tools.pyphen_syllable_extractor --source ~/documents/ --pattern "*.txt" --lang en_US

# Scan a directory recursively with auto-detection
python -m build_tools.pyphen_syllable_extractor --source ~/corpus/ --recursive --auto

# Use custom syllable length constraints and output directory
python -m build_tools.pyphen_syllable_extractor \
  --source ~/texts/ \
  --pattern "*.md" \
  --recursive \
  --auto \
  --min 3 \
  --max 6 \
  --output ~/results/

# Quiet mode (suppress progress indicators)
python -m build_tools.pyphen_syllable_extractor --files *.txt --lang de_DE --quiet

# Verbose mode (show detailed processing information)
python -m build_tools.pyphen_syllable_extractor --source ~/data/ --auto --verbose
```

## Batch Mode Options

### Input Options (mutually exclusive)

- `--file PATH` - Process a single file
- `--files PATH [PATH ...]` - Process multiple specific files
- `--source DIR` - Scan a directory for files (requires --pattern)

### Language Options (mutually exclusive, required)

- `--lang CODE` - Use specific language code (e.g., en_US, de_DE)
- `--auto` - Automatically detect language from text content

### Directory Scanning Options

- `--pattern PATTERN` - File pattern for directory scanning (default: `*.txt`)
- `--recursive` - Scan directories recursively

### Extraction Parameters

- `--min N` - Minimum syllable length (default: 2)
- `--max N` - Maximum syllable length (default: 8)
- `--output DIR` - Output directory (default: `_working/output/`)

### Output Control

- `--quiet` - Suppress progress indicators
- `--verbose` - Show detailed processing information

## Batch Mode Behavior

- **Sequential Processing:** Files are processed one at a time in sorted order (deterministic)
- **Error Handling:** Processing continues even if individual files fail
- **Summary Report:** Displays statistics, successful files, and failures at the end
- **Exit Codes:** Returns 0 if all files succeed, 1 if any failures occur
- **Flat Output:** All output files are saved to a single directory with language codes in filenames

## Programmatic Batch Usage

```python
from pathlib import Path
from build_tools.pyphen_syllable_extractor import (
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

## Programmatic Single-File Usage

```python
from pathlib import Path
from build_tools.pyphen_syllable_extractor import (
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

## Output Format

Files are saved to `_working/output/` with timestamped names including language codes:

- `YYYYMMDD_HHMMSS.syllables.LANG.txt` - Unique syllables (one per line, sorted, lowercase)
- `YYYYMMDD_HHMMSS.meta.LANG.txt` - Extraction metadata and statistics

Examples:

- `20260105_143022.syllables.en_US.txt`
- `20260105_143022.meta.en_US.txt`
- `20260105_143045.syllables.de_DE.txt`
- `20260105_143045.meta.de_DE.txt`

The language code in filenames enables easy sorting and organization when processing multiple files in different languages.

### Metadata Contents

Metadata includes:

- Extraction date/time
- Language code
- Syllable length constraints
- Input file path
- Total unique syllables extracted
- Length distribution (with bar chart)
- Sample syllables (first 15)

## Supported Languages

The tool supports 40+ languages via pyphen. Common examples:

- `en_US`, `en_GB` - English (US/UK)
- `de_DE`, `de_AT`, `de_CH` - German (Germany/Austria/Switzerland)
- `fr` - French
- `es` - Spanish
- `pt_BR`, `pt_PT` - Portuguese (Brazil/Portugal)
- `ru_RU` - Russian
- Many more (see `SUPPORTED_LANGUAGES` in the code)

## Important Notes

- This is a **build-time tool only** - pyphen should NEVER be a runtime dependency
- The extractor is deterministic (same input always produces same output)
- Only extracts syllables from words that pyphen can hyphenate (filters out unsplittable words)
- Case-insensitive processing (all output is lowercase)
- Punctuation and special characters are automatically removed

## Testing

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

## Test Coverage

### Core Extraction Tests

- Initialization and configuration
- Syllable extraction from text and files
- Length constraint enforcement
- Output file generation
- Metadata formatting
- Edge cases and error handling

### Batch Processing Tests

- File discovery with pattern matching and recursion
- Single file batch processing with error handling
- Multi-file batch processing
- Result aggregation and formatting
- Argument parsing and validation
- Main batch function integration
- End-to-end workflows and determinism

### Language Detection Tests

- ISO code to pyphen locale mapping
- Auto-detection with various languages
- Error handling and fallbacks
- Integration with SyllableExtractor
