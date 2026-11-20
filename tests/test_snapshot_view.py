import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from read_only_snapshot import build_read_only_snapshot
from snapshot_view import project_snapshot_for_display


def make_snapshot():
    profile = bytearray(64)
    profile[0] = 0x84
    profile[1] = 2
    keymaps = {
        (0, page): bytes([0xAB, 0x01, 0x00, page]) * 16
        for page in range(8)
    }
    magnetic = {
        (0, page): bytes([page, 0x01]) * 32
        for page in range(4)
    }
    return build_read_only_snapshot(
        bytes(profile), keymaps, magnetic,
        sublayers=(0,), magnetic_subops=(0,),
    )


class SnapshotViewTests(unittest.TestCase):
    def test_projection_preserves_profile_and_slot_order_without_guessing(self):
        view = project_snapshot_for_display(make_snapshot())
        self.assertEqual(view.active_profile_index, 2)
        self.assertEqual(len(view.keymap_layers), 1)
        layer = view.keymap_layers[0]
        self.assertEqual((layer.profile_index, layer.sublayer_index), (2, 0))
        self.assertEqual(len(layer.entries), 128)
        self.assertEqual(layer.entries[0].slot, 1)
        self.assertEqual(layer.entries[0].raw_hex, "AB 01 00 00")
        self.assertEqual(layer.entries[16].slot, 17)
        self.assertEqual(layer.entries[16].raw_hex, "AB 01 00 01")

    def test_magnetic_values_are_explicitly_raw_and_keep_width(self):
        view = project_snapshot_for_display(make_snapshot())
        column = view.magnetic_columns[0]
        self.assertEqual(column.get_subop, 0)
        self.assertEqual(column.value_width_bytes, 2)
        self.assertEqual(len(column.values), 128)
        self.assertEqual(column.values[0].slot, 1)
        self.assertEqual(column.values[0].raw_value, "256 (0x0100)")
        self.assertEqual(column.values[32].raw_value, "257 (0x0101)")

    def test_projection_returns_immutable_nested_sequences(self):
        view = project_snapshot_for_display(make_snapshot())
        self.assertIsInstance(view.keymap_layers, tuple)
        self.assertIsInstance(view.keymap_layers[0].entries, tuple)
        self.assertIsInstance(view.magnetic_columns, tuple)
        self.assertIsInstance(view.magnetic_columns[0].values, tuple)
        with self.assertRaises(AttributeError):
            view.active_profile_index = 0

    def test_projection_rejects_unvalidated_objects(self):
        for value in (None, {}, object()):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    project_snapshot_for_display(value)


if __name__ == "__main__":
    unittest.main()
