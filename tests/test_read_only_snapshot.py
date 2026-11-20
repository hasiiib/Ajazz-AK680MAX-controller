import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from active_profile import active_profile_get_packet
from keymap import parse_keymap_page
from magnetic_settings import parse_magnetic_settings_page
from read_only_snapshot import (
    SnapshotValidationError,
    assemble_keymap_layer,
    assemble_magnetic_column,
    build_read_only_snapshot,
)


def profile_reply(index=1):
    reply = bytearray(64)
    reply[0] = 0x84
    reply[1] = index
    return bytes(reply)


class SnapshotAssemblyTests(unittest.TestCase):
    def test_keymap_layer_orders_all_pages_by_page_number(self):
        pages = [
            parse_keymap_page(1, page, 2, bytes([page]) * 64)
            for page in reversed(range(8))
        ]
        result = assemble_keymap_layer(pages)
        self.assertEqual((result.profile, result.sublayer), (1, 2))
        self.assertEqual(len(result.entries), 128)
        self.assertEqual(result.entries[0], bytes([0]) * 4)
        self.assertEqual(result.entries[16], bytes([1]) * 4)
        self.assertEqual(result.entries[-1], bytes([7]) * 4)

    def test_keymap_layer_rejects_missing_duplicate_or_mixed_pages(self):
        complete = [parse_keymap_page(0, page, 0, bytes(64)) for page in range(8)]
        cases = (
            complete[:-1],
            complete[:-1] + [complete[0]],
            complete[:-1] + [parse_keymap_page(0, 7, 1, bytes(64))],
        )
        for pages in cases:
            with self.subTest(count=len(pages)):
                with self.assertRaises(SnapshotValidationError):
                    assemble_keymap_layer(pages)

    def test_magnetic_column_assembles_all_128_slots(self):
        pages = [
            parse_magnetic_settings_page(0, page, bytes([page, 0]) * 32)
            for page in reversed(range(4))
        ]
        result = assemble_magnetic_column(pages)
        self.assertEqual(result.subop, 0)
        self.assertEqual(result.value_width, 2)
        self.assertEqual(len(result.values), 128)
        self.assertEqual(result.values[0], 0)
        self.assertEqual(result.values[32], 1)

    def test_magnetic_column_rejects_missing_or_mixed_pages(self):
        complete = [
            parse_magnetic_settings_page(7, page, bytes(64))
            for page in range(2)
        ]
        with self.assertRaises(SnapshotValidationError):
            assemble_magnetic_column(complete[:1])
        mixed = [complete[0], parse_magnetic_settings_page(5, 1, bytes(64))]
        with self.assertRaises(SnapshotValidationError):
            assemble_magnetic_column(mixed)

    def test_snapshot_requires_exact_keymap_and_magnetic_reply_sets(self):
        keymaps = {(0, page): bytes(64) for page in range(8)}
        magnetics = {(0, page): bytes(64) for page in range(4)}
        result = build_read_only_snapshot(
            profile_reply(), keymaps, magnetics,
            sublayers=(0,), magnetic_subops=(0,),
        )
        self.assertEqual(result.active_profile, 1)
        self.assertEqual(len(result.keymap_layers), 1)
        self.assertEqual(len(result.keymap_layers[0].entries), 128)
        self.assertEqual(len(result.magnetic_columns[0].values), 128)

        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(
                profile_reply(), dict(list(keymaps.items())[:-1]), magnetics,
                sublayers=(0,), magnetic_subops=(0,),
            )
        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(
                profile_reply(), keymaps, {(0, 0): bytes(64)},
                sublayers=(0,), magnetic_subops=(0,),
            )

    def test_snapshot_rejects_invalid_active_profile_and_bad_payload(self):
        keymaps = {(0, page): bytes(64) for page in range(8)}
        magnetics = {(0, page): bytes(64) for page in range(4)}
        invalid_profile = bytearray(profile_reply())
        invalid_profile[1] = 4
        with self.assertRaises(ValueError):
            build_read_only_snapshot(
                invalid_profile, keymaps, magnetics,
                sublayers=(0,), magnetic_subops=(0,),
            )
        broken = dict(keymaps)
        broken[(0, 3)] = bytes(63)
        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(
                profile_reply(), broken, magnetics,
                sublayers=(0,), magnetic_subops=(0,),
            )

    def test_snapshot_rejects_duplicate_requested_dimensions(self):
        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(
                profile_reply(), {}, {}, sublayers=(0, 0), magnetic_subops=(0,),
            )
        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(
                profile_reply(), {}, {}, sublayers=(0,), magnetic_subops=(0, 0),
            )


if __name__ == "__main__":
    unittest.main()
