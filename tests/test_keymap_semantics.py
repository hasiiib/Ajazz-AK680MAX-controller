import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from keymap_semantics import describe_key_entry


class KeymapSemanticsTests(unittest.TestCase):
    def test_unassigned_base_layer_entry(self):
        self.assertEqual(describe_key_entry(bytes(4)), "Unassigned")

    def test_common_keyboard_usages_are_named(self):
        self.assertEqual(describe_key_entry(bytes([0, 0, 0x04, 0])), "A")
        self.assertEqual(describe_key_entry(bytes([0, 0, 0x1E, 0])), "1")
        self.assertEqual(describe_key_entry(bytes([0, 0, 0x28, 0])), "Enter")
        self.assertEqual(describe_key_entry(bytes([0, 0, 0xE1, 0])), "Left Shift")
        self.assertEqual(describe_key_entry(bytes([0, 0, 0x52, 0])), "Up")

    def test_consumer_controls_are_decoded_from_documented_shape(self):
        self.assertEqual(describe_key_entry(bytes([3, 0, 0xE9, 0x00])), "Volume Up")
        self.assertEqual(describe_key_entry(bytes([3, 0, 0xCD, 0x00])), "Play / Pause")

    def test_macro_mode_and_index_are_reported(self):
        self.assertEqual(describe_key_entry(bytes([9, 0, 0, 0])), "Macro 1 (repeat)")
        self.assertEqual(describe_key_entry(bytes([9, 1, 4, 0])), "Macro 5 (toggle)")
        self.assertEqual(describe_key_entry(bytes([9, 2, 2, 0])), "Macro 3 (while held)")

    def test_documented_special_functions_are_named(self):
        self.assertEqual(describe_key_entry(bytes([10, 1, 0, 0])), "Fn")
        self.assertEqual(describe_key_entry(bytes([10, 12, 0, 0])), "Power save")
        self.assertEqual(describe_key_entry(bytes([10, 17, 0, 0])), "Caps LED swap")

    def test_opaque_and_unknown_shapes_are_not_guessed(self):
        self.assertEqual(
            describe_key_entry(bytes([0, 1, 4, 0])),
            "HID combination / extended usage (raw)",
        )
        self.assertEqual(describe_key_entry(bytes([1, 0, 1, 0])), "Mouse button (raw)")
        self.assertEqual(describe_key_entry(bytes([0xFE, 1, 2, 3])), "Unknown assignment (raw)")

    def test_rejects_non_four_byte_entries(self):
        for entry in (b"", b"123", b"12345", "abcd", None):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    describe_key_entry(entry)


if __name__ == "__main__":
    unittest.main()
