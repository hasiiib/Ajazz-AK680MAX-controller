"""Conservative, read-only HID identification for the AJAZZ AK680 MAX.

Only the documented 0x8F Identify GET is sent. No configuration opcodes exist
in this module.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass

VENDOR_ID = 0x3151
PRODUCT_ID = 0x502D
SETTINGS_INTERFACE = 2
ANALOG_INPUT_INTERFACE = 1
USAGE_PAGE = 0xFFFF
USAGE = 0x0002
REPORT_LENGTH = 64
IDENTIFY_OPCODE = 0x8F
EXCHANGE_GAP_SECONDS = 0.010
IDENTIFY_TIMEOUT_SECONDS = 0.100
ANALOG_REPORT_ID = 0x05
ANALOG_STREAM_OPCODE = 0x1B
ANALOG_REPORT_LENGTH = 32


class IdentifyError(RuntimeError):
    """A safe identification attempt could not be completed."""


@dataclass(frozen=True)
class AnalogSample:
    """One validated key-travel sample from the vendor input report."""

    slot: int
    raw_travel: int


@dataclass(frozen=True)
class IdentifyResult:
    """Validated identity and revision metadata from one Identify reply."""

    device_id: int
    firmware_revision: str | None
    raw_reply: bytes


def parse_analog_report(report: bytes | bytearray) -> AnalogSample | None:
    """Parse a 32-byte report-ID-5 analog sample; never performs I/O."""
    if not isinstance(report, (bytes, bytearray)):
        return None
    data = bytes(report)
    if len(data) != ANALOG_REPORT_LENGTH:
        return None
    if data[0] != ANALOG_REPORT_ID or data[1] != ANALOG_STREAM_OPCODE:
        return None
    slot = data[4]
    if slot > 127:
        return None
    raw_travel = int.from_bytes(data[2:4], "little")
    return AnalogSample(slot=slot, raw_travel=raw_travel)


def parse_gen2_firmware_revision(reply: bytes | bytearray) -> str | None:
    """Decode gen2 revision digits from one normalized 64-byte Identify reply.

    The protocol documents (reply[8] << 8) | reply[7], with each
    hexadecimal nibble representing one decimal version digit.
    """

    if not isinstance(reply, (bytes, bytearray)):
        return None
    data = bytes(reply)
    if len(data) != REPORT_LENGTH or data[0] != IDENTIFY_OPCODE:
        return None
    encoded = (data[8] << 8) | data[7]
    digits = f"{encoded:04X}"
    if encoded == 0 or any(char not in "0123456789" for char in digits):
        return None
    return str(int(digits))


def identify_packet() -> bytes:
    """Build the documented 64-byte 0x8F GET payload with Bit7 checksum."""
    packet = bytearray(REPORT_LENGTH)
    packet[0] = IDENTIFY_OPCODE
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    return bytes(packet)


def parse_device_id(reply: bytes | bytearray) -> int | None:
    """Decode the board ID from one normalized 64-byte Identify reply."""
    if not isinstance(reply, (bytes, bytearray)):
        return None
    data = bytes(reply)
    request = identify_packet()
    refused = bytearray(request)
    refused[3] = 0xFF
    if len(data) != REPORT_LENGTH or data[0] != IDENTIFY_OPCODE:
        return None
    if data == bytes(refused):
        return None
    device_id = int.from_bytes(data[1:5], "little")
    return device_id if device_id > 0 else None


def _feature_payload(raw: bytes | bytearray) -> bytes:
    """Normalize hidapi's report-ID-prefixed and no-prefix return forms."""
    if not isinstance(raw, (bytes, bytearray)):
        raise IdentifyError("HID Feature report must be bytes or bytearray.")
    data = bytes(raw)
    if len(data) == REPORT_LENGTH + 1 and data[0] == 0:
        return data[1:]
    if len(data) == REPORT_LENGTH:
        return data
    raise IdentifyError(
        f"Keyboard returned a malformed Feature report ({len(data)} bytes); "
        f"expected exactly {REPORT_LENGTH} bytes, or {REPORT_LENGTH + 1} "
        "bytes with a leading zero report ID."
    )


def _path_text(path: object) -> str:
    """Convert hidapi's platform-specific path value to displayable text."""
    if isinstance(path, bytes):
        return os.fsdecode(path)
    return str(path) if path is not None else ""


def _sysfs_details(hid_path: str) -> dict[str, object]:
    """Resolve a /dev/hidraw node to its USB interface and physical USB parent."""
    node = os.path.basename(hid_path)
    # hidapi on Linux commonly returns the USB interface path itself
    # (for example "1-1:1.2"), not /dev/hidrawN. Resolve that path through
    # /sys/bus/usb/devices. Also retain support for hidraw-style paths.
    if node.startswith("hidraw"):
        link = f"/sys/class/hidraw/{node}/device"
    elif re.fullmatch(r"[^/]+:1\.\d+", node):
        link = f"/sys/bus/usb/devices/{node}"
    else:
        return {"sysfs_path": "", "usb_parent": "", "sysfs_interface": None}
    try:
        resolved = os.path.realpath(link)
    except OSError:
        resolved = ""
    match = re.search(r"(?:^|/)([^/]+):1\.(\d+)(?:/|$)", resolved)
    if not match:
        return {"sysfs_path": resolved, "usb_parent": "", "sysfs_interface": None}
    return {
        "sysfs_path": resolved,
        "usb_parent": match.group(1),
        "sysfs_interface": int(match.group(2)),
    }


def inspect_keyboard_interfaces(hid_module=None) -> list[dict[str, object]]:
    """Return HID collection metadata and Linux sysfs pairing evidence.

    The report descriptors previously inspected for this exact keyboard show
    interface 2 as the vendor Feature control collection and interface 1 as
    the collection carrying vendor input Report ID 5. This function does not
    open either node or send any report.
    """
    if hid_module is None:
        try:
            import hid as hid_module
        except ImportError:
            return []
    try:
        devices = hid_module.enumerate(VENDOR_ID, PRODUCT_ID)
    except Exception as exc:
        raise IdentifyError(f"Could not enumerate HID devices: {exc}") from exc

    inventory = []
    for item in devices:
        path = _path_text(item.get("path"))
        details = _sysfs_details(path)
        interface = item.get("interface_number")
        if not isinstance(interface, int) or interface < 0:
            interface = details["sysfs_interface"]
        if interface == SETTINGS_INTERFACE:
            role = "Feature control candidate (descriptor-confirmed interface 2)"
        elif interface == ANALOG_INPUT_INTERFACE:
            role = "Analog input candidate (descriptor-confirmed Report ID 5 on interface 1)"
        else:
            role = "Other HID collection"
        inventory.append({
            "interface_number": interface,
            "usage_page": item.get("usage_page"),
            "usage": item.get("usage"),
            "path": path,
            "usb_parent": details["usb_parent"],
            "sysfs_path": details["sysfs_path"],
            "role": role,
        })
    return inventory


def paired_keyboard_interfaces(inventory: list[dict[str, object]]) -> tuple[dict, dict] | None:
    """Return the unique control/input pair only when sysfs proves same USB parent."""
    controls = [x for x in inventory if x.get("interface_number") == SETTINGS_INTERFACE]
    inputs = [x for x in inventory if x.get("interface_number") == ANALOG_INPUT_INTERFACE]
    if len(controls) != 1 or len(inputs) != 1:
        return None
    parent = controls[0].get("usb_parent")
    if not parent or parent != inputs[0].get("usb_parent"):
        return None
    return controls[0], inputs[0]


def identify_exchange_details(device, sleep=time.sleep) -> IdentifyResult:
    """Send one Identify GET, then poll its Feature reply at 10 ms intervals.

    HallJoy's reviewed RongYuan transport sends a command once, waits 10 ms
    before each GET_FEATURE poll, and allows up to 100 ms for a valid reply.
    Re-sending the command on every poll is deliberately avoided.
    """
    request = identify_packet()
    wire_request = bytes([0]) + request
    # Match the vendor driver spacing before SET_FEATURE as well as GET_FEATURE.
    sleep(EXCHANGE_GAP_SECONDS)
    try:
        sent = device.send_feature_report(wire_request)
    except Exception as exc:
        raise IdentifyError(f"Could not send the read-only Identify request: {exc}") from exc
    if sent != len(wire_request):
        raise IdentifyError(
            f"hidapi sent an incomplete Identify request ({sent}/{len(wire_request)} bytes)."
        )

    last_reply_note = "The keyboard did not return a valid 0x8F Identify reply."
    poll_count = int(IDENTIFY_TIMEOUT_SECONDS / EXCHANGE_GAP_SECONDS)
    for _ in range(poll_count):
        sleep(EXCHANGE_GAP_SECONDS)
        try:
            raw = device.get_feature_report(0, REPORT_LENGTH + 1)
        except Exception as exc:
            raise IdentifyError(f"HID Feature read failed: {exc}") from exc
        reply = _feature_payload(raw)
        device_id = parse_device_id(reply)
        if device_id is not None:
            return IdentifyResult(
                device_id=device_id,
                firmware_revision=(
                    parse_gen2_firmware_revision(reply) if device_id == 2255 else None
                ),
                raw_reply=bytes(reply),
            )
        last_reply_note = (
            "The Feature report was received, but its contents were not a valid "
            "0x8F reply (or the device refused the request)."
        )
    raise IdentifyError(last_reply_note)


def identify_exchange(device, sleep=time.sleep) -> int:
    """Backward-compatible board-ID-only wrapper around the detailed exchange."""
    return identify_exchange_details(device, sleep=sleep).device_id


def identify_keyboard_details() -> IdentifyResult:
    """Identify the board through its verified vendor Feature collection.

    This performs one GET-only handshake. The device must be connected by USB,
    and the current user must have permission to open the matching HID node.
    """
    try:
        import hid
    except ImportError as exc:
        raise IdentifyError(
            "The hidapi Python package is missing. Reinstall the application."
        ) from exc

    inventory = inspect_keyboard_interfaces(hid)
    candidates = [
        item for item in inventory
        if item.get("interface_number") == SETTINGS_INTERFACE and item.get("path")
    ]
    if not candidates:
        details = "; ".join(
            "interface={interface!r}, usage_page={page!r}, usage={usage!r}, "
            "path={path!r}, sysfs_parent={parent!r}".format(
                interface=item.get("interface_number"),
                page=item.get("usage_page"),
                usage=item.get("usage"),
                path=item.get("path"),
                parent=item.get("usb_parent"),
            )
            for item in inventory
        ) or "hidapi returned no matching VID/PID entries"
        raise IdentifyError(
            "Could not select USB interface 2. hidapi enumeration: " + details
        )
    if len(candidates) != 1:
        raise IdentifyError(
            f"Found {len(candidates)} matching settings interfaces; refusing "
            "an ambiguous device selection."
        )

    selected = candidates[0]
    usage_note = (
        f" (hidapi usage_page={selected.get('usage_page')!r}, "
        f"usage={selected.get('usage')!r})"
    )
    device = hid.device()
    try:
        try:
            device.open_path(os.fsencode(selected["path"]))
        except Exception as exc:
            detail = str(exc).strip() or exc.__class__.__name__
            raise IdentifyError(
                "Could not open the keyboard's HID settings interface 2 "
                f"({selected['path']}). OS/hidapi error: {detail}. "
                "The scoped udev rule is now installed in the project; "
                "if access is still denied, verify the ACL on the matching "
                "/dev/hidraw node after reconnecting the keyboard. "
                "Do not run the GUI with sudo."
            ) from exc
        try:
            return identify_exchange_details(device)
        except IdentifyError as exc:
            raise IdentifyError(str(exc) + usage_note) from exc
    finally:
        try:
            device.close()
        except Exception:
            pass


def identify_keyboard() -> int:
    """Backward-compatible board-ID-only wrapper for the GUI and callers."""
    return identify_keyboard_details().device_id
