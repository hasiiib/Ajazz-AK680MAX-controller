# Development Roadmap

## Foundation and safety
- [x] PySide6 desktop application and user-local installer.
- [x] USB/HID enumeration and interface-role inspection.
- [x] Physical board-2255 read-only Identify handshake.
- [x] Scoped udev access and libusb-backed HID open verified.
- [x] Privacy-filtered diagnostic export.
- [x] Automated installer and protocol regression tests.
- [x] Exercise installer rollback when desktop-entry activation fails after the application swap.

## Connection and analog input
- [x] Conservative connection-state classification.
- [x] Automatic metadata-only USB/HID connection refresh.
- [x] Ensure background refresh sends no device commands.
- [x] Automatically abort analog monitoring when the paired interfaces disappear or input/enumeration fails.
- [x] Stop polling, clear stale samples, restore GUI controls, and attempt best-effort stream-clear during abort; target-board volatility remains unverified.
- [x] Close partially allocated analog HID handles on setup failures and validate poll batch bounds.
- [x] Re-identify the exact opened control handle before an experimental analog-stream attempt, preventing a separate identify/open cycle from authorizing a different device.
- [x] Add a prominent GUI warning that analog streaming is not verified on physical board 2255 and raw travel units/range are unknown.
- [x] Verify one bounded temporary analog-stream start/send path and parse valid Report ID 5 samples on physical board 2255; send the stop request and close handles.
- [ ] Verify sustained analog streaming, press/hold/release behavior, stop effectiveness, and disconnect recovery on the physical keyboard.
- [ ] Establish raw travel units and calibrated range.

## Read-only configuration foundation
- [x] Pure magnetic-settings GET request builder and response parsers.
- [x] Pure keymap GET page builder and opaque-entry parser.
- [x] Pure active-profile GET builder and parser.
- [x] Add strict, pure single-slot gen2 keymap and magnetic SET packet builders (offline only; no HID write transport).
- [x] Strict aggregation of complete 128-slot keymap layers and magnetic-settings columns from supplied replies.
- [x] Reject incomplete, duplicate, mixed-profile, mixed-sublayer, malformed, or unexpected reply sets.
- [x] Audit public board-2255 registry/protocol evidence and document family-level versus firmware-image evidence, the upstream `0x8A` byte-4 ambiguity, stock/custom firmware limits, and incompatible-board exclusions.
- [x] Validate one physical 0x84 active-profile GET response on board 2255 (accepted profile index 0; one capture only).
- [x] Validate one physical 0x8A keymap page-0 response on board 2255; preserve its 16 entries as opaque four-byte values.
- [x] Validate one physical 0xE5 magnetic sub-operation-0/page-0 response on board 2255; preserve its 32 values as raw little-endian u16 values.
- [x] Implement a user-triggered read-only GUI acquisition for the active profile, all eight base keymap pages, and four actuation-travel pages; it runs on a worker thread and sends no writes.
- [ ] Physically validate the complete 13-GET GUI read sequence on board 2255 before expanding it to advanced magnetic columns. See [hardware verification plan](docs/HARDWARE_VERIFICATION.md).
- [ ] Decode the physical key layout before enabling remapping.

## User-facing controls
- [x] Add a configuration snapshot browser tab with known gen2 keymap assignments decoded and unknown entries retained as raw values; magnetic values remain raw.
- [x] Add a user-triggered, worker-thread read-only configuration action guarded by a fresh same-handle board-2255 Identify.
- [x] Enforce immutable display-projection invariants for slot order, profile/layer identity, supported sub-operations, and raw-value shape.
- [x] Import strict offline capture bundles into the read-only viewer; require complete pages for each included layer/column, reject unknown fields/serial metadata, and retain the previous view on import failure. Target metadata is self-declared, not provenance evidence.
- [ ] Physically verify all eight keymap pages and four actuation pages through the new GUI acquisition path.
- [ ] Build editable controls only for capabilities verified on board 2255.
- [ ] Verify lighting capabilities and safe controls.
- [ ] Verify actuation, Rapid Trigger, DKS, and macro capabilities.
- [ ] Design read-back verification and recovery before any persistent write feature.
- [ ] Physical acceptance testing and versioned release.

## Evidence and safety
- [x] Publish a pinned-source board-2255 evidence note; do not treat family-level or other-board firmware evidence as target-board capture. See [board-2255 protocol evidence](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).
- [x] Add a regression guard preventing incompatible 3151:502C and 0C45:80B2 protocol identifiers from entering application or udev code.
- [ ] Establish target stock firmware provenance with an exact vendor image/hash or vendor confirmation; do not infer it from the Identify ID.
- [ ] Resolve the upstream `0x8A` byte-4 host-layer/sub-layer ambiguity using target-board read-only evidence.
- Physical Identify result 2255, one read-only 0x84 active-profile GET, one 0x8A keymap page-0 GET, and one 0xE5 magnetic sub-operation-0/page-0 GET are accepted. One bounded analog-stream probe also yielded 16 valid Report ID 5 samples on slot 15; sustained behavior, stop effectiveness, disconnect recovery, and travel units remain unverified.
- The live reader sends only 0x84, 0x8A base-layer, and 0xE5 actuation-column GET requests after a fresh same-handle Identify. The full page sequence is covered by fake-HID tests but still needs a bounded physical acceptance test; no setting-write opcode is sent.
- Similar AJAZZ model names do not guarantee protocol compatibility. Use only evidence applicable to USB 3151:502D / board 2255.
- Do not send guessed commands or implement persistent writes without exact protocol verification, backup/read-back recovery, and explicit user authorization.
- Preserve user settings and keep installation within the dedicated application directories.

## Current handoff
The suite contains **195 tests** (after the offline capture bundle-import and invalid-UTF-8 handling milestones), including response-to-snapshot integration, offline capture assessment, documentation safety checks, all Qt panel tests, strict immutable display-projection validation, precise one-shot Feature response diagnostics, and keymap/magnetic capture safety tests. Snapshot value objects enforce deep immutability, exact 128-slot coverage, protocol-compatible value widths/ranges, active-profile consistency, and unique layer/column identities. Sustained analog behavior/calibration and broader `0xE5`/`0x8A` page coverage remain hardware gates; one bounded analog probe yielded valid samples, while `0x84`, `0x8A` page 0, and `0xE5` sub-operation 0/page 0 each have one accepted physical capture. See [GitHub Actions](https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions) for the current branch's test result.


- [x] Add offline response-capture assessment for manually supplied 0x84/0x8A/0xE5 reports (no HID I/O).
- [x] Add strict offline capture bundle import with size/schema/target/page-completeness validation and GUI integration.
- [x] Add an explicitly confirmed, one-shot 0xE5 page-0 capture helper with no retries or writes.
- [x] Publish board-2255-specific protocol evidence and variant exclusions.
