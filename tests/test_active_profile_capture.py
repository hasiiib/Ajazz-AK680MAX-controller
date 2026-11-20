import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from capture_active_profile import CaptureError, capture_once


class FakeDevice:
    def __init__(self, response=None, send_result=65):
        self.response = response if response is not None else bytes([0x84, 2]) + bytes(62)
        self.send_result = send_result
        self.opened_path = None
        self.sent = []
        self.read_calls = []
        self.closed = False

    def open_path(self, path):
        self.opened_path = path

    def send_feature_report(self, report):
        self.sent.append(bytes(report))
        return self.send_result

    def get_feature_report(self, report_id, length):
        self.read_calls.append((report_id, length))
        return self.response

    def close(self):
        self.closed = True


class FakeHid:
    def __init__(self, devices, device):
        self.devices = devices
        self.fake_device = device
        self.device_calls = 0
        self.enumerate_calls = 0

    def enumerate(self, vendor_id, product_id):
        self.enumerate_calls += 1
        self.asserted_ids = (vendor_id, product_id)
        return self.devices

    def device(self):
        self.device_calls += 1
        return self.fake_device


class ActiveProfileCaptureTests(unittest.TestCase):
    def setUp(self):
        self.device = FakeDevice()
        self.hid = FakeHid(
            [{"interface_number": 2, "path": "fake-interface-2"}],
            self.device,
        )
        self.identity = lambda: SimpleNamespace(device_id=2255)
        self.sleeps = []

    def test_sends_one_exact_read_only_get_and_preserves_response(self):
        raw, sent = capture_once(
            self.hid,
            identify=self.identity,
            sleep=self.sleeps.append,
        )
        self.assertEqual(raw, self.device.response)
        self.assertEqual(sent, 65)
        self.assertEqual(len(self.device.sent), 1)
        self.assertEqual(len(self.device.sent[0]), 65)
        self.assertEqual(self.device.sent[0][0], 0)
        self.assertEqual(self.device.sent[0][1], 0x84)
        self.assertEqual(self.device.sent[0][8], 0x7B)
        self.assertEqual(self.device.read_calls, [(0, 65)])
        self.assertEqual(self.sleeps, [0.010])
        self.assertTrue(self.device.closed)
        self.assertEqual(self.hid.asserted_ids, (0x3151, 0x502D))

    def test_wrong_board_id_sends_nothing_and_does_not_enumerate(self):
        with self.assertRaisesRegex(CaptureError, "board ID 2255"):
            capture_once(
                self.hid,
                identify=lambda: SimpleNamespace(device_id=1234),
                sleep=self.sleeps.append,
            )
        self.assertEqual(self.hid.enumerate_calls, 0)
        self.assertEqual(self.hid.device_calls, 0)
        self.assertEqual(self.device.sent, [])

    def test_ambiguous_control_interface_is_rejected_before_open(self):
        self.hid.devices.append({"interface_number": 2, "path": "other-interface-2"})
        with self.assertRaisesRegex(CaptureError, "exactly one"):
            capture_once(self.hid, identify=self.identity, sleep=self.sleeps.append)
        self.assertEqual(self.hid.device_calls, 0)
        self.assertEqual(self.device.sent, [])

    def test_partial_send_is_not_retried_or_read(self):
        self.device.send_result = 64
        with self.assertRaisesRegex(CaptureError, "no retry attempted"):
            capture_once(self.hid, identify=self.identity, sleep=self.sleeps.append)
        self.assertEqual(len(self.device.sent), 1)
        self.assertEqual(self.device.read_calls, [])
        self.assertTrue(self.device.closed)

    def test_imported_helper_does_not_perform_device_io(self):
        self.assertEqual(self.hid.enumerate_calls, 0)
        self.assertEqual(self.hid.device_calls, 0)
        self.assertEqual(self.device.sent, [])


if __name__ == "__main__":
    unittest.main()
