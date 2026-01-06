"""Analysis tools for annotated syllables.

This subpackage provides post-annotation analysis utilities for inspecting
and understanding the annotated syllable corpus.

Available Tools
---------------
**random_sampler**: Random sampling utility for QA and inspection
**feature_signatures**: Feature signature analysis and distribution reporting
**tsne_visualizer**: t-SNE visualization of feature signature space

Quick Start
-----------
Random sampling::

    $ python -m build_tools.syllable_feature_annotator.analysis.random_sampler --samples 50

Feature signature analysis::

    $ python -m build_tools.syllable_feature_annotator.analysis.feature_signatures

t-SNE visualization::

    $ python -m build_tools.syllable_feature_annotator.analysis.tsne_visualizer

Programmatic Usage
------------------
Random sampling::

    >>> from build_tools.syllable_feature_annotator.analysis import (
    ...     load_annotated_syllables,
    ...     sample_syllables,
    ...     save_samples
    ... )
    >>> records = load_annotated_syllables(Path("data/annotated/syllables_annotated.json"))
    >>> samples = sample_syllables(records, 50, seed=42)
    >>> save_samples(samples, Path("output.json"))

Feature signature analysis::

    >>> from build_tools.syllable_feature_annotator.analysis import (
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

    >>> from build_tools.syllable_feature_annotator.analysis import (
    ...     run_tsne_visualization,
    ...     extract_feature_matrix
    ... )
    >>> result = run_tsne_visualization(
    ...     input_path=Path("data/annotated/syllables_annotated.json"),
    ...     output_dir=Path("_working/analysis/tsne/")
    ... )
"""

# Feature signatures exports
from build_tools.syllable_feature_annotator.analysis.feature_signatures import (
    analyze_feature_signatures,
    extract_signature,
    format_signature_report,
    run_analysis,
    save_report,
)
from build_tools.syllable_feature_annotator.analysis.feature_signatures import (
    parse_args as parse_feature_signatures_args,
)

# Random sampler exports
from build_tools.syllable_feature_annotator.analysis.random_sampler import (
    load_annotated_syllables,
    sample_syllables,
    save_samples,
)
from build_tools.syllable_feature_annotator.analysis.random_sampler import (
    parse_arguments as parse_random_sampler_arguments,
)

# t-SNE visualizer exports (optional - requires matplotlib, numpy, pandas, scikit-learn)
try:
    from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import (
        create_tsne_visualization,
        extract_feature_matrix,
        load_annotated_data,
        run_tsne_visualization,
        save_visualization,
    )
    from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import (
        parse_args as parse_tsne_visualizer_args,
    )

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

    create_tsne_visualization = _tsne_not_available
    extract_feature_matrix = _tsne_not_available
    load_annotated_data = _tsne_not_available
    run_tsne_visualization = _tsne_not_available
    save_visualization = _tsne_not_available
    parse_tsne_visualizer_args = _tsne_not_available

__all__ = [
    # Random sampler
    "load_annotated_syllables",
    "sample_syllables",
    "save_samples",
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
    "load_annotated_data",
    "extract_feature_matrix",
    "create_tsne_visualization",
    "save_visualization",
    "run_tsne_visualization",
    "parse_tsne_visualizer_args",
]
