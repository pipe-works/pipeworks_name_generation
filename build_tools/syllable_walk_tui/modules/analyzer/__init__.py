"""
Analyzer module - Analysis and visualization.

The analyzer module provides phonetic analysis, statistics, and visualization
of generated syllables and corpus data.
"""

from build_tools.syllable_walk_tui.modules.analyzer.panel import StatsPanel
from build_tools.syllable_walk_tui.modules.analyzer.screen import AnalysisScreen

__all__ = ["AnalysisScreen", "StatsPanel"]
