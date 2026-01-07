"""Common utilities for analysis tools.

This package provides shared functionality for all analysis tools in the
syllable feature annotator, eliminating code duplication and ensuring
consistent behavior across tools.

Modules
-------
paths
    Path management and default path configuration
data_io
    Data loading and saving operations
output
    Output file and directory management

Quick Start
-----------
Import commonly used utilities::

    from build_tools.syllable_analysis.common import (
        default_paths,
        load_annotated_syllables,
        save_json_output,
        ensure_output_dir,
        generate_timestamped_path,
    )

Path management::

    # Get default paths
    input_file = default_paths.annotated_syllables
    output_dir = default_paths.analysis_output_dir("tsne")

    # Use custom root (for testing)
    from build_tools.syllable_analysis.common.paths import AnalysisPathConfig
    custom_paths = AnalysisPathConfig(root=Path("/custom/root"))

Data I/O::

    # Load annotated syllables with validation
    records = load_annotated_syllables(Path("data/annotated/syllables_annotated.json"))

    # Load frequency data
    frequencies = load_frequency_data(Path("data/normalized/syllables_frequencies.json"))

    # Save JSON output
    save_json_output({"results": [...]}, Path("output.json"))

Output management::

    # Ensure directory exists
    output_dir = ensure_output_dir(Path("_working/analysis/tsne/"))

    # Generate timestamped path
    viz_path = generate_timestamped_path(output_dir, "tsne_visualization", "png")

    # Generate paired outputs
    viz_path, meta_path = generate_output_pair(
        output_dir, "visualization", "metadata", "png", "txt"
    )

Examples
--------
Typical analysis tool workflow::

    from build_tools.syllable_analysis.common import (
        default_paths,
        load_annotated_syllables,
        ensure_output_dir,
        generate_timestamped_path,
        save_json_output,
    )

    # Load input data
    records = load_annotated_syllables(default_paths.annotated_syllables)

    # Process data
    results = analyze_data(records)

    # Prepare output
    output_dir = ensure_output_dir(default_paths.analysis_output_dir("my_tool"))
    output_path = generate_timestamped_path(output_dir, "results", "json")

    # Save results
    save_json_output(results, output_path)
"""

# Data I/O exports
from build_tools.syllable_analysis.common.data_io import (
    load_annotated_syllables,
    load_frequency_data,
    save_json_output,
)

# Output management exports
from build_tools.syllable_analysis.common.output import (
    ensure_output_dir,
    generate_output_pair,
    generate_timestamped_path,
)

# Path management exports
from build_tools.syllable_analysis.common.paths import AnalysisPathConfig, default_paths

__all__ = [
    # Path management
    "AnalysisPathConfig",
    "default_paths",
    # Data I/O
    "load_annotated_syllables",
    "load_frequency_data",
    "save_json_output",
    # Output management
    "ensure_output_dir",
    "generate_timestamped_path",
    "generate_output_pair",
]
