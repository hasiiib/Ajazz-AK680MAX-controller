import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from keymap import (
    KeymapProtocolError,
    keymap_get_packet,
    parse_keymap_page,
)


class KeymapRequestTests(unittest.TestCase):
    def test_get_packet_contains_profile_all_slots_page_and_sublayer(self):
        packet = keymap_get_packet(profile=2, page=7, sublayer=3)
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[:5], bytes([0x8A, 2, 0xFF, 7, 3]))
        self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packet[8:], bytes([0xFF]) * 56)

    def test_request_rejects_out_of_range_and_bool_fields(self):
        invalid = (
            (-1, 0, 0), (4, 0, 0), (0, -1, 0), (0, 8, 0),
            (0, 0, -1), (0, 0, 4), (True, 0, 0), (0, False, 0),
        )
        for args in invalid:
            with self.subTest(args=args):
                with self.assertRaises(KeymapProtocolError):
                    keymap_get_packet(*args)


class KeymapParserTests(unittest.TestCase):
    def test_page_preserves_sixteen_four_byte_entries(self):
        raw = bytes(range(64))
        result = parse_keymap_page(1, 3, 2, raw)
        self.assertEqual(result.profile, 1)
        self.assertEqual(result.sublayer, 2)
        self.assertEqual(result.page, 3)
        self.assertEqual(result.first_slot, 48)
        self.assertEqual(len(result.entries), 16)
        self.assertEqual(result.entries[0], bytes([0, 1, 2, 3]))
        self.assertEqual(result.entries[-1], bytes([60, 61, 62, 63]))

    def test_parser_accepts_zero_report_id_prefix(self):
        raw = bytes([0]) + bytes([0xA5] * 64)
        result = parse_keymap_page(0, 0, 0, raw)
        self.assertEqual(result.entries[0], bytes([0xA5] * 4))

    def test_parser_rejects_malformed_payload_lengths(self):
        for raw in (bytes(63), bytes([1]) + bytes(64), bytes([0]) + bytes(65)):
            with self.subTest(length=len(raw)):
                with self.assertRaises(KeymapProtocolError):
                    parse_keymap_page(0, 0, 0, raw)


if __name__ == "__main__":
    unittest.main()
