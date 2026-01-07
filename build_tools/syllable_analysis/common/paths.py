"""Path management and default path configuration for analysis tools.

This module provides centralized path management for all analysis tools in the
syllable feature annotator. It eliminates code duplication by providing a single
source of truth for project structure and default paths.

Key Features
------------
- Automatic project root detection
- Standard default paths for inputs and outputs
- Per-tool output directory management
- Platform-independent path handling

Usage
-----
Using the module-level singleton (recommended)::

    from build_tools.syllable_analysis.common import default_paths

    # Access default input path
    input_path = default_paths.annotated_syllables

    # Get tool-specific output directory
    output_dir = default_paths.analysis_output_dir("tsne")

Creating a custom instance::

    from build_tools.syllable_analysis.common.paths import AnalysisPathConfig
    from pathlib import Path

    # Use custom root
    custom_paths = AnalysisPathConfig(root=Path("/custom/project/root"))
    input_path = custom_paths.annotated_syllables

Module Contents
---------------
- AnalysisPathConfig: Main path configuration class
- default_paths: Module-level singleton instance for convenience
"""

from pathlib import Path


class AnalysisPathConfig:
    """Centralized path configuration for analysis tools.

    This class manages all default paths used by analysis tools, including:
    - Project root detection
    - Input file paths (annotated syllables, frequencies)
    - Output directory paths (per-tool subdirectories)

    The class automatically detects the project root based on this file's location
    in the directory structure, but can also accept a custom root path for testing
    or alternative project layouts.

    Attributes
    ----------
    root : Path
        Project root directory (auto-detected or explicitly set)

    Examples
    --------
    Using default (auto-detected) root::

        >>> config = AnalysisPathConfig()
        >>> config.root
        PosixPath('/path/to/pipeworks_name_generation')
        >>> config.annotated_syllables
        PosixPath('/path/to/pipeworks_name_generation/data/annotated/syllables_annotated.json')

    Using custom root::

        >>> from pathlib import Path
        >>> config = AnalysisPathConfig(root=Path("/custom/root"))
        >>> config.annotated_syllables
        PosixPath('/custom/root/data/annotated/syllables_annotated.json')

    Getting tool-specific output directories::

        >>> config = AnalysisPathConfig()
        >>> config.analysis_output_dir("tsne")
        PosixPath('/path/to/pipeworks_name_generation/_working/analysis/tsne')
        >>> config.analysis_output_dir("feature_signatures")
        PosixPath('/path/to/pipeworks_name_generation/_working/analysis/feature_signatures')

    Notes
    -----
    This class is designed to be instantiated once per process (typically via the
    module-level `default_paths` singleton). Multiple instances are supported for
    testing purposes.

    The auto-detection assumes this file is located at:
    ``build_tools/syllable_analysis/common/paths.py``

    If the directory structure changes, the ``_detect_project_root()`` method
    must be updated accordingly.
    """

    def __init__(self, root: Path | None = None):
        """Initialize path configuration.

        Args
        ----
        root : Path, optional
            Project root path. If None (default), auto-detects based on this file's location.

        Examples
        --------
        Default auto-detection::

            >>> config = AnalysisPathConfig()

        Custom root path::

            >>> from pathlib import Path
            >>> config = AnalysisPathConfig(root=Path("/my/project"))
        """
        self.root = root if root is not None else self._detect_project_root()

    @staticmethod
    def _detect_project_root() -> Path:
        """Auto-detect project root from this file's location.

        This method calculates the project root by navigating up from this file's location.
        The calculation assumes this file is located at:
        ``build_tools/syllable_analysis/common/paths.py``

        Returns
        -------
        Path
            Absolute path to project root directory

        Notes
        -----
        Directory structure assumed::

            pipeworks_name_generation/      ← Root (4 levels up)
            └── build_tools/                ← 3 levels up
                └── syllable_analysis/      ← 2 levels up
                    └── common/             ← 1 level up
                        └── paths.py        ← This file

        The method uses ``Path(__file__).resolve()`` to get the absolute path,
        ensuring it works regardless of how the module is imported.

        Examples
        --------
        >>> root = AnalysisPathConfig._detect_project_root()
        >>> root.name
        'pipeworks_name_generation'
        >>> (root / "pyproject.toml").exists()
        True
        """
        # This file is in: build_tools/syllable_analysis/common/paths.py
        # Navigate up 4 levels to reach project root
        return Path(__file__).resolve().parent.parent.parent.parent

    @property
    def annotated_syllables(self) -> Path:
        """Default path to syllables_annotated.json.

        This is the primary input file for most analysis tools, containing
        syllables with their frequencies and feature annotations.

        Returns
        -------
        Path
            Path to ``data/annotated/syllables_annotated.json``

        Examples
        --------
        >>> config = AnalysisPathConfig()
        >>> config.annotated_syllables
        PosixPath('.../data/annotated/syllables_annotated.json')

        Use in argument parser::

            parser.add_argument(
                "--input",
                type=Path,
                default=default_paths.annotated_syllables,
                help="Path to annotated syllables"
            )

        Notes
        -----
        This file is produced by the syllable feature annotator pipeline and
        contains a JSON array of syllable records with structure::

            [
                {
                    "syllable": "ka",
                    "frequency": 187,
                    "features": {
                        "starts_with_vowel": false,
                        "contains_plosive": true,
                        ...
                    }
                },
                ...
            ]
        """
        return self.root / "data" / "annotated" / "syllables_annotated.json"

    @property
    def syllables_frequencies(self) -> Path:
        """Default path to syllables_frequencies.json.

        This file contains frequency counts for each syllable from the normalizer,
        useful for weighted analysis or filtering.

        Returns
        -------
        Path
            Path to ``data/normalized/syllables_frequencies.json``

        Examples
        --------
        >>> config = AnalysisPathConfig()
        >>> config.syllables_frequencies
        PosixPath('.../data/normalized/syllables_frequencies.json')

        Notes
        -----
        This file is produced by the syllable normalizer and contains a JSON
        object mapping syllables to their occurrence counts::

            {
                "ka": 187,
                "ra": 162,
                "mi": 145,
                ...
            }

        The frequencies represent pre-deduplication counts, capturing how often
        each canonical syllable appeared in the raw corpus.
        """
        return self.root / "data" / "normalized" / "syllables_frequencies.json"

    def analysis_output_dir(self, tool_name: str) -> Path:
        """Get output directory for a specific analysis tool.

        Each analysis tool should have its own subdirectory under ``_working/analysis/``
        to keep outputs organized and avoid naming conflicts.

        Args
        ----
        tool_name : str
            Name of the analysis tool (e.g., 'tsne', 'feature_signatures', 'random_sampler').
            This will be used as the subdirectory name.

        Returns
        -------
        Path
            Path to ``_working/analysis/{tool_name}/``

        Examples
        --------
        >>> config = AnalysisPathConfig()
        >>> config.analysis_output_dir("tsne")
        PosixPath('.../pipeworks_name_generation/_working/analysis/tsne')
        >>> config.analysis_output_dir("feature_signatures")
        PosixPath('.../pipeworks_name_generation/_working/analysis/feature_signatures')

        Use in argument parser::

            parser.add_argument(
                "--output",
                type=Path,
                default=default_paths.analysis_output_dir("tsne"),
                help="Output directory"
            )

        Notes
        -----
        The directory is not created by this method - it only returns the path.
        Use ``common.output.ensure_output_dir()`` to create the directory if needed.

        The ``_working/`` directory is typically git-ignored and used for
        build-time artifacts that don't need to be committed.
        """
        return self.root / "_working" / "analysis" / tool_name


# Module-level singleton for convenience
# Most code should use this instead of creating new instances
# This is the recommended way to access default paths in analysis tools.
# It uses auto-detected project root and provides a consistent interface
# across all tools.
#
# Examples:
#     from build_tools.syllable_analysis.common import default_paths
#
default_paths = AnalysisPathConfig()
