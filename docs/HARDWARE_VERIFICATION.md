# Board 2255 Hardware Verification Plan

This plan is a gate for validating the read-only configuration protocol on the physical AJAZZ AK680 MAX HE (USB VID:PID 3151:502D, board ID 2255). It is not an executable probe and does not authorize persistent configuration writes.

## Current evidence

- USB enumeration and HID interface pairing have been observed on the target Ubuntu system.
- A user-initiated, read-only Identify (0x8F) exchange returned board ID 2255.
- The 0x84 active-profile, 0x8A keymap, and 0xE5 magnetic-settings request builders and response parsers currently have synthetic unit-test coverage.
- No physical response for 0x84, 0x8A, or 0xE5 has been captured or validated on this board.
- The reviewed RongYuan protocol reference describes 0x84 as an opcode-echoing GET, while 0x8A keymap and 0xE5 magnetic page GETs return raw 64-byte pages without an opcode echo. This is family-level reference evidence, not a physical capture from board 2255.
- The analog stream is separate and also remains unverified on physical hardware.

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
| 1 | Active profile 0x84 GET | One request | Exact raw report bytes, transport return value, normalized length, response opcode, and a profile index in 0..3 |
| 2 | Keymap 0x8A GET | One profile, sublayer 0, page 0 | Exact raw report bytes and confirmed response framing; do not interpret the four-byte entries |
| 3 | Magnetic 0xE5 GET | One supported read-only sub-operation, page 0 | Exact raw report bytes and confirmed response framing; retain values as raw protocol units |

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

## Exit criteria

A read path may be connected to the application only after the physical captures establish the exact report framing and the board-2255 response semantics, and regression tests cover both valid captures and malformed variants. The GUI must remain read-only and user-initiated.

Persistent writes remain out of scope. Any future write feature requires separate exact protocol evidence, read-back/recovery design, and the user's explicit authorization.