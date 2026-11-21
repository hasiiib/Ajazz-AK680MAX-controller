import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

try:
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise
    QApplication = None

if QApplication is not None:
    from read_only_snapshot import build_read_only_snapshot
    from snapshot_panel import ReadOnlySnapshotPanel


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class ReadOnlySnapshotPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_snapshot(self):
        profile = bytearray(64)
        profile[0] = 0x84
        profile[1] = 1
        keymaps = {
            (0, page): bytes([0x10, 0x20, 0x30, page]) * 16
            for page in range(8)
        }
        magnetic = {
            (0, page): bytes([page, 0x02]) * 32
            for page in range(4)
        }
        return build_read_only_snapshot(
            bytes(profile), keymaps, magnetic,
            sublayers=(0,), magnetic_subops=(0,),
        )

    def test_panel_starts_empty_and_does_not_claim_device_data(self):
        panel = ReadOnlySnapshotPanel()
        self.assertEqual(panel.table.rowCount(), 0)
        self.assertIn("No verified snapshot", panel.status.text())
        self.assertFalse(panel.layer_selector.isEnabled())
        panel.close()

    def test_panel_displays_validated_snapshot_as_raw_rows(self):
        panel = ReadOnlySnapshotPanel()
        panel.set_snapshot(self.make_snapshot())
        self.assertIn("profile index: 1", panel.profile_label.text())
        self.assertEqual(panel.table.rowCount(), 128)
        self.assertEqual(panel.table.item(0, 0).text(), "1")
        self.assertEqual(panel.table.item(0, 1).text(), "10 20 30 00")
        self.assertTrue(panel.layer_selector.isEnabled())
        self.assertTrue(panel.magnetic_selector.isEnabled())
        self.assertIn("provenance are not verified", panel.status.text())

        panel.magnetic_selector.setCurrentIndex(0)
        self.assertEqual(panel.table.item(0, 1).text(), "512 (0x0200)")
        panel.layer_selector.setCurrentIndex(0)
        self.assertEqual(panel.table.item(0, 1).text(), "10 20 30 00")
        panel.close()

    def test_rejected_replacement_clears_previous_snapshot(self):
        panel = ReadOnlySnapshotPanel()
        panel.set_snapshot(self.make_snapshot())
        self.assertEqual(panel.table.rowCount(), 128)

        with self.assertRaises(TypeError):
            panel.set_snapshot_view(object())

        self.assertEqual(panel.table.rowCount(), 0)
        self.assertIsNone(panel._view)
        self.assertFalse(panel.layer_selector.isEnabled())
        self.assertFalse(panel.magnetic_selector.isEnabled())
        self.assertIn("No verified snapshot", panel.status.text())
        panel.close()

    def test_invalid_snapshot_replacement_clears_previous_snapshot(self):
        panel = ReadOnlySnapshotPanel()
        panel.set_snapshot(self.make_snapshot())
        with self.assertRaises(TypeError):
            panel.set_snapshot(object())
        self.assertEqual(panel.table.rowCount(), 0)
        self.assertIsNone(panel._view)
        self.assertIn("No verified snapshot", panel.status.text())
        panel.close()

    def test_import_button_loads_complete_offline_bundle_without_device_io(self):
        profile = bytearray(64)
        profile[0] = 0x84
        profile[1] = 1
        bundle = {
            "format": "ak680-read-only-capture-bundle-v1",
            "target": {"vid_pid": "3151:502D", "board_id": 2255},
            "active_profile_reply": bytes(profile).hex(" "),
            "keymap_replies": [
                {"sublayer": 0, "page": page, "raw_hex": (bytes([page, 1, 2, 3]) * 16).hex(" ")}
                for page in range(8)
            ],
            "magnetic_replies": [
                {"subop": 0, "page": page, "raw_hex": (bytes([page, 0]) * 32).hex(" ")}
                for page in range(4)
            ],
        }
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "bundle.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            panel = ReadOnlySnapshotPanel()
            with patch("snapshot_panel.QFileDialog.getOpenFileName", return_value=(str(path), "")):
                panel._import_bundle_from_file()
            self.assertEqual(panel.table.rowCount(), 128)
            self.assertIn("self-declared", panel.status.text())
            self.assertIn("provenance are not verified", panel.status.text())
            panel.close()

    def test_failed_import_retains_existing_snapshot(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text("not json", encoding="utf-8")
            panel = ReadOnlySnapshotPanel()
            panel.set_snapshot(self.make_snapshot())
            with patch("snapshot_panel.QFileDialog.getOpenFileName", return_value=(str(path), "")):
                panel._import_bundle_from_file()
            self.assertEqual(panel.table.rowCount(), 128)
            self.assertIn("existing display retained", panel.status.text())
            panel.close()

    def test_invalid_utf8_import_retains_existing_snapshot(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.json"
            path.write_bytes(bytes([0xFF, 0xFE, 0xFA]))
            panel = ReadOnlySnapshotPanel()
            panel.set_snapshot(self.make_snapshot())
            with patch("snapshot_panel.QFileDialog.getOpenFileName", return_value=(str(path), "")):
                panel._import_bundle_from_file()
            self.assertEqual(panel.table.rowCount(), 128)
            self.assertIn("existing display retained", panel.status.text())
            panel.close()

    def test_explicit_clear_removes_rows_and_selector_items(self):
        panel = ReadOnlySnapshotPanel()
        panel.set_snapshot(self.make_snapshot())
        panel.clear_snapshot()
        self.assertEqual(panel.table.rowCount(), 0)
        self.assertEqual(panel.layer_selector.count(), 0)
        self.assertEqual(panel.magnetic_selector.count(), 0)
        self.assertIsNone(panel._view)
        panel.close()


if __name__ == "__main__":
    unittest.main()
