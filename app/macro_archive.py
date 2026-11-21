"""Strict offline archive for a complete four-page macro capture.

This module performs no HID I/O and does not decode event semantics. The
board identity in an archive is self-declared metadata, not device provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping

from macros import (
    MACRO_BLOB_LENGTH,
    MACRO_SLOT_COUNT,
    MacroProtocolError,
    assemble_macro_blob,
    parse_macro_page,
)

ARCHIVE_FORMAT = "ak680-macro-raw-capture-v1"
TARGET_VID_PID = "3151:502D"
TARGET_BOARD_ID = 2255
MAX_ARCHIVE_BYTES = 16 * 1024


class MacroArchiveError(ValueError):
    """A macro archive is malformed, incomplete, or unsupported."""


@dataclass(frozen=True)
class MacroCaptureArchive:
    slot: int
    pages: tuple[bytes, bytes, bytes, bytes]

    def __post_init__(self) -> None:
        if type(self.slot) is not int or not 0 <= self.slot < MACRO_SLOT_COUNT:
            raise MacroArchiveError("Macro slot must be an integer from 0 through 49.")
        if not isinstance(self.pages, tuple) or len(self.pages) != 4:
            raise MacroArchiveError("Archive must contain exactly four ordered pages.")
        try:
            normalized = tuple(parse_macro_page(page) for page in self.pages)
        except (MacroProtocolError, TypeError) as exc:
            raise MacroArchiveError(f"Invalid macro page: {exc}") from exc
        object.__setattr__(self, "pages", normalized)

    @property
    def blob(self) -> bytes:
        return assemble_macro_blob({index: page for index, page in enumerate(self.pages)})


def _strict_object(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict):
        raise MacroArchiveError(f"{label} must be a JSON object.")
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise MacroArchiveError(f"{label} fields mismatch ({'; '.join(details)}).")
    return value


def _decode_page_hex(value: object, label: str) -> bytes:
    if not isinstance(value, str):
        raise MacroArchiveError(f"{label} raw_hex must be a string.")
    try:
        raw = bytes.fromhex(value)
        return parse_macro_page(raw)
    except (ValueError, MacroProtocolError) as exc:
        raise MacroArchiveError(f"{label} must contain one 64-byte page (optionally prefixed by report ID 0): {exc}") from exc


def import_macro_archive_text(text: str) -> MacroCaptureArchive:
    """Import a complete raw macro archive; no event decoding is performed."""
    if not isinstance(text, str):
        raise MacroArchiveError("Archive content must be text.")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise MacroArchiveError("Archive must be valid Unicode text.") from exc
    if size > MAX_ARCHIVE_BYTES:
        raise MacroArchiveError("Archive exceeds the 16 KiB size limit.")
    try:
        root = json.loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise MacroArchiveError("Archive is not valid UTF-8 JSON.") from exc

    root = _strict_object(root, {"format", "target", "slot", "pages"}, "Archive")
    if root["format"] != ARCHIVE_FORMAT:
        raise MacroArchiveError("Unsupported macro archive format.")
    target = _strict_object(root["target"], {"vid_pid", "board_id"}, "Target")
    if (target["vid_pid"] != TARGET_VID_PID
            or type(target["board_id"]) is not int
            or target["board_id"] != TARGET_BOARD_ID):
        raise MacroArchiveError("Target declaration must identify 3151:502D / board ID 2255.")
    slot = root["slot"]
    if type(slot) is not int or not 0 <= slot < MACRO_SLOT_COUNT:
        raise MacroArchiveError("Macro slot must be an integer from 0 through 49.")
    items = root["pages"]
    if not isinstance(items, list) or len(items) != 4:
        raise MacroArchiveError("Pages must contain exactly four entries.")
    pages: dict[int, bytes] = {}
    for index, item in enumerate(items):
        item = _strict_object(item, {"page", "raw_hex"}, f"Page entry {index}")
        page = item["page"]
        if type(page) is not int or not 0 <= page < 4:
            raise MacroArchiveError(f"Page entry {index} page must be an integer from 0 through 3.")
        if page in pages:
            raise MacroArchiveError(f"Duplicate macro page {page}.")
        pages[page] = _decode_page_hex(item["raw_hex"], f"Page entry {index}")
    if set(pages) != {0, 1, 2, 3}:
        raise MacroArchiveError("Archive must include pages 0, 1, 2, and 3 exactly once.")
    return MacroCaptureArchive(slot, tuple(pages[index] for index in range(4)))


def export_macro_archive_text(archive: MacroCaptureArchive) -> str:
    """Export normalized raw page payloads; target fields remain self-declared."""
    if not isinstance(archive, MacroCaptureArchive):
        raise MacroArchiveError("Export requires a validated MacroCaptureArchive.")
    document = {
        "format": ARCHIVE_FORMAT,
        "target": {"vid_pid": TARGET_VID_PID, "board_id": TARGET_BOARD_ID},
        "slot": archive.slot,
        "pages": [
            {"page": page, "raw_hex": archive.pages[page].hex(" ").upper()}
            for page in range(4)
        ],
    }
    result = json.dumps(document, indent=2, sort_keys=True)
    if len(result.encode("utf-8")) > MAX_ARCHIVE_BYTES:
        raise MacroArchiveError("Exported archive exceeds the 16 KiB size limit.")
    return result


def archive_from_pages(slot: int, pages: Mapping[int, bytes | bytearray]) -> MacroCaptureArchive:
    """Validate and assemble four already-captured pages without device I/O."""
    try:
        blob = assemble_macro_blob(pages)
        ordered = tuple(blob[offset:offset + 64] for offset in range(0, MACRO_BLOB_LENGTH, 64))
        return MacroCaptureArchive(slot, ordered)
    except (MacroProtocolError, TypeError) as exc:
        raise MacroArchiveError(f"Cannot archive macro pages: {exc}") from exc
