import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from offline_snapshot_import import (
    BUNDLE_FORMAT,
    SnapshotImportError,
    import_snapshot_bundle_text,
)


def make_bundle():
    active = bytearray(64)
    active[0] = 0x84
    active[1] = 1
    return {
        "format": BUNDLE_FORMAT,
        "target": {"vid_pid": "3151:502D", "board_id": 2255},
        "active_profile_reply": active.hex(" "),
        "keymap_replies": [
            {"sublayer": 0, "page": page, "raw_hex": (bytes([page, 0x11, 0x22, 0x33]) * 16).hex(" ")}
            for page in range(8)
        ],
        "magnetic_replies": [
            {"subop": 0, "page": page, "raw_hex": (bytes([page, 0x02]) * 32).hex(" ")}
            for page in range(4)
        ],
    }


class OfflineSnapshotImportTests(unittest.TestCase):
    def test_imports_complete_self_declared_target_bundle(self):
        snapshot = import_snapshot_bundle_text(json.dumps(make_bundle()))
        self.assertEqual(snapshot.active_profile, 1)
        self.assertEqual(len(snapshot.keymap_layers[0].entries), 128)
        self.assertEqual(snapshot.keymap_layers[0].entries[0], bytes([0, 0x11, 0x22, 0x33]))
        self.assertEqual(snapshot.keymap_layers[0].entries[16], bytes([1, 0x11, 0x22, 0x33]))
        self.assertEqual(len(snapshot.magnetic_columns[0].values), 128)
        self.assertEqual(snapshot.magnetic_columns[0].values[0], 512)
        self.assertEqual(snapshot.magnetic_columns[0].values[32], 513)

    def test_missing_keymap_page_rejects_incomplete_bundle(self):
        bundle = make_bundle()
        bundle["keymap_replies"].pop()
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))

    def test_missing_magnetic_page_rejects_incomplete_column(self):
        bundle = make_bundle()
        bundle["magnetic_replies"].pop()
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))

    def test_duplicate_keymap_and_magnetic_pages_are_rejected(self):
        for field in ("keymap_replies", "magnetic_replies"):
            bundle = make_bundle()
            bundle[field].append(bundle[field][0])
            with self.subTest(field=field), self.assertRaises(SnapshotImportError):
                import_snapshot_bundle_text(json.dumps(bundle))

    def test_wrong_target_declaration_is_rejected(self):
        bundle = make_bundle()
        bundle["target"]["board_id"] = 2336
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))

    def test_unknown_fields_are_rejected_including_serial_metadata(self):
        bundle = make_bundle()
        bundle["serial_number"] = "not allowed"
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))
        bundle = make_bundle()
        bundle["target"]["serial"] = "not allowed"
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))

    def test_bad_hex_and_wrong_response_lengths_are_rejected(self):
        bundle = make_bundle()
        bundle["keymap_replies"][0]["raw_hex"] = "not hex"
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))
        bundle = make_bundle()
        bundle["keymap_replies"][0]["raw_hex"] = bytes(63).hex(" ")
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))

    def test_nonzero_report_id_prefix_is_rejected(self):
        bundle = make_bundle()
        bundle["magnetic_replies"][0]["raw_hex"] = (bytes([1]) + bytes(64)).hex(" ")
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))

    def test_boolean_page_metadata_is_rejected(self):
        bundle = make_bundle()
        bundle["keymap_replies"][0]["page"] = True
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))

    def test_json_format_and_root_shape_are_rejected(self):
        for raw in ("not json", "[]", json.dumps({}), json.dumps({**make_bundle(), "format": "other"})):
            with self.subTest(raw=raw[:20]), self.assertRaises(SnapshotImportError):
                import_snapshot_bundle_text(raw)

    def test_empty_reply_lists_and_size_limit_are_rejected(self):
        bundle = make_bundle()
        bundle["keymap_replies"] = []
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(json.dumps(bundle))
        with self.assertRaises(SnapshotImportError):
            import_snapshot_bundle_text(" " * (256 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
