"""
File I/O operations for NLTK-based syllable extraction.

This module handles all file reading, writing, and output generation
for the NLTK syllable extractor.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import ExtractionResult

# Default output directory (relative to project root)
DEFAULT_OUTPUT_DIR = Path("_working/output")


def generate_output_filename(
    output_dir: Path | None = None,
    language_code: str | None = None,
    run_timestamp: str | None = None,
    input_filename: str | None = None,
) -> tuple[Path, Path]:
    """
    Generate output filenames in run-based subdirectory structure.

    Creates a run directory with timestamp and 'nltk' identifier, then organizes
    outputs into syllables/ and meta/ subdirectories:
    - output_dir/YYYYMMDD_HHMMSS_nltk/syllables/filename.txt
    - output_dir/YYYYMMDD_HHMMSS_nltk/meta/filename.txt

    This structure groups each extraction run's outputs together, making it
    easier to manage, archive, or delete complete runs as atomic units.

    Args:
        output_dir: Base output directory. Defaults to _working/output/
        language_code: Optional language code (e.g., 'en_US').
                      Used for filename if input_filename not provided.
        run_timestamp: Optional timestamp string (YYYYMMDD_HHMMSS format).
                      If provided, uses this timestamp for the run directory name.
                      If not provided, generates a new timestamp using datetime.now().
                      **Critical for batch processing** - pass the same timestamp to group
                      all files from a batch into one run directory.
        input_filename: Optional input filename to use for output naming.
                       If provided, output files will use this name (e.g., 'alice.txt').
                       Takes precedence over language_code for naming.

    Returns:
        Tuple of (syllables_path, metadata_path)

    Example:
        >>> # Interactive mode - single file with language code
        >>> syllables_path, meta_path = generate_output_filename(language_code='en_US')
        >>> print(syllables_path)
        _working/output/20260110_153022_nltk/syllables/en_US.txt

        >>> # Batch mode - multiple files sharing one run directory
        >>> timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        >>> s1, m1 = generate_output_filename(
        ...     run_timestamp=timestamp,
        ...     input_filename='alice.txt'
        ... )
        >>> s2, m2 = generate_output_filename(
        ...     run_timestamp=timestamp,
        ...     input_filename='middlemarch.txt'
        ... )
        >>> print(s1)
        _working/output/20260110_153022_nltk/syllables/alice.txt
        >>> print(s2)
        _working/output/20260110_153022_nltk/syllables/middlemarch.txt
        >>> # Both files share the same run directory

    Note:
        For batch processing, always pass the same run_timestamp to group all
        outputs into a single run directory. This represents one logical batch
        operation, regardless of how many input files are processed.
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    # Generate timestamp string if not provided
    if run_timestamp is None:
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create run directory structure (with nltk identifier)
    run_dir = output_dir / f"{run_timestamp}_nltk"
    syllables_dir = run_dir / "syllables"
    meta_dir = run_dir / "meta"

    # Ensure subdirectories exist
    syllables_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename (priority: input_filename > language_code > defaults)
    if input_filename:
        output_name = input_filename
    elif language_code:
        output_name = f"{language_code}.txt"
    else:
        output_name = "syllables.txt"

    # Build full paths
    syllables_path = syllables_dir / output_name
    metadata_path = meta_dir / output_name

    return syllables_path, metadata_path


def save_metadata(result: ExtractionResult, output_path: Path) -> None:
    """
    Save extraction metadata to a text file.

    Args:
        result: ExtractionResult containing metadata to save
        output_path: Path to the output metadata file

    Raises:
        IOError: If there's an error writing the file

    Example:
        >>> result = ExtractionResult(...)
        >>> save_metadata(result, Path("output.meta.txt"))
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.format_metadata())
    except Exception as e:
        raise IOError(f"Error writing metadata file {output_path}: {e}")
