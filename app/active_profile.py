"""Read-only RongYuan gen2 active-profile request and response parser.

This is pure framing/validation code only. It does not switch profiles or
perform HID I/O.
"""
from __future__ import annotations

REPORT_LENGTH = 64
PROFILE_GET_OPCODE = 0x84
PROFILE_COUNT = 4


class ProfileProtocolError(ValueError):
    """A profile request or response violates the documented gen2 shape."""


def active_profile_get_packet() -> bytes:
    """Build the documented 64-byte gen2 0x84 GET packet."""
    packet = bytearray(REPORT_LENGTH)
    packet[0] = PROFILE_GET_OPCODE
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    return bytes(packet)


def parse_active_profile_reply(reply: bytes | bytearray) -> int:
    """Return the zero-based active profile from a validated 0x84 reply."""
    if not isinstance(reply, (bytes, bytearray)):
        raise ProfileProtocolError("Profile reply must be bytes or bytearray.")
    data = bytes(reply)
    if len(data) == REPORT_LENGTH + 1 and data[0] == 0:
        data = data[1:]
    if len(data) != REPORT_LENGTH:
        raise ProfileProtocolError(
            f"Profile GET returned {len(data)} payload bytes; expected exactly 64."
        )
    if data[0] != PROFILE_GET_OPCODE:
        raise ProfileProtocolError(
            f"Profile GET returned opcode 0x{data[0]:02X}; expected 0x84."
        )
    profile = data[1]
    if profile >= PROFILE_COUNT:
        raise ProfileProtocolError(
            f"Keyboard reported unsupported profile index {profile}; expected 0..3."
        )
    return profile
