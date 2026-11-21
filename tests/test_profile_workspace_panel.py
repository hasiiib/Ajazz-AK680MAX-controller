import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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
    from profile_workspace_panel import ProfileWorkspacePanel


@unittest.skipIf(QApplication is None, "PySide6 is not installed in this test environment")
class ProfileWorkspacePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def snapshot(self):
        active = bytearray(64)
        active[0] = 0x84
        keymaps = {(0, page): bytes(64) for page in range(8)}
        magnetic = {(0, page): (200).to_bytes(2, "little") * 32 for page in range(4)}
        return build_read_only_snapshot(bytes(active), keymaps, magnetic,
                                        sublayers=(0,), magnetic_subops=(0,))

    def test_current_snapshot_can_be_saved_and_previewed_offline(self):
        viewer = ReadOnlySnapshotPanel()
        panel = ProfileWorkspacePanel(viewer)
        panel.set_current_snapshot(self.snapshot())
        with patch("profile_workspace_panel.QInputDialog.getText", return_value=("Gaming", True)):
            panel._save_current()
        self.assertEqual([p.name for p in panel.profiles], ["Gaming"])
        self.assertIn("not modified", panel.status.text())
        panel._preview_profile(0)
        self.assertEqual(viewer.table.rowCount(), 128)
        self.assertIn("not a hardware profile switch", panel.status.text())
        panel.close()
        viewer.close()

    def test_workspace_import_replaces_only_after_valid_parse(self):
        viewer = ReadOnlySnapshotPanel()
        panel = ProfileWorkspacePanel(viewer)
        panel.set_current_snapshot(self.snapshot())
        with patch("profile_workspace_panel.QInputDialog.getText", return_value=("Work", True)):
            panel._save_current()
        with TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("invalid", encoding="utf-8")
            with patch("profile_workspace_panel.QFileDialog.getOpenFileName", return_value=(str(path), "")):
                panel._import_workspace()
        self.assertEqual([p.name for p in panel.profiles], ["Work"])
        self.assertIn("retained", panel.status.text())
        panel.close()
        viewer.close()


if __name__ == "__main__":
    unittest.main()
