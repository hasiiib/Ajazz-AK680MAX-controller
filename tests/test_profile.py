import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from active_profile import (
    ProfileProtocolError,
    active_profile_get_packet,
    parse_active_profile_reply,
)


class ActiveProfileProtocolTests(unittest.TestCase):
    def test_get_packet_uses_gen2_opcode_and_bit7_checksum(self):
        packet = active_profile_get_packet()
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[0], 0x84)
        self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packet[8:], bytes(56))

    def test_parser_returns_each_supported_zero_based_profile(self):
        for index in range(4):
            reply = bytearray(64)
            reply[0] = 0x84
            reply[1] = index
            self.assertEqual(parse_active_profile_reply(reply), index)

    def test_parser_accepts_hidapi_zero_report_id_prefix(self):
        reply = bytearray(64)
        reply[0] = 0x84
        reply[1] = 2
        self.assertEqual(parse_active_profile_reply(bytes([0]) + reply), 2)

    def test_parser_rejects_non_byte_payloads(self):
        for reply in (64, "x" * 64, None):
            with self.subTest(reply_type=type(reply).__name__):
                with self.assertRaises(ProfileProtocolError):
                    parse_active_profile_reply(reply)

    def test_parser_rejects_wrong_opcode_invalid_index_and_bad_lengths(self):
        wrong_opcode = bytearray(64)
        wrong_opcode[0] = 0x85
        invalid_index = bytearray(64)
        invalid_index[0] = 0x84
        invalid_index[1] = 4
        for reply in (wrong_opcode, invalid_index, bytes(63), bytes([1]) + bytes(64)):
            with self.subTest(reply_length=len(reply)):
                with self.assertRaises(ProfileProtocolError):
                    parse_active_profile_reply(reply)


if __name__ == "__main__":
    unittest.main()
