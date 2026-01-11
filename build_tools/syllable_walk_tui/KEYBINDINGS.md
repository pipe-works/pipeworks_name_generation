# Syllable Walk TUI - Keybindings Configuration

## Overview

The Syllable Walk TUI supports configurable keybindings with sensible defaults. All keybindings can be customized by editing your config file.

## Configuration File

Keybindings are stored in: `~/.syllable_walk_tui_config.json`

## Default Keybindings

### Global Actions

| Action | Default Keys | Description |
|--------|--------------|-------------|
| Quit | `q` | Exit the application |
| Help | `?` | Show help message |
| Generate Quick | `g` | Generate 10 words quickly |
| Clear Output | `c` | Clear the output display |

### Navigation (File Browser)

The Oscillator module's file browser supports both **arrow keys** and **vim-style hjkl** navigation:

| Action | Default Keys | Description |
|--------|--------------|-------------|
| Navigate Up | `k`, `up` | Move cursor up in file browser |
| Navigate Down | `j`, `down` | Move cursor down in file browser |
| Navigate Left | `h`, `left` | Go to parent directory |
| Navigate Right | `l`, `right` | (reserved for future use) |
| Select/Load | `enter`, `l` | Navigate into directory OR load corpus file |

**Smart Selection Behavior:**

- **On directories**: Enter/l navigates into the directory
- **On corpus files** (`*_syllables_annotated.json`): Enter/l **immediately loads** the corpus (no need to click "Load Selected")
- **On other files**: Enter/l selects the file (but won't load it)

## Customizing Keybindings

### Method 1: Edit Config File Directly

1. Open `~/.syllable_walk_tui_config.json`
2. Edit the `keybindings` section:

```json
{
  "keybindings": {
    "quit": "x",
    "navigate_up": "k,up,w",
    "navigate_down": "j,down,s"
  }
}
```

3. Save and restart the TUI

### Method 2: Programmatic Configuration

```python
from build_tools.syllable_walk_tui.config import TUIConfig

config = TUIConfig()

# Change quit key to 'x'
config.set_keybinding("quit", "x")

# Add multiple keys (comma-separated)
config.set_keybinding("navigate_up", "k,up,w")
```

## Multiple Key Bindings

You can bind multiple keys to the same action using comma-separated values:

```json
"navigate_up": "k,up,w,ctrl+p"
```

All of these keys will trigger the same action.

## Available Actions

| Action Name | Purpose |
|-------------|---------|
| `quit` | Exit application |
| `help` | Show help |
| `generate_quick` | Generate 10 words |
| `clear_output` | Clear output |
| `navigate_up` | Move up in file browser |
| `navigate_down` | Move down in file browser |
| `navigate_left` | Go to parent directory |
| `navigate_right` | (reserved) |
| `select` | Select item in file browser |

## Key Format

Keys follow Textual's key naming convention:

- Letters: `a`, `b`, `c`, etc.
- Special keys: `enter`, `escape`, `space`, `tab`
- Arrow keys: `up`, `down`, `left`, `right`
- Modifiers: `ctrl+c`, `shift+tab`, `alt+x`
- Function keys: `f1`, `f2`, etc.

## Visual Feedback

When navigating into busy directories, the Oscillator shows a loading indicator to provide visual feedback that the operation is in progress.

## Tips

1. **Vim users**: The default hjkl navigation should feel natural
2. **Arrow key users**: Standard arrow keys work everywhere
3. **Hybrid users**: Mix and match! Both hjkl and arrows work simultaneously
4. **Custom workflows**: Bind multiple keys to the same action for flexibility
5. **Mouse-free workflow**: Navigate with j/k, press Enter to load - no mouse needed!
6. **Quick loading**: When you press Enter on a corpus file, it loads immediately (no extra button click required)

## Example Configurations

### Minimal (single key per action)

```json
{
  "keybindings": {
    "quit": "q",
    "help": "h",
    "generate_quick": "g",
    "clear_output": "c",
    "navigate_up": "up",
    "navigate_down": "down"
  }
}
```

### Vim-style only

```json
{
  "keybindings": {
    "quit": "q",
    "help": "question_mark",
    "generate_quick": "g",
    "clear_output": "c",
    "navigate_up": "k",
    "navigate_down": "j",
    "navigate_left": "h",
    "navigate_right": "l"
  }
}
```

### Hybrid (default)

```json
{
  "keybindings": {
    "quit": "q",
    "help": "question_mark",
    "generate_quick": "g",
    "clear_output": "c",
    "navigate_up": "k,up",
    "navigate_down": "j,down",
    "navigate_left": "h,left",
    "navigate_right": "l,right"
  }
}
```

## Troubleshooting

### Keybinding not working

1. Check the config file is valid JSON
2. Verify key names match Textual's convention
3. Restart the TUI after changes
4. Check for conflicts (one key bound to multiple actions)

### Config file corrupted

If the config file becomes corrupted, the TUI will automatically fall back to defaults. Simply delete `~/.syllable_walk_tui_config.json` to reset.

### Finding your config file

```bash
# Print path
echo ~/.syllable_walk_tui_config.json

# View contents
cat ~/.syllable_walk_tui_config.json

# Edit with your favorite editor
vim ~/.syllable_walk_tui_config.json
```
