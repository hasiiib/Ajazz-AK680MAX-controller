import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from protocol import IdentifyError, identify_packet, parse_device_id, _feature_payload


class IdentifyProtocolTests(unittest.TestCase):
    def test_identify_packet_is_64_bytes_with_bit7_checksum(self):
        packet = identify_packet()
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[0], 0x8F)
        self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packet[8:], bytes(56))

    def test_parse_device_id_little_endian(self):
        reply = bytearray(64)
        reply[0] = 0x8F
        reply[1:5] = (2255).to_bytes(4, "little")
        self.assertEqual(parse_device_id(reply), 2255)

    def test_reject_wrong_opcode_and_zero_id(self):
        self.assertIsNone(parse_device_id(bytes(64)))
        reply = bytearray(64)
        reply[0] = 0x8F
        self.assertIsNone(parse_device_id(reply))

    def test_reject_documented_refusal_echo(self):
        reply = bytearray(identify_packet())
        reply[3] = 0xFF
        self.assertIsNone(parse_device_id(reply))

    def test_normalize_hidapi_report_id_prefix(self):
        payload = identify_packet()
        self.assertEqual(_feature_payload(bytes([0]) + payload), payload)

    def test_normalize_report_without_prefix(self):
        payload = identify_packet()
        self.assertEqual(_feature_payload(payload), payload)

    def test_reject_short_feature_report(self):
        with self.assertRaises(IdentifyError):
            _feature_payload(b"short")


if __name__ == "__main__":
    unittest.main()
