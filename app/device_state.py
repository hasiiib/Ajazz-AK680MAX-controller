"""Pure connection-state interpretation for the target 3151:502D HID inventory.

This module only classifies already-enumerated metadata. It never opens HID
handles, sends commands, or treats an interface match as a completed Identify.
"""
from __future__ import annotations

from dataclasses import dataclass


SETTINGS_INTERFACE = 2
ANALOG_INPUT_INTERFACE = 1


@dataclass(frozen=True)
class ConnectionState:
    status: str
    message: str
    can_identify: bool
    analog_pair_candidate: bool


def _is_usable_hid_path(path: object) -> bool:
    """Accept only non-empty HIDAPI path values, never truthy placeholders."""
    return isinstance(path, (str, bytes)) and bool(path)


def evaluate_connection(inventory: list[dict[str, object]]) -> ConnectionState:
    """Classify the known control/input interface candidates conservatively."""
    if not isinstance(inventory, (list, tuple)) or any(
        not isinstance(item, dict) for item in inventory
    ):
        return ConnectionState(
            "invalid-inventory",
            "HID inventory has an unexpected structure — refusing device selection.",
            False,
            False,
        )

    controls = [
        item for item in inventory
        if type(item.get("interface_number")) is int
        and item.get("interface_number") == SETTINGS_INTERFACE
        and _is_usable_hid_path(item.get("path"))
    ]
    inputs = [
        item for item in inventory
        if type(item.get("interface_number")) is int
        and item.get("interface_number") == ANALOG_INPUT_INTERFACE
        and _is_usable_hid_path(item.get("path"))
    ]

    if not controls and not inputs:
        return ConnectionState(
            "disconnected",
            "Keyboard not detected — connect the keyboard by USB and scan again.",
            False,
            False,
        )

    if len(controls) > 1:
        return ConnectionState(
            "ambiguous",
            "Multiple control interfaces found — refusing automatic device selection.",
            False,
            False,
        )

    if len(controls) == 1:
        if len(inputs) == 1:
            parent = controls[0].get("usb_parent")
            input_parent = inputs[0].get("usb_parent")
            if isinstance(parent, str) and parent and parent == input_parent:
                return ConnectionState(
                    "paired-candidate",
                    "Control + analog interfaces paired. Read-only Identify is available; "
                    "analog streaming still requires a fresh board-2255 Identify.",
                    True,
                    True,
                )
        return ConnectionState(
            "control-only",
            "Control interface found. Read-only Identify is available; "
            "analog interface pairing is not confirmed.",
            True,
            False,
        )

    return ConnectionState(
        "input-only",
        "Analog input interface found, but no unique control interface is available.",
        False,
        False,
    )
