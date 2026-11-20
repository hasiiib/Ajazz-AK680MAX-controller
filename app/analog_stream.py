"""Opt-in temporary analog-stream experiment for target board 2255.

The board identity and HID interface pairing were physically verified, but
the 0x1B command transport, report framing, stop behavior, and travel scale
have not been verified on this physical keyboard. Raw values remain counts
with unknown physical units and calibrated range. Other gen2 firmware notes
describe the stream flag as volatile; that behavior is not confirmed here.
This module contains no persistent configuration writes.
"""
from __future__ import annotations

import os

from protocol import (
    ANALOG_REPORT_LENGTH,
    AnalogSample,
    identify_keyboard_details,
    inspect_keyboard_interfaces,
    paired_keyboard_interfaces,
    parse_analog_report,
)

VENDOR_ID = 0x3151
PRODUCT_ID = 0x502D
EXPECTED_BOARD_ID = 2255
CONTROL_INTERFACE = 2
INPUT_INTERFACE = 1
STREAM_OPCODE = 0x1B
MAX_REPORTS_PER_POLL = 128


class AnalogStreamError(RuntimeError):
    """The analog stream-control operation could not be started or read safely."""


def stream_control_packet(enabled: bool) -> bytes:
    """Build a 64-byte gen2 Bit7 Feature command (0x1B start/stop)."""
    packet = bytearray(64)
    packet[0] = STREAM_OPCODE
    packet[1] = 1 if enabled else 0
    packet[7] = (0xFF - (sum(packet[:7]) & 0xFF)) & 0xFF
    return bytes(packet)


class AnalogStreamSession:
    """Own paired HID handles; 0x1B volatility is unverified on board 2255."""

    def __init__(self, hid_module=None):
        self._hid = hid_module
        self._control = None
        self._input = None
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def _hid_module(self):
        if self._hid is None:
            try:
                import hid
            except ImportError as exc:
                raise AnalogStreamError(
                    "The hidapi package is missing; reinstall the application."
                ) from exc
            self._hid = hid
        return self._hid

    @staticmethod
    def _send_flag(device, enabled: bool) -> None:
        report = bytes([0]) + stream_control_packet(enabled)
        sent = device.send_feature_report(report)
        if sent != len(report):
            raise AnalogStreamError(
                f"hidapi sent an incomplete analog stream command ({sent}/{len(report)} bytes)."
            )

    def start(self) -> None:
        if self._active:
            return
        hid = self._hid_module()

        # Re-identify before the 0x1B command; its target-board effect is unverified.
        try:
            identity = identify_keyboard_details()
        except Exception as exc:
            raise AnalogStreamError(f"Read-only identity check failed: {exc}") from exc
        if identity.device_id != EXPECTED_BOARD_ID:
            raise AnalogStreamError(
                f"Refusing analog stream: expected board {EXPECTED_BOARD_ID}, "
                f"keyboard reported {identity.device_id}."
            )

        try:
            inventory = inspect_keyboard_interfaces(hid)
        except Exception as exc:
            raise AnalogStreamError(f"Could not inspect HID interfaces: {exc}") from exc
        pair = paired_keyboard_interfaces(inventory)
        if pair is None:
            raise AnalogStreamError(
                "Refusing analog stream: interface 2 and interface 1 are not "
                "a unique pair on the same physical USB device."
            )
        control_info, input_info = pair
        if not control_info.get("path") or not input_info.get("path"):
            raise AnalogStreamError("The paired HID interface path is missing.")

        # Retain each handle as soon as it is created so a failure while
        # allocating the second handle cannot leak the first one.
        try:
            self._control = hid.device()
            self._input = hid.device()
        except Exception as exc:
            self._close_handles()
            raise AnalogStreamError(f"Could not create HID handles: {exc}") from exc
        control = self._control
        input_device = self._input
        enable_attempted = False
        try:
            control.open_path(os.fsencode(control_info["path"]))
            input_device.open_path(os.fsencode(input_info["path"]))
            enable_attempted = True
            self._send_flag(control, True)
            self._active = True
        except Exception as exc:
            # A failed SET may have reached the device; make a best-effort stop.
            if enable_attempted:
                try:
                    self._send_flag(control, False)
                except Exception:
                    pass
            self._close_handles()
            if isinstance(exc, AnalogStreamError):
                raise
            raise AnalogStreamError(f"Could not start analog stream: {exc}") from exc

    def poll(self, max_reports: int = 128) -> list[AnalogSample]:
        if type(max_reports) is not int or not 1 <= max_reports <= MAX_REPORTS_PER_POLL:
            raise AnalogStreamError(
                f"max_reports must be an integer from 1 to {MAX_REPORTS_PER_POLL}."
            )
        if not self._active or self._input is None:
            return []
        samples = []
        try:
            for _ in range(max_reports):
                raw = self._input.read(ANALOG_REPORT_LENGTH, 0)
                if not raw:
                    break
                sample = parse_analog_report(bytes(raw))
                if sample is not None:
                    samples.append(sample)
        except Exception as exc:
            # Do not leave the stream running if a caller forgets to
            # perform GUI-level abort handling after an input transport error.
            cleanup_error = None
            try:
                self.stop()
            except AnalogStreamError as stop_exc:
                cleanup_error = stop_exc
            message = f"Analog input read failed: {exc}"
            if cleanup_error is not None:
                message += f"; stream stop also failed: {cleanup_error}"
            raise AnalogStreamError(message) from exc
        return samples

    def _close_handles(self) -> None:
        for device in (self._input, self._control):
            if device is not None:
                try:
                    device.close()
                except Exception:
                    pass
        self._input = None
        self._control = None
        self._active = False

    def stop(self) -> None:
        if self._control is not None and self._active:
            try:
                self._send_flag(self._control, False)
            except Exception as exc:
                raise AnalogStreamError(
                    f"Could not confirm analog stream stop: {exc}"
                ) from exc
            finally:
                self._close_handles()
        else:
            self._close_handles()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False
