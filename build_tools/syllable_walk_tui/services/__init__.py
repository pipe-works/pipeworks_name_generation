"""
Backend services for Syllable Walker TUI.

This module contains service layers for corpus loading, configuration management,
terrain weights, generation, and other backend operations.
"""

from build_tools.syllable_walk_tui.services.combiner_runner import CombinerResult, run_combiner
from build_tools.syllable_walk_tui.services.config import (
    KeybindingConfig,
    load_config_file,
    load_keybindings,
)
from build_tools.syllable_walk_tui.services.corpus import (
    get_corpus_info,
    load_annotated_data,
    load_corpus_data,
    validate_corpus_directory,
)
from build_tools.syllable_walk_tui.services.exporter import (
    export_names_to_txt,
    export_sample_json,
)
from build_tools.syllable_walk_tui.services.generation import WalkResult, generate_walks_for_patch
from build_tools.syllable_walk_tui.services.packager import (
    PackageOptions,
    PackageResult,
    build_package_metadata,
    collect_included_files,
    package_selections,
    scan_selections,
    write_metadata_json,
)
from build_tools.syllable_walk_tui.services.selector_runner import SelectorResult, run_selector
from build_tools.syllable_walk_tui.services.terrain_weights import (
    DEFAULT_TERRAIN_WEIGHTS,
    AxisWeights,
    TerrainWeights,
    create_default_craft_weights,
    create_default_shape_weights,
    create_default_space_weights,
    create_default_terrain_weights,
    load_terrain_weights,
)

__all__ = [
    # Config
    "KeybindingConfig",
    "load_config_file",
    "load_keybindings",
    # Corpus
    "validate_corpus_directory",
    "get_corpus_info",
    "load_corpus_data",
    "load_annotated_data",
    # Generation
    "WalkResult",
    "generate_walks_for_patch",
    # Combiner
    "CombinerResult",
    "run_combiner",
    # Selector
    "SelectorResult",
    "run_selector",
    # Export
    "export_names_to_txt",
    "export_sample_json",
    # Packaging
    "PackageOptions",
    "PackageResult",
    "build_package_metadata",
    "collect_included_files",
    "package_selections",
    "scan_selections",
    "write_metadata_json",
    # Terrain Weights
    "AxisWeights",
    "TerrainWeights",
    "create_default_shape_weights",
    "create_default_craft_weights",
    "create_default_space_weights",
    "create_default_terrain_weights",
    "load_terrain_weights",
    "DEFAULT_TERRAIN_WEIGHTS",
]
