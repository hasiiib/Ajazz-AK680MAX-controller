"""Ubuntu desktop profile workspace UI.

Profiles are offline snapshots only. Selecting a saved profile previews its
snapshot; it never changes the keyboard's active hardware profile.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QFileDialog, QInputDialog,
)

from profile_workspace import (
    ProfileWorkspace, ProfileWorkspaceError, WorkspaceProfile,
    workspace_from_text, workspace_to_text,
)


class ProfileWorkspacePanel(QWidget):
    """Manage up to four named offline snapshots without device writes."""

    def __init__(self, snapshot_panel, parent=None):
        super().__init__(parent)
        self.snapshot_panel = snapshot_panel
        self._profiles = []
        self._current_snapshot = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("LOCAL PROFILES — offline snapshots; no keyboard profile is changed"))
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._preview_profile)
        layout.addWidget(self.list_widget)

        actions = QHBoxLayout()
        self.save_button = QPushButton("Save current configuration as profile…")
        self.save_button.clicked.connect(self._save_current)
        actions.addWidget(self.save_button)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self._remove_selected)
        actions.addWidget(self.remove_button)
        layout.addLayout(actions)

        transfer = QHBoxLayout()
        self.import_button = QPushButton("Import workspace…")
        self.import_button.clicked.connect(self._import_workspace)
        transfer.addWidget(self.import_button)
        self.export_button = QPushButton("Export workspace…")
        self.export_button.clicked.connect(self._export_workspace)
        transfer.addWidget(self.export_button)
        layout.addLayout(transfer)

        self.status = QLabel("Read a configuration first, then save it as a local profile.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self._refresh()

    @property
    def profiles(self):
        return tuple(self._profiles)

    def set_current_snapshot(self, snapshot):
        self._current_snapshot = snapshot
        self.save_button.setEnabled(snapshot is not None)
        if snapshot is not None:
            self.status.setText("Current read-only configuration is ready to save as a named local profile.")

    def _refresh(self, selected=-1):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for profile in self._profiles:
            self.list_widget.addItem(profile.name)
        if 0 <= selected < len(self._profiles):
            self.list_widget.setCurrentRow(selected)
        self.list_widget.blockSignals(False)
        self.remove_button.setEnabled(bool(self._profiles))
        self.export_button.setEnabled(bool(self._profiles))

    def _save_current(self):
        if self._current_snapshot is None:
            self.status.setText("No current snapshot. Read configuration before saving.")
            return
        if len(self._profiles) >= 4:
            self.status.setText("Workspace limit reached: four profiles maximum.")
            return
        name, accepted = QInputDialog.getText(self, "Save local profile", "Profile name:")
        if not accepted:
            return
        try:
            candidate = WorkspaceProfile(name, self._current_snapshot)
            ProfileWorkspace(tuple(self._profiles + [candidate]))
        except ProfileWorkspaceError as exc:
            self.status.setText(f"Profile not saved: {exc}")
            return
        self._profiles.append(candidate)
        self._refresh(len(self._profiles) - 1)
        self.status.setText(f"Saved '{candidate.name}' locally. The keyboard was not modified.")

    def _remove_selected(self):
        index = self.list_widget.currentRow()
        if not 0 <= index < len(self._profiles):
            return
        removed = self._profiles.pop(index)
        self._refresh(min(index, len(self._profiles) - 1))
        self.status.setText(f"Removed local profile '{removed.name}'. The keyboard was not modified.")

    def _preview_profile(self, index):
        if not 0 <= index < len(self._profiles):
            return
        profile = self._profiles[index]
        self.snapshot_panel.set_snapshot(profile.snapshot)
        self.status.setText(
            f"Previewing '{profile.name}'. This is an offline preview, not a hardware profile switch."
        )

    def _import_workspace(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import AK680 profile workspace", str(Path.home()),
            "AK680 workspaces (*.json)",
        )
        if not filename:
            return
        try:
            path = Path(filename)
            if path.stat().st_size > 1024 * 1024:
                raise ProfileWorkspaceError("Workspace exceeds the 1 MiB size limit.")
            imported = workspace_from_text(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ProfileWorkspaceError) as exc:
            self.status.setText(f"Workspace import rejected; existing profiles retained. {exc}")
            return
        self._profiles = list(imported.profiles)
        self._refresh(0)
        self._preview_profile(0)
        self.status.setText("Workspace imported. Profiles are offline snapshots; no device settings were written.")

    def _export_workspace(self):
        if not self._profiles:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export AK680 profile workspace",
            str(Path.home() / "ak680-profiles.json"), "AK680 workspaces (*.json)",
        )
        if not filename:
            return
        try:
            content = workspace_to_text(ProfileWorkspace(tuple(self._profiles)))
            Path(filename).write_text(content, encoding="utf-8")
        except (OSError, ProfileWorkspaceError) as exc:
            self.status.setText(f"Workspace export failed: {exc}")
            return
        self.status.setText("Workspace exported. It contains local snapshots, not hardware profile-switch commands.")
