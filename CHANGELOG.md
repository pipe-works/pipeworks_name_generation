# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-08

This release represents a significant expansion of the build tools infrastructure while maintaining the Phase 1
proof-of-concept generator. The focus has been on creating a robust corpus linguistics pipeline for syllable
extraction, normalization, feature annotation, and phonetic space analysis.

### Features

#### Build Tools Suite

- **Syllable Extractor**: Dictionary-based hyphenation using pyphen (LibreOffice dictionaries)
  - Support for 40+ languages
  - Automatic language detection with langdetect
  - Batch processing capabilities
  - Configurable syllable length constraints
  - Multi-language output file support

- **Syllable Normalizer**: 3-step normalization pipeline
  - Character decomposition and normalization
  - Phoneme-based normalization
  - Length and structure filtering

- **Syllable Feature Annotator**: Phonetic feature detection system
  - 12 phonetic feature detectors (consonant clusters, vowel patterns, etc.)
  - Binary feature signatures for each syllable
  - JSON output with metadata

- **Syllable Walker**: Phonetic space exploration tool
  - Navigate through similar syllables based on feature signatures
  - Step-by-step phonetic transformations
  - Interactive exploration of syllable relationships

#### Analysis Tools

- **Feature Signature Analysis**: Statistical analysis of annotated syllables
  - Feature frequency distributions
  - Correlation analysis
  - Comprehensive reporting

- **t-SNE Visualization**: Dimensionality reduction and visualization
  - Interactive HTML visualizations with plotly
  - Static matplotlib plots
  - Parameter logging and syllable mapping
  - Responsive design with min-width constraints
  - Optional dependencies for CI compatibility

- **Random Sampler**: Stratified random sampling of annotated syllables

### Documentation

- **Automated CLI Documentation**: Integration with sphinx-argparse for auto-generated command-line reference
- **Modular Documentation Structure**: Reorganized CLAUDE.md into topic-specific files in `claude/` directory
  - Architecture and Design
  - Development Guide
  - CI/CD Pipeline
  - Build Tools Documentation
- **Documentation Content Rules**: Single source of truth policy for docstrings vs RST files
- **Pre-commit Hook**: Reminders for CLI documentation synchronization

### Internal Changes

- **Analysis Tools Reorganization**: Moved to top-level `build_tools/syllable_analysis/` structure
- **Syllable Extractor Modularization**: Extracted into proper package structure
- **CI Improvements**: Optional dependencies handling for matplotlib and dimensionality modules
- **Test Coverage Improvements**: Expanded coverage across build tools

### Fixes

- Platform compatibility fixes (Windows permission handling, matplotlib backend configuration)
- Sphinx documentation warnings resolution
- ReadTheDocs build improvements (optional pyphen import, dependency handling)
- Interactive visualization improvements (colorbar overlap fix, responsive design)
- Test suite cleanup and CI stability improvements

## [0.1.0] - Initial Release

Initial proof-of-concept release with Phase 1 generator:

- Basic `NameGenerator` class with deterministic seeding
- "simple" pattern with hardcoded syllables
- Zero runtime dependencies
- Comprehensive CI/CD infrastructure (GitHub Actions, pre-commit hooks)
- Sphinx documentation with ReadTheDocs integration
- GPL-3.0-or-later license
