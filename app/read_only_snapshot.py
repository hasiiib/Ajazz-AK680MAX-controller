"""Validated aggregation for complete, read-only configuration snapshots.

This module joins already-obtained response payloads. It performs no HID I/O,
does not infer key meanings, and does not expose any configuration write path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from active_profile import parse_active_profile_reply
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
    if len(pages) != KEYMAP_PAGE_COUNT:
        raise SnapshotValidationError(
            f"Keymap layer is incomplete: received {len(pages)} of {KEYMAP_PAGE_COUNT} pages."
        )
    first = pages[0]
    expected_identity = (first.profile, first.sublayer)
    by_page: dict[int, KeymapPage] = {}
    for page in pages:
        if (page.profile, page.sublayer) != expected_identity:
            raise SnapshotValidationError("Keymap pages belong to different profiles or sublayers.")
        if page.page in by_page:
            raise SnapshotValidationError(f"Duplicate keymap page {page.page}.")
        if len(page.entries) != 16 or any(len(entry) != 4 for entry in page.entries):
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
    if not pages:
        raise SnapshotValidationError("At least one magnetic-settings page is required.")
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
        if page.subop != subop:
            raise SnapshotValidationError("Magnetic pages belong to different sub-operations.")
        if page.page in by_page:
            raise SnapshotValidationError(f"Duplicate magnetic page {page.page}.")
        if page.value_width != pages[0].value_width:
            raise SnapshotValidationError("Magnetic pages use inconsistent value widths.")
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
    active_profile = parse_active_profile_reply(active_profile_reply)

    if not sublayers or len(set(sublayers)) != len(sublayers):
        raise SnapshotValidationError("Sublayers must be a non-empty sequence without duplicates.")
    if not magnetic_subops or len(set(magnetic_subops)) != len(magnetic_subops):
        raise SnapshotValidationError("Magnetic sub-operations must be non-empty and unique.")

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
