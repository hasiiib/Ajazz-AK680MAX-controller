# Development Roadmap

## Foundation and safety
- [x] PySide6 desktop application and user-local installer.
- [x] USB/HID enumeration and interface-role inspection.
- [x] Physical board-2255 read-only Identify handshake.
- [x] Scoped udev access and libusb-backed HID open verified.
- [x] Privacy-filtered diagnostic export.
- [x] Automated installer and protocol regression tests.

## Connection and analog input
- [x] Conservative connection-state classification.
- [x] Automatic metadata-only USB/HID connection refresh.
- [x] Ensure background refresh sends no device commands.
- [x] Automatically abort analog monitoring when the paired interfaces disappear or input/enumeration fails.
- [x] Stop polling, clear stale samples, restore GUI controls, and attempt best-effort stream-clear during abort; target-board volatility remains unverified.
- [x] Close partially allocated analog HID handles on setup failures and validate poll batch bounds.
- [x] Add a prominent GUI warning that analog streaming is not verified on physical board 2255 and raw travel units/range are unknown.
- [ ] Verify analog start/stop, transport, press/hold/release, and disconnect recovery on the physical keyboard.
- [ ] Establish raw travel units and calibrated range.

## Read-only configuration foundation
- [x] Pure magnetic-settings GET request builder and response parsers.
- [x] Pure keymap GET page builder and opaque-entry parser.
- [x] Pure active-profile GET builder and parser.
- [x] Strict aggregation of complete 128-slot keymap layers and magnetic-settings columns from supplied replies.
- [x] Reject incomplete, duplicate, mixed-profile, mixed-sublayer, malformed, or unexpected reply sets.
- [x] Audit public board-2255 registry/protocol evidence and document family-level versus firmware-image evidence, the upstream `0x8A` byte-4 ambiguity, stock/custom firmware limits, and incompatible-board exclusions.
- [x] Validate one physical 0x84 active-profile GET response on board 2255 (accepted profile index 0; one capture only).
- [ ] Validate 0x8A and 0xE5 response framing and values on physical board 2255 before connecting these reads to HID or the GUI. See [hardware verification plan](docs/HARDWARE_VERIFICATION.md).
- [ ] Decode the physical key layout before enabling remapping.

## User-facing controls
- [x] Add a read-only snapshot browser tab that renders validated keymap and magnetic values without assigning meanings.
- [x] Enforce immutable display-projection invariants for slot order, profile/layer identity, supported sub-operations, and raw-value shape.
- [ ] Connect snapshot acquisition only after 0xE5 and 0x8A response framing is physically verified on board 2255.
- [ ] Build editable controls only for capabilities verified on board 2255.
- [ ] Verify lighting capabilities and safe controls.
- [ ] Verify actuation, Rapid Trigger, DKS, and macro capabilities.
- [ ] Design read-back verification and recovery before any persistent write feature.
- [ ] Physical acceptance testing and versioned release.

## Evidence and safety
- [x] Publish a pinned-source board-2255 evidence note; do not treat family-level or other-board firmware evidence as target-board capture. See [board-2255 protocol evidence](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).
- [ ] Establish target stock firmware provenance with an exact vendor image/hash or vendor confirmation; do not infer it from the Identify ID.
- [ ] Resolve the upstream `0x8A` byte-4 host-layer/sub-layer ambiguity using target-board read-only evidence.
- Physical Identify result 2255 and one read-only 0x84 active-profile GET (Profile 1 / index 0) are verified; 0x8A/0xE5 reads and analog streaming are not yet physically verified.
- Snapshot aggregation is pure in-memory validation only; it does not issue HID requests or imply that the underlying response framing has been verified on this board.
- Similar AJAZZ model names do not guarantee protocol compatibility. Use only evidence applicable to USB 3151:502D / board 2255.
- Do not send guessed commands or implement persistent writes without exact protocol verification and explicit user authorization.
- Preserve user settings and keep installation within the dedicated application directories.

## Current handoff
The suite contains **167 tests**, including response-to-snapshot integration, offline capture assessment, documentation safety checks, all Qt panel tests, and strict immutable display-projection validation, precise one-shot Feature response diagnostics, and keymap capture safety tests. Snapshot value objects enforce deep immutability, exact 128-slot coverage, protocol-compatible value widths/ranges, active-profile consistency, and unique layer/column identities. Physical analog stream validation and `0x8A`/`0xE5` read-only response validation remain hardware gates; `0x84` has one accepted physical capture. The latest full run passed on commit `9d5863e`; [view the run](https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44784448456).


- [x] Add offline response-capture assessment for manually supplied 0x84/0x8A/0xE5 reports (no HID I/O).
- [x] Publish board-2255-specific protocol evidence and variant exclusions.
