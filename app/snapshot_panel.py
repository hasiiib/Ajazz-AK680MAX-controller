"""Read-only GUI for displaying an already validated configuration snapshot.

This widget never communicates with the keyboard. A future acquisition layer
must explicitly provide a validated ReadOnlyConfigurationSnapshot.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget,
    QTableWidgetItem, QAbstractItemView,
)

from read_only_snapshot import ReadOnlyConfigurationSnapshot
from snapshot_view import SnapshotView, project_snapshot_for_display


class ReadOnlySnapshotPanel(QWidget):
    """Browse raw keymap and magnetic values without assigning meanings."""

    EMPTY_STATUS = (
        "No verified snapshot loaded. Device configuration reads are not enabled."
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view: SnapshotView | None = None

        layout = QVBoxLayout(self)
        self.profile_label = QLabel("Active profile: —")
        layout.addWidget(self.profile_label)

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

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Slot", "Raw value"])
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

    def clear_snapshot(self) -> None:
        """Remove all displayed data and reset selectors to a safe empty state."""
        self._view = None
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

    def set_snapshot_view(self, view: SnapshotView) -> None:
        """Display an existing immutable projection, without interpreting it."""
        self.clear_snapshot()
        if not isinstance(view, SnapshotView):
            raise TypeError("Expected a validated SnapshotView.")
        self._view = view
        self.profile_label.setText(
            f"Active profile index: {view.active_profile_index}"
        )

        self.layer_selector.blockSignals(True)
        for layer in view.keymap_layers:
            self.layer_selector.addItem(
                f"Profile {layer.profile_index} / sublayer {layer.sublayer_index}"
            )
        self.layer_selector.blockSignals(False)
        self.layer_selector.setEnabled(bool(view.keymap_layers))

        self.magnetic_selector.blockSignals(True)
        for column in view.magnetic_columns:
            self.magnetic_selector.addItem(
                f"GET sub-op {column.get_subop} · {column.value_width_bytes}-byte values"
            )
        self.magnetic_selector.blockSignals(False)
        self.magnetic_selector.setEnabled(bool(view.magnetic_columns))

        if view.keymap_layers:
            self._show_layer(0)
        elif view.magnetic_columns:
            self._show_magnetic(0)
        self.status.setText(
            "Snapshot data loaded · raw protocol values only · device source and provenance are not verified here"
        )

    def _populate(self, rows) -> None:
        rows = tuple(rows)
        self.table.setRowCount(len(rows))
        for row_index, (slot, raw_value) in enumerate(rows):
            slot_item = QTableWidgetItem(str(slot))
            value_item = QTableWidgetItem(str(raw_value))
            self.table.setItem(row_index, 0, slot_item)
            self.table.setItem(row_index, 1, value_item)
        self.table.resizeColumnsToContents()

    def _show_layer(self, index: int) -> None:
        if self._view is None or not 0 <= index < len(self._view.keymap_layers):
            return
        layer = self._view.keymap_layers[index]
        self._populate((entry.slot, entry.raw_hex) for entry in layer.entries)

    def _show_magnetic(self, index: int) -> None:
        if self._view is None or not 0 <= index < len(self._view.magnetic_columns):
            return
        column = self._view.magnetic_columns[index]
        self._populate((value.slot, value.raw_value) for value in column.values)
