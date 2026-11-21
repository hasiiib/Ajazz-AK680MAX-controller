import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from keymap_write import KEYMAP_SET_OPCODE, KeymapWriteProtocolError, keymap_set_packet


class KeymapWriteBuilderTests(unittest.TestCase):
    def test_builds_single_slot_gen2_packet_with_bit7_checksum(self):
        entry = bytes([0, 0, 0x04, 0])
        packet = keymap_set_packet(2, 17, entry, sublayer=0)
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[0], KEYMAP_SET_OPCODE)
        self.assertEqual(packet[1:7], bytes([2, 17, 0, 0, 1, 0]))
        self.assertEqual(packet[8:12], entry)
        self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packet[12:], bytes(52))

    def test_supports_all_valid_profile_slot_and_sublayer_bounds(self):
        for profile, slot, sublayer in ((0, 0, 0), (3, 127, 3)):
            with self.subTest(profile=profile, slot=slot, sublayer=sublayer):
                packet = keymap_set_packet(profile, slot, bytes(4), sublayer=sublayer)
                self.assertEqual(packet[1], profile)
                self.assertEqual(packet[2], slot)
                self.assertEqual(packet[6], sublayer)

    def test_rejects_invalid_indices_and_entry_shapes(self):
        for args in (
            (-1, 0, bytes(4), 0),
            (4, 0, bytes(4), 0),
            (0, -1, bytes(4), 0),
            (0, 128, bytes(4), 0),
            (0, 0, bytes(4), 4),
            (True, 0, bytes(4), 0),
            (0, True, bytes(4), 0),
            (0, 0, b"bad", 0),
            (0, 0, [0, 0, 0, 0], 0),
        ):
            with self.subTest(args=args):
                with self.assertRaises(KeymapWriteProtocolError):
                    keymap_set_packet(args[0], args[1], args[2], sublayer=args[3])


if __name__ == "__main__":
    unittest.main()
