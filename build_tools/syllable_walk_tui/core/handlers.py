"""
Event handler routing for Syllable Walker TUI.

Contains handler dispatch logic extracted from the main App class.
The actual @on() decorated methods remain on the App, but delegate here.

This module provides pure functions that take the app instance and event data,
then route to appropriate state updates. This separation allows:
- Testing of handler logic without full App setup
- Clearer separation of concerns
- Easier maintenance and modification
"""

import random
from typing import TYPE_CHECKING

from build_tools.syllable_walk.profiles import WALK_PROFILES

if TYPE_CHECKING:
    from build_tools.syllable_walk_tui.core.app import SyllableWalkerApp
    from build_tools.syllable_walk_tui.modules.oscillator import PatchState


def switch_to_custom_mode(
    app: "SyllableWalkerApp",
    patch_name: str,
    patch: "PatchState",
) -> None:
    """
    Switch patch to custom mode when user manually adjusts profile parameters.

    This is called when the user manually changes max_flips, temperature, or
    frequency_weight - the three parameters that define walk profiles. When
    manually adjusted, the patch switches from a named profile to "custom" mode.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        patch: PatchState instance to update

    Note:
        Only switches to custom if currently using a named profile.
        If already in custom mode, does nothing.
    """
    from build_tools.syllable_walk_tui.controls import ProfileOption

    # Only switch if we're currently using a named profile (not already custom)
    if patch.current_profile == "custom":
        return

    # Update state to custom mode
    old_profile = patch.current_profile
    patch.current_profile = "custom"

    # Update ProfileOption widgets: deselect old, select custom
    try:
        # Deselect the previously selected profile
        old_option = app.query_one(f"#profile-{old_profile}-{patch_name}", ProfileOption)
        old_option.set_selected(False)

        # Select the custom option
        custom_option = app.query_one(f"#profile-custom-{patch_name}", ProfileOption)
        custom_option.set_selected(True)
    except Exception as e:  # nosec B110 - Safe widget query failure
        # Widget not found or update failed - log but don't crash
        print(f"Warning: Could not update profile selection to custom: {e}")


def handle_int_spinner_changed(
    app: "SyllableWalkerApp",
    widget_id: str,
    value: int,
) -> None:
    """
    Route IntSpinner.Changed events to appropriate state updates.

    Args:
        app: Application instance for state access
        widget_id: Widget ID from the event
        value: New value from the spinner
    """
    # Check for combiner panel widgets first (pattern: combiner-<param>-<patch>)
    if widget_id.startswith("combiner-"):
        comb = app.state.combiner_a if widget_id.endswith("-a") else app.state.combiner_b
        if "syllables" in widget_id:
            comb.syllables = value
        elif "count" in widget_id:
            comb.count = value
        return

    # Check for selector panel widgets (pattern: selector-<param>-<patch>)
    if widget_id.startswith("selector-"):
        sel = app.state.selector_a if widget_id.endswith("-a") else app.state.selector_b
        if "count" in widget_id:
            sel.count = value
        return

    # Parse widget ID to determine patch and parameter
    # Format: "<param>-<patch>" e.g., "min-length-A"
    parts = widget_id.rsplit("-", 1)
    if len(parts) != 2:
        return

    param_name, patch_name = parts
    if patch_name not in ("A", "B"):
        return  # Not a patch widget

    patch = app.state.patch_a if patch_name == "A" else app.state.patch_b

    # Update the appropriate parameter in patch state
    if param_name == "min-length":
        patch.min_length = value
    elif param_name == "max-length":
        patch.max_length = value
    elif param_name == "walk-length":
        patch.walk_length = value
    elif param_name == "max-flips":
        patch.max_flips = value
        # Max flips is a profile parameter - switch to custom mode
        # UNLESS we're updating from a profile change (prevents feedback loop)
        if app._updating_from_profile:
            app._pending_profile_updates -= 1
            if app._pending_profile_updates <= 0:
                app._updating_from_profile = False
                app._pending_profile_updates = 0
        else:
            switch_to_custom_mode(app, patch_name, patch)
    elif param_name == "neighbors":
        patch.neighbor_limit = value
    elif param_name == "walk-count":
        patch.walk_count = value


def handle_float_slider_changed(
    app: "SyllableWalkerApp",
    widget_id: str,
    value: float,
) -> None:
    """
    Route FloatSlider.Changed events to appropriate state updates.

    Args:
        app: Application instance for state access
        widget_id: Widget ID from the event
        value: New value from the slider
    """
    # Check for combiner panel widgets first (pattern: combiner-<param>-<patch>)
    if widget_id.startswith("combiner-") and "freq-weight" in widget_id:
        comb = app.state.combiner_a if widget_id.endswith("-a") else app.state.combiner_b
        comb.frequency_weight = value
        return

    # Parse widget ID to determine patch and parameter
    parts = widget_id.rsplit("-", 1)
    if len(parts) != 2:
        return

    param_name, patch_name = parts
    if patch_name not in ("A", "B"):
        return  # Not a patch widget

    patch = app.state.patch_a if patch_name == "A" else app.state.patch_b

    # Update the appropriate parameter in patch state
    if param_name == "temperature":
        patch.temperature = value
        # Temperature is a profile parameter - switch to custom mode
        if app._updating_from_profile:
            app._pending_profile_updates -= 1
            if app._pending_profile_updates <= 0:
                app._updating_from_profile = False
                app._pending_profile_updates = 0
        else:
            switch_to_custom_mode(app, patch_name, patch)
    elif param_name == "freq-weight":
        patch.frequency_weight = value
        # Frequency weight is a profile parameter - switch to custom mode
        if app._updating_from_profile:
            app._pending_profile_updates -= 1
            if app._pending_profile_updates <= 0:
                app._updating_from_profile = False
                app._pending_profile_updates = 0
        else:
            switch_to_custom_mode(app, patch_name, patch)


def handle_seed_changed(
    app: "SyllableWalkerApp",
    widget_id: str,
    value: int,
) -> None:
    """
    Route SeedInput.Changed events to appropriate state updates.

    Args:
        app: Application instance for state access
        widget_id: Widget ID from the event
        value: New seed value
    """
    # Check for combiner panel seed widget (pattern: combiner-seed-<patch>)
    if widget_id.startswith("combiner-seed"):
        comb = app.state.combiner_a if widget_id.endswith("-a") else app.state.combiner_b
        comb.seed = value
        return

    # Parse widget ID to determine patch
    # Format: "seed-<patch>" e.g., "seed-A"
    parts = widget_id.rsplit("-", 1)
    if len(parts) != 2 or parts[0] != "seed":
        return

    patch_name = parts[1]
    if patch_name not in ("A", "B"):
        return  # Not a patch widget

    patch = app.state.patch_a if patch_name == "A" else app.state.patch_b

    # Update seed in patch state with new value
    patch.seed = value
    patch.rng = random.Random(value)  # nosec B311 - Deterministic RNG for name generation


def handle_selector_mode_selected(
    app: "SyllableWalkerApp",
    widget_id: str,
    mode: str,
) -> None:
    """
    Handle selector mode radio option selection.

    Args:
        app: Application instance for state and widget access
        widget_id: Widget ID like "selector-mode-hard-a"
        mode: Mode name ("hard" or "soft")
    """
    from build_tools.syllable_walk_tui.controls import ProfileOption

    # Extract patch from widget ID (last character)
    patch_name = widget_id[-1].upper()
    selector = app.state.selector_a if patch_name == "A" else app.state.selector_b

    # Update selector state
    selector.mode = mode  # type: ignore[assignment]

    # Update radio button UI - deselect the other option
    try:
        hard_option = app.query_one(f"#selector-mode-hard-{patch_name.lower()}", ProfileOption)
        soft_option = app.query_one(f"#selector-mode-soft-{patch_name.lower()}", ProfileOption)

        if mode == "hard":
            hard_option.set_selected(True)
            soft_option.set_selected(False)
        else:
            hard_option.set_selected(False)
            soft_option.set_selected(True)
    except Exception:  # nosec B110 - Widget may not be mounted yet
        pass


def handle_selector_order_selected(
    app: "SyllableWalkerApp",
    widget_id: str,
    order: str,
) -> None:
    """
    Handle selector order radio option selection.

    Args:
        app: Application instance for state and widget access
        widget_id: Widget ID like "selector-order-random-a"
        order: Order name ("random" or "alphabetical")
    """
    from build_tools.syllable_walk_tui.controls import ProfileOption

    # Extract patch from widget ID (last character)
    patch_name = widget_id[-1].upper()
    selector = app.state.selector_a if patch_name == "A" else app.state.selector_b

    # Update selector state
    selector.order = order  # type: ignore[assignment]

    # Update radio button UI - deselect the other option
    try:
        random_option = app.query_one(f"#selector-order-random-{patch_name.lower()}", ProfileOption)
        alpha_option = app.query_one(
            f"#selector-order-alphabetical-{patch_name.lower()}", ProfileOption
        )

        if order == "random":
            random_option.set_selected(True)
            alpha_option.set_selected(False)
        else:
            random_option.set_selected(False)
            alpha_option.set_selected(True)
    except Exception:  # nosec B110 - Widget may not be mounted yet
        pass


def handle_selector_name_class_changed(
    app: "SyllableWalkerApp",
    widget_id: str,
    value: str,
) -> None:
    """
    Handle selector name class selection change.

    Args:
        app: Application instance for state access
        widget_id: Widget ID like "selector-name-class-a"
        value: Selected name class
    """
    # Extract patch from widget ID (last character)
    patch_name = widget_id[-1].upper()
    selector = app.state.selector_a if patch_name == "A" else app.state.selector_b
    selector.name_class = value


def handle_profile_selected(
    app: "SyllableWalkerApp",
    widget_id: str,
    profile_name: str,
) -> None:
    """
    Handle profile option selection (radio button click).

    Args:
        app: Application instance for state and widget access
        widget_id: Widget ID like "profile-clerical-A"
        profile_name: Name of the selected profile
    """
    from build_tools.syllable_walk_tui.controls import FloatSlider, IntSpinner, ProfileOption

    # Handle selector mode options (selector-mode-hard-a, selector-mode-soft-b)
    if widget_id.startswith("selector-mode-"):
        handle_selector_mode_selected(app, widget_id, profile_name)
        return

    # Handle selector order options (selector-order-random-a, selector-order-alphabetical-b)
    if widget_id.startswith("selector-order-"):
        handle_selector_order_selected(app, widget_id, profile_name)
        return

    parts = widget_id.rsplit("-", 1)
    if len(parts) != 2:
        return

    patch_name = parts[1]
    patch = app.state.patch_a if patch_name == "A" else app.state.patch_b

    # Deselect all other profile options for this patch
    for profile_key in ["clerical", "dialect", "goblin", "ritual", "custom"]:
        try:
            option = app.query_one(f"#profile-{profile_key}-{patch_name}", ProfileOption)
            should_select = profile_key == profile_name
            option.set_selected(should_select)
        except Exception:  # nosec B110, B112 - Widget query can fail safely
            pass

    # Update current profile in state
    patch.current_profile = profile_name

    # If "custom" selected, don't update parameters - user will set them manually
    if profile_name == "custom":
        return

    # Load profile parameters and update all controls
    profile = WALK_PROFILES.get(profile_name)
    if not profile:
        return

    # Update patch state with profile parameters
    patch.max_flips = profile.max_flips
    patch.temperature = profile.temperature
    patch.frequency_weight = profile.frequency_weight

    # CRITICAL: Set flag and counter to prevent auto-switch to custom during profile update
    app._updating_from_profile = True
    app._pending_profile_updates = 3  # Expecting 3 parameter changes

    try:
        # Update all parameter widget displays to match profile
        max_flips_widget = app.query_one(f"#max-flips-{patch_name}", IntSpinner)
        max_flips_widget.set_value(profile.max_flips)

        temperature_widget = app.query_one(f"#temperature-{patch_name}", FloatSlider)
        temperature_widget.set_value(profile.temperature)

        freq_weight_widget = app.query_one(f"#freq-weight-{patch_name}", FloatSlider)
        freq_weight_widget.set_value(profile.frequency_weight)

    except Exception as e:  # nosec B110 - Safe widget query failure
        print(f"Warning: Could not update parameter widgets for profile: {e}")
        app._updating_from_profile = False
        app._pending_profile_updates = 0
