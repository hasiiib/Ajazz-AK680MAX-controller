import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from keyboard_layout import KeyboardLayoutWidget, assess_factory_usage_coverage, load_keyboard_layout


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

    def test_factory_hid_usage_coverage_does_not_claim_physical_slots(self):
        entries = factory_entries()
        result = assess_factory_usage_coverage(entries)
        self.assertTrue(result.all_factory_usages_present_once)
        self.assertEqual(result.missing_hids, ())
        self.assertEqual(result.duplicate_hids, ())

    def test_remapped_or_missing_factory_usage_fails_closed(self):
        entries = list(factory_entries())
        entries[0] = bytes(4)
        result = assess_factory_usage_coverage(tuple(entries))
        self.assertFalse(result.all_factory_usages_present_once)
        self.assertIn(41, result.missing_hids)

    def test_duplicate_factory_usage_is_not_assigned_to_a_physical_slot(self):
        entries = list(factory_entries())
        entries[68] = entries[0]
        result = assess_factory_usage_coverage(tuple(entries))
        self.assertFalse(result.all_factory_usages_present_once)
        self.assertIn(41, result.duplicate_hids)

    def test_inference_rejects_incomplete_or_mutable_entries(self):
        with self.assertRaises(ValueError):
            assess_factory_usage_coverage(tuple(bytes(4) for _ in range(127)))
        entries = list(factory_entries())
        entries[0] = bytearray(4)
        with self.assertRaises(ValueError):
            assess_factory_usage_coverage(tuple(entries))


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

    def test_widget_never_claims_physical_slot_mapping(self):
        widget = KeyboardLayoutWidget()
        self.assertIn("physical slot mapping is not verified", widget.mapping_message)
        coverage = widget.set_keymap_entries(factory_entries())
        self.assertTrue(coverage.all_factory_usages_present_once)
        self.assertIn("remap can reorder them", widget.mapping_message)
        self.assertIn("not verified", widget.mapping_message)
        widget.resize(760, 236)
        widget.show()
        self.app.processEvents()
        widget.clear()
        self.assertIn("physical slot mapping is not verified", widget.mapping_message)
        widget.close()


if __name__ == "__main__":
    unittest.main()
