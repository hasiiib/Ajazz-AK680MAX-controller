import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from active_profile import PROFILE_GET_OPCODE
from keymap import KEYMAP_GET_OPCODE, KEYMAP_PAGE_COUNT
from live_configuration import ConfigurationReadError, read_configuration_snapshot
from magnetic_settings import MAGNETIC_GET_OPCODE
from protocol import IDENTIFY_OPCODE, identify_packet


class FakeDevice:
    def __init__(self, *, device_id=2255, profile=2, malformed_on=None):
        self.device_id = device_id
        self.profile = profile
        self.malformed_on = malformed_on
        self.last_request = None
        self.sent = []
        self.closed = False
        self.read_count = 0

    def open_path(self, path):
        self.opened_path = path

    def send_feature_report(self, report):
        self.last_request = bytes(report)
        self.sent.append(bytes(report))
        return len(report)

    def get_feature_report(self, report_id, length):
        self.read_count += 1
        payload = self.last_request[1:]
        opcode = payload[0]
        if opcode == IDENTIFY_OPCODE:
            reply = bytearray(64)
            reply[0] = IDENTIFY_OPCODE
            reply[1:5] = self.device_id.to_bytes(4, "little")
            return bytes([0]) + bytes(reply)
        if opcode == PROFILE_GET_OPCODE:
            reply = bytearray(64)
            reply[0] = PROFILE_GET_OPCODE
            reply[1] = self.profile
            return bytes([0]) + bytes(reply)
        if opcode == KEYMAP_GET_OPCODE:
            page = payload[3]
            raw = bytes((page * 64 + offset) & 0xFF for offset in range(64))
            return bytes([0]) + raw
        if opcode == MAGNETIC_GET_OPCODE:
            page = payload[3]
            if self.malformed_on == page:
                return b"bad"
            raw = b"".join((200).to_bytes(2, "little") for _ in range(32))
            return bytes([0]) + raw
        raise AssertionError(f"Unexpected GET opcode 0x{opcode:02X}")

    def close(self):
        self.closed = True


class FakeHid:
    def __init__(self, device):
        self.fake_device = device

    def device(self):
        return self.fake_device


class LiveConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.device = FakeDevice()
        self.hid = FakeHid(self.device)
        self.inventory = [{
            "interface_number": 2,
            "path": "1-1:1.2",
        }]

    def test_reads_profile_complete_base_keymap_and_actuation_column(self):
        with patch("live_configuration.inspect_keyboard_interfaces", return_value=self.inventory):
            snapshot = read_configuration_snapshot(self.hid, sleep=lambda _: None)

        self.assertEqual(snapshot.active_profile, 2)
        self.assertEqual(len(snapshot.keymap_layers), 1)
        self.assertEqual(snapshot.keymap_layers[0].profile, 2)
        self.assertEqual(snapshot.keymap_layers[0].sublayer, 0)
        self.assertEqual(len(snapshot.keymap_layers[0].entries), 128)
        self.assertEqual(len(snapshot.magnetic_columns), 1)
        self.assertEqual(snapshot.magnetic_columns[0].subop, 0)
        self.assertEqual(snapshot.magnetic_columns[0].values, (200,) * 128)
        self.assertTrue(self.device.closed)

        opcodes = [report[1] for report in self.device.sent]
        self.assertEqual(opcodes[0], IDENTIFY_OPCODE)
        self.assertEqual(opcodes[1], PROFILE_GET_OPCODE)
        self.assertEqual(opcodes.count(KEYMAP_GET_OPCODE), KEYMAP_PAGE_COUNT)
        self.assertEqual(opcodes.count(MAGNETIC_GET_OPCODE), 4)
        self.assertEqual(len(opcodes), 14)

    def test_wrong_board_stops_before_any_configuration_get(self):
        self.device.device_id = 1234
        with patch("live_configuration.inspect_keyboard_interfaces", return_value=self.inventory):
            with self.assertRaisesRegex(ConfigurationReadError, "board 2255"):
                read_configuration_snapshot(self.hid, sleep=lambda _: None)

        self.assertEqual([report[1] for report in self.device.sent], [IDENTIFY_OPCODE])
        self.assertTrue(self.device.closed)

    def test_malformed_page_aborts_and_closes_handle_without_retry(self):
        self.device.malformed_on = 2
        with patch("live_configuration.inspect_keyboard_interfaces", return_value=self.inventory):
            with self.assertRaisesRegex(ConfigurationReadError, "malformed Feature response"):
                read_configuration_snapshot(self.hid, sleep=lambda _: None)

        opcodes = [report[1] for report in self.device.sent]
        self.assertEqual(opcodes.count(MAGNETIC_GET_OPCODE), 3)
        self.assertTrue(self.device.closed)

    def test_ambiguous_settings_interface_refuses_to_open_device(self):
        inventory = self.inventory + [{"interface_number": 2, "path": "1-2:1.2"}]
        with patch("live_configuration.inspect_keyboard_interfaces", return_value=inventory):
            with self.assertRaisesRegex(ConfigurationReadError, "exactly one"):
                read_configuration_snapshot(self.hid, sleep=lambda _: None)
        self.assertEqual(self.device.sent, [])
        self.assertTrue(self.device.closed is False)


if __name__ == "__main__":
    unittest.main()
