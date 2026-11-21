"""Read-only GUI for displaying a validated live or offline configuration snapshot.

This widget never communicates with the keyboard. The main window supplies a
snapshot only after its bounded, read-only acquisition worker completes.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QPushButton, QFileDialog,
)

from offline_snapshot_import import (
    MAX_BUNDLE_BYTES,
    SnapshotImportError,
    import_snapshot_bundle_text,
    export_snapshot_bundle_text,
)
from read_only_snapshot import ReadOnlyConfigurationSnapshot
from snapshot_view import SnapshotView, project_snapshot_for_display
from keyboard_layout import KeyboardLayoutWidget


class ReadOnlySnapshotPanel(QWidget):
    """Browse documented keymap assignments and raw magnetic values."""

    EMPTY_STATUS = (
        "No verified snapshot loaded. Use Read Configuration or import a capture bundle."
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view: SnapshotView | None = None
        self._snapshot: ReadOnlyConfigurationSnapshot | None = None

        layout = QVBoxLayout(self)
        self.profile_label = QLabel("Active profile: —")
        layout.addWidget(self.profile_label)

        self.import_button = QPushButton("Import offline capture bundle…")
        self.import_button.clicked.connect(self._import_bundle_from_file)
        layout.addWidget(self.import_button)

        self.export_button = QPushButton("Export normalized backup bundle…")
        self.export_button.clicked.connect(self._export_bundle_to_file)
        self.export_button.setEnabled(False)
        layout.addWidget(self.export_button)

        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Keymap layer:"))
        self.layer_selector = QComboBox()
        self.layer_selector.currentIndexChanged.connect(self._show_layer)
        selectors.addWidget(self.layer_selector)
        selectors.addWidget(QLabel("Magnetic GET sub-operation:"))
        self.magnetic_selector = QComboBox()
        self.magnetic_selector.currentIndexChanged.connect(self._show_magnetic)
        selectors.addWidget(self.magnetic_selector)
        layout.addLayout(selectors)

        self.keyboard_layout = KeyboardLayoutWidget()
        layout.addWidget(self.keyboard_layout)
        self.layout_status = QLabel(self.keyboard_layout.mapping_message)
        self.layout_status.setWordWrap(True)
        layout.addWidget(self.layout_status)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Slot", "Gen2 assignment / value", "Raw bytes / value"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.status = QLabel(self.EMPTY_STATUS)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.layer_selector.setEnabled(False)
        self.magnetic_selector.setEnabled(False)

    def _import_bundle_from_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Offline Capture Bundle",
            str(Path.home()),
            "JSON bundles (*.json)",
        )
        if not filename:
            return
        try:
            file_path = Path(filename)
            if file_path.stat().st_size > MAX_BUNDLE_BYTES:
                raise SnapshotImportError("Bundle exceeds the 256 KiB size limit.")
            bundle_text = file_path.read_text(encoding="utf-8")
            snapshot = import_snapshot_bundle_text(bundle_text)
        except (OSError, UnicodeError, SnapshotImportError) as exc:
            self.status.setText(f"Import rejected; existing display retained. {exc}")
            return

        self.set_snapshot(snapshot)
        self.status.setText(
            "Offline bundle imported · known gen2 key entries are decoded, unknown entries stay raw · "
            "magnetic values remain raw · target metadata is self-declared"
        )

    def clear_snapshot(self) -> None:
        """Remove all displayed data and reset selectors to a safe empty state."""
        self._view = None
        self._snapshot = None
        self.export_button.setEnabled(False)
        self.keyboard_layout.clear()
        self.layout_status.setText(self.keyboard_layout.mapping_message)
        self.keyboard_layout.show()
        self.layout_status.show()
        for selector in (self.layer_selector, self.magnetic_selector):
            selector.blockSignals(True)
            selector.clear()
            selector.setCurrentIndex(-1)
            selector.setEnabled(False)
            selector.blockSignals(False)
        self.table.clearContents()
        self.table.setRowCount(0)
        self.profile_label.setText("Active profile: —")
        self.status.setText(self.EMPTY_STATUS)

    def set_snapshot(self, snapshot: ReadOnlyConfigurationSnapshot) -> None:
        """Accept only a validated immutable snapshot; perform no device I/O."""
        self.clear_snapshot()
        try:
            view = project_snapshot_for_display(snapshot)
        except (TypeError, ValueError):
            self.clear_snapshot()
            raise
        self.set_snapshot_view(view)
        self._snapshot = snapshot
        self.export_button.setEnabled(True)

    def set_snapshot_view(self, view: SnapshotView) -> None:
        """Display an existing immutable projection, without interpreting it."""
        self.clear_snapshot()
        if not isinstance(view, SnapshotView):
            raise TypeError("Expected a validated SnapshotView.")
        self._view = view
        self.profile_label.setText(
            f"Active profile: Profile {view.active_profile_index + 1} (index {view.active_profile_index})"
        )

        self.layer_selector.blockSignals(True)
        for layer in view.keymap_layers:
            self.layer_selector.addItem(
                f"Profile {layer.profile_index + 1} / layer {layer.sublayer_index}"
            )
        self.layer_selector.setCurrentIndex(-1)
        self.layer_selector.blockSignals(False)
        self.layer_selector.setEnabled(bool(view.keymap_layers))

        self.magnetic_selector.blockSignals(True)
        for column in view.magnetic_columns:
            self.magnetic_selector.addItem(
                "Actuation travel (raw)" if column.get_subop == 0 else f"Magnetic GET sub-op {column.get_subop}"
            )
        self.magnetic_selector.setCurrentIndex(-1)
        self.magnetic_selector.blockSignals(False)
        self.magnetic_selector.setEnabled(bool(view.magnetic_columns))

        if view.keymap_layers:
            self._show_layer(0)
        elif view.magnetic_columns:
            self._show_magnetic(0)
        self.status.setText(
            "Snapshot loaded · known gen2 key entries are decoded; unknown entries stay raw · magnetic values remain raw · device provenance is not verified here"
        )

    def _export_bundle_to_file(self) -> None:
        if self._snapshot is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Normalized Configuration Backup",
            str(Path.home() / "ak680-configuration-backup.json"),
            "JSON bundles (*.json)",
        )
        if not filename:
            return
        try:
            bundle_text = export_snapshot_bundle_text(self._snapshot)
            Path(filename).write_text(bundle_text, encoding="utf-8")
        except (OSError, SnapshotImportError) as exc:
            self.status.setText(f"Backup export failed. {exc}")
            return
        self.status.setText(
            "Normalized backup exported · values can be re-imported · "
            "this is not a bit-for-bit raw USB capture"
        )

    def _populate(self, rows) -> None:
        rows = tuple(rows)
        self.table.setRowCount(len(rows))
        for row_index, (slot, description, raw_value) in enumerate(rows):
            slot_item = QTableWidgetItem(str(slot))
            description_item = QTableWidgetItem(str(description))
            value_item = QTableWidgetItem(str(raw_value))
            self.table.setItem(row_index, 0, slot_item)
            self.table.setItem(row_index, 1, description_item)
            self.table.setItem(row_index, 2, value_item)
        self.table.resizeColumnsToContents()

    def _show_layer(self, index: int) -> None:
        if self._view is None or not 0 <= index < len(self._view.keymap_layers):
            return
        layer = self._view.keymap_layers[index]
        self.keyboard_layout.show()
        self.layout_status.show()
        self.keyboard_layout.set_keymap_entries(tuple(bytes.fromhex(entry.raw_hex) for entry in layer.entries))
        self.layout_status.setText(self.keyboard_layout.mapping_message)
        self._populate((entry.slot, entry.assignment, entry.raw_hex) for entry in layer.entries)

    def _show_magnetic(self, index: int) -> None:
        if self._view is None or not 0 <= index < len(self._view.magnetic_columns):
            return
        column = self._view.magnetic_columns[index]
        self.keyboard_layout.hide()
        self.layout_status.hide()
        self._populate((value.slot, "Actuation travel (raw)" if column.get_subop == 0 else f"Magnetic sub-op {column.get_subop} (raw)", value.raw_value) for value in column.values)
