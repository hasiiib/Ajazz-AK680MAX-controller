# Development Roadmap

This roadmap is ordered by dependencies. Complete and verify each stage before moving to the next.

## Phase 1 — Safe foundation
- [x] Create the initial PySide6 application scaffold.
- [x] Add USB/HID discovery UI scaffold.
- [x] Add a dedicated, staged Ubuntu installer with rollback protection.
- [ ] Confirm installation on the user's Ubuntu machine.
- [ ] Confirm the app launches and detects the actual AK680 MAX.
- [x] Record exact USB VID/PID, interfaces, hidraw nodes, and report descriptors.

## Phase 2 — Hardware protocol investigation
- [ ] Verify live board-reported device ID and exact controller revision (public AK680 MAX reference maps USB ID 3151:502D to candidate device ID 2255 / gen2).
- [ ] Research vendor software, official documentation, Linux driver support, and credible community protocol findings.
- [x] Retrieve and decode all three HID report descriptors (descriptor-only inspection; no reports sent).
- [ ] Document verified report formats and device communication constraints.
- [ ] Define a safe protocol test plan; do not send guessed configuration reports.

## Phase 3 — Core keyboard controls
Only begin after the relevant protocol is verified.
- [ ] Device connection/status and clear error handling.
- [ ] RGB lighting controls.
- [ ] Key remapping and per-key settings, if supported by the hardware.
- [ ] Save/load profiles.

## Phase 4 — Advanced features
Only implement features supported by verified firmware/protocol behavior.
- [ ] Per-key actuation settings.
- [ ] Rapid Trigger.
- [ ] DKS.
- [ ] Macro editor and playback.
- [ ] Additional supported modes and profile management.

## Phase 5 — Quality and release
- [ ] Validate behavior on the actual keyboard.
- [ ] Add automated tests for protocol encoding/decoding and application logic.
- [ ] Improve accessibility, UI polish, logging, and recovery behavior.
- [ ] Document installation, usage, compatibility, and limitations.
- [ ] Publish a versioned release when stable.

## Progress tracking rules
- Mark a task complete only after evidence or a reproducible test supports it.
- Record test environment, observed result, and known limitations.
- Update this roadmap and `PROJECT_STATUS.md` after meaningful changes.
- Add a dated session handoff to `PROJECT_STATUS.md` before ending a development session.


## Latest protocol finding (2026-11-20)
- Interface 2 exposes a vendor-defined 64-byte Feature report on Usage Page `0xFFFF`, Usage `0x02`, with no Report ID. This is a candidate for protocol research, not proof of a configuration API.
- Interface 1 also contains vendor-defined input Report ID 5 with a 31-byte payload.
- Next: locate official AJAZZ utility/docs or credible community protocol evidence matching VID:PID `3151:502d` and hardware revision. Keep testing read-only; never send guessed Feature/Output reports.


## Hardware identity checkpoint (2026-11-20)
- Public sources associate `3151:502D` with other magnetic keyboard models (including Epomaker HE68 Mag / Attack Shark X82HE), while one AK680 MAX reverse-engineering project describes lightless `3151:502C` and RGB `0C45:80B2` variants.
- This is an identity discrepancy, not proof of mislabeling. Similar USB descriptors do not prove protocol compatibility.
- Block protocol-specific implementation until the physical model/variant and USB bcdDevice/manufacturer/product strings are reconciled.
- Next safe step: confirm the underside/box model marking and inspect full USB identity fields. No HID reports are to be sent.


## Protocol reference update (2026-11-20)
- Found a public AK680 MAX board record matching VID:PID `3151:502d`: candidate device ID 2255, controller `ry5088_sg9005_rt004_dm_hall_8k`, protocol family gen2. The record lists other AK680 MAX revisions too, so verify the live device ID.
- Reference board page: https://getsharkfin.com/boards/ajazzmouse-ak680-max
- Reference protocol: https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md
- Protocol doc describes 64-byte Feature reports on Usage Page `0xFFFF`, Usage `0x02`, and identify GET opcode `0x8F` returning a 32-bit little-endian device ID. Gen2 and yc500 opcodes collide; never guess family.
- Next development milestone: add a narrowly scoped, GET-only identify operation (0x8F), verify device ID, and disable all writes/configuration changes. No protocol command has yet been sent to the user's keyboard.


## Read-only Identify UI milestone (2026-11-20)
- [x] Add guarded 0x8F Identify packet builder and response parser.
- [x] Restrict discovery to VID:PID 3151:502D, interface 2, Usage Page 0xFFFF / Usage 0x0002; refuse ambiguous matches.
- [x] Add an explicit read-only Identify button to the GUI.
- [x] Add unit tests for packet framing, checksum, response parsing, and malformed/refusal responses.
- [ ] Run the automated tests in the target Ubuntu environment.
- [ ] Run Identify against the physical keyboard and record the live board-reported device ID.
- [ ] If hidapi access is denied, inspect udev ancestry and add a narrowly scoped permission rule for only the verified settings interface.
- [ ] Confirm device ID and family before implementing any further GET operations.

Safety boundary: Identify is the only command currently implemented. No configuration writes or settings controls have been added. A public reference maps 3151:502D to candidate device ID 2255 / gen2, but the live board response remains unverified.
