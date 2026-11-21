"""Gen2 macro storage, event encoding, and page packet helpers.

All helpers are pure and operate on in-memory bytes. The module does not open
HID or send macro writes; board-2255 read/write behavior still needs a
separately authorized physical acceptance test before transport is connected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

REPORT_LENGTH = 64
MACRO_GET_OPCODE = 0x8B
MACRO_SET_OPCODE = 0x0B
MACRO_SLOT_COUNT = 50
MACRO_BLOB_LENGTH = 256
MACRO_READ_PAGE_SIZE = 64
MACRO_WRITE_PAGE_SIZE = 56
MACRO_WRITE_PAGE_COUNT = 5
MOUSE_BUTTON_BASE = 0xF0
MOUSE_MOVE_CODE = 0xF9
MAX_KEY_USAGE = 0xEF


class MacroProtocolError(ValueError):
    """A macro, page, or event does not match the documented gen2 shape."""


@dataclass(frozen=True)
class MacroKeyEvent:
    usage: int
    pressed: bool
    delay_ms: int


@dataclass(frozen=True)
class MacroMouseButtonEvent:
    button: int
    pressed: bool
    delay_ms: int


@dataclass(frozen=True)
class MacroMouseMoveEvent:
    dx: int
    dy: int
    delay_ms: int


MacroEvent = MacroKeyEvent | MacroMouseButtonEvent | MacroMouseMoveEvent


@dataclass(frozen=True)
class MacroDefinition:
    repeat: int
    events: tuple[MacroEvent, ...]

    def __post_init__(self):
        if type(self.repeat) is not int or not 0 <= self.repeat <= 0xFFFF:
            raise MacroProtocolError("Macro repeat must be a u16 integer.")
        if not isinstance(self.events, tuple):
            raise MacroProtocolError("Macro events must be an immutable tuple.")


def _validate_slot_page(slot: int, page: int) -> None:
    if type(slot) is not int or not 0 <= slot < MACRO_SLOT_COUNT:
        raise MacroProtocolError("Macro slot must be an integer from 0 through 49.")
    if type(page) is not int or not 0 <= page < 4:
        raise MacroProtocolError("Macro read page must be an integer from 0 through 3.")


def _bit7_packet(opcode: int, fields: tuple[int, ...]) -> bytes:
    packet = bytearray(REPORT_LENGTH)
    packet[0] = opcode
    packet[1:1 + len(fields)] = bytes(fields)
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    return bytes(packet)


def macro_get_packet(slot: int, page: int) -> bytes:
    """Build a raw 0x8B macro-page GET request; performs no I/O."""
    _validate_slot_page(slot, page)
    return _bit7_packet(MACRO_GET_OPCODE, (slot, page))


def parse_macro_page(reply: bytes | bytearray) -> bytes:
    """Normalize one raw 64-byte macro page; no opcode echo is assumed."""
    if not isinstance(reply, (bytes, bytearray)):
        raise MacroProtocolError("Macro page response must be bytes or bytearray.")
    data = bytes(reply)
    if len(data) == 65 and data[0] == 0:
        data = data[1:]
    if len(data) != MACRO_READ_PAGE_SIZE:
        raise MacroProtocolError("Macro page response must contain exactly 64 raw bytes.")
    return data


def assemble_macro_blob(pages: Mapping[int, bytes | bytearray]) -> bytes:
    """Assemble all four 64-byte read pages into one 256-byte macro blob."""
    if not isinstance(pages, Mapping) or set(pages) != {0, 1, 2, 3}:
        raise MacroProtocolError("Macro assembly requires exactly read pages 0, 1, 2, and 3.")
    blob = bytearray()
    for page in range(4):
        blob.extend(parse_macro_page(pages[page]))
    return bytes(blob)


def _encode_press(stream: bytearray, code: int, pressed: bool, delay_ms: int) -> None:
    high = 0x80 if pressed else 0
    if 1 <= delay_ms <= 127:
        stream.extend((code, high | delay_ms))
    else:
        stream.extend((code, high))
        stream.extend(delay_ms.to_bytes(2, "little"))


def encode_macro(definition: MacroDefinition) -> bytes:
    """Encode key, mouse-button and mouse-move events into a 256-byte blob."""
    if not isinstance(definition, MacroDefinition):
        raise MacroProtocolError("Expected a MacroDefinition.")
    stream = bytearray()
    for event in definition.events:
        if isinstance(event, MacroKeyEvent):
            if type(event.usage) is not int or not 0x04 <= event.usage <= MAX_KEY_USAGE:
                raise MacroProtocolError("Keyboard usage must be in range 0x04 through 0xEF.")
            if type(event.pressed) is not bool:
                raise MacroProtocolError("Key pressed state must be boolean.")
            if type(event.delay_ms) is not int or not 0 <= event.delay_ms <= 0xFFFF:
                raise MacroProtocolError("Key delay must be a u16 integer.")
            _encode_press(stream, event.usage, event.pressed, event.delay_ms)
        elif isinstance(event, MacroMouseButtonEvent):
            if type(event.button) is not int or not 0 <= event.button <= 4:
                raise MacroProtocolError("Mouse button must be an integer from 0 through 4.")
            if type(event.pressed) is not bool:
                raise MacroProtocolError("Mouse pressed state must be boolean.")
            if type(event.delay_ms) is not int or not 0 <= event.delay_ms <= 0xFFFF:
                raise MacroProtocolError("Mouse button delay must be a u16 integer.")
            _encode_press(
                stream, MOUSE_BUTTON_BASE + event.button, event.pressed, event.delay_ms
            )
        elif isinstance(event, MacroMouseMoveEvent):
            if type(event.dx) is not int or not -128 <= event.dx <= 127:
                raise MacroProtocolError("Mouse dx must be a signed byte.")
            if type(event.dy) is not int or not -128 <= event.dy <= 127:
                raise MacroProtocolError("Mouse dy must be a signed byte.")
            if type(event.delay_ms) is not int or not 0 <= event.delay_ms <= 0xFF:
                raise MacroProtocolError("Mouse-move delay must be a byte.")
            stream.extend((
                MOUSE_MOVE_CODE, event.delay_ms, event.dx & 0xFF, event.dy & 0xFF
            ))
        else:
            raise MacroProtocolError("Unsupported macro event type.")

    if len(stream) > MACRO_BLOB_LENGTH - 6:
        raise MacroProtocolError(
            f"Macro event stream is too long ({len(stream)} bytes; maximum 250)."
        )
    blob = bytearray(MACRO_BLOB_LENGTH)
    blob[:2] = definition.repeat.to_bytes(2, "little")
    blob[2:2 + len(stream)] = stream
    return bytes(blob)


def decode_macro(blob: bytes | bytearray) -> MacroDefinition:
    """Decode until the first zero terminator or first unknown event code."""
    if not isinstance(blob, (bytes, bytearray)) or len(blob) != MACRO_BLOB_LENGTH:
        raise MacroProtocolError("Macro blob must contain exactly 256 bytes.")
    data = bytes(blob)
    repeat = int.from_bytes(data[:2], "little")
    events: list[MacroEvent] = []
    offset = 2
    while offset < MACRO_BLOB_LENGTH:
        code = data[offset]
        if code == 0:
            break
        if code == MOUSE_MOVE_CODE:
            if offset + 3 >= MACRO_BLOB_LENGTH:
                break
            events.append(MacroMouseMoveEvent(
                dx=data[offset + 2] - 256 if data[offset + 2] >= 128 else data[offset + 2],
                dy=data[offset + 3] - 256 if data[offset + 3] >= 128 else data[offset + 3],
                delay_ms=data[offset + 1],
            ))
            offset += 4
            continue
        if offset + 1 >= MACRO_BLOB_LENGTH:
            break
        pressed = bool(data[offset + 1] & 0x80)
        short_delay = data[offset + 1] & 0x7F
        if short_delay:
            delay_ms = short_delay
            offset += 2
        else:
            if offset + 3 >= MACRO_BLOB_LENGTH:
                break
            delay_ms = int.from_bytes(data[offset + 2:offset + 4], "little")
            offset += 4
        if 0x04 <= code <= MAX_KEY_USAGE:
            events.append(MacroKeyEvent(code, pressed, delay_ms))
        elif MOUSE_BUTTON_BASE <= code <= MOUSE_BUTTON_BASE + 4:
            events.append(MacroMouseButtonEvent(code - MOUSE_BUTTON_BASE, pressed, delay_ms))
        else:
            break
    return MacroDefinition(repeat, tuple(events))


def macro_write_page_count(blob: bytes | bytearray) -> int:
    """Return the non-zero 56-byte prefix length, with one page for clear."""
    if not isinstance(blob, (bytes, bytearray)) or len(blob) != MACRO_BLOB_LENGTH:
        raise MacroProtocolError("Macro blob must contain exactly 256 bytes.")
    last = -1
    for page in range(MACRO_WRITE_PAGE_COUNT):
        start = page * MACRO_WRITE_PAGE_SIZE
        end = min(start + MACRO_WRITE_PAGE_SIZE, MACRO_BLOB_LENGTH)
        if any(blob[start:end]):
            last = page
    return max(1, last + 1)


def macro_write_packet(slot: int, page: int, last: bool, blob: bytes | bytearray) -> bytes:
    """Build one 0x0B 56-byte-page SET packet; performs no I/O."""
    if type(slot) is not int or not 0 <= slot < MACRO_SLOT_COUNT:
        raise MacroProtocolError("Macro slot must be an integer from 0 through 49.")
    if type(page) is not int or not 0 <= page < MACRO_WRITE_PAGE_COUNT:
        raise MacroProtocolError("Macro write page must be an integer from 0 through 4.")
    if type(last) is not bool:
        raise MacroProtocolError("Macro final-page flag must be boolean.")
    if not isinstance(blob, (bytes, bytearray)) or len(blob) != MACRO_BLOB_LENGTH:
        raise MacroProtocolError("Macro blob must contain exactly 256 bytes.")

    packet = bytearray(REPORT_LENGTH)
    packet[0] = MACRO_SET_OPCODE
    packet[1:6] = bytes((slot, page, MACRO_WRITE_PAGE_SIZE, int(last), 0))
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    start = page * MACRO_WRITE_PAGE_SIZE
    end = min(start + MACRO_WRITE_PAGE_SIZE, MACRO_BLOB_LENGTH)
    packet[8:8 + (end - start)] = bytes(blob[start:end])
    return bytes(packet)


def build_macro_write_packets(slot: int, blob: bytes | bytearray) -> tuple[bytes, ...]:
    """Build the required prefix of 56-byte pages; does not send them."""
    if type(slot) is not int or not 0 <= slot < MACRO_SLOT_COUNT:
        raise MacroProtocolError("Macro slot must be an integer from 0 through 49.")
    if not isinstance(blob, (bytes, bytearray)) or len(blob) != MACRO_BLOB_LENGTH:
        raise MacroProtocolError("Macro blob must contain exactly 256 bytes.")
    count = macro_write_page_count(blob)
    return tuple(
        macro_write_packet(slot, page, page == count - 1, blob)
        for page in range(count)
    )
