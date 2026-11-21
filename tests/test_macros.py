import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from macros import (
    MACRO_GET_OPCODE,
    MACRO_SET_OPCODE,
    MacroDefinition,
    MacroKeyEvent,
    MacroMouseButtonEvent,
    MacroMouseMoveEvent,
    MacroProtocolError,
    assemble_macro_blob,
    build_macro_write_packets,
    decode_macro,
    encode_macro,
    macro_get_packet,
    macro_write_page_count,
    parse_macro_page,
)


class MacroProtocolTests(unittest.TestCase):
    def test_get_packet_is_bit7_checksummed(self):
        packet = macro_get_packet(49, 3)
        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[:3], bytes([MACRO_GET_OPCODE, 49, 3]))
        self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packet[8:], bytes(56))

    def test_get_packet_rejects_invalid_slot_and_page(self):
        for slot, page in ((-1, 0), (50, 0), (0, -1), (0, 4), (True, 0)):
            with self.subTest(slot=slot, page=page):
                with self.assertRaises(MacroProtocolError):
                    macro_get_packet(slot, page)

    def test_page_parser_and_blob_assembly(self):
        pages = {page: bytes([page + 1]) * 64 for page in range(4)}
        self.assertEqual(parse_macro_page(bytes([0]) + pages[0]), pages[0])
        blob = assemble_macro_blob(pages)
        self.assertEqual(len(blob), 256)
        for page in range(4):
            self.assertEqual(blob[page * 64:(page + 1) * 64], pages[page])

    def test_page_parser_rejects_wrong_lengths_and_incomplete_assembly(self):
        for data in (b"", bytes(63), bytes(66), "x" * 64):
            with self.subTest(length=len(data)):
                with self.assertRaises(MacroProtocolError):
                    parse_macro_page(data)
        with self.assertRaises(MacroProtocolError):
            assemble_macro_blob({0: bytes(64), 1: bytes(64)})

    def test_macro_event_round_trip_short_and_long_delays(self):
        definition = MacroDefinition(
            repeat=3,
            events=(
                MacroKeyEvent(0x0B, True, 20),
                MacroKeyEvent(0x0B, False, 0),
                MacroKeyEvent(0x0C, True, 128),
                MacroMouseButtonEvent(0, True, 10),
                MacroMouseButtonEvent(4, False, 250),
                MacroMouseMoveEvent(-12, 34, 40),
            ),
        )
        blob = encode_macro(definition)
        self.assertEqual(len(blob), 256)
        self.assertEqual(decode_macro(blob), definition)

    def test_empty_macro_encodes_zero_terminator_and_repeat_header(self):
        blob = encode_macro(MacroDefinition(0, ()))
        self.assertEqual(blob, bytes(256))
        self.assertEqual(decode_macro(blob), MacroDefinition(0, ()))

    def test_macro_encoding_rejects_out_of_range_event_values(self):
        invalid_definitions = (
            MacroDefinition(1, (MacroKeyEvent(3, True, 20),)),
            MacroDefinition(1, (MacroKeyEvent(4, 1, 20),)),
            MacroDefinition(1, (MacroKeyEvent(4, True, 65536),)),
            MacroDefinition(1, (MacroMouseButtonEvent(5, True, 1),)),
            MacroDefinition(1, (MacroMouseMoveEvent(128, 0, 1),)),
            MacroDefinition(1, (MacroMouseMoveEvent(0, -129, 1),)),
            MacroDefinition(1, (MacroMouseMoveEvent(0, 0, 256),)),
        )
        for definition in invalid_definitions:
            with self.subTest(definition=definition):
                with self.assertRaises(MacroProtocolError):
                    encode_macro(definition)
        with self.assertRaises(MacroProtocolError):
            encode_macro(MacroDefinition(1, (MacroKeyEvent(4, True, 20),) * 126))

    def test_write_pages_are_bounded_and_last_flag_is_on_final_page(self):
        blob = bytes(range(256))
        packets = build_macro_write_packets(7, blob)
        self.assertEqual(len(packets), 5)
        for page, packet in enumerate(packets):
            self.assertEqual(len(packet), 64)
            self.assertEqual(packet[0], MACRO_SET_OPCODE)
            self.assertEqual(packet[1:6], bytes([7, page, 56, int(page == 4), 0]))
            self.assertEqual(packet[7], (0xFF - sum(packet[:7])) & 0xFF)
        self.assertEqual(packets[0][8:64], blob[:56])
        self.assertEqual(packets[3][8:64], blob[168:224])
        self.assertEqual(packets[4][8:40], blob[224:256])
        self.assertEqual(packets[4][40:], bytes(24))

    def test_short_and_empty_macro_uploads_use_minimal_safe_page_prefix(self):
        blob = encode_macro(MacroDefinition(
            1, (MacroKeyEvent(0x04, True, 10), MacroKeyEvent(0x04, False, 10))
        ))
        self.assertEqual(macro_write_page_count(blob), 1)
        self.assertEqual(len(build_macro_write_packets(0, blob)), 1)
        clear = bytes(256)
        packets = build_macro_write_packets(49, clear)
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][4], 1)
        self.assertEqual(packets[0][8:], bytes(56))

    def test_macro_write_rejects_invalid_slot_or_blob(self):
        for slot, blob in ((-1, bytes(256)), (50, bytes(256)), (0, bytes(255))):
            with self.subTest(slot=slot, length=len(blob)):
                with self.assertRaises(MacroProtocolError):
                    build_macro_write_packets(slot, blob)


if __name__ == "__main__":
    unittest.main()
