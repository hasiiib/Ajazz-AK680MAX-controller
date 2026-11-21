"""Pure gen2 LED parameter packet builders and response parser for board 2255.

The 2255 vendor host registry reports rainbow flag 8 and fixed-colour flag 7.
These helpers only build/parse packets in memory; no HID transport or GUI
lighting write is connected.
"""
from __future__ import annotations

from dataclasses import dataclass

REPORT_LENGTH = 64
LED_SET_OPCODE = 0x07
LED_GET_OPCODE = 0x87
BOARD_2255_RAINBOW_FLAG = 8
BOARD_2255_FIXED_FLAG = 7


class LightingProtocolError(ValueError):
    """A lighting packet or response does not match the supported gen2 shape."""


@dataclass(frozen=True)
class LedParameters:
    mode: int
    speed: int
    brightness: int
    option: int
    flags: int
    rgb: tuple[int, int, int]


def _validate_mode(mode: int) -> None:
    if type(mode) is not int or not 0 <= mode <= 31:
        raise LightingProtocolError("LED mode must be an integer from 0 through 31.")


def led_params_get_packet() -> bytes:
    """Build a Bit8-checksummed 0x87 GET request; performs no I/O."""
    packet = bytearray(REPORT_LENGTH)
    packet[0] = LED_GET_OPCODE
    packet[8] = (0xFF - (sum(packet[:8]) & 0xFF)) & 0xFF
    return bytes(packet)


def parse_led_params_reply(reply: bytes | bytearray) -> LedParameters:
    """Parse the documented 0x87 response fields without inventing mode labels."""
    if not isinstance(reply, (bytes, bytearray)):
        raise LightingProtocolError("LED response must be bytes or bytearray.")
    data = bytes(reply)
    if len(data) == REPORT_LENGTH + 1 and data[0] == 0:
        data = data[1:]
    if len(data) != REPORT_LENGTH:
        raise LightingProtocolError("LED response must contain exactly 64 payload bytes.")
    if data[0] != LED_GET_OPCODE:
        raise LightingProtocolError(
            f"LED GET returned opcode 0x{data[0]:02X}; expected 0x87."
        )
    option_flags = data[4]
    return LedParameters(
        mode=data[1],
        speed=data[2],
        brightness=data[3],
        option=(option_flags >> 4) & 0x0F,
        flags=option_flags & 0x0F,
        rgb=(data[5], data[6], data[7]),
    )


def led_params_set_packet(
    mode: int,
    speed: int,
    brightness: int,
    rgb: tuple[int, int, int] | list[int],
    *,
    option: int = 0,
    flags: int = BOARD_2255_FIXED_FLAG,
) -> bytes:
    """Build a 2255-targeted Bit8 0x07 SET packet; performs no I/O.

    This packet builder is offline-only. The caller must not send it until
    board-2255 mode availability, read-back behavior, and recovery are
    physically verified. Flags 7 (fixed) and 8 (rainbow) are from vendor
    host-software metadata for device ID 2255.
    """
    _validate_mode(mode)
    if type(speed) is not int or not 0 <= speed <= 4:
        raise LightingProtocolError("Gen2 LED speed must be an integer from 0 through 4.")
    if type(brightness) is not int or not 0 <= brightness <= 4:
        raise LightingProtocolError("Gen2 LED brightness must be an integer from 0 through 4.")
    if type(option) is not int or not 0 <= option <= 15:
        raise LightingProtocolError("LED option must be an integer from 0 through 15.")
    if type(flags) is not int or flags not in (
        BOARD_2255_FIXED_FLAG, BOARD_2255_RAINBOW_FLAG
    ):
        raise LightingProtocolError("Board 2255 LED flags must be 7 (fixed) or 8 (rainbow).")
    if not isinstance(rgb, (tuple, list)) or len(rgb) != 3:
        raise LightingProtocolError("LED colour must contain exactly three RGB bytes.")
    if any(type(channel) is not int or not 0 <= channel <= 255 for channel in rgb):
        raise LightingProtocolError("Each RGB channel must be an integer from 0 through 255.")

    packet = bytearray(REPORT_LENGTH)
    packet[0] = LED_SET_OPCODE
    packet[1] = mode
    packet[2] = speed
    packet[3] = brightness
    packet[4] = (option << 4) | flags
    packet[5:8] = bytes(rgb)
    packet[8] = (0xFF - (sum(packet[:8]) & 0xFF)) & 0xFF
    return bytes(packet)
