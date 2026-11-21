import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from capture_led_parameters import CaptureError, capture_once, main
from lighting import led_params_get_packet
from protocol import identify_packet


def identify_reply(device_id=2255):
    reply = bytearray(64)
    reply[0] = 0x8F
    reply[1:5] = device_id.to_bytes(4, "little")
    return bytes([0]) + bytes(reply)


def led_reply():
    reply = bytearray(64)
    reply[0] = 0x87
    reply[1:8] = bytes((3, 2, 4, 0x07, 10, 20, 30))
    return bytes([0]) + bytes(reply)


class FakeDevice:
    def __init__(self, device_id=2255, read_error=False, send_result=None):
        self.responses = [identify_reply(device_id), led_reply()]
        self.sent = []
        self.reads = 0
        self.closed = False
        self.read_error = read_error
        self.send_result = send_result

    def open_path(self, path):
        self.path = path

    def send_feature_report(self, report):
        self.sent.append(bytes(report))
        return len(report) if self.send_result is None else self.send_result

    def get_feature_report(self, report_id, length):
        self.reads += 1
        if self.read_error and self.reads == 2:
            raise OSError("disconnected")
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class FakeHid:
    def __init__(self, device, devices=None):
        self.fake_device = device
        self.devices = devices or [{"interface_number": 2, "path": "control"}]
        self.opens = 0

    def enumerate(self, vendor_id, product_id):
        self.ids = (vendor_id, product_id)
        return self.devices

    def device(self):
        self.opens += 1
        return self.fake_device


class LedCaptureTests(unittest.TestCase):
    def test_one_led_get_is_sent_after_same_handle_identify(self):
        device = FakeDevice()
        hid = FakeHid(device)
        raw, led, sent = capture_once(hid, sleep=lambda _: None)
        self.assertEqual(sent, 65)
        self.assertEqual(raw, led_reply())
        self.assertEqual((led.mode, led.speed, led.brightness), (3, 2, 4))
        self.assertEqual(led.rgb, (10, 20, 30))
        self.assertEqual(device.sent, [bytes([0]) + identify_packet(), bytes([0]) + led_params_get_packet()])
        self.assertEqual(hid.ids, (0x3151, 0x502D))
        self.assertEqual(hid.opens, 1)
        self.assertTrue(device.closed)

    def test_wrong_board_stops_before_led_get(self):
        device = FakeDevice(device_id=123)
        with self.assertRaisesRegex(CaptureError, "board ID 2255"):
            capture_once(FakeHid(device), sleep=lambda _: None)
        self.assertEqual(len(device.sent), 1)
        self.assertTrue(device.closed)

    def test_ambiguous_interface_stops_before_open(self):
        device = FakeDevice()
        hid = FakeHid(device, [
            {"interface_number": 2, "path": "a"},
            {"interface_number": 2, "path": "b"},
        ])
        with self.assertRaisesRegex(CaptureError, "exactly one"):
            capture_once(hid, sleep=lambda _: None)
        self.assertEqual(hid.opens, 0)
        self.assertEqual(device.sent, [])

    def test_failed_read_is_not_retried_and_handle_closes(self):
        device = FakeDevice(read_error=True)
        with self.assertRaisesRegex(CaptureError, "no retry attempted"):
            capture_once(FakeHid(device), sleep=lambda _: None)
        self.assertEqual(len(device.sent), 2)
        self.assertEqual(device.reads, 2)
        self.assertTrue(device.closed)

    def test_partial_send_is_not_retried_or_read(self):
        device = FakeDevice(send_result=64)
        with self.assertRaisesRegex(CaptureError, "no retry attempted"):
            capture_once(FakeHid(device), sleep=lambda _: None)
        self.assertEqual(len(device.sent), 2)
        self.assertEqual(device.reads, 1)
        self.assertTrue(device.closed)

    def test_cli_requires_explicit_confirmation(self):
        with self.assertRaises(SystemExit) as raised:
            main([])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
