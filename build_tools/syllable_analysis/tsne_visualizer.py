"""t-SNE Visualization for Feature Signature Space

This build-time analysis tool creates a t-SNE (t-distributed Stochastic Neighbor Embedding)
visualization of the feature signature space in the annotated syllable corpus.

t-SNE is a dimensionality reduction technique that projects high-dimensional feature vectors
into 2D space while preserving local structure. This visualization helps identify:
- Clustering patterns in the feature space
- Syllable similarity based on phonetic features
- Natural groupings and outliers in the corpus

The visualization uses:
- Position (x, y): t-SNE projection of 12-dimensional feature vectors
- Size: Syllable frequency (larger points = more common syllables)
- Color: Syllable frequency (warmer colors = more common syllables)

Technical Details:
- Uses Hamming distance metric (optimal for binary feature vectors)
- Perplexity=30 (balances local vs global structure)
- Fixed random seed for reproducibility (seed=42)

Output Formats:
- Static PNG: High-resolution matplotlib visualization (always generated)
- Interactive HTML: Plotly-based interactive visualization (optional, requires --interactive flag)

Usage::

    # Generate static PNG visualization with default paths
    python -m build_tools.syllable_analysis.tsne_visualizer

    # Generate both static PNG and interactive HTML
    python -m build_tools.syllable_analysis.tsne_visualizer \\
        --interactive \\
        --save-mapping

    # Custom input/output paths
    python -m build_tools.syllable_analysis.tsne_visualizer \\
        --input data/annotated/syllables_annotated.json \\
        --output _working/analysis/tsne/ \\
        --interactive

    # Adjust t-SNE parameters
    python -m build_tools.syllable_analysis.tsne_visualizer \\
        --perplexity 50 \\
        --random-state 123 \\
        --interactive

    # High-resolution output with interactive HTML
    python -m build_tools.syllable_analysis.tsne_visualizer \\
        --dpi 600 \\
        --interactive \\
        --save-mapping

Programmatic Usage:
    >>> from pathlib import Path
    >>> from build_tools.syllable_analysis import (
    ...     run_tsne_visualization,
    ...     extract_feature_matrix
    ... )
    >>> result = run_tsne_visualization(
    ...     input_path=Path("data/annotated/syllables_annotated.json"),
    ...     output_dir=Path("_working/analysis/tsne/"),
    ...     perplexity=30,
    ...     random_state=42,
    ...     interactive=True,
    ...     save_mapping=True
    ... )
    >>> print(f"Static visualization: {result['output_path']}")
    >>> print(f"Interactive HTML: {result['interactive_path']}")

Architecture:
    This module orchestrates calls to specialized modules:
    - common.data_io: Load annotated syllables
    - common.paths: Default path configuration
    - common.output: Output directory and file management
    - dimensionality.feature_matrix: Extract feature matrices
    - dimensionality.tsne_core: Apply t-SNE reduction
    - dimensionality.mapping: Create and save coordinate mappings
    - plotting.static: Create and save matplotlib PNG visualizations
    - plotting.interactive: Create and save Plotly HTML visualizations
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

# Configure matplotlib to use non-interactive backend (for headless environments like CI)
import matplotlib  # type: ignore[import-not-found]

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # type: ignore[import-not-found]

# Import from refactored modules
from build_tools.syllable_analysis.common import (
    default_paths,
    ensure_output_dir,
    load_annotated_syllables,
)
from build_tools.syllable_analysis.dimensionality import (
    ALL_FEATURES,
    apply_tsne,
    create_tsne_mapping,
    extract_feature_matrix,
    save_tsne_mapping,
)
from build_tools.syllable_analysis.plotting import (
    PLOTLY_AVAILABLE,
    create_metadata_text,
    create_tsne_scatter,
    save_static_plot,
)

# Conditional import for interactive plotting
if PLOTLY_AVAILABLE:
    from build_tools.syllable_analysis.plotting import (
        create_interactive_scatter,
        save_interactive_html,
    )


def run_tsne_visualization(
    input_path: Path,
    output_dir: Path,
    perplexity: int = 30,
    random_state: int = 42,
    dpi: int = 300,
    verbose: bool = False,
    save_mapping: bool = False,
    interactive: bool = False,
) -> dict:
    """Run the complete t-SNE visualization pipeline.

    This is the main entry point for programmatic use. It handles the full workflow:
    1. Load annotated syllables
    2. Extract feature matrix
    3. Apply t-SNE dimensionality reduction
    4. Create visualization
    5. Save outputs (PNG + optional HTML + optional mapping)

    Args:
        input_path: Path to syllables_annotated.json
        output_dir: Directory to save visualization outputs
        perplexity: t-SNE perplexity parameter (default: 30)
        random_state: Random seed for reproducibility (default: 42)
        dpi: Output resolution in dots per inch (default: 300)
        verbose: Print detailed progress information
        save_mapping: Save syllable→features→coordinates mapping as JSON (default: False)
        interactive: Generate interactive HTML visualization (requires Plotly, default: False)

    Returns:
        Dictionary containing:
            - syllable_count: Number of syllables visualized
            - feature_count: Number of features (always 12)
            - output_path: Path to saved visualization PNG
            - metadata_path: Path to saved metadata file
            - tsne_coordinates: numpy array of 2D coordinates
            - mapping_path: Path to mapping JSON (None if save_mapping=False)
            - interactive_path: Path to interactive HTML (None if interactive=False or Plotly unavailable)
            - processing_time: Total processing time in seconds

    Raises:
        FileNotFoundError: If input file does not exist
        ImportError: If required dependencies are missing
        ValueError: If input data is invalid

    Example:
        >>> from pathlib import Path
        >>> result = run_tsne_visualization(
        ...     input_path=Path("data/annotated/syllables_annotated.json"),
        ...     output_dir=Path("_working/analysis/tsne/"),
        ...     interactive=True,
        ...     save_mapping=True
        ... )
        >>> print(f"Visualized {result['syllable_count']} syllables")
        >>> print(f"Interactive HTML: {result['interactive_path']}")
    """
    start_time = time.time()

    if verbose:
        print(f"Loading data from: {input_path}")

    # Load annotated syllables using common module
    records = load_annotated_syllables(input_path)

    if verbose:
        print(f"Loaded {len(records):,} annotated syllables")
        print("Extracting feature matrix...")

    # Extract feature matrix and frequencies using dimensionality module
    feature_matrix, frequencies = extract_feature_matrix(records)

    if verbose:
        print(f"Feature matrix shape: {feature_matrix.shape}")
        print("Running t-SNE (this may take a minute)...")

    # Apply t-SNE using dimensionality module
    tsne_coords = apply_tsne(
        feature_matrix, n_components=2, perplexity=perplexity, random_state=random_state
    )

    if verbose:
        print("Creating static visualization...")

    # Create static matplotlib visualization using plotting module
    fig = create_tsne_scatter(tsne_coords, frequencies)

    # Ensure output directory exists
    ensure_output_dir(output_dir)

    if verbose:
        print("Saving visualization...")

    # Generate timestamped output paths
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    viz_path = output_dir / f"{timestamp}.tsne_visualization.png"
    meta_path = output_dir / f"{timestamp}.tsne_metadata.txt"

    # Save static plot using plotting module
    save_static_plot(fig, viz_path, dpi=dpi)

    # Generate and save metadata
    processing_time = time.time() - start_time
    metadata_text = create_metadata_text(
        output_filename=viz_path.name,
        dpi=dpi,
        perplexity=perplexity,
        random_state=random_state,
        processing_time=processing_time,
    )
    meta_path.write_text(metadata_text, encoding="utf-8")

    # Conditionally save mapping file
    mapping_path = None
    if save_mapping:
        # Create mapping using dimensionality module
        mapping = create_tsne_mapping(records, tsne_coords)
        mapping_path = output_dir / f"{timestamp}.tsne_mapping.json"
        save_tsne_mapping(mapping, mapping_path)
        if verbose:
            print(f"✓ Mapping saved to: {mapping_path}")

    # Conditionally save interactive HTML visualization
    interactive_path = None
    if interactive:
        if not PLOTLY_AVAILABLE:
            print("Warning: Plotly not available. Skipping interactive visualization.")
            print("Install with: pip install plotly")
        else:
            if verbose:
                print("Creating interactive visualization...")
            # Create interactive figure using plotting module
            interactive_fig = create_interactive_scatter(records, tsne_coords)
            interactive_path = output_dir / f"{timestamp}.tsne_interactive.html"
            save_interactive_html(interactive_fig, interactive_path, perplexity, random_state)
            if verbose:
                print(f"✓ Interactive HTML saved to: {interactive_path}")

    # Clean up matplotlib figure
    plt.close(fig)

    return {
        "syllable_count": len(records),
        "feature_count": len(ALL_FEATURES),
        "output_path": viz_path,
        "metadata_path": meta_path,
        "tsne_coordinates": tsne_coords,
        "mapping_path": mapping_path,
        "interactive_path": interactive_path,
        "processing_time": processing_time,
    }


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for t-SNE visualization.

    This function creates the ArgumentParser with all CLI options but does not
    parse arguments. This separation allows Sphinx documentation tools to
    introspect the parser and auto-generate CLI documentation.

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate t-SNE visualization of feature signature space",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Generate visualization with default settings
   python -m build_tools.syllable_analysis.tsne_visualizer

   # Custom input/output paths
   python -m build_tools.syllable_analysis.tsne_visualizer \\
     --input data/annotated/syllables_annotated.json \\
     --output _working/analysis/tsne/

   # Adjust t-SNE parameters
   python -m build_tools.syllable_analysis.tsne_visualizer \\
     --perplexity 50 \\
     --random-state 123

   # High-resolution output
   python -m build_tools.syllable_analysis.tsne_visualizer \\
     --dpi 600

   # Verbose output
   python -m build_tools.syllable_analysis.tsne_visualizer --verbose
        """,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=default_paths.annotated_syllables,
        help=f"Path to syllables_annotated.json (default: {default_paths.annotated_syllables})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=default_paths.analysis_output_dir("tsne"),
        help=f"Output directory for visualizations (default: {default_paths.analysis_output_dir('tsne')})",
    )

    parser.add_argument(
        "--perplexity",
        type=int,
        default=30,
        help="t-SNE perplexity parameter (default: 30, range: 5-50)",
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Output resolution in DPI (default: 300)",
    )

    parser.add_argument(
        "--save-mapping",
        action="store_true",
        help="Save syllable→features→coordinates mapping as JSON (default: False)",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Generate interactive HTML visualization in addition to static PNG (requires Plotly)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information",
    )

    return parser


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace with validated parameters
    """
    parser = create_argument_parser()
    return parser.parse_args()


def main() -> None:
    """Main entry point for the t-SNE visualization tool."""
    args = parse_args()

    # Validate input file exists
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        print("Have you run the syllable feature annotator yet?")
        print("Expected path: data/annotated/syllables_annotated.json")
        return

    # Validate perplexity range
    if not 5 <= args.perplexity <= 50:
        print(f"Warning: Perplexity {args.perplexity} is outside typical range (5-50)")
        print("This may produce suboptimal results.")

    # Add helpful note if --interactive used without --save-mapping
    if args.interactive and not args.save_mapping:
        print("Note: Interactive visualization works best with --save-mapping enabled")
        print("      to enable coordinate reuse and feature exploration.\n")

    if not args.verbose:
        print(f"Generating t-SNE visualization from: {args.input}")
        print(f"Output directory: {args.output}")
        print()

    try:
        # Run visualization
        result = run_tsne_visualization(
            input_path=args.input,
            output_dir=args.output,
            perplexity=args.perplexity,
            random_state=args.random_state,
            dpi=args.dpi,
            verbose=args.verbose,
            save_mapping=args.save_mapping,
            interactive=args.interactive,
        )

        # Display summary
        print(f"✓ Visualized {result['syllable_count']:,} syllables")
        print(f"✓ Projected {result['feature_count']} features into 2D space")
        print(f"✓ Visualization saved to: {result['output_path']}")
        print(f"✓ Metadata saved to: {result['metadata_path']}")
        if result["mapping_path"]:
            print(f"✓ Mapping saved to: {result['mapping_path']}")
        if result["interactive_path"]:
            print(f"✓ Interactive HTML saved to: {result['interactive_path']}")
        print(f"\nTotal processing time: {result['processing_time']:.2f} seconds")

    except ImportError as e:
        print(f"Error: {e}")
        print("\nRequired dependencies:")
        print("  pip install scikit-learn matplotlib numpy pandas")
        return

    except Exception as e:
        print(f"Error: {e}")
        return


if __name__ == "__main__":
    main()
