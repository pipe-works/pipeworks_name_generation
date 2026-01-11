"""
TUI Modules - Eurorack-Style Widgets

Each module corresponds to a phonetic processing concept:
- Oscillator: Syllable inventory (corpus selection)
- Filter: Feature-based filtering
- Envelope: Walk temporal shape
- LFO: Stochastic bias and modulation
- Attenuator: Sampling limits and restraint
- PatchCable: Corpus routing
- Output: Live word generation display
- ConditionsLog: Patch management and discovery journal
- CorpusMeta: Source provenance metadata display
- WalkDetails: Phonetic path trace visualization
- TabbedContent: Multi-view tabbed display for right panel
"""

from build_tools.syllable_walk_tui.modules.attenuator import AttenuatorModule
from build_tools.syllable_walk_tui.modules.conditions_log import ConditionsLogModule
from build_tools.syllable_walk_tui.modules.corpus_meta import CorpusMetaModule
from build_tools.syllable_walk_tui.modules.envelope import EnvelopeModule
from build_tools.syllable_walk_tui.modules.filter import FilterModule
from build_tools.syllable_walk_tui.modules.lfo import LFOModule
from build_tools.syllable_walk_tui.modules.oscillator import OscillatorModule
from build_tools.syllable_walk_tui.modules.output import OutputModule
from build_tools.syllable_walk_tui.modules.patch_cable import PatchCableModule
from build_tools.syllable_walk_tui.modules.tabbed_content import TabbedContentModule
from build_tools.syllable_walk_tui.modules.walk_details import WalkDetailsModule

__all__ = [
    "OscillatorModule",
    "FilterModule",
    "EnvelopeModule",
    "LFOModule",
    "AttenuatorModule",
    "PatchCableModule",
    "OutputModule",
    "ConditionsLogModule",
    "CorpusMetaModule",
    "WalkDetailsModule",
    "TabbedContentModule",
]
