# HallJoy / RongYuan reference findings — 2026-11-20

## Why this reference matters

The Universal Analog Plugin issue [#23 — Ajazz AK680 MAX](https://github.com/AnalogSense/universal-analog-plugin/issues/23) originally listed the AK680 MAX only as a possible future candidate. Its final comment links to [PashOK7/HallJoy](https://github.com/PashOK7/HallJoy), a separate gamepad application.

HallJoy's current README lists **AJAZZ AK680 MAX HE (USB)** under Supported. Its hardware record says the existing native RongYuan stream implementation covers board 2255 on USB ID `3151:502D`, plus boards 2336/2343/2371 on `3151:502F`. This is a much stronger match to our observed keyboard than the earlier unrelated-device reports for the same VID/PID.

References:
- [HallJoy README and supported keyboard list](https://github.com/PashOK7/HallJoy/blob/main/README.md)
- [HallJoy AK680 MAX support record](https://github.com/PashOK7/HallJoy/blob/main/docs/current/AJAZZ_AK680MAX_SUPPORTED_2026-11-05.md)
- [HallJoy RongYuan batch hardware table](https://github.com/PashOK7/HallJoy/blob/main/docs/current/RONGYUAN_BATCH_2_2026-09-24.md)
- [HallJoy RongYuan stream protocol source](https://github.com/PashOK7/HallJoy/blob/main/src/HallJoyProject/HallJoy/rongyuan_stream_protocol.h)
- [HallJoy RongYuan stream backend](https://github.com/PashOK7/HallJoy/blob/main/src/HallJoyProject/HallJoy/rongyuan_stream_backend.cpp)
- [HallJoy RongYuan snapshot protocol](https://github.com/PashOK7/HallJoy/blob/main/src/HallJoyProject/HallJoy/rongyuan_snapshot_protocol.h)
- [HallJoy 68-key ANSI layout record](https://github.com/PashOK7/HallJoy/blob/main/docs/research/rongyuan-layouts/ry_layout_2255.json)
- [HallJoy source license](https://github.com/PashOK7/HallJoy/blob/main/LICENSE)

## Match against our actual USB observations

Our Ubuntu scan reported VID:PID `3151:502D`, USB interface 1.0 / 1.1 / 1.2, and hidraw2 / hidraw3 / hidraw4 respectively.

Our descriptor inspection found:
- Interface 2: vendor-defined Usage Page `0xFFFF`, Usage `0x02`, 64-byte Feature payload with no Report ID in the descriptor.
- Interface 1: a vendor-defined input report ID 5 with a 31-byte payload. With the one-byte report ID, the input report is 32 bytes.

HallJoy's RongYuan backend uses a 65-byte Feature buffer including report ID zero for the control collection, and a separate 32-byte input collection for report ID 5. Its input collection is paired with the control collection belonging to the same physical USB device. This closely matches the structure we inspected, but our Linux hidapi collection metadata and actual input pairing still need to be verified.

The HallJoy stream parser expects a 32-byte input packet:
- byte 0: report ID `0x05`
- byte 1: stream opcode `0x1B`
- bytes 2–3: raw travel value, little-endian
- byte 4: physical slot, 0–127

This is source-derived protocol evidence, not yet a live capture from our keyboard.

## Identity and protocol sequence found in HallJoy

The HallJoy source uses the following sequence for its wired RongYuan stream path:

1. Open the vendor Feature/control collection.
2. Send the read-only `0x8F` Identify GET and validate the returned board ID against an exact VID/PID/model table.
3. Obtain controller/firmware version information and optional precision metadata using GET operations.
4. Read current assignment profile metadata (`0x84`) and assignment pages (`0x8A`) as GET operations.
5. Open the paired input collection.
6. Enable the live travel stream with `0x1B, 1`.
7. Read and validate report ID 5 input packets.
8. On shutdown, send `0x1B, 0` to disable the stream.

The 65-byte Feature buffer includes report ID zero at byte 0. The opcode is at byte 1; the Bit7 checksum is at byte 8 of that full buffer (equivalent to payload byte 7 after the report ID is removed).

The source inserts approximately 10 ms between vendor control exchanges. Its query path sends a request once, then polls GET_FEATURE with a delay while validating the reply. Our current Python Identify path sends the request and uses a shorter retry loop; this timing difference is worth reviewing if the physical Identify transaction later times out.

Important distinction:
- `0x8F`, `0x80`, `0xE6`, `0x84`, and `0x8A` are used as GET/read operations in the reviewed path.
- `0x1B` is a stream enable/disable SET operation. It is not the same as read-only Identify. It changes the live reporting state and must only be used after exact identity proof, with reliable cleanup that sends `0x1B, 0` even after a partial/ambiguous enable attempt.
- No stream command has been sent by our application.

## Board and scaling facts

HallJoy's exact model table identifies:
- board ID: `2255`
- VID:PID: `3151:502D`
- model: `AJAZZ AK680 MAX HE`
- profile key: `RY1B-2255`
- nominal travel range in its profile: 4000 µm

Its related records list boards 2336, 2343 and 2371 on PID `502F`. Do not generalize board 2255 support to similarly named AK680 variants or to every product sharing VID/PID `3151:502D`.

HallJoy's range is a software profile value, not a measurement performed on our physical keyboard. Keep 4 mm provisional until independently validated.

HallJoy determines travel units from device-reported firmware/precision information, not USB `bcdDevice`. Its documented fallback is version-based, while an optional `0xE6` reply may provide a precision enum. Our USB `bcdDevice 3.06` must not be treated as controller firmware version or board ID.

## Applicability and licensing

HallJoy itself is a Windows 10/11 x64 application and uses ViGEmBus to expose virtual Xbox controllers. It is not a Linux application and cannot be installed as our Ubuntu solution. The protocol and device-handling research is nevertheless directly useful.

HallJoy is licensed under AGPL-3.0. We will use it as a technical reference and independently implement the documented protocol behavior in our Python application. Do not copy HallJoy source files or substantial code into this repository without first reviewing the license and deciding how the resulting distribution should comply. Preserve attribution and links to the reference.

The Universal Analog Plugin repository's issue #23 and its Wooting SDK integration are not a direct implementation path for our Linux keyboard controller. HallJoy is the useful lead for the AK680 MAX hardware protocol and, separately, for the Windows gamepad-emulation use case.

## Safe next steps

1. Revisit Linux HID enumeration and pair the Interface 2 Feature collection with the Interface 1 report-ID-5 input collection using the same USB parent/device path. Do not pair on VID/PID alone if more than one matching device is connected.
2. Review the Identify transaction timing against HallJoy's 10 ms control-exchange spacing. Keep the request limited to the documented read-only `0x8F` operation.
3. After the user's next authorized test, verify the live board ID. Board 2255 is the expected candidate, not a hardcoded assumption.
4. Only after identity is confirmed, consider GET-only firmware/precision and assignment reads.
5. Keep `0x1B` stream enable/disable out of the current Identify stage. Before implementing it, add an explicit user-visible start/stop action, input-report validation, a cleanup path that attempts `0x1B, 0`, and tests for disconnect/error handling.
6. Design a narrow udev permission rule only after the exact control and input hidraw nodes are established. Do not chmod every keyboard interface or run the GUI as root.

## Current verification boundary

- USB VID/PID and all three HID interfaces: observed on the user's Ubuntu system.
- Interface 2 Feature descriptor and Interface 1 report ID 5 descriptor: observed.
- HallJoy AK680 MAX HE / board 2255 / PID 3151:502D support: documented in its public source.
- Live board ID from our keyboard: not yet read.
- HallJoy-style report ID 5 analog stream on our keyboard: not yet read.
- Any settings/configuration write: not implemented and not sent.


## Live Linux hardware confirmation (2026-11-20)

The project's Ubuntu GUI has now completed its read-only Identify transaction against the user's physical keyboard. The application reports board-reported device ID `2255`. Its HIDAPI inventory simultaneously confirms interface 2 (`1-1:1.2`, Feature-control candidate) and interface 1 (`1-1:1.1`, Report ID 5 analog-input candidate) share USB parent `1-1`; the app's pairing check reports PASS. This validates the board 2255 / VID:PID `3151:502d` association for this physical unit, rather than relying solely on the public model table.

This live test does not yet validate firmware metadata, travel units, analog streaming, or any writable settings. No `0x1B` stream command or configuration write has been sent. Keep the next protocol step GET-only and validate exact response bytes before adding any further feature.


## gen2 revision metadata clarification (2026-11-20)

The live physical Identify result confirms board 2255 / gen2. A current review of the ROYUAN protocol reference clarifies that wired gen2 keyboards return zero for GET `0x80`; the firmware revision is instead encoded in the Identify response at bytes 7–8, decoded as `(reply[8] << 8) | reply[7]`. The current app's Identify parser extracts only the 32-bit board ID, so this metadata is not yet retained or displayed. Implementing the revision display should reuse the same validated Identify response and must not send a separate `0x80` request. Byte 9's meaning remains unconfirmed for this board.

Reference: https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md (Families and Other).


## Analog travel stream protocol review and Linux implementation (2026-11-20)

The ROYUAN protocol reference's Magnetic switches section documents the gen2 travel stream:
- Control command `0x1B [flag]`, Bit7 checksum; nonzero starts and zero stops the volatile stream flag.
- Input is a 32-byte Report ID 5 frame on the vendor input collection (`0xFFFF:1`): byte 0 report ID `0x05`, byte 1 opcode `0x1B`, bytes 2–3 little-endian raw travel, byte 4 physical slot 0–127.
- The stream is cable-only. Reports are emitted when a key's travel changes and once with zero on release; an unchanged held key may produce no new report.
- The protocol reference reports substantial burst rates and finite host input queues, so the Linux reader uses nonblocking reads in bounded batches and retains the latest value per slot instead of appending every frame to the GUI log.

The application now contains an opt-in session implementation. Before start it performs a fresh read-only Identify and requires board ID 2255, then verifies a unique interface-2 / interface-1 pair on one USB parent. It sends the temporary start flag, reads interface 1, and best-effort sends the stop flag on user stop, startup failure after an attempted enable, input error, or app close. Unit tests cover packet checksum, identity gate, pairing, parsing, polling, and cleanup.

Important evidence boundary: the protocol document's firmware disassembly / hardware observations cover several gen2 boards; the user's own board has not yet been physically tested with the stream command. HallJoy lists AJAZZ AK680 MAX HE as supported, but our app must still verify actual samples and stop behavior on this unit. Raw travel units and full-scale range are not inferred from the 4000 µm profile note. No analog stream command has been sent to the user's keyboard by this development work.

Reference: https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md#magnetic-switches


## Variant separation: similarly named AK680 MAX protocols (2026-11-20)

A separate public repository, [shorekeeper/ajazzdesktopify](https://github.com/shorekeeper/ajazzdesktopify), documents two different AK680 MAX products and explicitly warns that their firmware/protocols are incompatible:

- Its lightless model is VID:PID `3151:502C`, using a different 64-byte Feature-report protocol.
- Its RGB model is VID:PID `0C45:80B2`, using vendor interfaces `0xFF68` / `0xFF67` and an `0xAA/0x55` chunked command protocol.
- Our physical keyboard is VID:PID `3151:502D`, and its live Identify response is board ID 2255. HallJoy's exact board profile identifies this as `AJAZZ AK680 MAX HE`, product `RY1B-2255`, with a nominal 4000 µm profile range.

Therefore neither the `3151:502C` lightless command set nor the `0C45:80B2` RGB command set is applicable to this unit. In particular, do not use the other repository's RGB commands `0x10`–`0x28`, chunk offsets, interface `0xFF68`, or its reported key/RGB tables with this device. The fact that product names overlap is not protocol evidence.

The exact HallJoy RongYuan stream source separately contains the 2255 / VID 3151 / PID 502D profile. It documents the 32-byte Report ID 5 / opcode 0x1B stream path used by this project. Its generic optional GET `0xE6` precision query and version fallback are useful research leads, but the profile marks precision-enum support as false; do not infer millimetres from the 4000 µm profile value. Any new read-only metadata query must validate the full response and remain optional. Writable feature work still needs board-2255-specific command/response evidence and physical acceptance.

References:
- [AK680 MAX variant/protocol analysis](https://github.com/shorekeeper/ajazzdesktopify)
- [HallJoy RongYuan stream protocol](https://github.com/PashOK7/HallJoy/blob/main/src/HallJoyProject/HallJoy/rongyuan_stream_protocol.h)
- [HallJoy board profile database](https://github.com/PashOK7/HallJoy/blob/main/docs/research/rongyuan-stream/profiles.json)

## Independent board-2255 capability cross-check: sharkfin (2026-11-20)

A second independent open-source project, [sharkfin](https://getsharkfin.com/boards/ajazzmouse-ak680-max), now provides a particularly useful model-specific cross-check. Its AK680 MAX page explicitly lists the four revisions and identifies this unit's exact row as:

- board/device ID 2255
- USB VID:PID `3151:502D`
- controller `ry5088_sg9005_rt004_dm_hall_8k`
- protocol family gen2
- four onboard profiles
- magnetic-switch controls: per-key actuation, release point, Rapid Trigger and dead-zone settings, plus advanced kinds
- 18 backlight effects

This corroborates that the 2255 product family is intended to expose magnetic-switch configuration, profile management and lighting. It is product-specific software-support evidence, not a physical test of our particular firmware revision. The page also says layout-to-slot mapping must be checked against the board's reported keymap before remapping; our application must not assume that the physical drawing order equals firmware slot order.

The sharkfin protocol reference gives useful gen2-family read details:

- `0xE5` is the GET side of multi-column magnetic settings. Its documented request payload is `[subop, 1, page]` with Bit7 checksum; the reply is a raw page rather than an echoed opcode.
- The gen2 magnetic columns are described as 128 slots each. u16 columns use four 32-value pages; byte columns use two 64-value pages.
- Sub-operations include actuation (0), release (1), Rapid Trigger press/release steps (2/3), DKS first point (4), bottom dead zone (6), key mode (7), and additional advanced data.
- The optional `0xE6` precision query is described as a feature-list response, but the sharkfin text says the response was not implemented in the examined firmware images and may simply echo the request. Do not rely on it without exact response validation.
- Firmware-dependent precision scaling is material: the protocol reference describes different raw travel scales across firmware generations. The AK680 MAX profile's nominal 4000 µm range is not a calibration measurement and must not be used as a conversion factor.

Evidence grading matters here. The sharkfin board page is exact-model software-support evidence. Its generic `0xE5` magnetic packet layouts and detailed handler notes are marked firmware-derived from other named gen2 boards, not a direct capture or firmware disassembly of board 2255. Therefore we may use them to design parsers and test vectors, but must not claim that every sub-operation, scale, response length, or setting is confirmed on this physical 2255 unit.

Safe implementation boundary:
1. Keep all first-stage configuration discovery GET-only and behind a fresh Identify check for board ID 2255.
2. Validate every page length, slot count, page index, checksum, and response shape before exposing parsed values.
3. Treat unsupported/stale replies as failure, not as a valid zero-filled configuration.
4. Do not send any `0x65` magnetic SET, keymap write, LED SET, profile SET, reset, or flash operation.
5. Do not display millimetres until the firmware-specific scale is established and independently checked against live travel data.
6. Keep the 2255's physical layout-to-slot mapping untrusted until a read-only keymap comparison or explicit owner confirmation validates it.

References:
- [sharkfin AK680 MAX exact model/revision support page](https://getsharkfin.com/boards/ajazzmouse-ak680-max)
- [sharkfin ROYUAN protocol reference](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md), especially Families, Keymap, Profiles, Settings, and Magnetic switches
- [sharkfin source repository and license](https://github.com/dniminenn/sharkfin)


## Read-only magnetic GET parser implementation (2026-11-20)

The repository now contains an independent, pure-Python parser for the documented gen2 magnetic-page GET format in `app/magnetic_settings.py`, with regression tests in `tests/test_magnetic_settings.py`. The request builder creates a 64-byte `0xE5` Bit7-checksummed payload with `[subop, 1, page]` in bytes 1–3. The response parser expects the documented raw 64-byte page without an echoed opcode; it also accepts hidapi's 65-byte form with a leading zero report ID.

Supported page layouts are:
- u16 columns 0–4 and 6: 32 little-endian values per page, four pages (128 slots);
- byte columns 5, 7 and 9: 64 values per page, two pages;
- read-only DKS action column 10: sixteen four-byte records per page, eight pages.

The write-only sub-operation 8, all `0x65` magnetic SET operations, and firmware-specific columns 251/252/254 are deliberately not exposed. The parser performs no HID I/O and the GUI does not call it. This is parser/test groundwork only, not proof that board 2255 returns these pages. The public protocol reference marks the detailed `0xE5` handler evidence as firmware-derived from other gen2 boards, so an actual board-2255 GET-only capture is still required before connecting this module to the device. No GET or SET command was sent to the physical keyboard during this development step.

Reference: [sharkfin ROYUAN protocol reference — Magnetic switches](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md#magnetic-switches).


## Read-only keymap GET parser implementation (2026-11-20)

The repository also now contains `app/keymap.py` with regression tests in `tests/test_keymap.py`. It independently builds the documented gen2 `0x8A` request shape `[profile, 0xFF, page, sublayer]` and parses one raw 64-byte response into sixteen four-byte entries. The parser validates profile 0–3, page 0–7, sublayer 0–3, exact response length, and optional zero report-ID prefix. It intentionally preserves each four-byte entry as opaque bytes.

A profile contains four 512-byte keymap sublayers; each sublayer is 128 four-byte slots, represented by eight 64-byte pages. This is sufficient to frame and retain the board's response without guessing field semantics. A factory keymap still must be compared with a verified physical layout before the app can safely present remapping controls.

As with the magnetic parser, the module performs no HID I/O and is not connected to the GUI. The `0x8A` layout is generic gen2 firmware evidence, not a live response from the user's board 2255. No keymap GET or SET was sent to the physical keyboard.

Reference: [sharkfin ROYUAN protocol reference — Keymap sub-layers](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md#keymap-sub-layers).


## Read-only active-profile GET parser implementation (2026-11-20)

Added `app/active_profile.py` with tests in `tests/test_profile.py`. The module constructs the gen2 `0x84` Feature GET packet and parses the zero-based active profile from response byte 1, accepting only the four indices 0–3. The response must have opcode `0x84` and exactly 64 payload bytes (optionally preceded by hidapi's zero report-ID byte).

This parser is pure and not connected to HID or the GUI. It does not switch profiles. Although the exact AK680 MAX 2255 software-support record lists four onboard profiles, the `0x84` transaction has not been tested on the physical unit. No profile GET or SET was sent during this development step.

Reference: [sharkfin ROYUAN protocol reference — Profiles](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md#profiles).


## Matrix GET request-tail sentinel clarification (2026-11-20)

A focused review of HallJoy's RongYuan snapshot transport found an additional request-framing detail: its shared 65-byte report builder fills the unused tail with `0xFF` for matrix-style GET opcodes `0xE5` and `0x8A`. The source comment explains this as an invalid initial tail so a partially produced snapshot cannot be accepted as a complete page. The checksum remains at full-report byte 8 (payload byte 7 after the leading report ID).

The independent Python builders in `app/magnetic_settings.py` and `app/keymap.py` now reproduce that request-tail sentinel: payload bytes 8–63 are `0xFF` for these two matrix GETs. The active-profile `0x84` request is unchanged and retains its zero-filled unused tail. Regression tests assert the distinct tail behavior.

Evidence boundary: this is source-level transport behavior from HallJoy's shared RongYuan implementation; the exact 2255 model is present in its stream-profile table, but the request-tail behavior has not been captured on the user's physical unit. These changes only construct bytes in pure Python; no HID request was sent. The modules remain disconnected from device I/O.
  
Reference: [HallJoy RongYuan snapshot protocol](https://github.com/PashOK7/HallJoy/blob/main/src/HallJoyProject/HallJoy/rongyuan_snapshot_protocol.h) and [RongYuan stream profiles](https://github.com/PashOK7/HallJoy/blob/main/src/HallJoyProject/HallJoy/rongyuan_stream_protocol.h).
