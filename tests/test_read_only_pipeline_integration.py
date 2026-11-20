"""Synthetic end-to-end tests for the read-only response-to-display pipeline.

These fixtures exercise parser composition only. They do not establish the
physical response framing or semantics of board 2255.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from magnetic_settings import MAGNETIC_DKS_ACTIONS_SUBOP, MAGNETIC_U16_SUBOPS, MAGNETIC_U8_SUBOPS
from read_only_snapshot import SnapshotValidationError, build_read_only_snapshot
from snapshot_view import project_snapshot_for_display


def make_profile_reply(profile=2):
    reply = bytearray(64)
    reply[0] = 0x84
    reply[1] = profile
    return bytes(reply)


def make_keymap_replies():
    # Each page has sixteen opaque four-byte entries.
    return {
        (0, page): bytes([0xA0 + page, 0x11, 0x22, 0x33]) * 16
        for page in range(8)
    }


def make_magnetic_replies():
    replies = {}
    for subop in sorted(MAGNETIC_U16_SUBOPS | MAGNETIC_U8_SUBOPS | {MAGNETIC_DKS_ACTIONS_SUBOP}):
        page_count = 8 if subop == MAGNETIC_DKS_ACTIONS_SUBOP else (
            4 if subop in MAGNETIC_U16_SUBOPS else 2
        )
        for page in range(page_count):
            if subop in MAGNETIC_U16_SUBOPS:
                payload = bytes([page + 1, 0x12]) * 32
            elif subop in MAGNETIC_U8_SUBOPS:
                payload = bytes([page + 1]) * 64
            else:
                payload = bytes([page + 1, 0x22, 0x33, 0x44]) * 16
            replies[(subop, page)] = payload
    return replies


class ReadOnlyPipelineIntegrationTests(unittest.TestCase):
    def test_all_response_families_assemble_and_project_together(self):
        snapshot = build_read_only_snapshot(
            make_profile_reply(),
            make_keymap_replies(),
            make_magnetic_replies(),
        )
        view = project_snapshot_for_display(snapshot)

        self.assertEqual(view.active_profile_index, 2)
        self.assertEqual(len(view.keymap_layers), 1)
        self.assertEqual(len(view.keymap_layers[0].entries), 128)
        self.assertEqual(view.keymap_layers[0].entries[0].raw_hex, "A0 11 22 33")
        self.assertEqual(view.keymap_layers[0].entries[16].raw_hex, "A1 11 22 33")
        self.assertEqual(len(view.magnetic_columns), 10)
        self.assertEqual(
            {column.get_subop for column in view.magnetic_columns},
            MAGNETIC_U16_SUBOPS | MAGNETIC_U8_SUBOPS | {MAGNETIC_DKS_ACTIONS_SUBOP},
        )
        for column in view.magnetic_columns:
            with self.subTest(subop=column.get_subop):
                self.assertEqual(len(column.values), 128)
                self.assertEqual(column.values[0].slot, 1)
                self.assertEqual(column.values[-1].slot, 128)
        u16_column = next(column for column in view.magnetic_columns if column.get_subop == 0)
        self.assertEqual(u16_column.values[0].raw_value, "4609 (0x1201)")
        dks_column = next(column for column in view.magnetic_columns if column.get_subop == 10)
        self.assertEqual(dks_column.values[0].raw_value, "01 22 33 44")

    def test_profile_hidapi_prefix_is_normalized_at_pipeline_boundary(self):
        snapshot = build_read_only_snapshot(
            bytes([0]) + make_profile_reply(3),
            make_keymap_replies(),
            make_magnetic_replies(),
        )
        self.assertEqual(project_snapshot_for_display(snapshot).active_profile_index, 3)

    def test_incomplete_or_malformed_response_set_never_reaches_display(self):
        keymaps = make_keymap_replies()
        magnetics = make_magnetic_replies()
        del magnetics[(10, 7)]
        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(make_profile_reply(), keymaps, magnetics)

        magnetics = make_magnetic_replies()
        keymaps[(0, 4)] = bytes(63)
        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(make_profile_reply(), keymaps, magnetics)

    def test_mismatched_profile_and_keymap_metadata_cannot_be_projected(self):
        keymaps = make_keymap_replies()
        with self.assertRaises(SnapshotValidationError):
            build_read_only_snapshot(
                make_profile_reply(1),
                keymaps,
                make_magnetic_replies(),
            )


if __name__ == "__main__":
    unittest.main()
