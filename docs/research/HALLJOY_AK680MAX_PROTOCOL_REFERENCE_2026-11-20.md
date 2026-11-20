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
