import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from device_state import evaluate_connection


def item(interface, parent="/sys/devices/usb1/1-1", path=b"hid-path"):
    return {
        "interface_number": interface,
        "usb_parent": parent,
        "path": path,
    }


class ConnectionStateTests(unittest.TestCase):
    def test_empty_inventory_is_disconnected(self):
        state = evaluate_connection([])
        self.assertEqual(state.status, "disconnected")
        self.assertFalse(state.can_identify)
        self.assertFalse(state.analog_pair_candidate)

    def test_control_and_input_on_same_usb_parent_are_pair_candidate(self):
        state = evaluate_connection([item(2), item(1)])
        self.assertEqual(state.status, "paired-candidate")
        self.assertTrue(state.can_identify)
        self.assertTrue(state.analog_pair_candidate)
        self.assertIn("fresh board-2255 Identify", state.message)

    def test_control_without_input_keeps_read_only_identify_available(self):
        state = evaluate_connection([item(2)])
        self.assertEqual(state.status, "control-only")
        self.assertTrue(state.can_identify)
        self.assertFalse(state.analog_pair_candidate)

    def test_different_usb_parents_do_not_pair_interfaces(self):
        state = evaluate_connection([item(2, "/usb/A"), item(1, "/usb/B")])
        self.assertEqual(state.status, "control-only")
        self.assertTrue(state.can_identify)
        self.assertFalse(state.analog_pair_candidate)

    def test_multiple_control_interfaces_are_ambiguous(self):
        state = evaluate_connection([item(2), item(2)])
        self.assertEqual(state.status, "ambiguous")
        self.assertFalse(state.can_identify)
        self.assertFalse(state.analog_pair_candidate)

    def test_input_without_control_is_not_identify_ready(self):
        state = evaluate_connection([item(1)])
        self.assertEqual(state.status, "input-only")
        self.assertFalse(state.can_identify)
        self.assertFalse(state.analog_pair_candidate)

    def test_boolean_interface_number_and_truthy_non_path_are_rejected(self):
        state = evaluate_connection([
            item(True),
            item(2, path=object()),
            item(1, path=123),
        ])
        self.assertEqual(state.status, "disconnected")
        self.assertFalse(state.can_identify)
        self.assertFalse(state.analog_pair_candidate)

    def test_invalid_inventory_container_or_entry_fails_closed(self):
        for inventory in (None, {}, [None], ["not-a-device-record"]):
            with self.subTest(inventory=inventory):
                state = evaluate_connection(inventory)
                self.assertEqual(state.status, "invalid-inventory")
                self.assertFalse(state.can_identify)
                self.assertFalse(state.analog_pair_candidate)

    def test_non_string_usb_parent_never_pairs_interfaces(self):
        state = evaluate_connection([
            item(2, parent=123),
            item(1, parent=123),
        ])
        self.assertEqual(state.status, "control-only")
        self.assertTrue(state.can_identify)
        self.assertFalse(state.analog_pair_candidate)

    def test_interface_without_hid_path_is_not_usable(self):
        state = evaluate_connection([item(2, path=None), item(1)])
        self.assertEqual(state.status, "input-only")
        self.assertFalse(state.can_identify)


if __name__ == "__main__":
    unittest.main()
