# Project Status

Last updated: 2026-11-20

## Goal
Build a reliable Linux desktop controller for the wired AJAZZ AK680 MAX HE, physical board ID 2255 (USB VID:PID 3151:502D).

## Verified on the physical Ubuntu system
- The keyboard enumerates as USB 3151:502D with HID interfaces 0, 1, and 2.
- Control interface 2 and analog-input interface 1 belong to the same USB device.
- Read-only Identify (0x8F) returned board ID 2255.
- The scoped udev rule grants access, and libusb-backed hidapi successfully opened the control interface.
- The user confirmed the GUI launches and can discover/identify the keyboard.

## Implemented
- PySide6 desktop application with USB/HID discovery.
- Read-only board identification and firmware metadata parsing.
- USB interface pairing checks.
- Automatic connection-state refresh through metadata-only HID enumeration; no periodic device commands.
- Automatic analog-monitor abort when its paired HID interfaces disappear or enumeration/input fails; polling stops, handles close, stale samples clear, and a temporary stop is attempted best-effort.
- Privacy-filtered diagnostic export with serial-number redaction.
- User-local staged installer with rollback protection.
- Automated unit tests and GitHub Actions CI.

## Not yet verified on the physical keyboard
- Live analog stream start, travel reports, hold/release behavior, and disconnect recovery.
- Raw travel units and calibrated travel range.
- Live magnetic settings, keymap, and active-profile reads.
- RGB, remapping, per-key actuation, Rapid Trigger, DKS, macros, and calibration.

## Safety boundaries
- Background connection refresh only enumerates HID metadata; it does not open handles or send commands.
- Identify remains user-initiated and read-only.
- Analog streaming remains user-initiated and temporary.
- The magnetic, keymap, and active-profile modules are pure parser/request-builder code only; they are not connected to HID or the GUI.
- Do not add persistent configuration writes, calibration, reset, or firmware operations until exact board-2255 behavior is verified and the user explicitly authorizes them.
- Never publish the keyboard's unique serial number.
- Never run the GUI with sudo.

## Latest automated verification
The latest CI run passed **71 tests** on commit `3d2fd03c74afd1df72bd92c0932c0fc093d2d29c`, including five regression tests for metadata-only automatic connection refresh, GUI inventory reuse, and diagnostic formatting: https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44765017962.
