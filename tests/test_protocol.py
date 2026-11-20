import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from protocol import (
    IdentifyError,
    identify_packet,
    parse_device_id,
    parse_gen2_firmware_revision,
    parse_analog_report,
    identify_exchange_details,
    _feature_payload,
    identify_exchange,
    identify_keyboard,
    paired_keyboard_interfaces,
    _sysfs_details,
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

    def test_parse_analog_report_little_endian_and_slot(self):
        report = bytearray(32)
        report[0] = 0x05
        report[1] = 0x1B
        report[2:4] = (1234).to_bytes(2, "little")
        report[4] = 67
        sample = parse_analog_report(report)
        self.assertEqual(sample.slot, 67)
        self.assertEqual(sample.raw_travel, 1234)

    def test_analog_report_rejects_wrong_length_id_opcode_and_slot(self):
        self.assertIsNone(parse_analog_report(bytes(31)))
        report = bytearray(32)
        report[0] = 0x04
        report[1] = 0x1B
        self.assertIsNone(parse_analog_report(report))
        report[0] = 0x05
        report[1] = 0x10
        self.assertIsNone(parse_analog_report(report))
        report[1] = 0x1B
        report[4] = 128
        self.assertIsNone(parse_analog_report(report))

    def test_parse_gen2_revision_from_identify_metadata(self):
        reply = bytearray(64)
        reply[0] = 0x8F
        reply[7] = 0x02
        reply[8] = 0x01
        self.assertEqual(parse_gen2_firmware_revision(reply), "102")

    def test_gen2_revision_rejects_non_decimal_nibbles_and_zero(self):
        reply = bytearray(64)
        reply[0] = 0x8F
        self.assertIsNone(parse_gen2_firmware_revision(reply))
        reply[7] = 0x0A
        self.assertIsNone(parse_gen2_firmware_revision(reply))

    def test_gen2_revision_rejects_short_or_wrong_opcode(self):
        self.assertIsNone(parse_gen2_firmware_revision(bytes(8)))
        reply = bytearray(64)
        reply[0] = 0x80
        reply[7] = 0x02
        reply[8] = 0x01
        self.assertIsNone(parse_gen2_firmware_revision(reply))

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

    def test_sysfs_details_resolves_hidapi_usb_interface_path(self):
        resolved = (
            "/sys/devices/pci0000:00/0000:00:14.0/usb1/1-1/1-1:1.2/"
            "0003:3151:502D.001A"
        )
        with patch("protocol.os.path.realpath", return_value=resolved):
            details = _sysfs_details("1-1:1.2")
        self.assertEqual(details["sysfs_interface"], 2)
        self.assertEqual(details["usb_parent"], "1-1")
        self.assertEqual(details["sysfs_path"], resolved)

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

    def test_identify_open_error_includes_os_detail_and_closes_device(self):
        class FakeDevice:
            closed = False

            def open_path(self, path):
                raise OSError("Permission denied")

            def close(self):
                self.closed = True

        device = FakeDevice()
        fake_hid = SimpleNamespace(device=lambda: device)
        inventory = [{
            "interface_number": 2,
            "path": "1-1:1.2",
            "usage_page": 0,
            "usage": 0,
            "usb_parent": "1-1",
        }]
        with patch.dict(sys.modules, {"hid": fake_hid}), patch(
            "protocol.inspect_keyboard_interfaces", return_value=inventory
        ):
            with self.assertRaisesRegex(IdentifyError, "Permission denied"):
                identify_keyboard()
        self.assertTrue(device.closed)

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

    def test_identify_exchange_details_preserves_reply_and_revision(self):
        class FakeDevice:
            def send_feature_report(self, report):
                return len(report)

            def get_feature_report(self, report_id, length):
                reply = bytearray(64)
                reply[0] = 0x8F
                reply[1:5] = (2255).to_bytes(4, "little")
                reply[7] = 0x02
                reply[8] = 0x01
                return bytes([0]) + bytes(reply)

        result = identify_exchange_details(FakeDevice(), sleep=lambda _: None)
        self.assertEqual(result.device_id, 2255)
        self.assertEqual(result.firmware_revision, "102")
        self.assertEqual(len(result.raw_reply), 64)
        self.assertEqual(result.raw_reply[7:9], bytes([0x02, 0x01]))

    def test_identify_revision_is_only_exposed_for_verified_gen2_board(self):
        class FakeDevice:
            def send_feature_report(self, report):
                return len(report)

            def get_feature_report(self, report_id, length):
                reply = bytearray(64)
                reply[0] = 0x8F
                reply[1:5] = (1234).to_bytes(4, "little")
                reply[7] = 0x02
                reply[8] = 0x01
                return bytes([0]) + bytes(reply)

        result = identify_exchange_details(FakeDevice(), sleep=lambda _: None)
        self.assertEqual(result.device_id, 1234)
        self.assertIsNone(result.firmware_revision)

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
