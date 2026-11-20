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
- [ ] Map exact board-2255 GET operations and response formats.
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
- [ ] Improve accessibility, keyboard navigation, connection-state handling, and diagnostic export.
- [ ] Expand automated tests for protocol, UI logic, installer, and failure recovery.
- [ ] Validate on the physical keyboard and document exact supported firmware.
- [ ] Publish a versioned release only after hardware acceptance.

## Evidence and safety rules
- Physical Identify result 2255 is verified; analog stream behavior is not yet physically verified.
- The 4000 µm travel range found in a public profile is provisional, not a measurement of this unit.
- No guessed command, persistent configuration write, calibration, reset, or firmware operation.
- Do not copy HallJoy source code; it is AGPL-3.0. Protocol facts may be independently implemented with attribution and license awareness.
- Preserve user settings and keep installation within the dedicated application directories.

## Current handoff
The latest GitHub Actions run for commit `e0f498c9b46205515cdf9e0277316ccb6fcf5f4c` passed. The next meaningful hardware gate is the first physical Start/Stop Analog Monitor test; until then, the feature remains opt-in and unverified on the device.
