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

    def __post_init__(self) -> None:
        if type(self.slot) is not int or not 1 <= self.slot <= 128:
            raise ValueError("Keymap display slot must be an integer from 1 through 128.")
        parts = self.raw_hex.split(" ") if isinstance(self.raw_hex, str) else ()
        if len(parts) != 4 or any(
            len(part) != 2 or any(char not in "0123456789ABCDEF" for char in part)
            for part in parts
        ):
            raise ValueError("Keymap display value must be four uppercase hexadecimal bytes.")


@dataclass(frozen=True)
class KeymapLayerView:
    profile_index: int
    sublayer_index: int
    entries: tuple[KeymapEntryView, ...]

    def __post_init__(self) -> None:
        if type(self.profile_index) is not int or not 0 <= self.profile_index < 4:
            raise ValueError("Display profile index must be from 0 through 3.")
        if type(self.sublayer_index) is not int or not 0 <= self.sublayer_index < 4:
            raise ValueError("Display sublayer index must be from 0 through 3.")
        if not isinstance(self.entries, tuple) or len(self.entries) != 128:
            raise ValueError("Keymap display layer must contain 128 immutable entries.")
        if any(
            not isinstance(entry, KeymapEntryView) or entry.slot != index
            for index, entry in enumerate(self.entries, 1)
        ):
            raise ValueError("Keymap display entries must be validated and in 1-based slot order.")


@dataclass(frozen=True)
class MagneticValueView:
    slot: int
    raw_value: str

    def __post_init__(self) -> None:
        if type(self.slot) is not int or not 1 <= self.slot <= 128:
            raise ValueError("Magnetic display slot must be an integer from 1 through 128.")
        if not isinstance(self.raw_value, str) or not self.raw_value:
            raise ValueError("Magnetic display value must be a non-empty string.")


@dataclass(frozen=True)
class MagneticColumnView:
    get_subop: int
    value_width_bytes: int
    values: tuple[MagneticValueView, ...]

    def __post_init__(self) -> None:
        widths = {0: 2, 1: 2, 2: 2, 3: 2, 4: 2, 5: 1, 6: 2, 7: 1, 9: 1, 10: 4}
        if type(self.get_subop) is not int or self.get_subop not in widths:
            raise ValueError("Unsupported magnetic display GET sub-operation.")
        if type(self.value_width_bytes) is not int or self.value_width_bytes != widths[self.get_subop]:
            raise ValueError("Magnetic display width does not match its GET sub-operation.")
        if not isinstance(self.values, tuple) or len(self.values) != 128:
            raise ValueError("Magnetic display column must contain 128 immutable values.")
        if any(
            not isinstance(value, MagneticValueView) or value.slot != index
            for index, value in enumerate(self.values, 1)
        ):
            raise ValueError("Magnetic display values must be validated and in 1-based slot order.")


@dataclass(frozen=True)
class SnapshotView:
    active_profile_index: int
    keymap_layers: tuple[KeymapLayerView, ...]
    magnetic_columns: tuple[MagneticColumnView, ...]

    def __post_init__(self) -> None:
        if type(self.active_profile_index) is not int or not 0 <= self.active_profile_index < 4:
            raise ValueError("Display active profile must be from 0 through 3.")
        if not isinstance(self.keymap_layers, tuple) or not self.keymap_layers or any(
            not isinstance(layer, KeymapLayerView) or layer.profile_index != self.active_profile_index
            for layer in self.keymap_layers
        ):
            raise ValueError("Display keymap layers must be immutable and match the active profile.")
        if len({layer.sublayer_index for layer in self.keymap_layers}) != len(self.keymap_layers):
            raise ValueError("Display keymap sublayers must be unique.")
        if not isinstance(self.magnetic_columns, tuple) or not self.magnetic_columns or any(
            not isinstance(column, MagneticColumnView) for column in self.magnetic_columns
        ):
            raise ValueError("Display magnetic columns must be a non-empty immutable tuple.")
        if len({column.get_subop for column in self.magnetic_columns}) != len(self.magnetic_columns):
            raise ValueError("Display magnetic GET sub-operations must be unique.")


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
