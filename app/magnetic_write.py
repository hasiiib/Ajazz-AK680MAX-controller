"""Pure gen2 single-slot magnetic SET packet builder.

No HID transport is present here. These packet shapes are based on public
firmware/host protocol research for the gen2 family and have NOT been
physically write-verified on board 2255. The GUI does not call this module.
"""
from __future__ import annotations

REPORT_LENGTH = 64
MAGNETIC_SET_OPCODE = 0x65

_U16_SUBOPS = frozenset({0, 1, 2, 3, 4, 6})
_U8_SUBOPS = frozenset({5, 7, 9})
_DKS_ACTIONS_SUBOP = 8


class MagneticWriteProtocolError(ValueError):
    """A proposed magnetic setting does not match a documented writable shape."""


def magnetic_setting_set_packet(subop: int, slot: int, value) -> bytes:
    """Build one Bit7-checksummed gen2 0x65 slot update; performs no I/O.

    Single-slot packets set the final/commit byte. Values are range-checked
    against the documented column width. Read-only sub-operation 10 and
    undocumented columns are rejected.
    """
    if type(subop) is not int or subop not in (_U16_SUBOPS | _U8_SUBOPS | {_DKS_ACTIONS_SUBOP}):
        raise MagneticWriteProtocolError(
            "Only documented writable magnetic sub-operations 0..9 are supported."
        )
    if type(slot) is not int or not 0 <= slot < 128:
        raise MagneticWriteProtocolError("slot must be an integer from 0 through 127.")

    encoded = bytearray(4)
    if subop in _U16_SUBOPS:
        if type(value) is not int or not 0 <= value <= 0xFFFF:
            raise MagneticWriteProtocolError("This magnetic column requires a u16 value.")
        encoded[:2] = value.to_bytes(2, "little")
    elif subop in _U8_SUBOPS:
        if type(value) is not int or not 0 <= value <= 0xFF:
            raise MagneticWriteProtocolError("This magnetic column requires a u8 value.")
        encoded[0] = value
    else:
        if not isinstance(value, (bytes, bytearray, tuple, list)) or len(value) != 4:
            raise MagneticWriteProtocolError("DKS actions require exactly four byte values.")
        if any(type(part) is not int or not 0 <= part <= 0xFF for part in value):
            raise MagneticWriteProtocolError("DKS action bytes must be integers from 0 through 255.")
        encoded[:] = bytes(value)

    packet = bytearray(REPORT_LENGTH)
    packet[0] = MAGNETIC_SET_OPCODE
    packet[1] = subop
    packet[3] = slot
    packet[4] = 1
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    packet[8:12] = encoded
    return bytes(packet)
