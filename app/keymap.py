"""Strict, read-only RongYuan gen2 keymap page framing.

This module preserves raw four-byte entries without assigning meanings to
unverified fields. It performs no HID I/O and contains no keymap write opcode.
"""
from __future__ import annotations

from dataclasses import dataclass

REPORT_LENGTH = 64
KEYMAP_GET_OPCODE = 0x8A
PROFILE_COUNT = 4
SUBLAYER_COUNT = 4
KEYMAP_PAGE_COUNT = 8
ENTRIES_PER_PAGE = 16
ENTRY_LENGTH = 4
KEYMAP_SLOT_COUNT = KEYMAP_PAGE_COUNT * ENTRIES_PER_PAGE


class KeymapProtocolError(ValueError):
    """A keymap request or response violates the documented gen2 shape."""


@dataclass(frozen=True)
class KeymapPage:
    """One raw keymap page containing sixteen four-byte slot entries."""

    profile: int
    sublayer: int
    page: int
    first_slot: int
    entries: tuple[bytes, ...]


def keymap_get_packet(profile: int, page: int, sublayer: int = 0) -> bytes:
    """Build a 64-byte Bit7-checksummed 0x8A GET request; never sends it."""
    for name, value, upper in (
        ("profile", profile, PROFILE_COUNT),
        ("page", page, KEYMAP_PAGE_COUNT),
        ("sublayer", sublayer, SUBLAYER_COUNT),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < upper:
            raise KeymapProtocolError(
                f"{name} must be an integer from 0 through {upper - 1}; got {value!r}."
            )

    packet = bytearray(REPORT_LENGTH)
    packet[0] = KEYMAP_GET_OPCODE
    packet[1] = profile
    packet[2] = 0xFF
    packet[3] = page
    packet[4] = sublayer
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    # Match the RongYuan snapshot transport's invalid-response sentinel tail.
    packet[8:] = bytes([0xFF]) * (REPORT_LENGTH - 8)
    return bytes(packet)


def parse_keymap_page(
    profile: int, page: int, sublayer: int, reply: bytes | bytearray
) -> KeymapPage:
    """Decode a raw 64-byte 0x8A page without guessing entry field semantics."""
    # Reuse request validation so parser and request bounds cannot diverge.
    keymap_get_packet(profile, page, sublayer)
    data = bytes(reply)
    if len(data) == REPORT_LENGTH + 1 and data[0] == 0:
        data = data[1:]
    if len(data) != REPORT_LENGTH:
        raise KeymapProtocolError(
            f"Keymap GET returned {len(data)} payload bytes; expected exactly 64."
        )
    entries = tuple(
        data[offset:offset + ENTRY_LENGTH]
        for offset in range(0, REPORT_LENGTH, ENTRY_LENGTH)
    )
    return KeymapPage(
        profile=profile,
        sublayer=sublayer,
        page=page,
        first_slot=page * ENTRIES_PER_PAGE,
        entries=entries,
    )
