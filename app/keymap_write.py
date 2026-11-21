"""Pure gen2 single-slot keymap SET packet builder.

This module never opens HID or sends packets. The command shape is derived
from public gen2 protocol documentation and remains unverified by a physical
write on target board 2255. The GUI does not expose or call this builder.
"""
from __future__ import annotations

REPORT_LENGTH = 64
KEYMAP_SET_OPCODE = 0x0A


class KeymapWriteProtocolError(ValueError):
    """A proposed single-slot keymap assignment is outside the gen2 shape."""


def keymap_set_packet(
    profile: int,
    slot: int,
    entry: bytes | bytearray,
    *,
    sublayer: int = 0,
) -> bytes:
    """Build one Bit7-checksummed gen2 0x0A slot update; performs no I/O.

    The final/apply flag is set to 1 so the target firmware applies the single
    entry. The caller must read the old value first and verify the new value
    through 0x8A before considering a write successful.
    """
    for name, value, upper in (
        ("profile", profile, 4),
        ("slot", slot, 128),
        ("sublayer", sublayer, 4),
    ):
        if type(value) is not int or not 0 <= value < upper:
            raise KeymapWriteProtocolError(
                f"{name} must be an integer from 0 through {upper - 1}."
            )
    if not isinstance(entry, (bytes, bytearray)) or len(entry) != 4:
        raise KeymapWriteProtocolError("A keymap assignment must contain exactly four bytes.")

    packet = bytearray(REPORT_LENGTH)
    packet[0] = KEYMAP_SET_OPCODE
    packet[1] = profile
    packet[2] = slot
    packet[5] = 1
    packet[6] = sublayer
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    packet[8:12] = bytes(entry)
    return bytes(packet)
