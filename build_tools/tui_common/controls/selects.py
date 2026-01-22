"""
Custom Select widget with j/k keybindings.

This module provides a JKSelect widget that extends Textual's Select
widget to support vim-style j/k navigation in addition to arrow keys.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.widgets import Select
from textual.widgets._select import SelectCurrent, SelectOverlay


class JKSelectOverlay(SelectOverlay):
    """Select overlay with j/k keybinding support.

    Handles j/k directly in key event processing to provide
    vim-style navigation in addition to arrow keys.
    """

    async def _on_key(self, event: events.Key) -> None:
        """Handle key events with j/k navigation support."""
        # Handle j/k directly for vim-style navigation
        if event.character == "j":
            event.stop()
            event.prevent_default()
            self.action_cursor_down()
            return
        if event.character == "k":
            event.stop()
            event.prevent_default()
            self.action_cursor_up()
            return
        # For other keys, use default type-to-search behavior
        await super()._on_key(event)


class JKSelect(Select):
    """
    Select widget with vim-style j/k navigation support.

    Extends the standard Textual Select widget to respond to j/k keys
    in addition to the standard up/down arrow keys when the dropdown
    is open.

    Usage is identical to the standard Select widget:

    .. code-block:: python

        yield JKSelect(
            [("Option 1", "opt1"), ("Option 2", "opt2")],
            value="opt1",
            id="my-select",
        )
    """

    def compose(self) -> ComposeResult:
        """Compose Select with JKSelectOverlay for j/k navigation."""
        yield SelectCurrent(self.prompt)
        yield JKSelectOverlay(type_to_search=self._type_to_search).data_bind(compact=Select.compact)
