import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from lighting import (
    BOARD_2255_FIXED_FLAG,
    BOARD_2255_RAINBOW_FLAG,
    LED_GET_OPCODE,
    LED_SET_OPCODE,
    LightingProtocolError,
    led_params_get_packet,
    led_params_set_packet,
    parse_led_params_reply,
)


class LightingProtocolTests(unittest.TestCase):
    def test_get_packet_uses_bit8_checksum(self):
        packet = led_params_get_packet()
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[0], LED_GET_OPCODE)
        self.assertEqual(packet[8], (0xFF - sum(packet[:8])) & 0xFF)
        self.assertEqual(packet[9:], bytes(55))

    def test_parser_reads_mode_speed_brightness_flags_and_rgb(self):
        reply = bytearray(64)
        reply[0] = LED_GET_OPCODE
        reply[1:8] = bytes([13, 2, 4, 0x38, 12, 34, 56])
        parsed = parse_led_params_reply(reply)
        self.assertEqual(parsed.mode, 13)
        self.assertEqual(parsed.speed, 2)
        self.assertEqual(parsed.brightness, 4)
        self.assertEqual(parsed.option, 3)
        self.assertEqual(parsed.flags, BOARD_2255_FIXED_FLAG)
        self.assertEqual(parsed.rgb, (12, 34, 56))

    def test_parser_accepts_hidapi_report_id_prefix(self):
        reply = bytearray(64)
        reply[0] = LED_GET_OPCODE
        self.assertEqual(parse_led_params_reply(bytes([0]) + reply).mode, 0)

    def test_parser_rejects_wrong_opcode_and_malformed_lengths(self):
        for reply in (bytes(64), bytes(63), bytes(65), "x" * 64):
            with self.subTest(length=len(reply)):
                with self.assertRaises(LightingProtocolError):
                    parse_led_params_reply(reply)

    def test_set_packet_uses_board_2255_flags_and_bit8_checksum(self):
        for flags in (BOARD_2255_FIXED_FLAG, BOARD_2255_RAINBOW_FLAG):
            packet = led_params_set_packet(
                13, 2, 4, (10, 20, 30), option=3, flags=flags
            )
            self.assertEqual(len(packet), 64)
            self.assertEqual(packet[0], LED_SET_OPCODE)
            self.assertEqual(packet[1:8], bytes([13, 2, 4, (3 << 4) | flags, 10, 20, 30]))
            self.assertEqual(packet[8], (0xFF - sum(packet[:8])) & 0xFF)
            self.assertEqual(packet[9:], bytes(55))

    def test_set_packet_rejects_out_of_range_values(self):
        invalid = (
            (-1, 0, 0, (0, 0, 0)),
            (32, 0, 0, (0, 0, 0)),
            (1, 5, 0, (0, 0, 0)),
            (1, 0, 5, (0, 0, 0)),
            (1, 0, 0, (0, 0, 256)),
            (1, 0, 0, (0, 0)),
        )
        for args in invalid:
            with self.subTest(args=args):
                with self.assertRaises(LightingProtocolError):
                    led_params_set_packet(*args)
        for flags in (0, 6, 9, True):
            with self.subTest(flags=flags):
                with self.assertRaises(LightingProtocolError):
                    led_params_set_packet(1, 0, 0, (0, 0, 0), flags=flags)


if __name__ == "__main__":
    unittest.main()
