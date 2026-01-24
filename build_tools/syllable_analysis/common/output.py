"""Output file and directory management for analysis tools.

This module provides utilities for managing output files and directories,
including automatic directory creation, timestamped filename generation,
and paired output file management (e.g., data + metadata).

Key Features
------------
- Automatic output directory creation
- Timestamped filename generation (YYYYMMDD_HHMMSS format)
- Paired output file generation (matching timestamps)
- Consistent naming conventions across all analysis tools

Usage
-----
Ensure output directory exists::

    from build_tools.syllable_analysis.common import ensure_output_dir
    from pathlib import Path

    output_dir = ensure_output_dir(Path("_working/analysis/tsne/"))

Generate timestamped output path::

    from build_tools.syllable_analysis.common import generate_timestamped_path

    viz_path = generate_timestamped_path(
        output_dir=Path("_working/analysis/tsne/"),
        suffix="tsne_visualization",
        extension="png"
    )
    # Returns: _working/analysis/tsne/20260107_143022.tsne_visualization.png

Generate paired output paths::

    from build_tools.syllable_analysis.common import generate_output_pair

    viz_path, meta_path = generate_output_pair(
        output_dir=Path("_working/analysis/tsne/"),
        primary_suffix="tsne_visualization",
        metadata_suffix="tsne_metadata",
        primary_ext="png",
        metadata_ext="txt"
    )
    # Returns matching timestamps:
    # - _working/analysis/tsne/20260107_143022.tsne_visualization.png
    # - _working/analysis/tsne/20260107_143022.tsne_metadata.txt

Module Contents
---------------
- ensure_output_dir(): Create output directory if it doesn't exist
- generate_timestamped_path(): Generate single timestamped output path
- generate_output_pair(): Generate pair of timestamped output paths
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def ensure_output_dir(output_dir: Path) -> Path:
    """Ensure output directory exists, creating it if necessary.

    This function creates the specified directory and all parent directories
    if they don't already exist. It is idempotent - calling it multiple times
    with the same path is safe and has no side effects.

    Parameters
    ----------
    output_dir : Path
        Directory path to ensure exists

    Returns
    -------
    Path
        The same path that was passed in (for chaining)

    Examples
    --------
    Basic usage::

        >>> from pathlib import Path
        >>> output_dir = ensure_output_dir(Path("_working/analysis/tsne/"))
        >>> output_dir.exists()
        True

    Create nested directories::

        >>> nested = ensure_output_dir(Path("_working/new/nested/dirs/"))
        >>> nested.exists()
        True

    Idempotent operation::

        >>> dir1 = ensure_output_dir(Path("_working/test/"))
        >>> dir2 = ensure_output_dir(Path("_working/test/"))
        >>> dir1 == dir2
        True

    Chaining::

        >>> output_file = ensure_output_dir(Path("_working/analysis/")) / "output.json"

    Notes
    -----
    This function uses ``Path.mkdir(parents=True, exist_ok=True)`` which:
    - Creates all parent directories as needed (like ``mkdir -p``)
    - Does not raise an error if the directory already exists
    - Raises ``PermissionError`` if insufficient permissions
    - Raises ``OSError`` for other filesystem errors

    The function returns the input path unchanged, which allows for convenient
    chaining in expressions.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_timestamped_path(
    output_dir: Path,
    suffix: str,
    extension: str = "txt",
    timestamp: str | None = None,
) -> Path:
    """Generate timestamped output file path.

    This function creates a path with format:
    ``{output_dir}/{timestamp}.{suffix}.{extension}``

    The timestamp format is ``YYYYMMDD_HHMMSS`` (e.g., ``20260107_143022``),
    which provides:
    - Chronological sorting
    - Uniqueness (assuming not more than one file per second)
    - Human readability
    - No special characters that could cause path issues

    Parameters
    ----------
    output_dir : Path
        Output directory (should exist or be created first)
    suffix : str
        File suffix describing content (e.g., 'tsne_visualization', 'metadata')
    extension : str, default='txt'
        File extension without leading dot (e.g., 'txt', 'json', 'png')
    timestamp : str, optional
        Specific timestamp string (format: YYYYMMDD_HHMMSS). If None (default),
        uses current time via ``datetime.now()``

    Returns
    -------
    Path
        Timestamped output file path

    Examples
    --------
    Basic usage (auto-generated timestamp)::

        >>> from pathlib import Path
        >>> path = generate_timestamped_path(
        ...     output_dir=Path("_working/analysis/tsne/"),
        ...     suffix="tsne_visualization",
        ...     extension="png"
        ... )
        >>> path.name
        '20260107_143022.tsne_visualization.png'

    Custom extension::

        >>> path = generate_timestamped_path(
        ...     output_dir=Path("_working/"),
        ...     suffix="results",
        ...     extension="json"
        ... )
        >>> path.suffix
        '.json'

    Explicit timestamp (for reproducibility or paired files)::

        >>> path = generate_timestamped_path(
        ...     output_dir=Path("_working/"),
        ...     suffix="output",
        ...     timestamp="20260107_120000"
        ... )
        >>> "20260107_120000" in str(path)
        True

    Notes
    -----
    File Naming Convention::

        {YYYYMMDD_HHMMSS}.{suffix}.{extension}

    Examples:
    - ``20260107_143022.tsne_visualization.png``
    - ``20260107_143022.tsne_metadata.txt``
    - ``20260107_143022.feature_signatures.txt``

    The directory is NOT created by this function - use ``ensure_output_dir()``
    first if the directory might not exist.

    Timestamp Format:
    - YYYY: 4-digit year
    - MM: 2-digit month (01-12)
    - DD: 2-digit day (01-31)
    - HH: 2-digit hour (00-23)
    - MM: 2-digit minute (00-59)
    - SS: 2-digit second (00-59)
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{timestamp}.{suffix}.{extension}"
    return output_dir / filename


def generate_output_pair(
    output_dir: Path,
    primary_suffix: str,
    metadata_suffix: str,
    primary_ext: str = "txt",
    metadata_ext: str = "txt",
) -> tuple[Path, Path]:
    """Generate matching pair of timestamped output paths.

    This function is useful for tools that generate both primary output and
    accompanying metadata files. It ensures both files use the same timestamp,
    making it easy to associate files and maintain chronological ordering.

    Parameters
    ----------
    output_dir : Path
        Output directory (should exist or be created first)
    primary_suffix : str
        Suffix for primary output file (e.g., 'tsne_visualization')
    metadata_suffix : str
        Suffix for metadata file (e.g., 'tsne_metadata')
    primary_ext : str, default='txt'
        File extension for primary file (e.g., 'png', 'json', 'html')
    metadata_ext : str, default='txt'
        File extension for metadata file (typically 'txt' or 'json')

    Returns
    -------
    tuple[Path, Path]
        Tuple of (primary_path, metadata_path) with matching timestamps

    Examples
    --------
    Generate visualization and metadata pair::

        >>> from pathlib import Path
        >>> viz_path, meta_path = generate_output_pair(
        ...     output_dir=Path("_working/analysis/tsne/"),
        ...     primary_suffix="tsne_visualization",
        ...     metadata_suffix="tsne_metadata",
        ...     primary_ext="png",
        ...     metadata_ext="txt"
        ... )
        >>> viz_path.name
        '20260107_143022.tsne_visualization.png'
        >>> meta_path.name
        '20260107_143022.tsne_metadata.txt'

    Generate data and metadata pair::

        >>> data_path, meta_path = generate_output_pair(
        ...     output_dir=Path("_working/results/"),
        ...     primary_suffix="analysis_results",
        ...     metadata_suffix="analysis_meta",
        ...     primary_ext="json",
        ...     metadata_ext="json"
        ... )

    Verify timestamp matching::

        >>> viz_path, meta_path = generate_output_pair(
        ...     output_dir=Path("_working/"),
        ...     primary_suffix="primary",
        ...     metadata_suffix="metadata"
        ... )
        >>> viz_path.stem.split('.')[0] == meta_path.stem.split('.')[0]
        True  # Same timestamp

    Notes
    -----
    Output Format::

        Primary:  {output_dir}/{timestamp}.{primary_suffix}.{primary_ext}
        Metadata: {output_dir}/{timestamp}.{metadata_suffix}.{metadata_ext}

    Examples:
    - Primary:  ``_working/analysis/tsne/20260107_143022.tsne_visualization.png``
    - Metadata: ``_working/analysis/tsne/20260107_143022.tsne_metadata.txt``

    The timestamp is generated once and used for both files, ensuring they
    are always associated and sort together in directory listings.

    The directory is NOT created by this function - use ``ensure_output_dir()``
    first if the directory might not exist.

    Use Cases:
    - t-SNE visualizer: PNG + metadata TXT
    - Feature analysis: results JSON + metadata TXT
    - Interactive plots: HTML + metadata JSON
    """
    # Generate timestamp once for both files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate both paths with the same timestamp
    primary_path = generate_timestamped_path(output_dir, primary_suffix, primary_ext, timestamp)
    metadata_path = generate_timestamped_path(output_dir, metadata_suffix, metadata_ext, timestamp)

    return primary_path, metadata_path
