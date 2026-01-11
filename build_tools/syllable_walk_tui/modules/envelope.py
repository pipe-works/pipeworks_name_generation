"""
Envelope Module - Walk Temporal Shape

Controls the length and temporal characteristics of the syllable walk.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, Static


class EnvelopeModule(Container):
    """
    Envelope widget for walk length and shape control.

    Phase 1 (MVP):
    - Quick select buttons for walk length (3, 5, 7, random)
    - Displays current step count

    Future:
    - Attack/decay sliders for walk shape
    - Asymmetric walk patterns
    - ADSR-style controls
    """

    DEFAULT_ID = "envelope"

    def __init__(self, id: str = DEFAULT_ID):
        super().__init__(id=id)
        self.current_steps = 5

    def compose(self) -> ComposeResult:
        """Create the envelope module UI."""
        with Vertical(classes="module"):
            yield Label("ENVELOPE", classes="module-header")
            yield Label("Walk Shape", classes="module-subtitle")
            yield Static("", classes="spacer")

            # Quick select buttons for walk length
            yield Label("Steps:", classes="info-text")
            with Horizontal(classes="button-group"):
                yield Button("3", id="steps-3", classes="step-button")
                yield Button("5", id="steps-5", classes="step-button active")
                yield Button("7", id="steps-7", classes="step-button")
                yield Button("∞", id="steps-random", classes="step-button")

            yield Static("", classes="spacer")

            # Current setting display
            yield Label("Current: 5 steps", id="steps-display", classes="info-text")

            yield Static("", classes="spacer")

            # Placeholder controls (not wired yet)
            yield Label("Decay:  [not wired]", classes="info-text placeholder")
            yield Label("Attack: [not wired]", classes="info-text placeholder")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle step button clicks."""
        button_id = event.button.id

        # Update active button styling
        for btn in self.query(".step-button"):
            btn.remove_class("active")
        event.button.add_class("active")

        # Set step count based on button
        if button_id == "steps-3":
            self.current_steps = 3
        elif button_id == "steps-5":
            self.current_steps = 5
        elif button_id == "steps-7":
            self.current_steps = 7
        elif button_id == "steps-random":
            self.current_steps = -1  # -1 means random

        # Update display
        display = self.query_one("#steps-display", Label)
        if self.current_steps == -1:
            display.update("Current: random (3-10)")
        else:
            display.update(f"Current: {self.current_steps} steps")

        # Post message for app to handle
        self.post_message(self.StepsChanged(self.current_steps))

    class StepsChanged(Message):
        """Message posted when step count changes."""

        bubble = True  # Allow message to bubble up to app

        def __init__(self, steps: int) -> None:
            super().__init__()
            self.steps = steps
