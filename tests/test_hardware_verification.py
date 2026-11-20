import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from hardware_verification import assess_capture, assess_hex_capture


class HardwareCaptureAssessmentTests(unittest.TestCase):
    def test_active_profile_capture_accepts_opcode_echo_and_reports_metadata(self):
        reply = bytearray(64)
        reply[0] = 0x84
        reply[1] = 2
        result = assess_capture("active-profile", reply)
        self.assertTrue(result.accepted)
        self.assertEqual(result.raw_length, 64)
        self.assertFalse(result.report_id_prefix)
        self.assertEqual(result.normalized_length, 64)
        self.assertIn("profile index 2", result.summary)
        self.assertEqual(result.raw_hex.split()[:2], ["84", "02"])

    def test_active_profile_capture_accepts_leading_zero_report_id(self):
        reply = bytearray(64)
        reply[0] = 0x84
        reply[1] = 1
        result = assess_capture("active-profile", bytes([0]) + reply)
        self.assertTrue(result.accepted)
        self.assertTrue(result.report_id_prefix)
        self.assertEqual(result.raw_length, 65)
        self.assertEqual(result.normalized_length, 64)

    def test_keymap_page_does_not_require_opcode_echo(self):
        # The first payload byte is deliberately not 0x8A.
        raw = bytes([0xE5]) + bytes(63)
        result = assess_capture("keymap", raw, profile=1, sublayer=2, page=3)
        self.assertTrue(result.accepted)
        self.assertIn("16 opaque entries", result.summary)
        self.assertTrue(result.raw_hex.startswith("E5 00"))

    def test_magnetic_page_does_not_require_opcode_echo(self):
        raw = bytes([0x84]) + bytes(63)
        result = assess_capture("magnetic", raw, subop=5, page=0)
        self.assertTrue(result.accepted)
        self.assertIn("64 values", result.summary)
        self.assertTrue(result.raw_hex.startswith("84 00"))

    def test_malformed_frames_are_rejected_without_repair(self):
        for raw in (bytes(63), bytes([1]) + bytes(64), bytes([0]) + bytes(65)):
            with self.subTest(length=len(raw)):
                result = assess_capture("active-profile", raw)
                self.assertFalse(result.accepted)
                self.assertEqual(result.raw_length, len(raw))
                self.assertEqual(len(result.raw_hex.split()), len(raw))

    def test_unknown_stage_and_invalid_metadata_are_rejected(self):
        cases = (
            ("unknown", bytes(64), {}),
            ("keymap", bytes(64), {"profile": True}),
            ("magnetic", bytes(64), {"subop": 8}),
            ("active-profile", bytes(64), {"page": 1}),
        )
        for stage, raw, kwargs in cases:
            with self.subTest(stage=stage, kwargs=kwargs):
                result = assess_capture(stage, raw, **kwargs)
                self.assertFalse(result.accepted)
                self.assertIn("Rejected:", result.summary)

    def test_hex_capture_accepts_common_whitespace_and_preserves_bytes(self):
        result = assess_hex_capture("active-profile", "84 02 " + "00 " * 62)
        self.assertTrue(result.accepted)
        self.assertEqual(result.raw_length, 64)
        self.assertEqual(result.raw_hex.split()[:2], ["84", "02"])

    def test_hex_capture_rejects_incomplete_or_decorated_input(self):
        for raw_hex in ("84 0", "0x84 02", "84:02", "not hex"):
            with self.subTest(raw_hex=raw_hex):
                with self.assertRaises(ValueError):
                    assess_hex_capture("active-profile", raw_hex)

    def test_hex_capture_requires_text(self):
        with self.assertRaises(TypeError):
            assess_hex_capture("active-profile", bytes(64))

    def test_non_byte_capture_is_rejected_at_boundary(self):
        for raw in (64, "x" * 64, None):
            with self.subTest(raw_type=type(raw).__name__):
                with self.assertRaises(TypeError):
                    assess_capture("active-profile", raw)

    def test_raw_capture_is_copied_and_unchanged(self):
        raw = bytearray(64)
        raw[0] = 0x84
        raw[1] = 3
        result = assess_capture("active-profile", raw)
        raw[1] = 0
        self.assertTrue(result.accepted)
        self.assertEqual(result.raw_hex.split()[:2], ["84", "03"])


if __name__ == "__main__":
    unittest.main()
