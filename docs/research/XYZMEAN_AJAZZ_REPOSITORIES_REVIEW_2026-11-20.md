# Review of xyzmean AJAZZ driver repositories (2026-11-20)

## Repositories inspected

- Production Electron wrapper: https://github.com/xyzmean/ajazz-driver-electron
- Typed reverse-engineered WebHID protocol: https://github.com/xyzmean/ajazz-driver-reverse
- Rust + Tauri port: https://github.com/xyzmean/ajazz-tauri
- UI snapshot pipeline: https://github.com/xyzmean/ajazz-driver-artifact

The Electron repository is principally a Windows Electron wrapper around a pinned vendor UI snapshot. The protocol implementation of research interest is in `ajazz-driver-reverse`; `ajazz-tauri` is a Rust port and a useful second view of that same protocol family.

## Critical model mismatch: do not transplant this protocol

The reverse repository's `models.ts` lists two entries named `AJAZZ AK680 MAX`:

| USB VID:PID | Decimal in model table | Name |
|---|---:|---|
| `0C45:80B2` | vendor 3141, product 32946 | AJAZZ AK680 MAX |
| `0C45:80B4` | vendor 3141, product 32948 | AJAZZ AK680 MAX |

The physical keyboard for this project is `3151:502D`, and its read-only Identify response reports RongYuan board ID `2255`. The inspected `models.ts` does not list `3151:502D`.

The reverse repository documents a different wire protocol:

- Request header `0xAA`; response header `0x55`.
- WebHID report ID 0.
- Eight-byte header; command byte at offset 1; payload begins at offset 8.
- Device-info command `0x10`; Rapid Trigger GET command `0x17`.
- Its Tauri port hardcodes 64-byte reports for its target vendor interface and uses a chunked request/response transport.

Our target's verified read-only identity path is RongYuan gen2 Feature command `0x8F` over the `3151:502D` device, with board ID `2255`. It is not the `0xAA/0x55` protocol above. Similar product names are not enough to establish protocol compatibility.

**Decision:** do not import, port, or transmit the `0xAA/0x55` commands, `0x10` device-info, `0x17` Rapid Trigger, 64-byte report assumptions, `0x32` RGB stream, or any SET/reset/calibration commands from these repositories to board 2255. They remain reference-only for their own model IDs unless independent evidence proves otherwise.

## Useful engineering ideas retained

1. **Separate enumeration from handshake.** The Tauri implementation groups HID collections by physical VID/PID, attempts a protocol handshake on a candidate, and only then considers it identified. This is a useful design principle, but its handshake and candidate interface rules are not copied.
2. **Represent connection readiness explicitly.** A USB device can be enumerated while the control interface is missing, the input interface is missing, or the pair cannot be proven to share one USB parent. The Linux project now models these as separate states and reports that interface pairing is only a candidate until a fresh board-2255 Identify succeeds.
3. **Keep protocol layers typed and independent of UI.** The reverse repository separates frame transport, command encoders/decoders, and model metadata. We continue the same separation with pure Python packet builders/parsers and no HID side effects in those modules.
4. **Treat model metadata as protocol selection input.** The reverse model table demonstrates why VID/PID and board identity must be checked before selecting a protocol family.

## Security and scope observations

- The Electron wrapper disables Chromium `webSecurity` and broadly auto-grants HID access. Those are deliberate compromises in that Windows wrapper and are not suitable defaults for this Linux native application.
- The reverse command layer contains persistent SET operations, factory reset, calibration, lighting, and Rapid Trigger writes. Their existence is not evidence that those commands apply to board 2255.
- The Tauri helper daemon continuously sends real-time RGB frames for its own supported vendor interface. This is unrelated to our board's verified protocol and is not being adopted.
- The Electron repository is a wrapper around a pinned vendor UI artifact. This project does not need to scrape, embed, or redistribute that vendor UI.

## Project changes following the review

Added `app/device_state.py`, a pure classifier for the target keyboard's already-enumerated HID interface metadata. It distinguishes disconnected, control-only, input-only, ambiguous, and control/input-paired candidate states. It never opens a HID handle or sends a report. A paired interface state explicitly does not imply that the board has passed Identify or that analog streaming is physically verified.

The GUI now displays this connection assessment during Scan USB / HID. The diagnostic inventory is collected once per scan and reused to render the log. Regression tests cover no device, paired interfaces on one USB parent, mismatched USB parents, missing interfaces, missing paths, and ambiguous control interfaces.

## Sources

- [Electron wrapper README](https://github.com/xyzmean/ajazz-driver-electron)
- [Reverse protocol README](https://github.com/xyzmean/ajazz-driver-reverse)
- [Reverse protocol core](https://github.com/xyzmean/ajazz-driver-reverse/blob/main/src/protocol/core.ts)
- [Reverse protocol command decoders](https://github.com/xyzmean/ajazz-driver-reverse/blob/main/src/protocol/commands.ts)
- [Reverse model table](https://github.com/xyzmean/ajazz-driver-reverse/blob/main/src/protocol/models.ts)
- [Tauri Rust protocol port](https://github.com/xyzmean/ajazz-tauri/blob/main/src-tauri/src/protocol.rs)
- [Tauri HID discovery and commands](https://github.com/xyzmean/ajazz-tauri/blob/main/src-tauri/src/commands.rs)

This review records public source observations. It does not establish physical compatibility or validate any additional command on the user's keyboard.
