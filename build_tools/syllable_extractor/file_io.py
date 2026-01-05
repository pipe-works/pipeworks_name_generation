"""
File I/O operations for syllable extraction.

This module handles all file reading, writing, and output generation
for the syllable extractor.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ExtractionResult

# Default output directory (relative to project root)
DEFAULT_OUTPUT_DIR = Path("_working/output")


def generate_output_filename(
    output_dir: Optional[Path] = None, language_code: Optional[str] = None
) -> tuple[Path, Path]:
    """
    Generate timestamped output filenames for syllables and metadata.

    Creates two output paths with the format:
    - YYYYMMDD_HHMMSS.syllables.LANG.txt (if language_code provided)
    - YYYYMMDD_HHMMSS.meta.LANG.txt (if language_code provided)

    Or without language code:
    - YYYYMMDD_HHMMSS.syllables.txt
    - YYYYMMDD_HHMMSS.meta.txt

    Args:
        output_dir: Directory to save files. Defaults to _working/output/
        language_code: Optional pyphen language code (e.g., 'en_US', 'de_DE').
                      If provided, will be included in the filename for easy
                      identification of language-specific syllable sets.

    Returns:
        Tuple of (syllables_path, metadata_path)

    Example:
        >>> # With language code
        >>> syllables_path, meta_path = generate_output_filename(language_code='en_US')
        >>> print(syllables_path)
        _working/output/20260104_153022.syllables.en_US.txt

        >>> # Without language code (backward compatible)
        >>> syllables_path, meta_path = generate_output_filename()
        >>> print(syllables_path)
        _working/output/20260104_153022.syllables.txt

    Note:
        Including the language code in filenames is useful when processing
        multiple files in different languages, making it easy to identify
        and organize language-specific syllable sets.
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp string
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Build filename with optional language code
    if language_code:
        syllables_path = output_dir / f"{timestamp}.syllables.{language_code}.txt"
        metadata_path = output_dir / f"{timestamp}.meta.{language_code}.txt"
    else:
        syllables_path = output_dir / f"{timestamp}.syllables.txt"
        metadata_path = output_dir / f"{timestamp}.meta.txt"

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
