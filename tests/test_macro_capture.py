import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from capture_macro_page import CaptureError, capture_once, main
from macros import macro_get_packet
from protocol import identify_packet


def identify_reply():
    reply = bytearray(64)
    reply[0] = 0x8F
    reply[1:5] = (2255).to_bytes(4, "little")
    return bytes([0]) + bytes(reply)


def macro_reply():
    return bytes([0]) + bytes(range(64))


class FakeDevice:
    def __init__(self, *, device_id=2255, read_error=False):
        self.responses = [identify_reply(), macro_reply()]
        self.device_id = device_id
        self.read_error = read_error
        self.sent = []
        self.read_calls = []
        self.closed = False
        self.opened_path = None

    def open_path(self, path):
        self.opened_path = path

    def send_feature_report(self, report):
        self.sent.append(bytes(report))
        return len(report)

    def get_feature_report(self, report_id, length):
        self.read_calls.append((report_id, length))
        if self.read_error and len(self.read_calls) == 2:
            raise OSError("synthetic read failure")
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class FakeHid:
    def __init__(self, device):
        self.fake_device = device
        self.device_calls = 0

    def enumerate(self, vendor_id, product_id):
        self.ids = (vendor_id, product_id)
        return [{"interface_number": 2, "path": "fake-interface-2"}]

    def device(self):
        self.device_calls += 1
        return self.fake_device


class MacroCaptureTests(unittest.TestCase):
    def setUp(self):
        self.device = FakeDevice()
        self.hid = FakeHid(self.device)
        self.delays = []

    def identify(self, device, sleep):
        sleep(0.010)
        sent = device.send_feature_report(bytes([0]) + identify_packet())
        if sent != 65:
            raise RuntimeError("synthetic identify send failure")
        sleep(0.010)
        device.get_feature_report(0, 65)
        return SimpleNamespace(device_id=self.device.device_id)

    def test_sends_identify_then_exactly_one_selected_macro_get(self):
        raw, sent = capture_once(
            self.hid, identify=self.identify, sleep=self.delays.append,
            slot=7, page=2,
        )
        self.assertEqual(
            self.device.sent,
            [bytes([0]) + identify_packet(), bytes([0]) + macro_get_packet(7, 2)],
        )
        self.assertEqual(self.device.read_calls, [(0, 65), (0, 65)])
        self.assertEqual(raw, macro_reply())
        self.assertEqual(sent, 65)
        self.assertEqual(self.delays, [0.010, 0.010, 0.010, 0.010])
        self.assertEqual(self.hid.ids, (0x3151, 0x502D))
        self.assertEqual(self.device.opened_path, b"fake-interface-2")
        self.assertTrue(self.device.closed)

    def test_invalid_slot_or_page_is_rejected_before_device_open(self):
        for selection in ({"slot": 50}, {"slot": -1}, {"page": 4}):
            with self.subTest(selection=selection):
                device = FakeDevice()
                hid = FakeHid(device)
                with self.assertRaisesRegex(CaptureError, "Invalid macro GET selection"):
                    capture_once(
                        hid, identify=self.identify, sleep=lambda _: None, **selection
                    )
                self.assertEqual(hid.device_calls, 0)
                self.assertEqual(device.sent, [])

    def test_wrong_board_id_stops_before_macro_get(self):
        self.device.device_id = 1234
        with self.assertRaisesRegex(CaptureError, "board ID 2255"):
            capture_once(self.hid, identify=self.identify, sleep=lambda _: None)
        self.assertEqual(len(self.device.sent), 1)
        self.assertEqual(self.device.read_calls, [(0, 65)])
        self.assertTrue(self.device.closed)

    def test_feature_read_failure_is_not_retried(self):
        self.device.read_error = True
        with self.assertRaisesRegex(
            CaptureError, r"0x8B GET was sent successfully \(65/65 bytes\)"
        ):
            capture_once(self.hid, identify=self.identify, sleep=lambda _: None)
        self.assertEqual(len(self.device.sent), 2)
        self.assertEqual(len(self.device.read_calls), 2)
        self.assertTrue(self.device.closed)

    def test_ambiguous_interface_stops_before_open(self):
        self.hid.enumerate = lambda *_: [
            {"interface_number": 2, "path": "one"},
            {"interface_number": 2, "path": "two"},
        ]
        with self.assertRaisesRegex(CaptureError, "exactly one"):
            capture_once(self.hid, identify=self.identify, sleep=lambda _: None)
        self.assertEqual(self.hid.device_calls, 0)
        self.assertEqual(self.device.sent, [])

    def test_cli_requires_explicit_confirmation(self):
        with self.assertRaises(SystemExit) as raised:
            main([])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(self.hid.device_calls, 0)
        self.assertEqual(self.device.sent, [])

    def test_partial_get_send_is_not_retried_or_read(self):
        original_send = self.device.send_feature_report

        def partial_send(report):
            sent = original_send(report)
            return sent - 1 if len(self.device.sent) == 2 else sent

        self.device.send_feature_report = partial_send
        with self.assertRaisesRegex(CaptureError, "no retry attempted"):
            capture_once(self.hid, identify=self.identify, sleep=lambda _: None)
        self.assertEqual(len(self.device.sent), 2)
        self.assertEqual(self.device.read_calls, [(0, 65)])
        self.assertTrue(self.device.closed)


if __name__ == "__main__":
    unittest.main()
