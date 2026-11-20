"""Conservative, read-only HID identification for the AJAZZ AK680 MAX.

Only the documented 0x8F Identify GET is sent. No configuration opcodes exist
in this module.
"""
from __future__ import annotations

import time

VENDOR_ID = 0x3151
PRODUCT_ID = 0x502D
SETTINGS_INTERFACE = 2
USAGE_PAGE = 0xFFFF
USAGE = 0x0002
REPORT_LENGTH = 64
IDENTIFY_OPCODE = 0x8F


class IdentifyError(RuntimeError):
    """A safe identification attempt could not be completed."""


def identify_packet() -> bytes:
    """Build the documented 64-byte 0x8F GET packet with Bit7 checksum."""
    packet = bytearray(REPORT_LENGTH)
    packet[0] = IDENTIFY_OPCODE
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    return bytes(packet)


def parse_device_id(reply: bytes | bytearray) -> int | None:
    """Decode [0x8F, device_id:u32 little-endian, ...]; reject refusal echo."""
    data = bytes(reply)
    request = identify_packet()
    refused = bytearray(request)
    refused[3] = 0xFF
    if data[:REPORT_LENGTH] == bytes(refused):
        return None
    if len(data) < 5 or data[0] != IDENTIFY_OPCODE:
        return None
    device_id = int.from_bytes(data[1:5], "little")
    return device_id if device_id > 0 else None


def _feature_payload(raw: bytes | bytearray) -> bytes:
    """Normalize hidapi's report-ID-prefixed and no-prefix return forms."""
    data = bytes(raw)
    if len(data) >= REPORT_LENGTH + 1 and data[0] == 0:
        return data[1:REPORT_LENGTH + 1]
    if len(data) >= REPORT_LENGTH:
        return data[:REPORT_LENGTH]
    raise IdentifyError(
        f"Keyboard returned a short Feature report ({len(data)} bytes; "
        f"expected at least {REPORT_LENGTH})."
    )


def identify_keyboard() -> int:
    """Identify the exact board through its verified vendor Feature collection.

    This performs a GET-only handshake. The device must be connected by USB,
    and the current user must have permission to open the matching HID node.
    """
    try:
        import hid
    except ImportError as exc:
        raise IdentifyError(
            "The hidapi Python package is missing. Reinstall the application."
        ) from exc

    try:
        devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    except Exception as exc:
        raise IdentifyError(f"Could not enumerate HID devices: {exc}") from exc

    candidates = [
        item for item in devices
        if item.get("interface_number") == SETTINGS_INTERFACE
        and item.get("usage_page") == USAGE_PAGE
        and item.get("usage") == USAGE
        and item.get("path")
    ]
    if not candidates:
        raise IdentifyError(
            "The expected settings interface was not found. Check that the "
            "keyboard is connected by USB and that interface 2 exposes "
            "Usage Page 0xFFFF / Usage 0x0002."
        )
    if len(candidates) != 1:
        raise IdentifyError(
            f"Found {len(candidates)} matching settings interfaces; refusing "
            "an ambiguous device selection."
        )

    device = hid.device()
    try:
        try:
            device.open_path(candidates[0]["path"])
        except Exception as exc:
            raise IdentifyError(
                "The keyboard was found, but this user cannot open its HID "
                "settings interface. On Ubuntu this is usually a udev "
                "permission issue. Do not run the whole GUI with sudo; "
                "we will add a narrowly scoped rule after this interface "
                "check is complete."
            ) from exc

        request = identify_packet()
        # Match the documented hidapi convention: leading zero is the
        # unnumbered report ID; the following 64 bytes are the Feature data.
        wire_request = bytes([0]) + request
        last_error = "The keyboard did not answer the Identify request."
        for attempt in range(3):
            try:
                sent = device.send_feature_report(wire_request)
                if sent is not None and sent <= 0:
                    raise IdentifyError("hidapi did not send the Feature report.")
                time.sleep(0.010 * (attempt + 1))
                raw = device.get_feature_report(0, REPORT_LENGTH + 1)
                reply = _feature_payload(raw)
                device_id = parse_device_id(reply)
                if device_id is not None:
                    return device_id
                last_error = (
                    "The Feature report arrived, but it was not a valid "
                    "0x8F Identify reply."
                )
            except IdentifyError:
                raise
            except Exception as exc:
                last_error = f"HID Identify transaction failed: {exc}"
        raise IdentifyError(last_error)
    finally:
        try:
            device.close()
        except Exception:
            pass
