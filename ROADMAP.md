# Development Roadmap

This roadmap reflects the current repository and physical-device evidence. A checkbox is complete only when code/tests or an actual keyboard test support it.

## Phase 1 — Foundation
- [x] PySide6 desktop application scaffold.
- [x] USB/HID inventory and descriptor-informed interface roles.
- [x] User-local installer with staged update and rollback.
- [x] Physical Ubuntu launch and USB/HID detection confirmed.
- [x] Narrow udev access for VID:PID 3151:502D; libusb-backed hidapi open verified.

## Phase 2 — Identity and protocol research
- [x] Decode all three HID report descriptors.
- [x] Implement and physically verify read-only Identify opcode 0x8F.
- [x] Confirm physical board ID 2255 and gen2 family.
- [x] Pair control interface 2 and analog input interface 1 by shared USB parent.
- [x] Parse gen2 firmware revision from Identify response bytes 7–8.
- [x] Document HallJoy/RongYuan protocol research and license boundary.

## Phase 3 — Analog monitoring
- [x] Add strict board-2255 gate before temporary stream activation.
- [x] Add interface-pair validation and independent HID handles.
- [x] Add report-ID-5 parser and per-slot raw travel state.
- [x] Add user-controlled Start/Stop monitor and application shutdown cleanup.
- [x] Add startup failure, best-effort stop, and handle cleanup tests.
- [x] GitHub Actions unit-test workflow passes on commit e0f498c.
- [ ] Verify live analog reports on the physical keyboard.
- [ ] Verify key press, hold, release, stop, app close, and disconnect behavior on hardware.
- [ ] Determine raw travel units and calibrated physical range from evidence.

## Phase 4 — Core controls (research before implementation)
- [x] Separate the 3151:502D / board-2255 RongYuan protocol from incompatible AK680 MAX 3151:502C lightless and 0C45:80B2 RGB protocols; document explicit non-applicability.
- [x] Cross-check board 2255 capabilities against an independent AK680 MAX software record (magnetic settings, profiles, lighting); retain firmware-level vs exact-board evidence grades.
- [x] Implement a pure, strict 0xE5 magnetic GET packet builder and response-page parsers for gen2 sub-operations 0–7, 9, and read-only 10; enforce page bounds, exact 64-byte payloads, little-endian u16 values, and four-byte DKS records.
- [x] Implement a pure 0x8A keymap GET page builder/parser for four profiles, four sublayers, eight pages, and sixteen opaque four-byte entries per page; do not guess keycode or physical-layout semantics.
- [x] Implement a pure 0x84 active-profile GET packet and strict zero-based profile-index parser (0–3); no profile-switch command.
- [x] Match the RongYuan matrix GET request-tail sentinel (`0xFF`) for pure 0xE5 / 0x8A packet builders, with regression tests; physical response remains unverified.
- [ ] Physically verify 0xE5, 0x8A, and 0x84 GET response timing, shape, and values on board 2255 before enabling any configuration reads in the GUI.
- [ ] Decode and validate the factory keymap against a verified physical layout before enabling remapping.
- [ ] Identify supported RGB capabilities and safe read/write protocol.
- [ ] Identify keymap/remapping capabilities and profile format.
- [ ] Design transactional writes, read-back verification, and recovery before exposing controls.
- [ ] Implement only features proven supported by board 2255.

## Phase 5 — Advanced magnetic features
- [ ] Research and verify per-key actuation point support.
- [ ] Research and verify Rapid Trigger behavior and parameters.
- [ ] Research and verify DKS / multi-action support.
- [ ] Research macro support and safe macro storage/playback.
- [ ] Establish calibrated travel conversion before showing millimetres.

## Phase 6 — Product quality and release
- [ ] Refine GUI into clear device, lighting, key, and advanced-feature sections as capabilities become verified.
- [x] Add privacy-filtered diagnostic export with serial-number redaction and explicit unverified-hardware warnings.
- [x] Compile every app Python module in CI without importing hardware/UI dependencies.
- [x] Add a conservative HID connection-state classifier and display it in the GUI; interface pairing remains distinct from Identify success.
- [ ] Improve accessibility and keyboard navigation.
- [x] Add installer/udev regression checks for Bash syntax, staged rollback structure, no executable sudo/broad chmod, and narrowly scoped VID/PID/interface permissions.
- [ ] Expand automated tests for protocol, UI logic, and hardware failure recovery.
- [ ] Validate on the physical keyboard and document exact supported firmware.
- [ ] Publish a versioned release only after hardware acceptance.

## Evidence and safety rules
- Physical Identify result 2255 is verified; analog stream behavior is not yet physically verified.
- The 4000 µm travel range found in a public profile is provisional, not a measurement of this unit.
- An independent AK680 MAX software record lists board 2255 / 3151:502D as a gen2 magnetic keyboard with four profiles and lighting; this is exact-model capability corroboration, not a physical test of every command on this firmware.
- No guessed command, persistent configuration write, calibration, reset, or firmware operation.
- Do not copy HallJoy source code; it is AGPL-3.0. Protocol facts may be independently implemented with attribution and license awareness.
- Preserve user settings and keep installation within the dedicated application directories.

## Current handoff
The latest full unit-test workflow for commit `f9d98cdc9534ab876ecf3c6b3f78e1d140d962f5` passed all 66 tests, including the new connection-state tests: https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44763956318. The magnetic and keymap parsers are software-only: they build GET requests and decode captured replies but do not open HID or send commands. The next hardware gates remain physical Start/Stop Analog Monitor validation and separately authorized read-only 0xE5 / 0x8A response checks; none has been performed yet.
