# Board 2255 Hardware Verification Plan

This plan is a gate for validating the read-only configuration protocol on the physical AJAZZ AK680 MAX HE (USB VID:PID 3151:502D, board ID 2255). It is not an executable probe and does not authorize persistent configuration writes.

## Current evidence

- USB enumeration and HID interface pairing have been observed on the target Ubuntu system.
- A user-initiated, read-only Identify (0x8F) exchange returned board ID 2255.
- The active-profile `0x84` GET has now been physically captured once on board 2255: a 65-byte hidapi result with leading report-ID `00`, opcode `84`, active-profile index `00`, and the parser accepted it. The request send returned 65/65 bytes.
- The `0x8A` keymap and `0xE5` magnetic-settings builders/parsers currently have synthetic unit-test coverage only; neither has a physical capture on this board.
- The reviewed RongYuan protocol reference describes 0x84 as an opcode-echoing GET, while 0x8A keymap and 0xE5 magnetic page GETs return raw 64-byte pages without an opcode echo. This is family-level reference evidence, not a physical capture from board 2255.
- The analog stream is separate and also remains unverified on physical hardware.
- The board-specific evidence audit is in [BOARD_2255_PROTOCOL_EVIDENCE.md](BOARD_2255_PROTOCOL_EVIDENCE.md). It records the upstream `0x8A` byte-4 ambiguity and distinguishes `0xE5` firmware-image evidence and `0x1B` observations on other devices from target-board hardware evidence. The gen2 family label alone does not clear this gate.

## Preconditions

Before a physical configuration-read test is attempted:

1. Confirm the connected device is still VID:PID 3151:502D and Identify reports board ID 2255.
2. Confirm interface 2 is the unique Feature-control candidate. Do not choose a device by display name or serial number.
3. Use a separately invoked, explicitly user-started diagnostic operation. Never run configuration reads from application startup, a timer, connection refresh, or background monitoring.
4. Send only one documented GET at a time. Do not send profile-switch, setting, keymap, calibration, reset, firmware, or other write operations.
5. Do not automatically retry a command after a timeout, malformed frame, or ambiguous response. Stop and preserve the failure evidence.
6. Do not save or publish USB serial numbers, device paths containing unique identifiers, or unrelated HID metadata.

## Staged verification order

| Stage | Request | Initial scope | Acceptance evidence |
|---|---|---|---|
| 1 | Active profile 0x84 GET | <strong>Physically verified once</strong> | Captured 65-byte raw result, 65/65-byte send, leading report-ID `00`, opcode `84`, profile index `0`; no retry |
| 2 | Keymap 0x8A GET | One profile, sublayer 0, page 0 | Exact raw report bytes and confirmed response framing; do not interpret the four-byte entries |
| 3 | Magnetic 0xE5 GET | One supported read-only sub-operation, page 0 | Exact raw report bytes and confirmed response framing; retain values as raw protocol units |

### Stage 1 request envelope (0x84 only)

The pure `active_profile_get_packet()` builder currently produces a 64-byte payload with:

- Byte 0: `0x84` (GET opcode).
- Bytes 1–6: `0x00`.
- Byte 7: `0x7B` (the gen2 checksum for bytes 0–6).
- Bytes 8–63: `0x00`.

The existing hidapi transport convention prepends a zero report-ID byte to the payload for `send_feature_report`, producing a 65-byte host buffer. On the physical board-2255 capture, `send_feature_report` returned 65/65 bytes. `get_feature_report(0, 65)` returned 65 bytes beginning `00 84 00`; the parser normalized the leading report-ID byte and accepted active-profile index `0` (Profile 1). This verifies one successful exchange and framing on this board; it does not establish behavior across repeated reads, other profile states, disconnects, or firmware variants.

For the first physical test, do not run a bulk snapshot, keymap read, magnetic read, or analog monitor. The only permitted operation in this stage is one explicitly user-started `0x84` GET after a fresh Identify result of 2255 and unique interface-2 selection. Record the complete response exactly as returned; do not trim the leading byte, pad a short response, or issue another request to recover from an ambiguous result. Stop after one attempt and review the capture offline with `assess_hex_capture("active-profile", "...")`.

### Optional one-shot capture helper

The repository includes `app/capture_active_profile.py` as an isolated, explicitly invoked diagnostic. Importing it or displaying its help sends no device command. It requires the explicit `--confirm-one-read-only-0x84` flag, selects exactly one interface-2 candidate, opens that handle once, and performs the fresh read-only `0x8F` Identify on that same handle. Only if that opened handle reports board ID 2255 does it send one `0x84` GET and read one Feature response. Reusing the same handle prevents a disconnect/re-enumeration race from redirecting the profile request to another keyboard that shares the PID. The helper accepts hidapi's bytes, bytearray, list-of-integers, and tuple-of-integers Feature return forms, converts them to bytes without dropping or changing the report-ID prefix, and rejects invalid byte values. It never retries either command, saves a file, or prints a serial number or device path. An Identify failure, wrong board ID, partial send, or transport error stops the operation before any later step.

After updating the installed application files, the user can start the one-shot test from a terminal with:

```bash
~/.local/opt/ak680-controller/.venv/bin/python \\
  ~/.local/opt/ak680-controller/capture_active_profile.py \\
  --confirm-one-read-only-0x84
```

The explicit flag is the user's confirmation to send one read-only GET. This Stage 1 capture has already been completed successfully on the user's board; do not rerun it merely to reproduce the result. The helper prints exact response HEX and offline assessment; it does not change any keyboard setting. Share only that output and any error text, never serial numbers or device paths.

### Stage 1 capture worksheet

Record the following without including the USB serial number or unique device path:

- Board identity check: VID:PID `3151:502D`, Identify board ID `2255`.
- Selected HID interface number: `2`; candidate count: `1`.
- Request payload: 64 bytes; host buffer: 65 bytes including leading report-ID zero.
- `send_feature_report` return value: exact integer returned by hidapi.
- `get_feature_report` returned length: exact byte count.
- Raw response: uppercase hex, preserving every byte and its order.
- Offline assessment: accepted/rejected and parser summary.

### Stage 1 physical capture record

- Result: accepted, one user-initiated capture.
- `send_feature_report`: `65/65` bytes.
- `get_feature_report`: 65 raw bytes.
- Raw response: `00 84 00 00 00 00 00 00 7B 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`.
- Framing: leading report-ID `00`, followed by opcode `84`; normalized payload length 64 bytes.
- Parsed active-profile index: `0` (Profile 1).
- No retry; no capture file or serial/device path was recorded.

A timeout, partial send, malformed length, unexpected opcode, or profile byte outside 0..3 ends this stage. Do not continue to another opcode on the basis of a guessed or repaired frame.

Do not proceed to the next stage if the preceding stage has an unexpected report length, report-ID prefix, opcode, refusal/echo pattern, timeout, or inconsistent repeated result. Any repeated observation must be a deliberate new user action, not an automatic retry.

## Evidence record

For each manually initiated observation, record only:

- Date/time and application version or commit.
- VID:PID and the confirmed board ID (never the unique serial).
- Interface number and whether it was uniquely selected.
- Request opcode and non-sensitive request parameters.
- Number of bytes returned by hidapi and the exact raw response bytes.
- Whether the bytes include a report-ID prefix and how normalization was done.
- Parser outcome and a concise error if rejected.

Keep the first raw response unchanged. Do not silently trim, pad, or repair a response to make it pass a parser. Raw captures should be reviewed before changing parser assumptions.

## Offline capture assessment

`assess_capture()` accepts one manually supplied byte sequence, while
`assess_hex_capture()` accepts a copied hexadecimal string with ordinary
whitespace between byte pairs. Both require one explicit stage
(`active-profile`, `keymap`, or `magnetic`). Keymap and magnetic stages require
their corresponding metadata. The hex helper rejects incomplete or decorated
input instead of guessing how to repair it. The assessor calls only the existing
pure parsers; it cannot open the keyboard, send a request, or initiate a retry.
Synthetic unit tests cover opcode-echo distinctions, report-ID prefixes,
malformed lengths, invalid metadata, and preservation of the original capture.

## Exit criteria

A read path may be connected to the application only after the physical captures establish the exact report framing and the board-2255 response semantics, and regression tests cover both valid captures and malformed variants. The GUI must remain read-only and user-initiated.

Persistent writes remain out of scope. Any future write feature requires separate exact protocol evidence, read-back/recovery design, and the user's explicit authorization.