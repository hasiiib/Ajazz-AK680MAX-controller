import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from macro_archive import (
    ARCHIVE_FORMAT,
    MacroArchiveError,
    MacroCaptureArchive,
    archive_from_pages,
    export_macro_archive_text,
    import_macro_archive_text,
)


def make_archive_data():
    return {
        "format": ARCHIVE_FORMAT,
        "target": {"vid_pid": "3151:502D", "board_id": 2255},
        "slot": 12,
        "pages": [
            {"page": page, "raw_hex": (bytes([page + 1]) * 64).hex(" ")}
            for page in range(4)
        ],
    }


class MacroArchiveTests(unittest.TestCase):
    def test_import_export_round_trip_preserves_all_raw_bytes(self):
        pages = {page: bytes([page * 17 + value for value in range(64)]) for page in range(4)}
        archive = archive_from_pages(49, pages)
        self.assertEqual(len(archive.blob), 256)
        restored = import_macro_archive_text(export_macro_archive_text(archive))
        self.assertEqual(restored, archive)
        self.assertEqual(restored.blob, b"".join(pages[index] for index in range(4)))

    def test_import_accepts_report_id_prefixed_capture_pages(self):
        data = make_archive_data()
        for item in data["pages"]:
            item["raw_hex"] = (bytes([0]) + bytes.fromhex(item["raw_hex"])).hex(" ")
        archive = import_macro_archive_text(json.dumps(data))
        self.assertEqual(archive.pages[0], bytes([1]) * 64)

    def test_archive_from_pages_requires_exact_complete_page_set(self):
        for pages in ({0: bytes(64)}, {0: bytes(64), 1: bytes(64), 2: bytes(64), 4: bytes(64)}):
            with self.subTest(keys=tuple(pages)), self.assertRaises(MacroArchiveError):
                archive_from_pages(0, pages)

    def test_rejects_duplicate_missing_and_invalid_page_indices(self):
        for mutate in (
            lambda d: d["pages"].append(d["pages"][0]),
            lambda d: d["pages"].pop(),
            lambda d: d["pages"][0].update(page=4),
            lambda d: d["pages"][0].update(page=True),
        ):
            data = make_archive_data()
            mutate(data)
            with self.subTest(pages=data["pages"]), self.assertRaises(MacroArchiveError):
                import_macro_archive_text(json.dumps(data))

    def test_rejects_bad_payloads_and_target_claims(self):
        data = make_archive_data()
        data["pages"][0]["raw_hex"] = bytes(63).hex()
        with self.assertRaises(MacroArchiveError):
            import_macro_archive_text(json.dumps(data))
        data = make_archive_data()
        data["target"]["board_id"] = 2336
        with self.assertRaises(MacroArchiveError):
            import_macro_archive_text(json.dumps(data))

    def test_rejects_unknown_fields_including_serial_metadata(self):
        data = make_archive_data()
        data["serial_number"] = "private"
        with self.assertRaises(MacroArchiveError):
            import_macro_archive_text(json.dumps(data))
        data = make_archive_data()
        data["target"]["serial"] = "private"
        with self.assertRaises(MacroArchiveError):
            import_macro_archive_text(json.dumps(data))

    def test_rejects_invalid_slots_and_boolean_metadata(self):
        for slot in (-1, 50, True):
            data = make_archive_data()
            data["slot"] = slot
            with self.subTest(slot=slot), self.assertRaises(MacroArchiveError):
                import_macro_archive_text(json.dumps(data))

    def test_rejects_invalid_json_format_and_size(self):
        for value in ("not json", "[]", json.dumps({**make_archive_data(), "format": "other"})):
            with self.subTest(value=value[:10]), self.assertRaises(MacroArchiveError):
                import_macro_archive_text(value)
        with self.assertRaises(MacroArchiveError):
            import_macro_archive_text(" " * (16 * 1024 + 1))

    def test_export_rejects_unvalidated_objects(self):
        with self.assertRaises(MacroArchiveError):
            export_macro_archive_text(None)


if __name__ == "__main__":
    unittest.main()
