import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from magnetic_settings import (
    MagneticSettingsProtocolError,
    magnetic_settings_get_packet,
    parse_magnetic_settings_page,
)


class MagneticSettingsRequestTests(unittest.TestCase):
    def test_get_packet_has_gen2_page_fields_and_bit7_checksum(self):
        packet = magnetic_settings_get_packet(0, 3)
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[:4], bytes([0xE5, 0, 1, 3]))
        self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packet[8:], bytes(56))

    def test_request_supports_documented_page_ranges(self):
        for subop, last_page in ((0, 3), (6, 3), (5, 1), (7, 1), (9, 1), (10, 7)):
            self.assertEqual(len(magnetic_settings_get_packet(subop, last_page)), 64)

    def test_request_rejects_invalid_subop_and_page(self):
        for subop, page in ((8, 0), (11, 0), (0, 4), (5, 2), (10, 8), (0, -1)):
            with self.subTest(subop=subop, page=page):
                with self.assertRaises(MagneticSettingsProtocolError):
                    magnetic_settings_get_packet(subop, page)

    def test_request_rejects_bool_as_page(self):
        with self.assertRaises(MagneticSettingsProtocolError):
            magnetic_settings_get_packet(0, True)


class MagneticSettingsParserTests(unittest.TestCase):
    def test_u16_page_decodes_little_endian_values_and_slot_offset(self):
        raw = bytearray(64)
        raw[0:2] = (0x1234).to_bytes(2, "little")
        raw[2:4] = (0xABCD).to_bytes(2, "little")
        result = parse_magnetic_settings_page(0, 2, raw)
        self.assertEqual(result.first_slot, 64)
        self.assertEqual(result.value_width, 2)
        self.assertEqual(len(result.values), 32)
        self.assertEqual(result.values[:2], (0x1234, 0xABCD))

    def test_u8_page_decodes_64_slots(self):
        raw = bytes(range(64))
        result = parse_magnetic_settings_page(7, 1, raw)
        self.assertEqual(result.first_slot, 64)
        self.assertEqual(result.value_width, 1)
        self.assertEqual(result.values, tuple(range(64)))

    def test_feature_report_id_prefix_is_removed(self):
        raw = bytes([0]) + bytes([0x5A] * 64)
        result = parse_magnetic_settings_page(5, 0, raw)
        self.assertEqual(result.values, tuple([0x5A] * 64))

    def test_dks_actions_are_grouped_as_four_bytes_per_key(self):
        raw = bytes(range(64))
        result = parse_magnetic_settings_page(10, 7, raw)
        self.assertEqual(result.first_slot, 112)
        self.assertEqual(result.value_width, 4)
        self.assertEqual(len(result.values), 16)
        self.assertEqual(result.values[0], (0, 1, 2, 3))
        self.assertEqual(result.values[-1], (60, 61, 62, 63))

    def test_parser_rejects_short_and_oversized_pages(self):
        for raw in (bytes(63), bytes([1]) + bytes(64), bytes([0]) + bytes(65)):
            with self.subTest(length=len(raw)):
                with self.assertRaises(MagneticSettingsProtocolError):
                    parse_magnetic_settings_page(0, 0, raw)

    def test_parser_rejects_unsupported_write_only_column(self):
        with self.assertRaises(MagneticSettingsProtocolError):
            parse_magnetic_settings_page(8, 0, bytes(64))

    def test_parser_rejects_invalid_page_even_if_payload_is_valid(self):
        with self.assertRaises(MagneticSettingsProtocolError):
            parse_magnetic_settings_page(10, 8, bytes(64))


if __name__ == "__main__":
    unittest.main()
