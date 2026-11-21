import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from keyboard_layout import KeyboardLayoutWidget, infer_layout_slots, load_keyboard_layout


def factory_entries():
    keys = load_keyboard_layout()
    entries = [
        bytes([0x0A, 1, 0, 0]) if key.hid == 1033 else bytes([0, 0, key.hid, 0])
        for key in keys
    ]
    entries.extend([bytes(4)] * (128 - len(entries)))
    return tuple(entries)


class KeyboardLayoutInferenceTests(unittest.TestCase):
    def test_bundled_layout_matches_board_2255_ansi_geometry(self):
        keys = load_keyboard_layout()
        self.assertEqual(len(keys), 68)
        self.assertEqual(keys[0].label, "Esc")
        self.assertEqual(keys[0].hid, 41)
        self.assertEqual(keys[-1].label, "Right")
        self.assertEqual(keys[-1].hid, 79)
        self.assertEqual(len({key.hid for key in keys}), 68)

    def test_factory_hid_assignments_infer_all_physical_slots(self):
        entries = factory_entries()
        result = infer_layout_slots(entries)
        self.assertTrue(result.complete)
        self.assertEqual(result.missing_hids, ())
        self.assertEqual(result.duplicate_hids, ())
        self.assertEqual(len(result.slot_by_hid), 68)
        keys = load_keyboard_layout()
        for slot, key in enumerate(keys, start=1):
            self.assertEqual(result.slot_by_hid[key.hid], slot)

    def test_remapped_or_missing_factory_usage_fails_closed(self):
        entries = list(factory_entries())
        entries[0] = bytes(4)
        result = infer_layout_slots(tuple(entries))
        self.assertFalse(result.complete)
        self.assertIn(41, result.missing_hids)
        self.assertNotIn(41, result.slot_by_hid)

    def test_duplicate_factory_usage_is_not_assigned_to_a_physical_slot(self):
        entries = list(factory_entries())
        entries[68] = entries[0]
        result = infer_layout_slots(tuple(entries))
        self.assertFalse(result.complete)
        self.assertIn(41, result.duplicate_hids)
        self.assertNotIn(41, result.slot_by_hid)

    def test_inference_rejects_incomplete_or_mutable_entries(self):
        with self.assertRaises(ValueError):
            infer_layout_slots(tuple(bytes(4) for _ in range(127)))
        entries = list(factory_entries())
        entries[0] = bytearray(4)
        with self.assertRaises(ValueError):
            infer_layout_slots(tuple(entries))


try:
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class KeyboardLayoutWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_widget_displays_inferred_slots_only_when_complete(self):
        widget = KeyboardLayoutWidget()
        self.assertIn("no keymap loaded", widget.mapping_message)
        widget.set_keymap_entries(factory_entries())
        self.assertIn("68 physical slots inferred", widget.mapping_message)
        widget.resize(760, 236)
        widget.show()
        self.app.processEvents()
        widget.clear()
        self.assertIn("no keymap loaded", widget.mapping_message)
        widget.close()


if __name__ == "__main__":
    unittest.main()
