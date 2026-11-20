"""Privacy-conscious text diagnostics for the Linux companion app.

Only caller-supplied diagnostic text is included. Serial-number fields are
redacted before export; no HID device is opened and no protocol command is sent.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

_SERIAL_PATTERNS = (
    re.compile(r"(\b(?:iSerialNumber|serial(?:_number)?|ID_SERIAL_SHORT)\s*[:=]\s*)(\S+)", re.IGNORECASE),
    re.compile(r"(\bSerial Number\s*:\s*)(\S+)", re.IGNORECASE),
    re.compile(r"(\bserial\s+)([A-Za-z0-9_-]{6,})", re.IGNORECASE),
)


def redact_serial_numbers(text: str) -> str:
    """Redact common USB/HID serial-number fields while preserving labels."""
    result = str(text)
    for pattern in _SERIAL_PATTERNS:
        result = pattern.sub(r"\1[REDACTED]", result)
    return result


def build_diagnostic_report(
    scan_text: str,
    generated_at: datetime | None = None,
) -> str:
    """Build a timestamped support report without serial-number values."""
    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    safe_scan = redact_serial_numbers(scan_text).strip()
    return (
        "AJAZZ AK680 Controller — Diagnostic Report\n"
        f"Generated: {timestamp.astimezone().isoformat(timespec='seconds')}\n"
        "Hardware identity: USB VID:PID 3151:502D (serial number omitted)\n"
        "Safety: diagnostics are read-only; no configuration writes were sent.\n"
        "Physical analog stream verification: NOT YET VERIFIED.\n"
        "\n"
        "=== USB / HID DISCOVERY ===\n"
        f"{safe_scan or 'No discovery output available.'}\n"
    )
