import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from magnetic_write import (
    MAGNETIC_SET_OPCODE,
    MagneticWriteProtocolError,
    magnetic_setting_set_packet,
)


class MagneticWriteBuilderTests(unittest.TestCase):
    def test_builds_u16_single_slot_packet(self):
        packet = magnetic_setting_set_packet(0, 31, 200)
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[0], MAGNETIC_SET_OPCODE)
        self.assertEqual(packet[1:5], bytes([0, 0, 31, 1]))
        self.assertEqual(packet[8:12], bytes([200, 0, 0, 0]))
        self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packet[12:], bytes(52))

    def test_builds_u8_and_dks_single_slot_packets(self):
        u8 = magnetic_setting_set_packet(7, 4, 0x81)
        self.assertEqual(u8[8:12], bytes([0x81, 0, 0, 0]))
        dks = magnetic_setting_set_packet(8, 5, (3, 2, 0, 0))
        self.assertEqual(dks[8:12], bytes([3, 2, 0, 0]))

    def test_accepts_documented_writable_u16_columns(self):
        for subop in (0, 1, 2, 3, 4, 6):
            with self.subTest(subop=subop):
                packet = magnetic_setting_set_packet(subop, 127, 0x1234)
                self.assertEqual(packet[1], subop)
                self.assertEqual(packet[8:10], bytes([0x34, 0x12]))

    def test_rejects_read_only_and_undocumented_columns(self):
        for subop in (10, 251, 252, 254, 11, -1, True):
            with self.subTest(subop=subop):
                with self.assertRaises(MagneticWriteProtocolError):
                    magnetic_setting_set_packet(subop, 0, 0)

    def test_rejects_invalid_slot_and_value_width_or_range(self):
        invalid = (
            (0, -1, 100), (0, 128, 100), (0, 1, -1), (0, 1, 65536),
            (5, 1, 256), (8, 1, (1, 2, 3)), (8, 1, (1, 2, 3, 256)),
            (0, True, 100), (0, 1, True),
        )
        for args in invalid:
            with self.subTest(args=args):
                with self.assertRaises(MagneticWriteProtocolError):
                    magnetic_setting_set_packet(*args)


if __name__ == "__main__":
    unittest.main()
