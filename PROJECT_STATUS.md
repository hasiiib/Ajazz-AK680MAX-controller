# Project Status

Last updated: 2026-11-20

## Goal
Build a polished Linux desktop controller for the wired AJAZZ AK680 MAX HE (board 2255), with hardware behavior verified before features are advertised.

## Verified on the user's physical Ubuntu system
- USB VID:PID: `3151:502D`.
- HID interfaces 0, 1, and 2 enumerate correctly.
- Interface 1 (vendor input Report ID 5) and interface 2 (vendor Feature control) resolve to the same USB parent.
- Read-only Identify opcode `0x8F` returned board ID `2255`, matching the public AK680 MAX gen2 board record.
- The narrowly scoped udev access rule was installed; the USB device node ACL granted the active user read/write access, and libusb-backed hidapi successfully opened interface 2.
- The GUI has launched and its USB/HID discovery and Identify workflow were confirmed by the user.

## Implemented
- PySide6 desktop application and USB/HID inventory.
- Read-only Identify with strict VID/PID/interface selection, response validation, and safe diagnostics.
- Gen2 firmware revision parsing from the Identify reply only; no extra firmware query is sent.
- Linux sysfs pairing check for control/input HID interfaces.
- Opt-in Analog Monitor with fresh board-2255 identity check, paired interface validation, temporary stream start/stop, nonblocking input polling, per-slot raw travel display, and shutdown/error cleanup.
- Staged user-local installer with rollback protection.
- Standard-library unit tests and GitHub Actions workflow.

## Automated verification
- GitHub Actions run for commit `e19b648753ca41c3d144fc67231381c00952db0c`: **success**.
- The workflow's `unittest` job passed **55 tests**, covering Identify, analog stream lifecycle/cleanup, strict magnetic settings pages, keymap pages, active-profile metadata, installer syntax/rollback structure, and udev rule scope.
- Latest workflow: https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44762476803

## Not yet physically verified
- The analog stream has not yet been tested on the physical keyboard.
- Raw travel values have no confirmed physical unit or calibrated full-scale range.
- RGB, remapping, profiles, per-key actuation, Rapid Trigger, DKS, macros, and calibration are not implemented/verified.

## Safety boundaries
- Do not send guessed HID reports.
- Do not add configuration writes, calibration, reset, RGB, remapping, or profile commands until their exact board-2255 behavior and rollback/recovery are understood.
- The stream start/stop flag is temporary by protocol reference, but still requires actual hardware validation before advertising the monitor as working.
- Never publish the keyboard's unique serial number.
- Never run the GUI with sudo; preserve the narrowly scoped udev access model.

## Next development focus
1. Continue code review and improve GUI structure, state presentation, and error recovery without claiming untested hardware behavior.
2. Investigate additional board-2255 protocol features from credible sources, separating read-only operations from writes.
3. Keep physical analog stream validation as a clearly marked release gate.
4. Expand automated tests for lifecycle edge cases and installer safety.
5. Maintain this status and ROADMAP.md as the authoritative current handoff.


## Protocol variant guard (2026-11-20)

A further protocol comparison established that similarly named AK680 MAX variants are not interchangeable. The physical board is 3151:502D / board 2255 / RY1B-2255. A public AK680 MAX lightless implementation targets 3151:502C, while a separate RGB implementation targets 0C45:80B2 and a different 0xAA/0x55 chunk protocol. Those command sets are explicitly excluded from this project. Future controls must be sourced from board-2255 RongYuan evidence only. See [the research note](docs/research/HALLJOY_AK680MAX_PROTOCOL_REFERENCE_2026-11-20.md#variant-separation-similarly-named-ak680-max-protocols-2026-11-20).


## Independent board-2255 capability cross-check (2026-11-20)

The [sharkfin AK680 MAX record](https://getsharkfin.com/boards/ajazzmouse-ak680-max) independently lists the exact 2255 / 3151:502D revision and identifies it as a gen2 magnetic keyboard with four onboard profiles, 18 backlight effects, and per-key actuation/release/Rapid Trigger/dead-zone controls. This confirms that the product family has a richer feature surface worth implementing; it does not prove that every documented sub-command or scale has been physically validated on this particular unit.

The sharkfin protocol reference describes gen2 GET 0xE5 magnetic-setting pages and GET 0x8A keymap pages, but its detailed magnetic handler evidence is firmware-derived from other named gen2 boards. The next software step is to build strict, read-only parsers and tests around these documented response formats while preserving an explicit “not yet hardware-verified on board 2255” state. No magnetic SET (0x65), keymap write, profile write, LED write, reset, or flash command has been sent or implemented.

Reference: [sharkfin ROYUAN protocol reference](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md).


## Read-only magnetic settings parser groundwork (2026-11-20)

Added `app/magnetic_settings.py` as a pure protocol module. It builds the documented gen2 `0xE5` GET page request and parses raw response pages without performing HID I/O. Supported layouts are the documented u16 columns (sub-ops 0–4 and 6), byte columns (5, 7, 9), and read-only four-byte DKS action records (10). It validates sub-operation support, page bounds, exact 64-byte payload length, report-ID prefix handling, little-endian decoding, and slot offsets. The write-only sub-operation 8 and all `0x65` SET operations are excluded.

Automated tests were added for request checksum/layout, supported page ranges, invalid requests, u16 and byte decoding, DKS grouping, report-ID normalization, and malformed pages.

Evidence boundary: the public gen2 reference labels the `0xE5` layout and detailed handlers as firmware-derived from other gen2 boards; the exact AK680 MAX 2255 page independently corroborates that the model is gen2 and supports magnetic settings, but no `0xE5` request or response has been observed on this physical keyboard. This module is deliberately disconnected from the GUI and cannot send a report. Do not enable device reads or show these values as live settings until a separately authorized hardware GET test validates response timing, page structure, and semantics.

No configuration SET, calibration, reset, profile change, or flash operation was added or sent.


## Read-only keymap page parser groundwork (2026-11-20)

Added `app/keymap.py` and `tests/test_keymap.py`. The module builds the documented gen2 `0x8A` GET request for a selected profile (0–3), page (0–7), and sublayer (0–3), then parses a raw 64-byte page into sixteen opaque four-byte entries. It preserves all entry bytes and computes only the page's slot offset; it does not guess the meaning of keycodes, modifier flags, Fn layers, or the physical key-to-slot map.

This code is pure and disconnected from HID/GUI. The protocol shape is family-level firmware evidence; no `0x8A` request or response has been observed on physical board 2255. Sharkfin's exact-model support page says the layout should be checked against the board-reported keymap before remapping. Therefore no remapping UI, keymap write, profile switch, or physical layout assumption is introduced.

The magnetic settings and keymap modules are both request builders/parsers only. No GET or SET command was sent to the physical keyboard during these changes.

The combined 51-test suite passed on commit `ee49492e52fc136f458c2cd79b49ae66fa1f0aa7`: https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44761830077.

## Installer and udev safety regression coverage (2026-11-20)

Added `tests/test_installer_safety.py` with checks for Bash syntax, staged activation/rollback structure, absence of executable sudo or broad permission changes, and exact VID/PID/interface scoping of the udev access rules. The latest 55-test GitHub Actions run passed these checks on commit `e19b648753ca41c3d144fc67231381c00952db0c`: https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44762476803.


## Read-only active-profile parser groundwork (2026-11-20)

Added `app/active_profile.py` and `tests/test_profile.py`. The module builds the gen2 `0x84` GET request and validates the zero-based active profile index in response byte 1, accepting only profile indices 0–3. It validates the full 64-byte payload, opcode, and optional zero report-ID prefix. It does not switch profiles and performs no HID I/O.

The sharkfin AK680 MAX board record lists four onboard profiles, but no `0x84` request or response has been captured from the user's physical board. The module remains disconnected from the GUI pending a board-2255 hardware read-only validation. No profile SET command has been added or sent.


## Matrix GET request framing refinement (2026-11-20)

A further source review of HallJoy's RongYuan snapshot transport identified a request-tail sentinel for matrix GET opcodes `0xE5` and `0x8A`: after the opcode/arguments/checksum, the unused bytes are initialized to `0xFF` so an incomplete firmware snapshot cannot be mistaken for a valid all-zero page. The pure Python request builders now match this framing, with regression assertions for the tail. The `0x84` active-profile request remains zero-filled.

This is source-derived protocol detail, not a physical capture from board 2255. No request was transmitted; the parsers remain software-only and disconnected from HID.
