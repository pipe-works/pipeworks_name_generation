# Syllable Walk TUI - Phonetic Discovery Interface

A eurorack-inspired terminal interface for exploring syllable space and discovering phonetic textures.

## Purpose

This is a **build-time discovery tool** for listening to phonetic climates and documenting the conditions that produce interesting sounds. It's designed for worldbuilding - helping you discover what different regions, cultures, or factions in your world should *sound* like.

**Core Philosophy**: We patch conditions, not outputs.

> "We are not trying to produce consistent outputs.
> We are trying to produce consistent conditions."

## Installation

```bash
# Install TUI dependencies
pip install -e ".[tui]"

# Or install textual directly
pip install "textual>=0.50.0"
```

## Usage

```bash
# Launch the TUI
python -m build_tools.syllable_walk_tui
```

## The Eurorack Analogy

The TUI is modeled after a modular synthesizer rack, where each module controls a different aspect of phonetic generation:

| Module | Purpose | Phase 1 Status |
|--------|---------|----------------|
| **Oscillator** | Syllable inventory (NLTK vs Pyphen) | ✓ Functional |
| **Filter** | Feature-based filtering | ⚠ Placeholder |
| **Envelope** | Walk length and temporal shape | ✓ Functional |
| **LFO** | Stochastic bias and probability modulation | ⚠ Placeholder |
| **Attenuator** | Sampling limits and restraint | ⚠ Placeholder |
| **Patch Cable** | Corpus routing and A/B comparison | ⚠ Placeholder |
| **Output** | Live word generation display | ✓ Functional |
| **Conditions Log** | Patch management and discovery journal | ✓ Functional (basic) |

## Phase 1 (MVP) Features

The current version implements the minimum viable noodling interface:

### Functional Modules

1. **Oscillator** - Switch between NLTK and Pyphen corpora
   - NLTK: Phonetic splitting (CMUDict, onset/coda)
   - Pyphen: Typographic hyphenation (40+ languages)

2. **Envelope** - Control walk length
   - Quick select: 3, 5, 7, or random (3-10) steps

3. **Output** - Generate and display words
   - Generate 1, 10, or 100 words at a time
   - Scrollable output display
   - Clear output
   - Mark interesting conditions

4. **Conditions Log** - Record interesting moments
   - Logs current module states when you find something interesting
   - Timestamped entries
   - Shows example output that triggered the log

### Keybindings

- `g` - Generate 10 words quickly
- `c` - Clear output display
- `q` - Quit
- `?` - Show help

## How to Use This Tool

### 1. Listen, Don't Judge

Don't evaluate individual words. Instead, notice:

- What *kinds* of things appear
- Under which conditions
- With which corpora

Laughter, discomfort, or surprise are all valid signals.

### 2. Explore Conditions

When something interesting happens, don't ask:
> "How do I get more of that?"

Ask instead:
> "What conditions were present when that happened?"

Press the "→ Interesting!" button to log those conditions.

### 3. Compare Textures

Try switching between corpora (NLTK vs Pyphen) with the same envelope settings. Notice how the *texture* changes even though the structure stays the same.

### 4. Build Your Phonetic Palette

Use the conditions log to build a library of "sounds" for different parts of your world:

- Short pyphen walks might feel formal and clean
- Long NLTK walks might feel ancient and fragmented
- Different step counts create different rhythms

## Example Workflow: Discovering "The Northern Kingdom"

1. **Start with pyphen corpus** (typographic, formal)
2. **Set envelope to 3 steps** (short, clipped sounds)
3. **Generate 100 words**, notice the texture
4. **Find an interesting one?** Press "→ Interesting!" to log conditions
5. **Switch to 5 steps**, notice how the feel changes
6. **Switch to NLTK corpus**, compare the difference
7. **Review your conditions log** - you now have documented textures you can reference

## Future Phases

As you discover what you need, modules will be wired:

- **Phase 2**: Filter & Attenuator (shape output through restriction)
- **Phase 3**: LFO & Bias (modulate probability space)
- **Phase 4**: Patch Cable & Routing (mix corpora, A/B compare)

The TUI grows with the listening.

## Technical Notes

### Architecture

```
syllable_walk_tui/
├── __init__.py           # Module exports
├── __main__.py           # Entry point
├── app.py                # Main Textual App
├── walk_controller.py    # Bridge to syllable_walk backend
├── modules/              # Module widgets
│   ├── oscillator.py     # Corpus selection (functional)
│   ├── envelope.py       # Walk length (functional)
│   ├── output.py         # Display (functional)
│   ├── conditions_log.py # Logging (basic)
│   ├── filter.py         # Feature filtering (placeholder)
│   ├── lfo.py            # Bias modulation (placeholder)
│   ├── attenuator.py     # Sampling limits (placeholder)
│   └── patch_cable.py    # Routing (placeholder)
└── README.md             # This file
```

### Dependencies

- **textual** >= 0.50.0 - Terminal UI framework
- Existing syllable_walk backend (no new runtime deps)

### Integration

The TUI does **not** reimplement syllable walk logic. It:

1. Uses `build_tools.syllable_walk` for all phonetic operations
2. Translates UI controls → walk parameters
3. Displays results

## Philosophy Checkpoint

If you find yourself:

- Cherry-picking individual outputs → Stop, refocus on conditions
- Asking "how do I get exactly this word?" → Wrong question
- Building deterministic presets → You've lost the plot

The TUI succeeds when it helps you discover unexpected phonetic climates.

**No patch is permanent. No output is sacred. Only conditions matter.**

## See Also

- [Eurorack Analogy Document](_working/sfa_syllable_walker.md) - Detailed mental model
- [TUI Plan](_working/sw_tui_plan.md) - Implementation roadmap
- [Syllable Walk Backend](../syllable_walk/) - Core walking algorithm
