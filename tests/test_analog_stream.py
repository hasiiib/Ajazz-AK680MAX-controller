import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from analog_stream import (
    AnalogStreamError,
    AnalogStreamSession,
    stream_control_packet,
)


class StreamPacketTests(unittest.TestCase):
    def test_start_and_stop_packets_use_bit7_checksum(self):
        for enabled, flag in ((True, 1), (False, 0)):
            packet = stream_control_packet(enabled)
            self.assertEqual(len(packet), 64)
            self.assertEqual(packet[0], 0x1B)
            self.assertEqual(packet[1], flag)
            self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
            self.assertEqual(packet[8:], bytes(56))


class AnalogStreamSessionTests(unittest.TestCase):
    def test_session_identifies_pairs_opens_streams_reads_and_stops(self):
        class FakeDevice:
            def __init__(self, reports=None):
                self.reports = list(reports or [])
                self.opened = None
                self.sent = []
                self.closed = False

            def open_path(self, path):
                self.opened = path

            def send_feature_report(self, report):
                self.sent.append(bytes(report))
                return len(report)

            def read(self, length, timeout):
                return self.reports.pop(0) if self.reports else []

            def close(self):
                self.closed = True

        analog = bytes([0x05, 0x1B, 0xD2, 0x04, 7]) + bytes(27)
        control_device = FakeDevice()
        input_device = FakeDevice([list(analog)])
        devices = iter([control_device, input_device])
        fake_hid = SimpleNamespace(
            enumerate=lambda vendor, product: [],
            device=lambda: next(devices),
        )
        inventory = [
            {"interface_number": 2, "path": "1-1:1.2", "usb_parent": "1-1"},
            {"interface_number": 1, "path": "1-1:1.1", "usb_parent": "1-1"},
        ]
        identity = SimpleNamespace(device_id=2255)
        session = AnalogStreamSession(hid_module=fake_hid)

        with patch("analog_stream.identify_keyboard_details", return_value=identity), patch(
            "analog_stream.inspect_keyboard_interfaces", return_value=inventory
        ):
            session.start()
            self.assertTrue(session.active)
            self.assertEqual(control_device.opened, b"1-1:1.2")
            self.assertEqual(input_device.opened, b"1-1:1.1")
            self.assertEqual(control_device.sent[0][1:], stream_control_packet(True))

            samples = session.poll()
            self.assertEqual(len(samples), 1)
            self.assertEqual(samples[0].slot, 7)
            self.assertEqual(samples[0].raw_travel, 1234)

            session.stop()

        self.assertFalse(session.active)
        self.assertEqual(control_device.sent[1][1:], stream_control_packet(False))
        self.assertTrue(control_device.closed)
        self.assertTrue(input_device.closed)

    def test_unpaired_interfaces_refuse_before_opening(self):
        created = []
        class FakeDevice:
            def __init__(self):
                self.open_calls = 0
                created.append(self)
            def open_path(self, path):
                self.open_calls += 1
            def close(self):
                pass

        fake_hid = SimpleNamespace(device=FakeDevice)
        inventory = [
            {"interface_number": 2, "path": "1-1:1.2", "usb_parent": "1-1"},
            {"interface_number": 1, "path": "1-2:1.1", "usb_parent": "1-2"},
        ]
        session = AnalogStreamSession(hid_module=fake_hid)
        with patch(
            "analog_stream.identify_keyboard_details",
            return_value=SimpleNamespace(device_id=2255),
        ), patch("analog_stream.inspect_keyboard_interfaces", return_value=inventory):
            with self.assertRaises(AnalogStreamError):
                session.start()
        self.assertEqual(created, [])

    def test_stop_failure_still_closes_handles(self):
        class FakeDevice:
            def __init__(self, fail_stop=False):
                self.fail_stop = fail_stop
                self.sent = 0
                self.closed = False
            def open_path(self, path):
                pass
            def send_feature_report(self, report):
                self.sent += 1
                if self.fail_stop and self.sent == 2:
                    raise OSError("disconnected")
                return len(report)
            def read(self, length, timeout):
                return []
            def close(self):
                self.closed = True

        control = FakeDevice(fail_stop=True)
        input_device = FakeDevice()
        devices = iter([control, input_device])
        fake_hid = SimpleNamespace(device=lambda: next(devices))
        inventory = [
            {"interface_number": 2, "path": "1-1:1.2", "usb_parent": "1-1"},
            {"interface_number": 1, "path": "1-1:1.1", "usb_parent": "1-1"},
        ]
        session = AnalogStreamSession(hid_module=fake_hid)
        with patch(
            "analog_stream.identify_keyboard_details",
            return_value=SimpleNamespace(device_id=2255),
        ), patch("analog_stream.inspect_keyboard_interfaces", return_value=inventory):
            session.start()
            with self.assertRaises(AnalogStreamError):
                session.stop()
        self.assertFalse(session.active)
        self.assertTrue(control.closed)
        self.assertTrue(input_device.closed)

    def test_wrong_board_id_refuses_before_opening_any_interface(self):
        class FakeDevice:
            def __init__(self):
                self.open_calls = 0

            def open_path(self, path):
                self.open_calls += 1

            def close(self):
                pass

        device = FakeDevice()
        fake_hid = SimpleNamespace(device=lambda: device)
        session = AnalogStreamSession(hid_module=fake_hid)

        with patch(
            "analog_stream.identify_keyboard_details",
            return_value=SimpleNamespace(device_id=9999),
        ):
            with self.assertRaises(AnalogStreamError):
                session.start()

        self.assertEqual(device.open_calls, 0)


    def test_enable_send_without_length_confirmation_is_rejected(self):
        class FakeDevice:
            def __init__(self):
                self.sent = []
                self.closed = False
            def open_path(self, path):
                pass
            def send_feature_report(self, report):
                self.sent.append(bytes(report))
                return None
            def close(self):
                self.closed = True

        control = FakeDevice()
        input_device = FakeDevice()
        devices = iter([control, input_device])
        fake_hid = SimpleNamespace(device=lambda: next(devices))
        inventory = [
            {"interface_number": 2, "path": "1-1:1.2", "usb_parent": "1-1"},
            {"interface_number": 1, "path": "1-1:1.1", "usb_parent": "1-1"},
        ]
        session = AnalogStreamSession(hid_module=fake_hid)
        with patch(
            "analog_stream.identify_keyboard_details",
            return_value=SimpleNamespace(device_id=2255),
        ), patch("analog_stream.inspect_keyboard_interfaces", return_value=inventory):
            with self.assertRaisesRegex(AnalogStreamError, "incomplete analog stream"):
                session.start()

        self.assertFalse(session.active)
        self.assertEqual(len(control.sent), 2)
        self.assertTrue(control.closed)
        self.assertTrue(input_device.closed)

    def test_partial_enable_send_triggers_best_effort_stop_and_cleanup(self):
        class FakeDevice:
            def __init__(self, partial_first=False):
                self.partial_first = partial_first
                self.sent = []
                self.closed = False
            def open_path(self, path):
                pass
            def send_feature_report(self, report):
                self.sent.append(bytes(report))
                if self.partial_first and len(self.sent) == 1:
                    return len(report) - 1
                return len(report)
            def close(self):
                self.closed = True

        control = FakeDevice(partial_first=True)
        input_device = FakeDevice()
        devices = iter([control, input_device])
        fake_hid = SimpleNamespace(device=lambda: next(devices))
        inventory = [
            {"interface_number": 2, "path": "1-1:1.2", "usb_parent": "1-1"},
            {"interface_number": 1, "path": "1-1:1.1", "usb_parent": "1-1"},
        ]
        session = AnalogStreamSession(hid_module=fake_hid)
        with patch(
            "analog_stream.identify_keyboard_details",
            return_value=SimpleNamespace(device_id=2255),
        ), patch("analog_stream.inspect_keyboard_interfaces", return_value=inventory):
            with self.assertRaisesRegex(AnalogStreamError, "incomplete analog stream"):
                session.start()

        self.assertFalse(session.active)
        self.assertEqual(len(control.sent), 2)
        self.assertEqual(control.sent[0][2], 1)
        self.assertEqual(control.sent[1][2], 0)
        self.assertTrue(control.closed)
        self.assertTrue(input_device.closed)

    def test_input_open_failure_closes_both_handles_without_enabling_stream(self):
        class FakeDevice:
            def __init__(self, fail_open=False):
                self.fail_open = fail_open
                self.closed = False
                self.sent = []
            def open_path(self, path):
                if self.fail_open:
                    raise OSError("input interface unavailable")
            def send_feature_report(self, report):
                self.sent.append(bytes(report))
                return len(report)
            def close(self):
                self.closed = True

        control = FakeDevice()
        input_device = FakeDevice(fail_open=True)
        devices = iter([control, input_device])
        fake_hid = SimpleNamespace(device=lambda: next(devices))
        inventory = [
            {"interface_number": 2, "path": "1-1:1.2", "usb_parent": "1-1"},
            {"interface_number": 1, "path": "1-1:1.1", "usb_parent": "1-1"},
        ]
        session = AnalogStreamSession(hid_module=fake_hid)
        with patch(
            "analog_stream.identify_keyboard_details",
            return_value=SimpleNamespace(device_id=2255),
        ), patch("analog_stream.inspect_keyboard_interfaces", return_value=inventory):
            with self.assertRaises(AnalogStreamError):
                session.start()

        self.assertFalse(session.active)
        self.assertEqual(control.sent, [])
        self.assertTrue(control.closed)
        self.assertTrue(input_device.closed)

    def test_enable_failure_attempts_best_effort_stop_and_closes_handles(self):
        class FakeDevice:
            def __init__(self, fail_enable=False):
                self.fail_enable = fail_enable
                self.sent = []
                self.closed = False
            def open_path(self, path):
                pass
            def send_feature_report(self, report):
                self.sent.append(bytes(report))
                if self.fail_enable and len(self.sent) == 1:
                    raise OSError("write outcome uncertain")
                return len(report)
            def close(self):
                self.closed = True

        control = FakeDevice(fail_enable=True)
        input_device = FakeDevice()
        devices = iter([control, input_device])
        fake_hid = SimpleNamespace(device=lambda: next(devices))
        inventory = [
            {"interface_number": 2, "path": "1-1:1.2", "usb_parent": "1-1"},
            {"interface_number": 1, "path": "1-1:1.1", "usb_parent": "1-1"},
        ]
        session = AnalogStreamSession(hid_module=fake_hid)
        with patch(
            "analog_stream.identify_keyboard_details",
            return_value=SimpleNamespace(device_id=2255),
        ), patch("analog_stream.inspect_keyboard_interfaces", return_value=inventory):
            with self.assertRaises(AnalogStreamError):
                session.start()

        self.assertFalse(session.active)
        self.assertEqual(len(control.sent), 2)
        self.assertEqual(control.sent[0][2], 1)
        self.assertEqual(control.sent[1][2], 0)
        self.assertTrue(control.closed)
        self.assertTrue(input_device.closed)


if __name__ == "__main__":
    unittest.main()
