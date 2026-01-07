# Analysis Tools

Post-annotation analysis utilities for exploring and visualizing syllable feature data. These
tools help understand feature distributions, patterns, and relationships in the annotated
syllable corpus.

## Modular Architecture

The analysis tools follow a clean modular architecture with shared utilities:

```text
build_tools/syllable_feature_annotator/analysis/
├── common/                      # Shared utilities
│   ├── paths.py                 # Path management and defaults
│   ├── data_io.py               # Data loading/saving functions
│   └── output.py                # Output file management
├── dimensionality/              # Dimensionality reduction
│   ├── feature_matrix.py        # Feature extraction and transformation
│   ├── tsne_core.py             # t-SNE dimensionality reduction
│   └── mapping.py               # Coordinate mapping utilities
├── plotting/                    # Visualization modules
│   ├── styles.py                # Shared styling constants
│   ├── static.py                # Matplotlib static visualizations
│   └── interactive.py           # Plotly interactive visualizations
├── random_sampler.py            # Random sampling utility for QA
├── feature_signatures.py        # Feature combination frequency analysis
└── tsne_visualizer.py           # t-SNE visualization CLI
```

## Key Features

- **Modular Design**: Shared utilities eliminate code duplication
- **Reusable Components**: Dimensionality reduction and plotting modules work independently
- **High Test Coverage**: 100% coverage on core modules (common, dimensionality feature_matrix/mapping, plotting static/styles)
- **Optional Dependencies**: Matplotlib, numpy, plotly are optional (gracefully handled)
- **Deterministic**: All tools produce reproducible results with same inputs

## Common Utilities

Shared functionality used across all analysis tools:

```python
from build_tools.syllable_analysis.common import (
    default_paths,              # Centralized path configuration
    load_annotated_syllables,   # Load syllables_annotated.json with validation
    load_frequency_data,         # Load syllables_frequencies.json
    save_json_output,            # Save JSON with consistent formatting
    ensure_output_dir,           # Create output directories
    generate_timestamped_path,   # Generate timestamped file paths
)

# Access default paths
input_path = default_paths.annotated_syllables
output_dir = default_paths.analysis_output_dir("tsne")

# Load annotated data
records = load_annotated_syllables(input_path)

# Save results
save_json_output(results, output_path)
```

## Dimensionality Reduction

Extract feature matrices and apply dimensionality reduction algorithms:

```python
from build_tools.syllable_analysis.dimensionality import (
    ALL_FEATURES,              # 12 canonical feature names
    extract_feature_matrix,    # Convert records to numpy matrix
    apply_tsne,                # Apply t-SNE dimensionality reduction
    create_tsne_mapping,       # Map coordinates back to syllables
    save_tsne_mapping,         # Save mapping as JSON
)

# Extract feature matrix
feature_matrix, frequencies = extract_feature_matrix(records)

# Apply t-SNE
tsne_coords = apply_tsne(feature_matrix, perplexity=30, random_state=42)

# Create mapping
mapping = create_tsne_mapping(records, tsne_coords)
save_tsne_mapping(mapping, output_path)
```

## Visualization

Create static (matplotlib) and interactive (Plotly) visualizations:

```python
from build_tools.syllable_analysis.plotting import (
    # Static plotting (matplotlib)
    create_tsne_scatter,       # Create scatter plot
    save_static_plot,          # Save as PNG
    create_metadata_text,      # Generate metadata

    # Interactive plotting (Plotly) - optional
    PLOTLY_AVAILABLE,          # Check if Plotly installed
    create_interactive_scatter,  # Create interactive plot
    save_interactive_html,       # Save as HTML

    # Styling constants
    DEFAULT_COLORMAP,          # "viridis"
    DEFAULT_FIGURE_SIZE,       # (14, 10)
    DEFAULT_DPI,               # 300
)

# Static visualization
fig = create_tsne_scatter(tsne_coords, frequencies)
save_static_plot(fig, Path("output.png"), dpi=300)

# Interactive visualization (if Plotly available)
if PLOTLY_AVAILABLE:
    fig = create_interactive_scatter(records, tsne_coords)
    save_interactive_html(fig, Path("output.html"), perplexity=30, random_state=42)
```

## Available Analysis Tools

### 1. Random Sampler

Random sampling of annotated syllables for QA:

```bash
python -m build_tools.syllable_analysis.random_sampler \
  --samples 10 \
  --seed 42 \
  --output _working/analysis/random_sampler/
```

**Features:**

- Deterministic sampling with seed support
- Quick corpus exploration
- QA for feature detection accuracy

### 2. Feature Signatures

Analyze frequency of feature combinations:

```bash
python -m build_tools.syllable_analysis.feature_signatures \
  --input data/annotated/syllables_annotated.json \
  --output _working/analysis/feature_signatures/ \
  --limit 20
```

**Features:**

- Identify common and rare feature patterns
- Generate detailed reports with statistics
- Understand feature co-occurrence

### 3. t-SNE Visualizer

Dimensionality reduction visualization of feature space:

```bash
python -m build_tools.syllable_analysis.tsne_visualizer \
  --input data/annotated/syllables_annotated.json \
  --output _working/analysis/tsne/ \
  --perplexity 30 \
  --dpi 300 \
  --interactive \
  --save-mapping
```

**Features:**

- Generate static (PNG) and interactive (HTML) plots
- Explore feature clustering and relationships
- Visualize high-dimensional feature space in 2D

## Design Principles

1. **Modularity**: Shared utilities in `common/`, reusable ML in `dimensionality/`, independent plotting in `plotting/`
2. **Separation of Concerns**: Data loading, ML algorithms, and visualization are independent
3. **Optional Dependencies**: Tools work without matplotlib/numpy/plotly (graceful degradation)
4. **Deterministic**: Same inputs always produce same outputs (reproducible analysis)
5. **Testability**: Pure functions with clear contracts (100% coverage on core modules)
6. **Extensibility**: Easy to add new analysis tools using shared utilities

## Testing

```bash
# Run all analysis tests (218 tests)
pytest tests/test_analysis_common.py tests/test_dimensionality.py tests/test_plotting.py \
       tests/test_random_sampler.py tests/test_feature_signatures.py -v

# Test coverage:
# - Common modules: 66 tests (100% coverage on paths, data_io, output)
# - Dimensionality: 43 tests (87-100% coverage on feature_matrix, tsne_core, mapping)
# - Plotting: 40 tests (91-100% coverage on static, interactive, styles)
# - Random sampler: 35 tests (85% coverage)
# - Feature signatures: 34 tests (77% coverage)
```

## Important Notes

- These are **build-time analysis tools** (not used during runtime name generation)
- All tools accept custom paths (defaults use `common.default_paths`)
- Output files are timestamped to prevent overwriting
- Tools work independently but share common infrastructure
- Matplotlib/numpy/plotly are optional dependencies (tools check availability)
