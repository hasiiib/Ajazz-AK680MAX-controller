import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from diagnostics import build_diagnostic_report, redact_serial_numbers


class DiagnosticPrivacyTests(unittest.TestCase):
    def test_redacts_common_serial_fields_and_preserves_other_diagnostics(self):
        source = (
            "ID_SERIAL_SHORT=ABCDEF123456\n"
            "ID_SERIAL=USB-UNIQUE-123456\n"
            "serialNumber=CAMEL-UNIQUE-654321\n"
            "iSerialNumber: 7\n"
            "Serial Number: UNIQUE-987654\n"
            "USB ID 3151:502d\n"
            "Interface 2: Feature control"
        )
        safe = redact_serial_numbers(source)
        self.assertNotIn("ABCDEF123456", safe)
        self.assertNotIn("USB-UNIQUE-123456", safe)
        self.assertNotIn("CAMEL-UNIQUE-654321", safe)
        self.assertNotIn("UNIQUE-987654", safe)
        self.assertNotIn("iSerialNumber: 7", safe)
        self.assertIn("ID_SERIAL_SHORT=[REDACTED]", safe)
        self.assertIn("ID_SERIAL=[REDACTED]", safe)
        self.assertIn("serialNumber=[REDACTED]", safe)
        self.assertIn("USB ID 3151:502d", safe)
        self.assertIn("Interface 2: Feature control", safe)

    def test_report_marks_read_only_and_analog_verification_limit(self):
        timestamp = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
        report = build_diagnostic_report(
            "ID_SERIAL_SHORT=private-serial\nUSB 3151:502d",
            generated_at=timestamp,
        )
        self.assertIn("3151:502D", report)
        self.assertIn("no configuration writes were sent", report)
        self.assertIn("NOT YET VERIFIED", report)
        self.assertNotIn("private-serial", report)
        self.assertIn("USB 3151:502d", report)

    def test_report_rejects_naive_timestamp(self):
        with self.assertRaises(ValueError):
            build_diagnostic_report(
                "USB inventory",
                generated_at=datetime(2026, 11, 20, 12, 0),
            )


if __name__ == "__main__":
    unittest.main()
