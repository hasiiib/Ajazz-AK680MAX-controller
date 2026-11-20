import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "BOARD_2255_PROTOCOL_EVIDENCE.md"


class Board2255DocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = EVIDENCE.read_text(encoding="utf-8")
        cls.evidence_lower = cls.evidence.lower()

    def test_exact_target_and_incompatible_protocols_are_pinned(self):
        for token in (
            "RY1B-2255", "3151:502D", "board ID 2255",
            "3151:502C", "0C45:80B2",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.evidence)

    def test_family_evidence_is_not_misrepresented_as_target_hardware(self):
        for token in ("2268", "2116", "3708"):
            with self.subTest(token=token):
                self.assertIn(token.lower(), self.evidence_lower)
        self.assertTrue(
            any(
                phrase in self.evidence_lower
                for phrase in (
                    "not captured on board 2255",
                    "no board-2255 hardware capture",
                    "no target-board capture",
                )
            ),
            "Magnetic GET evidence must remain explicitly unverified on board 2255.",
        )
        self.assertIn("upstream source ambiguity", self.evidence_lower)
        self.assertIn("not verified on board 2255", self.evidence_lower)

    def test_stock_firmware_host_software_and_custom_firmware_are_distinguished(self):
        for token in ("stock firmware", "host configurator", "custom firmware", "firmware image"):
            with self.subTest(token=token):
                self.assertIn(token, self.evidence_lower)
        self.assertIn("has not flashed firmware", self.evidence_lower)
        self.assertIn("Single-Mode Wired Dual-Mode Magnetic Switch", self.evidence)
        self.assertIn("Single-Mode Wired RGB", self.evidence)
        self.assertIn("8+1K", self.evidence)
        self.assertIn("8+8K", self.evidence)

    def test_application_code_never_targets_incompatible_board_protocols(self):
        forbidden = ("3151:502c", "0x502c", "0c45:80b2", "0x80b2")
        source_paths = list((ROOT / "app").rglob("*.py")) + list((ROOT / "udev").glob("*"))
        for source_path in source_paths:
            source = source_path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                with self.subTest(path=source_path.relative_to(ROOT), token=token):
                    self.assertNotIn(token, source)
        protocol = (ROOT / "app" / "protocol.py").read_text(encoding="utf-8")
        self.assertIn("PRODUCT_ID = 0x502D", protocol)

    def test_public_docs_link_evidence_and_keep_analog_unverified(self):
        for path in ("README.md", "PROJECT_STATUS.md", "ROADMAP.md", "HARDWARE_VERIFICATION.md"):
            doc_path = ROOT / path if path != "HARDWARE_VERIFICATION.md" else ROOT / "docs" / path
            content = doc_path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIn("BOARD_2255_PROTOCOL_EVIDENCE.md", content)
        self.assertIn("not verified on physical board 2255", (ROOT / "README.md").read_text(encoding="utf-8").lower())
        self.assertIn("not verified on physical board 2255", (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8").lower())


    def test_first_hardware_stage_is_one_read_only_084_capture(self):
        plan = (ROOT / "docs" / "HARDWARE_VERIFICATION.md").read_text(encoding="utf-8")
        for token in (
            "Stage 1 request envelope (0x84 only)",
            "Byte 7: `0x7B`",
            "65-byte host buffer",
            "Stage 1 physical test is complete for one user-initiated `0x84` GET",
            "The capture was reviewed offline with the existing parser",
            "do not rerun it merely to reproduce the result",
            "Do not continue to another opcode",
            "app/capture_active_profile.py",
            "~/.local/opt/ak680-controller/capture_active_profile.py",
            "--confirm-one-read-only-0x84",
            "never retries either command",
            "same handle",
            "one `0x84` GET",
        ):
            with self.subTest(token=token):
                self.assertIn(token, plan)
    def test_magnetic_stage_three_capture_is_recorded_without_overclaiming(self):
        plan = (ROOT / "docs" / "HARDWARE_VERIFICATION.md").read_text(encoding="utf-8")
        evidence = (ROOT / "docs" / "BOARD_2255_PROTOCOL_EVIDENCE.md").read_text(encoding="utf-8")
        for token in (
            "Stage 3 physical magnetic capture record",
            "65/65",
            "32 little-endian 16-bit values",
            "every value is decimal 200",
            "raw protocol units",
            "Other sub-operations/pages and value meanings remain unverified",
        ):
            with self.subTest(token=token):
                self.assertIn(token.lower(), (plan + evidence).lower())
        self.assertIn("not connected to HID", (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8").lower())

if __name__ == "__main__":
    unittest.main()
