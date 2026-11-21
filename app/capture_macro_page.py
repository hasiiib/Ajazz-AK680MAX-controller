"""One-shot, explicitly confirmed read-only macro-page GET for board 2255.

Each invocation sends exactly one 0x8B GET after a fresh Identify on the same
opened HID handle. It does not assemble multiple pages, write macros, retry,
persist captures, or expose USB paths or serial numbers. Importing is inert.
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

from macros import macro_get_packet, parse_macro_page  # noqa: E402
from protocol import (  # noqa: E402
    SETTINGS_INTERFACE,
    feature_report_bytes,
    identify_exchange_details,
    inspect_keyboard_interfaces,
)


class CaptureError(RuntimeError):
    """A safe one-shot macro read could not be completed."""


def capture_once(
    hid_module,
    *,
    identify: Callable = identify_exchange_details,
    sleep: Callable[[float], None] = time.sleep,
    slot: int = 0,
    page: int = 0,
):
    """Identify board 2255 and read exactly one selected 0x8B macro page."""
    try:
        payload = macro_get_packet(slot, page)
    except (TypeError, ValueError) as exc:
        raise CaptureError(f"Invalid macro GET selection: {exc}") from exc

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
                f"Fresh read-only Identify failed; no 0x8B request sent "
                f"({exc.__class__.__name__})."
            ) from exc

        if getattr(identity, "device_id", None) != 2255:
            raise CaptureError(
                "Fresh Identify on the selected HID handle did not report board ID 2255; "
                "no 0x8B request sent."
            )

        sleep(0.010)
        request = bytes([0]) + payload
        try:
            sent = device.send_feature_report(request)
        except Exception as exc:
            raise CaptureError(
                f"0x8B GET send raised {exc.__class__.__name__}; no retry attempted."
            ) from exc
        if type(sent) is not int or sent != len(request):
            raise CaptureError(
                f"Incomplete 0x8B GET send ({sent!r}/{len(request)} bytes); "
                "no retry attempted."
            )

        sleep(0.010)
        try:
            raw = device.get_feature_report(0, 65)
        except Exception as exc:
            raise CaptureError(
                f"0x8B GET was sent successfully ({sent}/65 bytes), but the "
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
                f"0x8B GET was sent successfully ({sent}/65 bytes), but its "
                f"Feature response was unusable ({note}); no retry attempted."
            ) from exc
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError(
            f"One-shot 0x8B capture failed ({exc.__class__.__name__}); no retry attempted."
        ) from exc
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture one read-only macro page from board 2255."
    )
    parser.add_argument("--slot", type=int, default=0, help="macro slot 0..49 (default: 0)")
    parser.add_argument("--page", type=int, default=0, help="macro page 0..3 (default: 0)")
    parser.add_argument(
        "--confirm-one-read-only-0x8b",
        action="store_true",
        help="explicitly authorize one 0x8B GET after a fresh Identify check",
    )
    args = parser.parse_args(argv)
    try:
        macro_get_packet(args.slot, args.page)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    if not args.confirm_one_read_only_0x8b:
        parser.error(
            "No device command sent. Re-run only when ready with "
            "--confirm-one-read-only-0x8b."
        )

    try:
        import hid
    except ImportError:
        print("hidapi Python package is unavailable in this environment.", file=sys.stderr)
        return 2

    try:
        raw, sent = capture_once(hid, slot=args.slot, page=args.page)
    except CaptureError as exc:
        print(f"Capture stopped: {exc}", file=sys.stderr)
        return 1

    try:
        page_data = parse_macro_page(raw)
    except (TypeError, ValueError) as exc:
        print(f"Offline assessment: rejected macro page ({exc})", file=sys.stderr)
        print(f"Raw response length: {len(raw)} bytes")
        print(f"Raw response HEX: {raw.hex(' ').upper()}")
        return 3

    print(f"SET_FEATURE send return: {sent}/65 bytes")
    print(f"Raw response length: {len(raw)} bytes")
    print(f"Macro page payload length: {len(page_data)} bytes")
    print(f"Raw response HEX: {raw.hex(' ').upper()}")
    print(
        f"Offline assessment: accepted one raw 0x8B page; "
        f"slot {args.slot}, page {args.page}. No macro meaning inferred."
    )
    print("This invocation read one page only; no multi-page blob was assembled.")
    print("No capture file was written; no serial number or device path was recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
