# Project Status

Last updated: 2026-11-21

## Goal
Build a reliable Linux desktop controller for the wired AJAZZ AK680 MAX HE, physical board ID 2255 (USB VID:PID 3151:502D).

## Verified on the physical Ubuntu system
- The keyboard enumerates as USB 3151:502D with HID interfaces 0, 1, and 2.
- Control interface 2 and analog-input interface 1 belong to the same USB device.
- Read-only Identify (0x8F) returned board ID 2255.
- The scoped udev rule grants access, and libusb-backed hidapi successfully opened the control interface.
- The user confirmed the GUI launches and can discover/identify the keyboard.
- One explicitly authorized, bounded physical `0x1B` probe completed: 16 valid Report ID 5 samples were parsed, slot 15 was observed, the stop request was sent, and both HID handles were closed. The sample values in this batch ranged from 32 to 165 raw counts.

## Implemented
- PySide6 desktop application with USB/HID discovery.
- Read-only board identification and firmware metadata parsing.
- USB interface pairing checks.
- Automatic connection-state refresh through metadata-only HID enumeration; no periodic device commands.
- Automatic analog-monitor abort when its paired HID interfaces disappear or enumeration/input fails; polling stops, handles close, stale samples clear, and a best-effort stream-clear is attempted.
- Analog session setup now closes partially allocated HID handles on second-handle creation or input-open failure, rejects invalid poll batch limits, and performs read-only Identify on the exact opened control handle before any experimental stream command; a reconnect cannot silently substitute a different control handle between identity check and use.
- The GUI warning now reflects the successful bounded analog probe while retaining clear limitations around sustained behavior, stop effectiveness, disconnect recovery, and raw travel units/range.
- Privacy-filtered diagnostic export with expanded USB serial-field redaction.
- User-local staged installer that prepares launcher metadata before activation and restores the previous application directory after post-swap failures; a shell-level integration test simulates a failed desktop-entry activation.
- Pure read-only request builders and parsers for active profile, keymap pages, and magnetic-settings pages. One physical active-profile GET and one keymap page-0 GET have each been accepted; the keymap entries remain opaque and wire byte 4 semantics remain unresolved. A separate, opt-in one-shot magnetic page-0 capture helper has one accepted physical capture: sub-operation 0/page 0 returned 32 raw u16 values, all 200.
- Strict snapshot assembly that requires complete, consistent 128-slot keymap layers and magnetic-setting columns while preserving raw protocol values.
- User-triggered, worker-thread live configuration acquisition: fresh Identify on the same interface-2 handle, then 0x84 active profile, all eight 0x8A base-layer pages, and four 0xE5 sub-operation-0 actuation-travel pages. It sends GETs only, never switches profiles or writes settings; physical validation of the full page sequence is still pending.
- Conservative gen2 keymap-entry decoder for documented keyboard usages, consumer controls, macro bindings, and special functions. Unknown/composite entries remain labelled raw rather than guessed.
- Pure gen2 profile-select (`0x04`), single-slot keymap (`0x0A`), magnetic-setting (`0x65`), board-2255 LED parameter (`0x07`/`0x87`), and macro (`0x0B`/`0x8B`) packet helpers. The macro codec handles key, mouse-button, and mouse-move events in 256-byte slots. These are offline protocol builders/parsers only; no HID write transport or GUI apply action is connected.
- Immutable display-only snapshot projection and a **Configuration (read-only)** GUI tab. The user can initiate a bounded live read; acquisition runs outside the GUI thread and the viewer receives only a validated snapshot. The table shows decoded documented assignments alongside raw bytes, while magnetic values remain raw. A board-2255 ANSI keyboard diagram shows reference geometry and checks factory HID-usage coverage, but never infers physical slots because a remap can reorder usages while preserving the full set.
- Strict offline JSON capture bundle import and normalized backup export. Import requires complete keymap pages per included layer and complete magnetic pages per included GET sub-operation, rejects unknown fields and serial metadata, and retains the existing display if validation fails. Export preserves represented keymap/magnetic values but reconstructs normalized pages rather than raw USB framing. Both are offline; target metadata is self-declared, not provenance evidence.
- Automated unit tests and GitHub Actions CI.

## Protocol research findings (not target-board validation)
- The independent Sharkfin configurator and registry explicitly list board ID 2255 / USB 3151:502D as writable AK680 MAX gen2 hardware, and describe remapping, RGB, macros, profiles, and magnetic-switch controls. This is a useful independent host-software reference, not stock-firmware proof. Its protocol documentation provides gen2 command shapes, but target-board physical write verification remains a separate gate.
- The same AK680 MAX name covers four device IDs; 2336/2343/2371 use PID 3151:502F and different controller strings. PID 3151:502D is also shared by unrelated device IDs, so Identify ID 2255 remains essential.
- One physical `0x84` active-profile GET and one `0x8A` keymap page-0 GET have been accepted on target board 2255. The `0x8A` parser accepted 16 opaque four-byte entries; upstream documentation and code still disagree on the meaning of byte 4 in that request.
- Public `0xE5` protocol details remain firmware-image-derived from other gen2 IDs (2268, 2116, 3708); board 2255 has one accepted physical sub-operation-0/page-0 capture (32 raw u16 values, all 200), but this does not establish other pages or value meanings.
- Public `0x1B` travel-stream findings are from other firmware images and other hardware. The target board now has one bounded physical probe confirming a successful host-side Feature send and valid Report ID 5 parsing; this does not establish sustained stream behavior, stop effectiveness, disconnect recovery, or travel units.
- Stock firmware provenance is not established by the Identify ID alone; this project has not flashed firmware and no board-2255 stock image/hash has been matched. Full sources and exclusions are in [BOARD_2255_PROTOCOL_EVIDENCE.md](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).

## Not yet verified on the physical keyboard
- Sustained analog monitoring is **not verified on physical board 2255** as a complete feature. Press/hold/release behavior, stop effectiveness (the stop request was sent but post-stop cessation was not independently measured), and physical confirmation of disconnect recovery remain open. Keep the GUI warning visible until these are tested on board 2255.
- Raw travel units and calibrated travel range.
- The new live read path is covered by fake-HID tests but has not yet been run end-to-end on the physical keyboard. The original standalone physical captures covered one `0x84`, one `0x8A` page 0, and one `0xE5` sub-operation-0/page-0 request only. The remaining seven keymap pages and magnetic pages 1–3 need the first bounded GUI read acceptance test. Fn layers and advanced magnetic columns are not yet read.
- RGB, remapping, per-key actuation, Rapid Trigger, DKS, macros, and calibration.

## Safety boundaries
- Background connection refresh only enumerates HID metadata; it does not open handles or send commands.
- Identify remains user-initiated and read-only.
- Analog streaming remains user-initiated and experimental; before any attempt, the exact opened control handle is re-identified as board 2255. One bounded probe confirmed the start Feature send path and valid Report ID 5 samples; the stop request was sent and handles closed. This does not verify sustained behavior, stop effectiveness, disconnect recovery, or travel scale.
- The live configuration reader is user-initiated and worker-threaded. It confirms board 2255 on the same opened interface-2 handle before sending only `0x84`, `0x8A` base-layer pages 0–7, and `0xE5` sub-operation-0 pages 0–3. It does not send any setting-write opcode, switch profiles, calibrate, reset, or flash firmware. The additional pages still require physical acceptance testing.
- The profile, keymap, magnetic, lighting, and macro SET helpers only construct packets in memory. They are not imported by the live reader, do not open HID, and are not exposed in the GUI. No `0x04`, `0x0A`, `0x65`, `0x07`, or `0x0B` write has been sent.
- Do not add persistent configuration writes, calibration, reset, or firmware operations until exact board-2255 behavior is verified and the user explicitly authorizes them.
- Never publish the keyboard's unique serial number.
- Never run the GUI with sudo.

## Latest automated verification
The suite contains **250 tests**, including response-to-snapshot integration, offline capture assessment and bundle import, documentation safety checks, all offscreen Qt viewer tests, strict immutable display-projection validation, precise one-shot Feature response diagnostics, keymap/magnetic capture safety tests, and a source-level guard excluding incompatible 3151:502C and 0C45:80B2 protocols. Latest successful run: [44931768943](https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44931768943).


The offline hardware response capture assessor and complete offline capture bundle importer are implemented and covered by automated tests. The importer performs no HID I/O and does not persist captures. Bundle target metadata is self-declared and not provenance evidence. The `0x84` active-profile, `0x8A` keymap page-0, and `0xE5` magnetic sub-operation-0/page-0 response framing each have one accepted physical capture. Other magnetic pages/sub-operations and value meanings remain unverified. See [HARDWARE_VERIFICATION.md](docs/HARDWARE_VERIFICATION.md) and [BOARD_2255_PROTOCOL_EVIDENCE.md](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).
