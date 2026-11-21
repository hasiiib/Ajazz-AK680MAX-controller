"""Board-2255 ANSI layout reference and conservative slot inference."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QFont
from PySide6.QtWidgets import QWidget

from keymap_semantics import extract_layout_usage


LAYOUT_PATH = Path(__file__).with_name("ak680_max_2255_layout.json")


class KeyboardLayoutError(ValueError):
    """The bundled board-2255 layout reference is invalid."""


@dataclass(frozen=True)
class LayoutKey:
    hid: int
    label: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class LayoutInference:
    all_factory_usages_present_once: bool
    missing_hids: tuple[int, ...]
    duplicate_hids: tuple[int, ...]


def load_keyboard_layout(path: Path = LAYOUT_PATH) -> tuple[LayoutKey, ...]:
    """Load the bundled ANSI geometry, validating board identity and key shape."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KeyboardLayoutError("Could not load the bundled AK680 MAX layout.") from exc
    if not isinstance(data, dict) or data.get("board_id") != 2255 or data.get("variant") != "ANSI":
        raise KeyboardLayoutError("Bundled layout is not the board-2255 ANSI variant.")
    raw_keys = data.get("keys")
    if not isinstance(raw_keys, list) or len(raw_keys) != 68:
        raise KeyboardLayoutError("Board-2255 ANSI layout must contain exactly 68 keys.")
    keys = []
    seen_hids = set()
    for index, item in enumerate(raw_keys):
        if not isinstance(item, dict):
            raise KeyboardLayoutError(f"Layout key {index} must be an object.")
        hid = item.get("hid")
        label = item.get("label")
        x, y, width, height = (
            item.get("x"), item.get("y"), item.get("w"), item.get("h")
        )
        if type(hid) is not int or not 0 <= hid <= 0xFFFF:
            raise KeyboardLayoutError(f"Layout key {index} has an invalid HID usage.")
        if not isinstance(label, str) or not label:
            raise KeyboardLayoutError(f"Layout key {index} has an invalid label.")
        if any(type(value) is not int or value < 0 for value in (x, y, width, height)):
            raise KeyboardLayoutError(f"Layout key {index} has invalid geometry.")
        if width == 0 or height == 0:
            raise KeyboardLayoutError(f"Layout key {index} has zero area.")
        if hid in seen_hids:
            raise KeyboardLayoutError(f"Layout HID usage {hid} is duplicated.")
        seen_hids.add(hid)
        keys.append(LayoutKey(hid, label, x, y, width, height))
    return tuple(keys)


def assess_factory_usage_coverage(
    entries: Sequence[bytes],
    layout_keys: Sequence[LayoutKey] | None = None,
) -> LayoutInference:
    """Check whether factory HID usages are present once; do not infer slots.

    A customized keymap can contain all 68 usages while swapping their
    physical positions. Therefore usage coverage alone is never used to label
    a physical key with a slot number.
    """
    if not isinstance(entries, (tuple, list)) or len(entries) != 128:
        raise ValueError("Layout assessment requires exactly 128 four-byte keymap entries.")
    if any(not isinstance(entry, bytes) or len(entry) != 4 for entry in entries):
        raise ValueError("Layout assessment entries must be immutable four-byte values.")
    keys = tuple(layout_keys if layout_keys is not None else load_keyboard_layout())
    expected = {key.hid for key in keys}
    matches: dict[int, list[int]] = {hid: [] for hid in expected}
    for entry in entries:
        usage = extract_layout_usage(entry)
        if usage in matches:
            matches[usage].append(usage)
    missing = tuple(sorted(hid for hid, usages in matches.items() if not usages))
    duplicates = tuple(sorted(hid for hid, usages in matches.items() if len(usages) > 1))
    return LayoutInference(
        all_factory_usages_present_once=not missing and not duplicates,
        missing_hids=missing,
        duplicate_hids=duplicates,
    )

class KeyboardLayoutWidget(QWidget):
    """Display the ANSI key geometry and inferred slot numbers, never edit keys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.keys = load_keyboard_layout()
        self.entries: tuple[bytes, ...] | None = None
        self.inference = LayoutInference(False, tuple(key.hid for key in self.keys), ())
        self.setMinimumSize(760, 236)

    def sizeHint(self) -> QSize:
        return QSize(770, 244)

    def clear(self) -> None:
        self.entries = None
        self.inference = LayoutInference(
            False, tuple(key.hid for key in self.keys), ()
        )
        self.update()

    def set_keymap_entries(self, entries: Sequence[bytes]) -> LayoutInference:
        self.inference = assess_factory_usage_coverage(entries, self.keys)
        self.entries = tuple(entries)
        self.update()
        return self.inference

    @property
    def mapping_message(self) -> str:
        if self.entries is None:
            return (
                "ANSI reference geometry only · no keymap loaded · physical slot mapping is not verified"
            )
        if self.inference.all_factory_usages_present_once:
            return (
                "All 68 factory HID usages appear once, but a remap can reorder them. "
                "Physical slot mapping is not verified; use the slot table below."
            )
        return (
            "Current keymap differs from the factory HID usage set. "
            "Physical slot mapping is not verified; use the slot table below."
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        palette = self.palette()
        painter.fillRect(self.rect(), palette.base())
        scale = min(
            max(0.1, (self.width() - 16) / 750.0),
            max(0.1, (self.height() - 16) / 224.0),
        )
        offset_x = (self.width() - 750 * scale) / 2
        offset_y = (self.height() - 224 * scale) / 2
        for key in self.keys:
            rect = QRectF(
                offset_x + key.x * scale,
                offset_y + key.y * scale,
                key.width * scale,
                key.height * scale,
            )
            painter.setBrush(palette.button())
            painter.setPen(palette.mid().color())
            painter.drawRoundedRect(rect, 3.0 * scale, 3.0 * scale)
            painter.setPen(palette.buttonText().color())
            font = QFont(self.font())
            font.setPointSizeF(max(6.0, 8.0 * scale))
            painter.setFont(font)
            painter.drawText(rect.adjusted(2, 1, -2, -1), Qt.AlignmentFlag.AlignCenter, key.label)
        painter.end()
