import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from protocol import (
    IdentifyError,
    identify_packet,
    parse_device_id,
    _feature_payload,
    identify_exchange,
    paired_keyboard_interfaces,
)


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

    def test_pair_requires_unique_interfaces_and_same_usb_parent(self):
        control = {
            "interface_number": 2,
            "usb_parent": "1-1",
            "path": "/dev/hidraw4",
        }
        analog = {
            "interface_number": 1,
            "usb_parent": "1-1",
            "path": "/dev/hidraw3",
        }
        self.assertEqual(
            paired_keyboard_interfaces([control, analog]), (control, analog)
        )
        other_device = dict(analog, usb_parent="1-2")
        self.assertIsNone(paired_keyboard_interfaces([control, other_device]))
        self.assertIsNone(
            paired_keyboard_interfaces([control, analog, dict(control)])
        )

    def test_identify_exchange_sends_once_then_polls_for_reply(self):
        class FakeDevice:
            def __init__(self):
                self.sent = []
                self.reads = 0

            def send_feature_report(self, report):
                self.sent.append(report)
                return len(report)

            def get_feature_report(self, report_id, length):
                self.reads += 1
                if self.reads == 1:
                    return bytes([0]) + bytes(64)
                reply = bytearray(64)
                reply[0] = 0x8F
                reply[1:5] = (2255).to_bytes(4, "little")
                return bytes([0]) + bytes(reply)

        device = FakeDevice()
        delays = []
        result = identify_exchange(device, sleep=delays.append)
        self.assertEqual(result, 2255)
        self.assertEqual(len(device.sent), 1)
        self.assertEqual(len(device.sent[0]), 65)
        self.assertEqual(device.sent[0][0], 0)
        self.assertEqual(device.sent[0][1:], identify_packet())
        self.assertEqual(device.reads, 2)
        self.assertEqual(delays, [0.010, 0.010, 0.010])

    def test_identify_exchange_does_not_resend_on_timeout(self):
        class SilentDevice:
            def __init__(self):
                self.sent = 0

            def send_feature_report(self, report):
                self.sent += 1
                return len(report)

            def get_feature_report(self, report_id, length):
                return bytes([0]) + bytes(64)

        device = SilentDevice()
        with self.assertRaises(IdentifyError):
            identify_exchange(device, sleep=lambda _: None)
        self.assertEqual(device.sent, 1)


if __name__ == "__main__":
    unittest.main()
