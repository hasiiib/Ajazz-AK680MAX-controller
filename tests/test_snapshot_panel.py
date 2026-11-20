import os
import sys
import unittest
from pathlib import Path

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
        panel.magnetic_selector.setCurrentIndex(0)
        self.assertEqual(panel.table.rowCount(), 128)
        self.assertEqual(panel.table.item(0, 1).text(), "512 (0x0200)")
        panel.close()

    def test_panel_rejects_unvalidated_view_objects(self):
        panel = ReadOnlySnapshotPanel()
        with self.assertRaises(TypeError):
            panel.set_snapshot_view(object())
        panel.close()


if __name__ == "__main__":
    unittest.main()
