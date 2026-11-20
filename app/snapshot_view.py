"""Display-only projection of validated snapshots; never assigns setting meanings.

Raw keymap bytes and magnetic protocol values remain explicitly labelled as
raw data until board-2255 response semantics are physically verified.
"""
from __future__ import annotations

from dataclasses import dataclass

from read_only_snapshot import ReadOnlyConfigurationSnapshot


@dataclass(frozen=True)
class KeymapEntryView:
    slot: int
    raw_hex: str


@dataclass(frozen=True)
class KeymapLayerView:
    profile_index: int
    sublayer_index: int
    entries: tuple[KeymapEntryView, ...]


@dataclass(frozen=True)
class MagneticValueView:
    slot: int
    raw_value: str


@dataclass(frozen=True)
class MagneticColumnView:
    get_subop: int
    value_width_bytes: int
    values: tuple[MagneticValueView, ...]


@dataclass(frozen=True)
class SnapshotView:
    active_profile_index: int
    keymap_layers: tuple[KeymapLayerView, ...]
    magnetic_columns: tuple[MagneticColumnView, ...]


def project_snapshot_for_display(snapshot: ReadOnlyConfigurationSnapshot) -> SnapshotView:
    """Project a validated snapshot into immutable, semantics-neutral UI rows."""
    if not isinstance(snapshot, ReadOnlyConfigurationSnapshot):
        raise TypeError("Display projection requires a validated read-only snapshot.")

    layers = tuple(
        KeymapLayerView(
            profile_index=layer.profile,
            sublayer_index=layer.sublayer,
            entries=tuple(
                KeymapEntryView(slot=index + 1, raw_hex=entry.hex(" ").upper())
                for index, entry in enumerate(layer.entries)
            ),
        )
        for layer in snapshot.keymap_layers
    )

    columns = tuple(
        MagneticColumnView(
            get_subop=column.subop,
            value_width_bytes=column.value_width,
            values=tuple(
                MagneticValueView(
                    slot=index + 1,
                    raw_value=(
                        " ".join(f"{part:02X}" for part in value)
                        if isinstance(value, tuple)
                        else f"{value} (0x{value:0{column.value_width * 2}X})"
                    ),
                )
                for index, value in enumerate(column.values)
            ),
        )
        for column in snapshot.magnetic_columns
    )

    return SnapshotView(
        active_profile_index=snapshot.active_profile,
        keymap_layers=layers,
        magnetic_columns=columns,
    )
