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
- Strict snapshot assembly that requires complete, consistent 128-slot keymap layers and magnetic-setting columns while preserving opaque keymap entries and raw protocol units.
- Immutable display-only snapshot projection and a **Configuration (read-only)** GUI tab for browsing a validated snapshot. The viewer starts empty and accepts only validated in-memory snapshot objects; it does not read from or write to the keyboard.
- Strict offline JSON capture bundle import into the read-only viewer. It requires complete keymap pages per included layer and complete magnetic pages per included GET sub-operation, rejects unknown fields and serial metadata, and retains the existing display if import validation fails. It performs no HID I/O and does not save captures; imported target metadata is self-declared, not provenance evidence.
- Automated unit tests and GitHub Actions CI.

## Protocol research findings (not target-board validation)
- The independent Sharkfin registry maps board ID 2255 / USB 3151:502D to the AK680 MAX gen2 family and controller string `ry5088_sg9005_rt004_dm_hall_8k`; this is third-party host-software metadata, not stock-firmware proof.
- The same AK680 MAX name covers four device IDs; 2336/2343/2371 use PID 3151:502F and different controller strings. PID 3151:502D is also shared by unrelated device IDs, so Identify ID 2255 remains essential.
- One physical `0x84` active-profile GET and one `0x8A` keymap page-0 GET have been accepted on target board 2255. The `0x8A` parser accepted 16 opaque four-byte entries; upstream documentation and code still disagree on the meaning of byte 4 in that request.
- Public `0xE5` protocol details remain firmware-image-derived from other gen2 IDs (2268, 2116, 3708); board 2255 has one accepted physical sub-operation-0/page-0 capture (32 raw u16 values, all 200), but this does not establish other pages or value meanings.
- Public `0x1B` travel-stream findings are from other firmware images and other hardware. The target board now has one bounded physical probe confirming a successful host-side Feature send and valid Report ID 5 parsing; this does not establish sustained stream behavior, stop effectiveness, disconnect recovery, or travel units.
- Stock firmware provenance is not established by the Identify ID alone; this project has not flashed firmware and no board-2255 stock image/hash has been matched. Full sources and exclusions are in [BOARD_2255_PROTOCOL_EVIDENCE.md](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).

## Not yet verified on the physical keyboard
- Sustained analog monitoring is **not verified on physical board 2255** as a complete feature. Press/hold/release behavior, stop effectiveness (the stop request was sent but post-stop cessation was not independently measured), and physical confirmation of disconnect recovery remain open. Keep the GUI warning visible until these are tested on board 2255.
- Raw travel units and calibrated travel range.
- Other magnetic sub-operations/pages and broader keymap page coverage remain unverified; snapshot assembly currently consumes supplied response payloads and performs no HID I/O. One user-initiated `0x84` GET, one `0x8A` GET (profile 0/page 0), and one `0xE5` GET (sub-operation 0/page 0) have been physically accepted, but no live read path is connected to the GUI. The staged, read-only hardware verification gate is documented in [HARDWARE_VERIFICATION.md](docs/HARDWARE_VERIFICATION.md).
- RGB, remapping, per-key actuation, Rapid Trigger, DKS, macros, and calibration.

## Safety boundaries
- Background connection refresh only enumerates HID metadata; it does not open handles or send commands.
- Identify remains user-initiated and read-only.
- Analog streaming remains user-initiated and experimental; before any attempt, the exact opened control handle is re-identified as board 2255. One bounded probe confirmed the start Feature send path and valid Report ID 5 samples; the stop request was sent and handles closed. This does not verify sustained behavior, stop effectiveness, disconnect recovery, or travel scale.
- The magnetic, keymap, active-profile, and snapshot acquisition modules remain pure framing/validation code and are not connected to HID; standalone one-shot `0x84`, `0x8A`, and `0xE5` capture helpers are separate and require explicit flags. The `0x84`, `0x8A`, and `0xE5` helpers each have one accepted physical capture; `0xE5` evidence is limited to sub-operation 0/page 0 and its raw values remain uninterpreted. The GUI viewer only renders a validated snapshot explicitly supplied by an application caller.
- Do not add persistent configuration writes, calibration, reset, or firmware operations until exact board-2255 behavior is verified and the user explicitly authorizes them.
- Never publish the keyboard's unique serial number.
- Never run the GUI with sudo.

## Latest automated verification
The suite contains **194 tests**, including response-to-snapshot integration, offline capture assessment and bundle import, documentation safety checks, all offscreen Qt viewer tests, strict immutable display-projection validation, precise one-shot Feature response diagnostics, keymap/magnetic capture safety tests, and a source-level guard excluding incompatible 3151:502C and 0C45:80B2 protocols. See [GitHub Actions](https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions) for the latest run.


The offline hardware response capture assessor and complete offline capture bundle importer are implemented and covered by automated tests. The importer performs no HID I/O and does not persist captures. Bundle target metadata is self-declared and not provenance evidence. The `0x84` active-profile, `0x8A` keymap page-0, and `0xE5` magnetic sub-operation-0/page-0 response framing each have one accepted physical capture. Other magnetic pages/sub-operations and value meanings remain unverified. See [HARDWARE_VERIFICATION.md](docs/HARDWARE_VERIFICATION.md) and [BOARD_2255_PROTOCOL_EVIDENCE.md](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).
