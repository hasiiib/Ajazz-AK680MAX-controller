"""Offline assessment of manually captured, read-only board responses.

This module never opens HID devices, sends commands, retries requests, or
persists captures. It validates a caller-supplied byte sequence and returns a
copyable raw-hex record plus parser outcome for review.
"""
from __future__ import annotations

from dataclasses import dataclass

from active_profile import ProfileProtocolError, parse_active_profile_reply
from keymap import KeymapProtocolError, parse_keymap_page
from magnetic_settings import (
    MagneticSettingsProtocolError,
    parse_magnetic_settings_page,
)


@dataclass(frozen=True)
class CaptureAssessment:
    """Privacy-minimal assessment of one manually supplied response."""

    stage: str
    raw_length: int
    report_id_prefix: bool
    normalized_length: int | None
    accepted: bool
    summary: str
    raw_hex: str


def _raw_bytes(raw: bytes | bytearray) -> bytes:
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("Captured response must be bytes or bytearray.")
    return bytes(raw)


def _frame_details(data: bytes) -> tuple[bool, int | None]:
    if len(data) == 65 and data[0] == 0:
        return True, 64
    if len(data) == 64:
        return False, 64
    return False, None


def assess_capture(
    stage: str,
    raw: bytes | bytearray,
    *,
    profile: int | None = None,
    sublayer: int = 0,
    page: int = 0,
    subop: int | None = None,
) -> CaptureAssessment:
    """Assess one 0x84, 0x8A, or 0xE5 reply without performing device I/O.

    Required metadata is explicit for matrix pages. The returned raw_hex is
    the exact supplied byte sequence, including any report-ID prefix.
    """
    data = _raw_bytes(raw)
    prefix, normalized_length = _frame_details(data)
    raw_hex = data.hex(" ").upper()

    try:
        if stage == "active-profile":
            if any(value is not None for value in (profile, subop)):
                raise ValueError("Active-profile assessment takes no profile or subop.")
            if sublayer != 0 or page != 0:
                raise ValueError("Active-profile assessment takes no page metadata.")
            value = parse_active_profile_reply(data)
            summary = f"Accepted 0x84 reply; active profile index {value}."
        elif stage == "keymap":
            if not isinstance(profile, int) or isinstance(profile, bool):
                raise ValueError("Keymap assessment requires an integer profile.")
            if subop is not None:
                raise ValueError("Keymap assessment does not take a magnetic subop.")
            parsed = parse_keymap_page(profile, page, sublayer, data)
            summary = (
                f"Accepted raw 0x8A page; profile {parsed.profile}, "
                f"sublayer {parsed.sublayer}, page {parsed.page}, "
                f"first slot {parsed.first_slot}, 16 opaque entries."
            )
        elif stage == "magnetic":
            if not isinstance(subop, int) or isinstance(subop, bool):
                raise ValueError("Magnetic assessment requires an integer subop.")
            if profile is not None or sublayer != 0:
                raise ValueError("Magnetic assessment takes no profile or sublayer.")
            parsed = parse_magnetic_settings_page(subop, page, data)
            summary = (
                f"Accepted raw 0xE5 page; subop {parsed.subop}, page {parsed.page}, "
                f"first slot {parsed.first_slot}, {len(parsed.values)} values "
                f"at {parsed.value_width} byte(s) each."
            )
        else:
            raise ValueError(
                "Unknown capture stage; expected 'active-profile', 'keymap', or 'magnetic'."
            )
    except (ProfileProtocolError, KeymapProtocolError, MagneticSettingsProtocolError, ValueError) as exc:
        return CaptureAssessment(
            stage=stage,
            raw_length=len(data),
            report_id_prefix=prefix,
            normalized_length=normalized_length,
            accepted=False,
            summary=f"Rejected: {exc}",
            raw_hex=raw_hex,
        )

    return CaptureAssessment(
        stage=stage,
        raw_length=len(data),
        report_id_prefix=prefix,
        normalized_length=normalized_length,
        accepted=True,
        summary=summary,
        raw_hex=raw_hex,
    )
