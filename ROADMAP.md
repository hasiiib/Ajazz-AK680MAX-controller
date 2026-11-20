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
- [x] Inspect udev ancestry and add a narrowly scoped permission rule for only the verified settings interface; user ACL on /dev/hidraw4 verified after reconnect.
- [ ] Confirm device ID and family before implementing any further GET operations.

Safety boundary: Identify is the only command currently implemented. No configuration writes or settings controls have been added. A public reference maps 3151:502D to candidate device ID 2255 / gen2, but the live board response remains unverified.


## HID discovery filter correction (2026-11-20)
- [x] Use the already descriptor-verified USB interface 2 as the selector, without rejecting Linux hidapi's possibly incomplete Usage Page / Usage metadata.
- [x] Keep exact VID/PID, interface-number and unique-path checks; refuse ambiguous matches.
- [ ] Retest Identify on the physical keyboard and capture the live Device ID or detailed enumeration error.
- [ ] Only investigate udev permissions if interface selection succeeds but opening the node is denied.


## HallJoy / RongYuan reference update (2026-11-20)

Research task completed using [Universal Analog Plugin issue #23](https://github.com/AnalogSense/universal-analog-plugin/issues/23) and [PashOK7/HallJoy](https://github.com/PashOK7/HallJoy).

- [x] Find an implementation that explicitly lists AJAZZ AK680 MAX HE as supported.
- [x] Confirm HallJoy's exact AK680 MAX board table: board 2255 / VID:PID 3151:502D; other listed revisions 2336, 2343 and 2371 use PID 502F.
- [x] Compare HallJoy's RongYuan HID transport and stream report shape against the user's descriptors.
- [x] Record the read-only identity and metadata GET sequence, plus the separate stream enable/disable operation.
- [x] Record HallJoy's AGPL-3.0 license and decision not to copy its source code.
- [x] Add detailed research note: docs/research/HALLJOY_AK680MAX_PROTOCOL_REFERENCE_2026-11-20.md.

Updated protocol picture:
- Interface 1.2 / Feature Usage Page 0xFFFF Usage 0x02 is the candidate control channel.
- Interface 1.1 / report ID 5 input is the candidate live analog stream channel.
- HallJoy's 32-byte stream frame is [0x05, 0x1B, raw_lo, raw_hi, slot, ...].
- 0x8F identifies the live board. 0x80 / 0xE6 / 0x84 / 0x8A are GET/read paths in HallJoy's implementation.
- 0x1B,1 enables live stream; 0x1B,0 disables it. Do not send either until exact board identity is verified and explicit stream cleanup is implemented.

Next implementation sequence:
1. [ ] Pair the two HID collections in Linux by the same physical USB device path.
2. [ ] Review/adjust 0x8F transaction timing to match the documented ~10 ms control exchange spacing.
3. [ ] User retests the read-only Identify operation; capture live board ID or exact hidapi/open error.
4. [ ] Verify board ID + VID/PID against exact model table before any board-specific reads.
5. [ ] Add GET-only firmware/precision/assignment reads with unit tests.
6. [ ] Only then design a separate analog stream start/stop feature using 0x1B with guaranteed disable on shutdown, errors and disconnect.

Safety and verification:
- The live board ID is still unknown; 2255 remains a candidate.
- The stream packet format is reference-derived, not yet captured from this physical keyboard.
- HallJoy's nominal 4 mm range is provisional, not a physical measurement.
- No new keyboard command has been sent and no setting has been changed.
- HallJoy is Windows-only and AGPL-3.0; its implementation is a technical reference, not a dependency to install or copy into this Linux project.


## HID topology and Identify transport milestone (2026-11-20)

- [x] Add Linux hidapi + sysfs inventory for the keyboard's HID interfaces.
- [x] Identify interface 2 as the descriptor-confirmed Feature-control candidate.
- [x] Identify interface 1 as the descriptor-confirmed Report ID 5 analog-input candidate.
- [x] Add strict same-USB-parent pairing diagnostics; no input stream is opened.
- [x] Align the read-only 0x8F transaction with HallJoy's reviewed timing: one SET_FEATURE send, 10 ms exchange spacing, and GET_FEATURE polling for up to 100 ms without retransmitting the request.
- [x] Add unit tests for interface pairing, one-send/multiple-poll behavior, and timeout behavior.
- [x] Add GitHub Actions workflow for Python protocol tests.
- [ ] Confirm CI unit-test workflow passes.
- [ ] User scans HIDAPI collections and confirms the control/input pair on the actual Ubuntu system.
- [ ] User runs the read-only Identify request and reports live board ID or exact failure.
- [ ] Add narrow udev access only if the verified interface opens with a permission error.

Safety boundary remains unchanged: 0x1B analog stream enable/disable is not implemented or sent. No keyboard settings have been changed. The live board ID is still unverified.


## User-space HID access milestone (2026-11-20)
- [x] Add the interface-2-only udev `uaccess` rule for VID:PID 3151:502D.
- [x] Verify after reconnect that the active Ubuntu user has `rw-` ACL on `/dev/hidraw4`; no other interface permissions were broadened.
- [x] Improve Identify open-error diagnostics and add a regression test for surfaced OS errors / handle cleanup.
- [ ] Run the physical read-only Identify transaction now that access is granted.
- [ ] Capture and verify the live board ID before adding further GET commands.

The permission milestone is complete, but protocol communication is not yet confirmed. Keep all commands except the documented read-only 0x8F Identify disabled.


## Linux libusb access correction (2026-11-20)

- [x] Diagnose the bundled Python hidapi backend: it links to libusb rather than opening hidraw directly.
- [x] Confirm /dev/hidraw4 native read/write open succeeds with the existing interface-2 ACL.
- [x] Confirm the matching /dev/bus/usb/001/013 node denies the user write open.
- [x] Extend the udev rule with a VID:PID-scoped uaccess tag for USB device nodes 3151:502d, retaining the interface-2-only hidraw rule.
- [ ] Install the updated rule, reconnect the keyboard, and verify the USB device node receives an ACL for the active user.
- [ ] Retest HIDAPI open and then run the read-only 0x8F Identify transaction.

No HID reports have been sent and no keyboard settings have been changed during this diagnosis.


## USB permission and HIDAPI open verified (2026-11-20)

- [x] Install VID:PID-scoped USB-device uaccess rule and reconnect keyboard.
- [x] Verify current USB node ACL includes user:ayon:rw- (current node at test time: /dev/bus/usb/001/014).
- [x] Verify hidapi successfully opens interface 2 at path 1-1:1.2 as the ordinary user.
- [ ] Run the GUI read-only Identify operation and record the live board ID / exact error.

No keyboard reports or settings changes were part of the open test. Continue with only the documented read-only 0x8F Identify request.
