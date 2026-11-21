"""One-shot, user-confirmed keymap page-0 GET capture for board 2255.

This isolated CLI sends exactly one read-only 0x8A GET after identifying the
same opened HID handle as board 2255. The initial probe fixes profile 0,
page 0, and wire byte 4 to zero; it does not resolve the upstream byte-4
host-layer/sub-layer naming ambiguity. It never writes persistent settings,
retries a command, saves a capture, or prints USB paths or serial numbers.
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

from hardware_verification import assess_capture  # noqa: E402
from keymap import keymap_get_packet  # noqa: E402
from protocol import (  # noqa: E402
    SETTINGS_INTERFACE,
    feature_report_bytes,
    identify_exchange_details,
    inspect_keyboard_interfaces,
)


class CaptureError(RuntimeError):
    """A safe one-shot capture could not be completed."""


def capture_once(
    hid_module,
    *,
    identify: Callable = identify_exchange_details,
    sleep: Callable[[float], None] = time.sleep,
    profile: int = 0,
    page: int = 0,
    wire_byte4: int = 0,
):
    """Identify the opened board, send one selected 0x8A GET, return raw bytes."""
    # Validate the request before opening the device or sending anything.
    try:
        packet_payload = keymap_get_packet(
            profile=profile, page=page, sublayer=wire_byte4
        )
    except (TypeError, ValueError) as exc:
        raise CaptureError(f"Invalid keymap GET selection: {exc}") from exc
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
                f"Fresh read-only Identify failed; no 0x8A request sent "
                f"({exc.__class__.__name__})."
            ) from exc

        if getattr(identity, "device_id", None) != 2255:
            raise CaptureError(
                "Fresh Identify on the selected HID handle did not report board ID 2255; "
                "no 0x8A request sent."
            )

        # Byte 4 is passed through unchanged. Its host-layer/sub-layer meaning
        # remains unresolved for the target board.
        sleep(0.010)
        request = bytes([0]) + packet_payload
        try:
            sent = device.send_feature_report(request)
        except Exception as exc:
            raise CaptureError(
                f"0x8A GET send raised {exc.__class__.__name__}; no retry attempted."
            ) from exc
        if type(sent) is not int or sent != len(request):
            raise CaptureError(
                f"Incomplete 0x8A GET send ({sent!r}/{len(request)} bytes); "
                "no retry attempted."
            )

        sleep(0.010)
        try:
            raw = device.get_feature_report(0, 65)
        except Exception as exc:
            raise CaptureError(
                f"0x8A GET was sent successfully ({sent}/65 bytes), but the "
                f"Feature read raised {exc.__class__.__name__}; no retry attempted."
            ) from exc
        try:
            return feature_report_bytes(raw), sent
        except Exception as exc:
            if isinstance(raw, (bytes, bytearray, list, tuple)):
                note = f"type={type(raw).__name__}, length={len(raw)}"
            else:
                note = f"type={type(raw).__name__}, unsupported return type"
            raise CaptureError(
                f"0x8A GET was sent successfully ({sent}/65 bytes), but its "
                f"Feature response was unusable ({note}); no retry attempted."
            ) from exc
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError(
            f"One-shot 0x8A capture failed ({exc.__class__.__name__}); no retry attempted."
        ) from exc
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture one selected read-only keymap page from board 2255."
    )
    parser.add_argument("--profile", type=int, default=0, help="profile index 0..3 (default: 0)")
    parser.add_argument("--page", type=int, default=0, help="page index 0..7 (default: 0)")
    parser.add_argument(
        "--byte4", type=int, default=0,
        help="raw request byte 4, accepted values 0..3; host-layer/sub-layer meaning unresolved",
    )
    parser.add_argument(
        "--confirm-one-read-only-0x8a",
        action="store_true",
        help="explicitly authorize one 0x8A GET after a fresh Identify check",
    )
    args = parser.parse_args(argv)
    try:
        keymap_get_packet(args.profile, args.page, args.byte4)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    if not args.confirm_one_read_only_0x8a:
        parser.error(
            "No device command sent. Re-run only when ready with "
            "--confirm-one-read-only-0x8a."
        )

    try:
        import hid
    except ImportError:
        print("hidapi Python package is unavailable in this environment.", file=sys.stderr)
        return 2

    try:
        raw, sent = capture_once(
            hid, profile=args.profile, page=args.page, wire_byte4=args.byte4
        )
    except CaptureError as exc:
        print(f"Capture stopped: {exc}", file=sys.stderr)
        return 1

    assessment = assess_capture(
        "keymap", raw, profile=args.profile, sublayer=args.byte4, page=args.page
    )
    print(f"SET_FEATURE send return: {sent}/65 bytes")
    print(f"Raw response length: {len(raw)} bytes")
    print(f"Raw response HEX: {raw.hex(' ').upper()}")
    print(f"Offline assessment: {assessment.summary}")
    print(
        f"Probe metadata: profile {args.profile}, page {args.page}, "
        f"wire byte 4 = {args.byte4} (host-layer/sub-layer meaning unresolved)."
    )
    print("No capture file was written; no serial number or device path was recorded.")
    return 0 if assessment.accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
