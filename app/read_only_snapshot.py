"""Validated aggregation for complete, read-only configuration snapshots.

This module joins already-obtained response payloads. It performs no HID I/O,
does not infer key meanings, and does not expose any configuration write path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from active_profile import ProfileProtocolError, parse_active_profile_reply
from keymap import (
    KEYMAP_PAGE_COUNT,
    KeymapPage,
    KeymapProtocolError,
    parse_keymap_page,
)
from magnetic_settings import (
    MagneticSettingsPage,
    MagneticSettingsProtocolError,
    _page_count,
    parse_magnetic_settings_page,
)


class SnapshotValidationError(ValueError):
    """A read-only snapshot is incomplete, inconsistent, or malformed."""


@dataclass(frozen=True)
class KeymapLayerSnapshot:
    """One complete 128-slot keymap layer, retaining opaque raw entries."""

    profile: int
    sublayer: int
    entries: tuple[bytes, ...]


@dataclass(frozen=True)
class MagneticColumnSnapshot:
    """One complete magnetic-settings column with its original value width."""

    subop: int
    values: tuple[int | tuple[int, int, int, int], ...]
    value_width: int


@dataclass(frozen=True)
class ReadOnlyConfigurationSnapshot:
    """Validated read-only data; values retain protocol-native units."""

    active_profile: int
    keymap_layers: tuple[KeymapLayerSnapshot, ...]
    magnetic_columns: tuple[MagneticColumnSnapshot, ...]


def assemble_keymap_layer(pages: tuple[KeymapPage, ...] | list[KeymapPage]) -> KeymapLayerSnapshot:
    """Require exactly pages 0..7 for one profile/sublayer before assembly."""
    if not isinstance(pages, (tuple, list)):
        raise SnapshotValidationError("Keymap pages must be supplied as a list or tuple.")
    if len(pages) != KEYMAP_PAGE_COUNT:
        raise SnapshotValidationError(
            f"Keymap layer is incomplete: received {len(pages)} of {KEYMAP_PAGE_COUNT} pages."
        )
    if any(not isinstance(page, KeymapPage) for page in pages):
        raise SnapshotValidationError("Every keymap page must be a validated KeymapPage.")
    first = pages[0]
    if (
        not isinstance(first.profile, int) or isinstance(first.profile, bool)
        or not 0 <= first.profile < 4
        or not isinstance(first.sublayer, int) or isinstance(first.sublayer, bool)
        or not 0 <= first.sublayer < 4
    ):
        raise SnapshotValidationError("Keymap page has an invalid profile or sublayer.")
    expected_identity = (first.profile, first.sublayer)
    by_page: dict[int, KeymapPage] = {}
    for page in pages:
        if (
            not isinstance(page.profile, int) or isinstance(page.profile, bool)
            or not isinstance(page.sublayer, int) or isinstance(page.sublayer, bool)
            or not isinstance(page.page, int) or isinstance(page.page, bool)
            or not isinstance(page.first_slot, int) or isinstance(page.first_slot, bool)
        ):
            raise SnapshotValidationError("Keymap page metadata must contain integers, not booleans.")
        if (page.profile, page.sublayer) != expected_identity:
            raise SnapshotValidationError("Keymap pages belong to different profiles or sublayers.")
        if page.page in by_page:
            raise SnapshotValidationError(f"Duplicate keymap page {page.page}.")
        if page.page not in range(KEYMAP_PAGE_COUNT):
            raise SnapshotValidationError(f"Keymap page index {page.page} is out of range.")
        if page.first_slot != page.page * 16:
            raise SnapshotValidationError(f"Keymap page {page.page} has an inconsistent first-slot offset.")
        if not isinstance(page.entries, tuple) or len(page.entries) != 16 or any(
            not isinstance(entry, bytes) or len(entry) != 4 for entry in page.entries
        ):
            raise SnapshotValidationError(f"Keymap page {page.page} has an invalid entry shape.")
        by_page[page.page] = page
    expected_pages = set(range(KEYMAP_PAGE_COUNT))
    if set(by_page) != expected_pages:
        raise SnapshotValidationError("Keymap pages do not cover the complete 0..7 range.")
    ordered = tuple(entry for index in range(KEYMAP_PAGE_COUNT) for entry in by_page[index].entries)
    return KeymapLayerSnapshot(first.profile, first.sublayer, ordered)


def assemble_magnetic_column(
    pages: tuple[MagneticSettingsPage, ...] | list[MagneticSettingsPage],
) -> MagneticColumnSnapshot:
    """Require every page for a supported GET sub-operation, in page order."""
    if not isinstance(pages, (tuple, list)) or not pages:
        raise SnapshotValidationError("Magnetic pages must be a non-empty list or tuple.")
    if any(not isinstance(page, MagneticSettingsPage) for page in pages):
        raise SnapshotValidationError("Every magnetic page must be a validated MagneticSettingsPage.")
    subop = pages[0].subop
    try:
        expected_count = _page_count(subop)
    except MagneticSettingsProtocolError as exc:
        raise SnapshotValidationError(str(exc)) from exc
    if len(pages) != expected_count:
        raise SnapshotValidationError(
            f"Magnetic sub-operation {subop} is incomplete: received {len(pages)} "
            f"of {expected_count} pages."
        )
    by_page: dict[int, MagneticSettingsPage] = {}
    for page in pages:
        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in (page.subop, page.page, page.first_slot, page.value_width)
        ):
            raise SnapshotValidationError("Magnetic page metadata must contain integers, not booleans.")
        if page.subop != subop:
            raise SnapshotValidationError("Magnetic pages belong to different sub-operations.")
        if page.page in by_page:
            raise SnapshotValidationError(f"Duplicate magnetic page {page.page}.")
        if page.page not in range(expected_count):
            raise SnapshotValidationError(f"Magnetic page index {page.page} is out of range.")
        if not isinstance(page.values, tuple):
            raise SnapshotValidationError(f"Magnetic page {page.page} values must be an immutable tuple.")
        if page.value_width != pages[0].value_width:
            raise SnapshotValidationError("Magnetic pages use inconsistent value widths.")
        expected_width = 4 if subop == 10 else (2 if subop in {0, 1, 2, 3, 4, 6} else 1)
        expected_values = 16 if expected_width == 4 else (32 if expected_width == 2 else 64)
        if page.value_width != expected_width or len(page.values) != expected_values:
            raise SnapshotValidationError(f"Magnetic page {page.page} has an invalid value shape.")
        if page.first_slot != page.page * expected_values:
            raise SnapshotValidationError(f"Magnetic page {page.page} has an inconsistent first-slot offset.")
        if expected_width == 4:
            if any(not isinstance(value, tuple) or len(value) != 4 or any(
                not isinstance(part, int) or isinstance(part, bool) or not 0 <= part <= 255
                for part in value
            ) for value in page.values):
                raise SnapshotValidationError(f"Magnetic page {page.page} has an invalid four-byte record.")
        elif any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < (1 << (8 * expected_width)) for value in page.values):
            raise SnapshotValidationError(f"Magnetic page {page.page} has an invalid numeric value.")
        by_page[page.page] = page
    if set(by_page) != set(range(expected_count)):
        raise SnapshotValidationError("Magnetic pages do not cover the complete page range.")
    ordered_pages = tuple(by_page[index] for index in range(expected_count))
    first_slot = 0
    values: list[int | tuple[int, int, int, int]] = []
    for page in ordered_pages:
        if page.first_slot != first_slot:
            raise SnapshotValidationError("Magnetic page slot offsets are inconsistent.")
        values.extend(page.values)
        first_slot += len(page.values)
    if first_slot != 128:
        raise SnapshotValidationError(
            f"Magnetic column covers {first_slot} slots; expected exactly 128."
        )
    return MagneticColumnSnapshot(subop, tuple(values), ordered_pages[0].value_width)


def build_read_only_snapshot(
    active_profile_reply: bytes | bytearray,
    keymap_replies: Mapping[tuple[int, int], bytes | bytearray],
    magnetic_replies: Mapping[tuple[int, int], bytes | bytearray],
    *,
    sublayers: tuple[int, ...] = (0,),
    magnetic_subops: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 9, 10),
) -> ReadOnlyConfigurationSnapshot:
    """Build a complete snapshot from raw replies; missing/extra pages fail closed.

    Keymap mapping keys are (sublayer, page); all pages are for the active
    profile. Magnetic mapping keys are (sub-operation, page).
    """
    if not isinstance(active_profile_reply, (bytes, bytearray)):
        raise SnapshotValidationError("Active-profile reply must be bytes or bytearray.")
    try:
        active_profile = parse_active_profile_reply(active_profile_reply)
    except ProfileProtocolError as exc:
        raise SnapshotValidationError(f"Invalid active-profile reply: {exc}") from exc

    if not isinstance(sublayers, (tuple, list)) or not sublayers:
        raise SnapshotValidationError("Sublayers must be a non-empty sequence.")
    if any(not isinstance(layer, int) or isinstance(layer, bool) or not 0 <= layer < 4 for layer in sublayers):
        raise SnapshotValidationError("Every sublayer must be an integer from 0 through 3.")
    if len(set(sublayers)) != len(sublayers):
        raise SnapshotValidationError("Sublayers must not contain duplicates.")
    if not isinstance(magnetic_subops, (tuple, list)) or not magnetic_subops:
        raise SnapshotValidationError("Magnetic sub-operations must be a non-empty sequence.")
    if any(not isinstance(subop, int) or isinstance(subop, bool) for subop in magnetic_subops):
        raise SnapshotValidationError("Every magnetic sub-operation must be an integer.")
    if len(set(magnetic_subops)) != len(magnetic_subops):
        raise SnapshotValidationError("Magnetic sub-operations must not contain duplicates.")
    for subop in magnetic_subops:
        try:
            _page_count(subop)
        except MagneticSettingsProtocolError as exc:
            raise SnapshotValidationError(str(exc)) from exc

    if not isinstance(keymap_replies, Mapping) or not isinstance(magnetic_replies, Mapping):
        raise SnapshotValidationError("Keymap and magnetic replies must be mappings.")
    if any(not isinstance(reply, (bytes, bytearray)) for reply in keymap_replies.values()):
        raise SnapshotValidationError("Every keymap reply must be bytes or bytearray.")
    if any(not isinstance(reply, (bytes, bytearray)) for reply in magnetic_replies.values()):
        raise SnapshotValidationError("Every magnetic reply must be bytes or bytearray.")

    expected_keymap = {(layer, page) for layer in sublayers for page in range(KEYMAP_PAGE_COUNT)}
    if set(keymap_replies) != expected_keymap:
        missing = len(expected_keymap - set(keymap_replies))
        extra = len(set(keymap_replies) - expected_keymap)
        raise SnapshotValidationError(f"Keymap reply set mismatch ({missing} missing, {extra} unexpected).")

    keymap_layers: list[KeymapLayerSnapshot] = []
    for layer in sublayers:
        pages = []
        for page in range(KEYMAP_PAGE_COUNT):
            try:
                pages.append(parse_keymap_page(active_profile, page, layer, keymap_replies[(layer, page)]))
            except KeymapProtocolError as exc:
                raise SnapshotValidationError(
                    f"Invalid keymap page {page} for sublayer {layer}: {exc}"
                ) from exc
        keymap_layers.append(assemble_keymap_layer(pages))

    expected_magnetic = {
        (subop, page)
        for subop in magnetic_subops
        for page in range(_page_count(subop))
    }
    if set(magnetic_replies) != expected_magnetic:
        missing = len(expected_magnetic - set(magnetic_replies))
        extra = len(set(magnetic_replies) - expected_magnetic)
        raise SnapshotValidationError(
            f"Magnetic reply set mismatch ({missing} missing, {extra} unexpected)."
        )

    magnetic_columns: list[MagneticColumnSnapshot] = []
    for subop in magnetic_subops:
        pages = []
        for page in range(_page_count(subop)):
            try:
                pages.append(parse_magnetic_settings_page(subop, page, magnetic_replies[(subop, page)]))
            except MagneticSettingsProtocolError as exc:
                raise SnapshotValidationError(
                    f"Invalid magnetic page {page} for sub-operation {subop}: {exc}"
                ) from exc
        magnetic_columns.append(assemble_magnetic_column(pages))

    return ReadOnlyConfigurationSnapshot(
        active_profile=active_profile,
        keymap_layers=tuple(keymap_layers),
        magnetic_columns=tuple(magnetic_columns),
    )
