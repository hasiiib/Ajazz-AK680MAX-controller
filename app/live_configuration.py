"""User-initiated, read-only live configuration acquisition for board 2255.

Reads only the active profile, the eight base-layer keymap pages, and the four
pages of magnetic actuation-travel column 0. Every command is preceded by a
fresh Identify on the same opened HID handle. No profile switching, setting
writes, calibration, reset, or firmware commands are present.
"""
from __future__ import annotations

import os
import time
from typing import Callable

from active_profile import active_profile_get_packet
from keymap import KEYMAP_PAGE_COUNT, keymap_get_packet
from magnetic_settings import magnetic_settings_get_packet
from protocol import (
    SETTINGS_INTERFACE,
    IdentifyError,
    feature_report_bytes,
    identify_exchange_details,
    inspect_keyboard_interfaces,
)
from read_only_snapshot import ReadOnlyConfigurationSnapshot, build_read_only_snapshot


class ConfigurationReadError(RuntimeError):
    """A bounded read-only configuration acquisition could not be completed."""


def _send_get(device, payload: bytes, label: str, sleep: Callable[[float], None]) -> bytes:
    """Send exactly one GET and read exactly one Feature response; never retry."""
    if len(payload) != 64:
        raise ConfigurationReadError(f"{label}: request payload must be 64 bytes.")
    sleep(0.010)
    request = bytes([0]) + payload
    try:
        sent = device.send_feature_report(request)
    except Exception as exc:
        raise ConfigurationReadError(
            f"{label}: Feature GET send failed ({exc.__class__.__name__}); no retry."
        ) from exc
    if type(sent) is not int or sent != len(request):
        raise ConfigurationReadError(
            f"{label}: incomplete Feature GET send ({sent!r}/65 bytes); no retry."
        )
    sleep(0.010)
    try:
        raw = device.get_feature_report(0, 65)
    except Exception as exc:
        raise ConfigurationReadError(
            f"{label}: GET was sent, but Feature response failed "
            f"({exc.__class__.__name__}); no retry."
        ) from exc
    try:
        data = feature_report_bytes(raw)
    except IdentifyError as exc:
        raise ConfigurationReadError(
            f"{label}: Feature response has an unsupported representation."
        ) from exc
    if len(data) not in (64, 65) or (len(data) == 65 and data[0] != 0):
        raise ConfigurationReadError(
            f"{label}: malformed Feature response length/Report ID ({len(data)} bytes)."
        )
    return data


def read_configuration_snapshot(
    hid_module=None,
    *,
    identify: Callable = identify_exchange_details,
    sleep: Callable[[float], None] = time.sleep,
) -> ReadOnlyConfigurationSnapshot:
    """Read a minimal, validated configuration snapshot from exact board 2255.

    The operation is explicitly user-triggered by the GUI. It opens only the
    unique interface-2 settings collection, confirms board ID 2255 on that
    exact handle, then performs 13 bounded GETs: active profile, eight base
    keymap pages, and four pages of magnetic sub-operation 0. All other
    configuration columns remain untouched and are not claimed as acquired.
    """
    if hid_module is None:
        try:
            import hid as hid_module
        except ImportError as exc:
            raise ConfigurationReadError(
                "The hidapi Python package is unavailable. Reinstall the application."
            ) from exc

    try:
        inventory = inspect_keyboard_interfaces(hid_module)
    except Exception as exc:
        raise ConfigurationReadError(
            f"Could not inspect keyboard HID interfaces ({exc.__class__.__name__})."
        ) from exc

    candidates = [
        item for item in inventory
        if item.get("interface_number") == SETTINGS_INTERFACE and item.get("path")
    ]
    if len(candidates) != 1:
        raise ConfigurationReadError(
            "Expected exactly one HID settings interface 2; refusing ambiguous selection."
        )

    device = None
    try:
        device = hid_module.device()
        try:
            device.open_path(os.fsencode(candidates[0]["path"]))
        except Exception as exc:
            raise ConfigurationReadError(
                "Could not open HID settings interface 2. Check the USB connection "
                "and the project's scoped udev permissions."
            ) from exc

        try:
            identity = identify(device, sleep=sleep)
        except Exception as exc:
            raise ConfigurationReadError(
                f"Fresh read-only Identify failed ({exc.__class__.__name__}); no configuration GET sent."
            ) from exc
        if getattr(identity, "device_id", None) != 2255:
            raise ConfigurationReadError(
                "The opened device did not identify as board 2255; no configuration GET sent."
            )

        active_reply = _send_get(
            device, active_profile_get_packet(), "Active profile 0x84", sleep
        )
        # Parse the profile before building profile-specific keymap requests.
        from active_profile import parse_active_profile_reply
        active_profile = parse_active_profile_reply(active_reply)

        keymap_replies = {}
        for page in range(KEYMAP_PAGE_COUNT):
            request = keymap_get_packet(active_profile, page, sublayer=0)
            keymap_replies[(0, page)] = _send_get(
                device, request, f"Base keymap 0x8A page {page}", sleep
            )

        magnetic_replies = {}
        for page in range(4):
            request = magnetic_settings_get_packet(subop=0, page=page)
            magnetic_replies[(0, page)] = _send_get(
                device, request, f"Actuation travel 0xE5 page {page}", sleep
            )

        return build_read_only_snapshot(
            active_reply,
            keymap_replies,
            magnetic_replies,
            sublayers=(0,),
            magnetic_subops=(0,),
        )
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass
