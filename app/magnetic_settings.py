"""Strict, read-only parsers for RongYuan gen2 magnetic-setting pages.

The 0xE5 request layout is documented for gen2 firmware, but its behavior
has not yet been physically verified on board 2255. This module deliberately
contains no HID I/O and no 0x65 write command.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

REPORT_LENGTH = 64
MAGNETIC_GET_OPCODE = 0xE5
MAGNETIC_U16_SUBOPS = frozenset({0, 1, 2, 3, 4, 6})
MAGNETIC_U8_SUBOPS = frozenset({5, 7, 9})
MAGNETIC_DKS_ACTIONS_SUBOP = 10
MAGNETIC_SLOT_COUNT = 128
PAGE_BYTES = 64


class MagneticSettingsProtocolError(ValueError):
    """A magnetic-setting request or response violates the documented shape."""


MagneticValue: TypeAlias = int | tuple[int, int, int, int]


@dataclass(frozen=True)
class MagneticSettingsPage:
    """One decoded 64-byte magnetic-setting page."""

    subop: int
    page: int
    first_slot: int
    values: tuple[MagneticValue, ...]
    value_width: int


def _page_count(subop: int) -> int:
    if not isinstance(subop, int) or isinstance(subop, bool):
        raise MagneticSettingsProtocolError(
            f"Magnetic sub-operation must be an integer; got {subop!r}."
        )
    if subop in MAGNETIC_U16_SUBOPS:
        return 4
    if subop in MAGNETIC_U8_SUBOPS:
        return 2
    if subop == MAGNETIC_DKS_ACTIONS_SUBOP:
        return 8
    if subop == 8:
        raise MagneticSettingsProtocolError(
            "Magnetic sub-operation 8 is documented as write-one-slot only."
        )
    raise MagneticSettingsProtocolError(
        f"Unsupported magnetic GET sub-operation: {subop}."
    )


def magnetic_settings_get_packet(subop: int, page: int) -> bytes:
    """Build a 64-byte Bit7-checksummed 0xE5 GET; never sends it."""
    page_count = _page_count(subop)
    if not isinstance(page, int) or isinstance(page, bool) or not 0 <= page < page_count:
        raise MagneticSettingsProtocolError(
            f"Page {page!r} is invalid for magnetic sub-operation {subop}; "
            f"expected 0..{page_count - 1}."
        )

    packet = bytearray(REPORT_LENGTH)
    packet[0] = MAGNETIC_GET_OPCODE
    packet[1] = subop
    packet[2] = 1
    packet[3] = page
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    # The reviewed RongYuan snapshot transport fills the unused request tail
    # with 0xFF for matrix-style GETs, so a partially produced reply cannot
    # accidentally resemble an all-zero valid page.
    packet[8:] = bytes([0xFF]) * (REPORT_LENGTH - 8)
    return bytes(packet)


def _normalize_raw_page(reply: bytes | bytearray) -> bytes:
    if not isinstance(reply, (bytes, bytearray)):
        raise MagneticSettingsProtocolError("Magnetic reply must be bytes or bytearray.")
    data = bytes(reply)
    # hidapi may include the leading zero report ID in Feature reads.
    if len(data) == REPORT_LENGTH + 1 and data[0] == 0:
        data = data[1:]
    if len(data) != PAGE_BYTES:
        raise MagneticSettingsProtocolError(
            f"Magnetic GET returned {len(data)} payload bytes; expected exactly 64."
        )
    return data


def parse_magnetic_settings_page(
    subop: int, page: int, reply: bytes | bytearray
) -> MagneticSettingsPage:
    """Decode one raw 0xE5 page; the gen2 response does not echo the opcode."""
    page_count = _page_count(subop)
    if not isinstance(page, int) or isinstance(page, bool) or not 0 <= page < page_count:
        raise MagneticSettingsProtocolError(
            f"Page {page!r} is invalid for magnetic sub-operation {subop}; "
            f"expected 0..{page_count - 1}."
        )

    data = _normalize_raw_page(reply)
    if subop in MAGNETIC_U16_SUBOPS:
        values: tuple[MagneticValue, ...] = tuple(
            int.from_bytes(data[offset:offset + 2], "little")
            for offset in range(0, PAGE_BYTES, 2)
        )
        return MagneticSettingsPage(subop, page, page * 32, values, 2)

    if subop in MAGNETIC_U8_SUBOPS:
        values = tuple(data)
        return MagneticSettingsPage(subop, page, page * 64, values, 1)

    records = tuple(
        tuple(data[offset:offset + 4])
        for offset in range(0, PAGE_BYTES, 4)
    )
    return MagneticSettingsPage(subop, page, page * 16, records, 4)
