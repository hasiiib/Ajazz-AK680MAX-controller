"""Strict offline import for complete read-only board-2255 response bundles.

This module performs no HID I/O and does not persist or export captures. Bundle
metadata is self-declared; importing cannot establish the source device or
firmware provenance.
"""
from __future__ import annotations

import json

from read_only_snapshot import (
    ReadOnlyConfigurationSnapshot,
    SnapshotValidationError,
    build_read_only_snapshot,
)

BUNDLE_FORMAT = "ak680-read-only-capture-bundle-v1"
TARGET_VID_PID = "3151:502D"
TARGET_BOARD_ID = 2255
MAX_BUNDLE_BYTES = 256 * 1024


class SnapshotImportError(ValueError):
    """An offline capture bundle is invalid, incomplete, or unsupported."""


def _decode_hex(value: object, label: str) -> bytes:
    if not isinstance(value, str):
        raise SnapshotImportError(f"{label} must be a hexadecimal string.")
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise SnapshotImportError(f"{label} must contain complete hexadecimal byte pairs.") from exc
    if len(raw) not in (64, 65):
        raise SnapshotImportError(f"{label} must contain 64 payload bytes or 65 bytes with a report-ID prefix.")
    if len(raw) == 65 and raw[0] != 0:
        raise SnapshotImportError(f"{label} has an unsupported report-ID prefix.")
    return raw


def _strict_object(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict):
        raise SnapshotImportError(f"{label} must be a JSON object.")
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unexpected " + ", ".join(extra))
        raise SnapshotImportError(f"{label} fields mismatch ({'; '.join(detail)}).")
    return value


def import_snapshot_bundle_text(text: str) -> ReadOnlyConfigurationSnapshot:
    """Validate and assemble a complete in-memory snapshot from a JSON bundle.

    The bundle must contain all eight keymap pages for each listed sublayer and
    all pages for each listed magnetic GET sub-operation. Missing pages,
    duplicates, unsupported metadata, or mismatched target declarations fail
    closed. The target declaration is a claim in the file, not device evidence.
    """
    if not isinstance(text, str):
        raise SnapshotImportError("Bundle content must be text.")
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise SnapshotImportError("Bundle content must be valid Unicode text.") from exc
    if encoded_size > MAX_BUNDLE_BYTES:
        raise SnapshotImportError("Bundle exceeds the 256 KiB size limit.")
    try:
        root = json.loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SnapshotImportError("Bundle is not valid UTF-8 JSON.") from exc

    root = _strict_object(
        root,
        {"format", "target", "active_profile_reply", "keymap_replies", "magnetic_replies"},
        "Bundle",
    )
    if root["format"] != BUNDLE_FORMAT:
        raise SnapshotImportError("Unsupported bundle format.")
    target = _strict_object(root["target"], {"vid_pid", "board_id"}, "Target")
    if target["vid_pid"] != TARGET_VID_PID or type(target["board_id"]) is not int or target["board_id"] != TARGET_BOARD_ID:
        raise SnapshotImportError("Target declaration must identify 3151:502D / board ID 2255.")

    active_profile_reply = _decode_hex(root["active_profile_reply"], "Active-profile reply")
    keymap_items = root["keymap_replies"]
    magnetic_items = root["magnetic_replies"]
    if not isinstance(keymap_items, list) or not keymap_items:
        raise SnapshotImportError("Keymap replies must be a non-empty list.")
    if not isinstance(magnetic_items, list) or not magnetic_items:
        raise SnapshotImportError("Magnetic replies must be a non-empty list.")

    keymap_replies: dict[tuple[int, int], bytes] = {}
    for index, item in enumerate(keymap_items):
        item = _strict_object(item, {"sublayer", "page", "raw_hex"}, f"Keymap entry {index}")
        sublayer, page = item["sublayer"], item["page"]
        if type(sublayer) is not int or type(page) is not int:
            raise SnapshotImportError(f"Keymap entry {index} metadata must be integers, not booleans.")
        key = (sublayer, page)
        if key in keymap_replies:
            raise SnapshotImportError(f"Duplicate keymap reply for sublayer {sublayer}, page {page}.")
        keymap_replies[key] = _decode_hex(item["raw_hex"], f"Keymap entry {index}")

    magnetic_replies: dict[tuple[int, int], bytes] = {}
    for index, item in enumerate(magnetic_items):
        item = _strict_object(item, {"subop", "page", "raw_hex"}, f"Magnetic entry {index}")
        subop, page = item["subop"], item["page"]
        if type(subop) is not int or type(page) is not int:
            raise SnapshotImportError(f"Magnetic entry {index} metadata must be integers, not booleans.")
        key = (subop, page)
        if key in magnetic_replies:
            raise SnapshotImportError(f"Duplicate magnetic reply for sub-operation {subop}, page {page}.")
        magnetic_replies[key] = _decode_hex(item["raw_hex"], f"Magnetic entry {index}")

    sublayers = tuple(sorted({key[0] for key in keymap_replies}))
    magnetic_subops = tuple(sorted({key[0] for key in magnetic_replies}))
    try:
        return build_read_only_snapshot(
            active_profile_reply,
            keymap_replies,
            magnetic_replies,
            sublayers=sublayers,
            magnetic_subops=magnetic_subops,
        )
    except (SnapshotValidationError, ValueError, TypeError) as exc:
        raise SnapshotImportError(f"Bundle validation failed: {exc}") from exc
