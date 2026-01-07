"""Analysis tools for annotated syllables.

This subpackage provides post-annotation analysis utilities for inspecting
and understanding the annotated syllable corpus.

Subpackages
-----------
**common**: Shared utilities (data I/O, paths, output management)
**dimensionality**: Dimensionality reduction (feature matrices, t-SNE, mapping)
**plotting**: Visualization utilities (static matplotlib, interactive Plotly)

Available Tools
---------------
**random_sampler**: Random sampling utility for QA and inspection
**feature_signatures**: Feature signature analysis and distribution reporting
**tsne_visualizer**: t-SNE visualization of feature signature space

Quick Start
-----------
Random sampling::

    $ python -m build_tools.syllable_analysis.random_sampler --samples 50

Feature signature analysis::

    $ python -m build_tools.syllable_analysis.feature_signatures

t-SNE visualization::

    $ python -m build_tools.syllable_analysis.tsne_visualizer

Programmatic Usage
------------------
Using common utilities::

    >>> from build_tools.syllable_analysis import (
    ...     default_paths,
    ...     load_annotated_syllables,
    ...     ensure_output_dir,
    ... )
    >>> # Load data using default paths
    >>> records = load_annotated_syllables(default_paths.annotated_syllables)
    >>> # Prepare output directory
    >>> output_dir = ensure_output_dir(default_paths.analysis_output_dir("my_tool"))

Random sampling::

    >>> from build_tools.syllable_analysis import (
    ...     load_annotated_syllables,
    ...     sample_syllables,
    ...     save_json_output
    ... )
    >>> records = load_annotated_syllables(Path("data/annotated/syllables_annotated.json"))
    >>> samples = sample_syllables(records, 50, seed=42)
    >>> save_json_output(samples, Path("output.json"))

Feature signature analysis::

    >>> from build_tools.syllable_analysis import (
    ...     run_analysis,
    ...     extract_signature,
    ...     analyze_feature_signatures
    ... )
    >>> result = run_analysis(
    ...     input_path=Path("data/annotated/syllables_annotated.json"),
    ...     output_dir=Path("_working/analysis/"),
    ...     limit=20
    ... )

t-SNE visualization::

    >>> from build_tools.syllable_analysis import (
    ...     run_tsne_visualization,
    ...     extract_feature_matrix
    ... )
    >>> result = run_tsne_visualization(
    ...     input_path=Path("data/annotated/syllables_annotated.json"),
    ...     output_dir=Path("_working/analysis/tsne/")
    ... )
"""

# Common utilities (NEW - Phase 1 refactoring)
from build_tools.syllable_analysis.common import (
    AnalysisPathConfig,
    default_paths,
    ensure_output_dir,
    generate_output_pair,
    generate_timestamped_path,
    load_annotated_syllables,
    load_frequency_data,
    save_json_output,
)

# Dimensionality reduction utilities (NEW - Phase 4 refactoring)
# Optional - requires numpy and scikit-learn
try:
    from build_tools.syllable_analysis.dimensionality import (
        ALL_FEATURES,
        apply_tsne,
        calculate_optimal_perplexity,
        create_tsne_mapping,
        extract_feature_matrix,
        get_feature_vector,
        save_tsne_mapping,
        validate_feature_matrix,
    )

    _DIMENSIONALITY_AVAILABLE = True
except ImportError:
    # Dimensionality reduction dependencies not installed
    _DIMENSIONALITY_AVAILABLE = False

    # Provide stub implementations that raise helpful errors
    def _dimensionality_not_available(*args, **kwargs):
        raise ImportError(
            "Dimensionality reduction requires additional dependencies. "
            "Install with: pip install -e '.[build-tools]'"
        )

    ALL_FEATURES = []
    extract_feature_matrix = _dimensionality_not_available
    validate_feature_matrix = _dimensionality_not_available
    get_feature_vector = _dimensionality_not_available
    apply_tsne = _dimensionality_not_available
    calculate_optimal_perplexity = _dimensionality_not_available
    create_tsne_mapping = _dimensionality_not_available
    save_tsne_mapping = _dimensionality_not_available

# Plotting utilities (NEW - Phase 5 refactoring)
# Static plotting always available (matplotlib is required dependency)
from build_tools.syllable_analysis.plotting import (
    PLOTLY_AVAILABLE,
    create_metadata_text,
    create_tsne_scatter,
    save_static_plot,
)

# Interactive plotting (optional - requires Plotly)
if PLOTLY_AVAILABLE:
    from build_tools.syllable_analysis.plotting import (
        build_hover_text,
        create_interactive_scatter,
        create_metadata_footer,
        inject_responsive_css,
        save_interactive_html,
    )
else:
    # Provide stub implementations that raise helpful errors
    def _plotly_not_available(*args, **kwargs):
        raise ImportError(
            "Interactive plotting requires Plotly. " "Install with: pip install plotly"
        )

    build_hover_text = _plotly_not_available
    create_interactive_scatter = _plotly_not_available
    create_metadata_footer = _plotly_not_available
    inject_responsive_css = _plotly_not_available
    save_interactive_html = _plotly_not_available

# Feature signatures exports
from build_tools.syllable_analysis.feature_signatures import (
    analyze_feature_signatures,
    extract_signature,
    format_signature_report,
    run_analysis,
    save_report,
)
from build_tools.syllable_analysis.feature_signatures import (
    parse_args as parse_feature_signatures_args,
)

# Random sampler exports
# Note: load_annotated_syllables is now imported from common (above)
from build_tools.syllable_analysis.random_sampler import (
    parse_arguments as parse_random_sampler_arguments,
)
from build_tools.syllable_analysis.random_sampler import sample_syllables

# t-SNE visualizer exports (optional - requires matplotlib, numpy, scikit-learn)
try:
    from build_tools.syllable_analysis.tsne_visualizer import (
        parse_args as parse_tsne_visualizer_args,
    )
    from build_tools.syllable_analysis.tsne_visualizer import run_tsne_visualization

    _TSNE_AVAILABLE = True
except ImportError:
    # t-SNE visualizer dependencies not installed
    _TSNE_AVAILABLE = False

    # Provide stub implementations that raise helpful errors
    def _tsne_not_available(*args, **kwargs):
        raise ImportError(
            "t-SNE visualization requires additional dependencies. "
            "Install with: pip install -e '.[build-tools]'"
        )

    run_tsne_visualization = _tsne_not_available
    parse_tsne_visualizer_args = _tsne_not_available

__all__ = [
    # Common utilities (Phase 1 refactoring)
    "AnalysisPathConfig",
    "default_paths",
    "load_annotated_syllables",
    "load_frequency_data",
    "save_json_output",
    "ensure_output_dir",
    "generate_timestamped_path",
    "generate_output_pair",
    # Dimensionality reduction (Phase 4 refactoring - optional)
    "_DIMENSIONALITY_AVAILABLE",
    "ALL_FEATURES",
    "extract_feature_matrix",
    "validate_feature_matrix",
    "get_feature_vector",
    "apply_tsne",
    "calculate_optimal_perplexity",
    "create_tsne_mapping",
    "save_tsne_mapping",
    # Plotting (Phase 5 refactoring)
    "PLOTLY_AVAILABLE",
    "create_tsne_scatter",
    "save_static_plot",
    "create_metadata_text",
    "create_interactive_scatter",
    "build_hover_text",
    "save_interactive_html",
    "inject_responsive_css",
    "create_metadata_footer",
    # Random sampler
    "sample_syllables",
    "parse_random_sampler_arguments",
    # Feature signatures
    "extract_signature",
    "analyze_feature_signatures",
    "format_signature_report",
    "run_analysis",
    "save_report",
    "parse_feature_signatures_args",
    # t-SNE visualizer (optional)
    "_TSNE_AVAILABLE",
    "run_tsne_visualization",
    "parse_tsne_visualizer_args",
]
