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
        for token in ("2268", "2116", "3708", "not captured on board 2255"):
            with self.subTest(token=token):
                self.assertIn(token.lower(), self.evidence_lower)
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
            "one explicitly user-started `0x84` GET",
            "assess_hex_capture(\"active-profile\", \"...\")",
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
if __name__ == "__main__":
    unittest.main()
