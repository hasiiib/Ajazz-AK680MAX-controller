import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from active_profile import active_profile_get_packet
from capture_active_profile import CaptureError, capture_once, main, _safe_identify_failure
from protocol import identify_packet


def identify_reply(device_id=2255):
    reply = bytearray(64)
    reply[0] = 0x8F
    reply[1:5] = device_id.to_bytes(4, "little")
    return bytes([0]) + bytes(reply)


def profile_reply(profile=2):
    reply = bytearray(64)
    reply[0] = 0x84
    reply[1] = profile
    return bytes([0]) + bytes(reply)


class FakeDevice:
    def __init__(
        self,
        *,
        device_id=2255,
        profile=2,
        send_results=None,
        read_error_on=None,
        open_error=False,
    ):
        self.identify_response = identify_reply(device_id)
        self.profile_response = profile_reply(profile)
        self.responses = [self.identify_response, self.profile_response]
        self.send_results = list(send_results or [])
        self.read_error_on = read_error_on
        self.open_error = open_error
        self.opened_path = None
        self.sent = []
        self.read_calls = []
        self.closed = False

    def open_path(self, path):
        self.opened_path = path
        if self.open_error:
            raise OSError("permission denied")

    def send_feature_report(self, report):
        self.sent.append(bytes(report))
        if self.send_results:
            return self.send_results.pop(0)
        return len(report)

    def get_feature_report(self, report_id, length):
        self.read_calls.append((report_id, length))
        if self.read_error_on == len(self.read_calls):
            raise OSError("device disconnected")
        return self.responses.pop(0) if self.responses else b""

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
        self.sleeps = []

    def test_identify_and_one_profile_get_use_the_same_handle(self):
        raw, sent = capture_once(
            self.hid,
            sleep=self.sleeps.append,
        )
        self.assertEqual(raw, self.device.profile_response)
        self.assertEqual(sent, 65)
        self.assertEqual(
            self.device.sent,
            [bytes([0]) + identify_packet(), bytes([0]) + active_profile_get_packet()],
        )
        self.assertEqual(self.device.read_calls, [(0, 65), (0, 65)])
        self.assertEqual(self.sleeps, [0.010, 0.010, 0.010, 0.010])
        self.assertEqual(self.hid.device_calls, 1)
        self.assertEqual(self.hid.enumerate_calls, 1)
        self.assertEqual(self.hid.asserted_ids, (0x3151, 0x502D))
        self.assertEqual(self.device.opened_path, b"fake-interface-2")
        self.assertTrue(self.device.closed)

    def test_wrong_board_id_sends_identify_only_and_never_sends_profile_get(self):
        self.device = FakeDevice(device_id=1234)
        self.hid.fake_device = self.device
        with self.assertRaisesRegex(CaptureError, "board ID 2255"):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(self.device.sent, [bytes([0]) + identify_packet()])
        self.assertEqual(self.device.read_calls, [(0, 65)])
        self.assertEqual(self.hid.device_calls, 1)
        self.assertTrue(self.device.closed)

    def test_ambiguous_control_interface_is_rejected_before_open(self):
        self.hid.devices.append({"interface_number": 2, "path": "other-interface-2"})
        with self.assertRaisesRegex(CaptureError, "exactly one"):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(self.hid.device_calls, 0)
        self.assertEqual(self.device.sent, [])

    def test_partial_profile_send_is_not_retried_or_read(self):
        self.device.send_results = [65, 64]
        with self.assertRaisesRegex(CaptureError, "no retry attempted"):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(len(self.device.sent), 2)
        self.assertEqual(self.device.sent[0], bytes([0]) + identify_packet())
        self.assertEqual(self.device.sent[1], bytes([0]) + active_profile_get_packet())
        self.assertEqual(self.device.read_calls, [(0, 65)])
        self.assertTrue(self.device.closed)

    def test_cli_requires_explicit_confirmation_before_any_device_access(self):
        with self.assertRaises(SystemExit) as raised:
            main([])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(self.hid.enumerate_calls, 0)
        self.assertEqual(self.device.sent, [])

    def test_identify_failure_message_is_actionable_without_exposing_paths(self):
        detail = _safe_identify_failure(
            RuntimeError("Could not open /dev/hidraw7. serial_number=UNIQUE123")
        )
        self.assertIn("permissions", detail)
        self.assertNotIn("/dev/hidraw7", detail)
        self.assertNotIn("UNIQUE123", detail)

    def test_nested_identify_error_preserves_safe_cause_and_redacts_identity(self):
        cause = OSError("hidapi read error at /dev/hidraw9 serial_number=UNIQUE-ABC")
        wrapped = RuntimeError("IdentifyError: transport failed")
        wrapped.__cause__ = cause
        detail = _safe_identify_failure(wrapped)
        self.assertIn("transport failed", detail)
        self.assertIn("hidapi read error", detail)
        self.assertNotIn("/dev/hidraw9", detail)
        self.assertNotIn("UNIQUE-ABC", detail)

    def test_identify_timeout_has_distinct_safe_diagnostic(self):
        detail = _safe_identify_failure(
            RuntimeError("The keyboard did not return a valid 0x8F Identify reply.")
        )
        self.assertIn("within the timeout", detail)

    def test_identify_failure_stops_before_profile_get_and_closes_handle(self):
        self.device.responses[0] = bytes(63)
        with self.assertRaisesRegex(CaptureError, "Fresh read-only Identify failed"):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(self.device.sent, [bytes([0]) + identify_packet()])
        self.assertEqual(self.device.read_calls, [(0, 65)])
        self.assertTrue(self.device.closed)

    def test_profile_read_accepts_hidapi_list_and_tuple_results(self):
        for container in (list, tuple):
            with self.subTest(container=container.__name__):
                device = FakeDevice()
                device.responses[1] = container(device.profile_response)
                hid = FakeHid(
                    [{"interface_number": 2, "path": "fake-interface-2"}],
                    device,
                )
                raw, _ = capture_once(hid, sleep=lambda _: None)
                self.assertEqual(raw, device.profile_response)
                self.assertEqual(len(device.sent), 2)
                self.assertTrue(device.closed)

    def test_profile_read_rejects_invalid_sequence_values_without_retry(self):
        self.device.responses[1] = list(self.device.profile_response)
        self.device.responses[1][-1] = 256
        with self.assertRaisesRegex(CaptureError, "no retry attempted"):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(len(self.device.sent), 2)
        self.assertEqual(len(self.device.read_calls), 2)
        self.assertTrue(self.device.closed)

    def test_profile_read_failure_reports_confirmed_send_and_exception_type(self):
        self.device.read_error_on = 2
        with self.assertRaisesRegex(
            CaptureError, r"0x84 GET was sent successfully \(65/65 bytes\).*OSError"
        ):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(len(self.device.sent), 2)
        self.assertEqual(len(self.device.read_calls), 2)
        self.assertTrue(self.device.closed)

    def test_profile_read_unsupported_return_reports_safe_type_and_length(self):
        self.device.responses[1] = None
        with self.assertRaisesRegex(
            CaptureError, r"0x84 GET was sent successfully \(65/65 bytes\).*type=NoneType"
        ):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(len(self.device.sent), 2)
        self.assertEqual(len(self.device.read_calls), 2)
        self.assertTrue(self.device.closed)

    def test_profile_read_invalid_sequence_reports_type_without_payload(self):
        self.device.responses[1] = [0, 0, 256]
        with self.assertRaisesRegex(
            CaptureError, r"type=list, length=3, invalid byte elements"
        ):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(len(self.device.sent), 2)
        self.assertEqual(len(self.device.read_calls), 2)
        self.assertTrue(self.device.closed)

    def test_open_failure_closes_handle_without_sending_a_command(self):
        self.device.open_error = True
        with self.assertRaisesRegex(CaptureError, "One-shot 0x84 capture failed"):
            capture_once(self.hid, sleep=self.sleeps.append)
        self.assertEqual(self.device.sent, [])
        self.assertEqual(self.device.read_calls, [])
        self.assertTrue(self.device.closed)

    def test_imported_helper_does_not_perform_device_io(self):
        self.assertEqual(self.hid.enumerate_calls, 0)
        self.assertEqual(self.hid.device_calls, 0)
        self.assertEqual(self.device.sent, [])


if __name__ == "__main__":
    unittest.main()
