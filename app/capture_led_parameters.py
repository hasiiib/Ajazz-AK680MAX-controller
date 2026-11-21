"""One-shot, user-confirmed read-only LED-parameter GET for board 2255.

Sends exactly one 0x87 request after identifying board 2255 on the same opened
HID handle. No LED writes, retries, resets, or firmware commands are present.
Importing this module performs no device I/O.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time
from typing import Callable

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from lighting import led_params_get_packet, parse_led_params_reply  # noqa: E402
from protocol import (  # noqa: E402
    SETTINGS_INTERFACE,
    feature_report_bytes,
    identify_exchange_details,
    inspect_keyboard_interfaces,
)


class CaptureError(RuntimeError):
    """A safe one-shot LED capture could not be completed."""


def capture_once(
    hid_module,
    *,
    identify: Callable = identify_exchange_details,
    sleep: Callable[[float], None] = time.sleep,
):
    """Identify the opened board, send one 0x87 GET, and parse its response."""
    try:
        inventory = inspect_keyboard_interfaces(hid_module)
    except Exception as exc:
        raise CaptureError(
            f"Could not inspect HID interfaces ({exc.__class__.__name__}); no command sent."
        ) from exc

    candidates = [
        item for item in inventory
        if item.get("interface_number") == SETTINGS_INTERFACE and item.get("path")
    ]
    if len(candidates) != 1:
        raise CaptureError(
            "Expected exactly one HID interface-2 candidate; refusing ambiguous selection."
        )

    device = None
    try:
        device = hid_module.device()
        device.open_path(os.fsencode(candidates[0]["path"]))
        try:
            identity = identify(device, sleep=sleep)
        except Exception as exc:
            raise CaptureError(
                f"Fresh read-only Identify failed ({exc.__class__.__name__}); no 0x87 request sent."
            ) from exc
        if getattr(identity, "device_id", None) != 2255:
            raise CaptureError(
                "Fresh Identify on the selected HID handle did not report board ID 2255; "
                "no 0x87 request sent."
            )

        sleep(0.010)
        request = bytes([0]) + led_params_get_packet()
        try:
            sent = device.send_feature_report(request)
        except Exception as exc:
            raise CaptureError(
                f"0x87 GET send raised {exc.__class__.__name__}; no retry attempted."
            ) from exc
        if type(sent) is not int or sent != len(request):
            raise CaptureError(
                f"Incomplete 0x87 GET send ({sent!r}/{len(request)} bytes); no retry attempted."
            )

        sleep(0.010)
        try:
            raw = device.get_feature_report(0, 65)
        except Exception as exc:
            raise CaptureError(
                f"0x87 GET was sent successfully ({sent}/65 bytes), but the Feature "
                f"read raised {exc.__class__.__name__}; no retry attempted."
            ) from exc
        try:
            normalized = feature_report_bytes(raw)
            parsed = parse_led_params_reply(normalized)
        except Exception as exc:
            raise CaptureError(
                f"0x87 GET was sent successfully ({sent}/65 bytes), but its response "
                f"was invalid ({exc.__class__.__name__}); no retry attempted."
            ) from exc
        return normalized, parsed, sent
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError(
            f"One-shot 0x87 capture failed ({exc.__class__.__name__}); no retry attempted."
        ) from exc
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture one read-only LED-parameter response from board 2255."
    )
    parser.add_argument(
        "--confirm-one-read-only-0x87",
        action="store_true",
        help="explicitly authorize one 0x87 GET after a fresh Identify check",
    )
    args = parser.parse_args(argv)
    if not args.confirm_one_read_only_0x87:
        parser.error(
            "No device command sent. Re-run only when ready with --confirm-one-read-only-0x87."
        )

    try:
        import hid
    except ImportError:
        print("hidapi Python package is unavailable in this environment.", file=sys.stderr)
        return 2

    try:
        raw, led, sent = capture_once(hid)
    except CaptureError as exc:
        print(f"Capture stopped: {exc}", file=sys.stderr)
        return 1

    print(f"SET_FEATURE send return: {sent}/65 bytes")
    print(f"Raw response length: {len(raw)} bytes")
    print(f"Raw response HEX: {raw.hex(' ').upper()}")
    print(
        "Parsed LED parameters: "
        f"mode={led.mode}, speed={led.speed}, brightness={led.brightness}, "
        f"option={led.option}, flags={led.flags}, RGB={led.rgb}"
    )
    print("No LED setting was changed; no capture file, serial number, or device path was recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
