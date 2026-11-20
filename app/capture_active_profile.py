"""One-shot, user-confirmed active-profile GET capture for board 2255.

This isolated CLI sends exactly one read-only 0x84 GET after identifying the
same opened HID handle as board 2255. It never writes persistent settings,
retries a command, saves a capture, or prints USB paths or serial numbers.
Importing this module performs no device I/O.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
import sys
import time
from typing import Callable

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from active_profile import active_profile_get_packet  # noqa: E402
from hardware_verification import assess_capture  # noqa: E402
from protocol import (  # noqa: E402
    SETTINGS_INTERFACE,
    identify_exchange_details,
    inspect_keyboard_interfaces,
)


class CaptureError(RuntimeError):
    """A safe one-shot capture could not be completed."""


def _safe_identify_failure(exc: Exception) -> str:
    """Return useful error context while redacting device paths and serials."""
    chain = []
    current = exc
    seen = set()
    while current is not None and id(current) not in seen and len(chain) < 4:
        seen.add(id(current))
        chain.append(f"{current.__class__.__name__}: {current}")
        current = current.__cause__ or current.__context__
    message = " | ".join(chain).lower()

    if any(token in message for token in ("could not open", "permission", "access denied", "hidapi_error")):
        category = "could not open settings interface 2; check USB connection and hidraw permissions"
    elif any(token in message for token in ("could not send", "incomplete identify request")):
        category = "read-only Identify request could not be sent completely"
    elif "feature read failed" in message:
        category = "HID Feature read failed while waiting for the Identify response"
    elif any(token in message for token in ("not a valid 0x8f", "refused the request", "did not return a valid 0x8f")):
        category = "no valid 0x8F Identify response arrived within the timeout; reply framing may also be unexpected"
    elif any(token in message for token in ("could not select usb interface 2", "matching settings interfaces", "no matching vid/pid")):
        category = "could not uniquely select HID settings interface 2"
    elif "hidapi python package is missing" in message:
        category = "hidapi Python package is missing from the installed environment"
    else:
        # Preserve the useful diagnostic while removing identifying host details.
        detail = " | ".join(chain)
        detail = re.sub(r"/dev/[^\s,;:)]+", "<hid-device-path>", detail, flags=re.IGNORECASE)
        detail = re.sub(
            r"(serial(?:_?number)?|iSerialNumber|ID_SERIAL(?:_SHORT)?)\s*[:=]\s*[^\s,;]+",
            r"\1=<redacted>",
            detail,
            flags=re.IGNORECASE,
        )
        detail = re.sub(r"(?i)(?:path=|path:)[^,;]+", "path=<redacted>", detail)
        detail = " ".join(detail.split())
        if len(detail) > 240:
            detail = detail[:237] + "..."
        category = detail or f"Identify failed ({exc.__class__.__name__}; no further details)"
    return category


def capture_once(
    hid_module,
    *,
    identify: Callable = identify_exchange_details,
    sleep: Callable[[float], None] = time.sleep,
):
    """Identify the opened board, send one 0x84 GET, and return exact raw bytes.

    The 0x8F Identify and the 0x84 GET use the same uniquely selected,
    already-open interface-2 handle. This prevents a disconnect/re-enumeration
    race from moving the profile request to a different same-PID keyboard.
    Feature polling for each command is deliberately bounded; neither command
    is resent. A wrong board ID stops before the 0x84 request.
    """
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
                f"Fresh read-only Identify failed: {_safe_identify_failure(exc)}; "
                "no 0x84 request sent."
            ) from exc

        if getattr(identity, "device_id", None) != 2255:
            raise CaptureError(
                "Fresh Identify on the selected HID handle did not report board ID 2255; "
                "no 0x84 request sent."
            )

        # Preserve the reviewed transport gap between distinct Feature commands.
        sleep(0.010)
        request = bytes([0]) + active_profile_get_packet()
        sent = device.send_feature_report(request)
        if type(sent) is not int or sent != len(request):
            raise CaptureError(
                f"Incomplete 0x84 GET send ({sent!r}/{len(request)} bytes); no retry attempted."
            )
        sleep(0.010)
        raw = device.get_feature_report(0, 65)
        if not isinstance(raw, (bytes, bytearray)):
            raise CaptureError("HID Feature read did not return bytes; no retry attempted.")
        return bytes(raw), sent
    except CaptureError:
        raise
    except Exception as exc:
        raise CaptureError(
            f"One-shot 0x84 capture failed ({exc.__class__.__name__}); no retry attempted."
        ) from exc
    finally:
        if device is not None:
            try:
                device.close()
            except Exception:
                pass

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture one read-only active-profile response from board 2255."
    )
    parser.add_argument(
        "--confirm-one-read-only-0x84",
        action="store_true",
        help="explicitly authorize one 0x84 GET after a fresh Identify check",
    )
    args = parser.parse_args(argv)
    if not args.confirm_one_read_only_0x84:
        parser.error(
            "No device command sent. Re-run only when ready with "
            "--confirm-one-read-only-0x84."
        )

    try:
        import hid
    except ImportError:
        print("hidapi Python package is unavailable in this environment.", file=sys.stderr)
        return 2

    try:
        raw, sent = capture_once(hid)
    except CaptureError as exc:
        print(f"Capture stopped: {exc}", file=sys.stderr)
        return 1

    assessment = assess_capture("active-profile", raw)
    print(f"SET_FEATURE send return: {sent}/65 bytes")
    print(f"Raw response length: {len(raw)} bytes")
    print(f"Raw response HEX: {raw.hex(' ').upper()}")
    print(f"Offline assessment: {assessment.summary}")
    print("No capture file was written; no serial number or device path was recorded.")
    return 0 if assessment.accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
