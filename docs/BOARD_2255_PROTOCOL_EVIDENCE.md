# Board 2255 protocol evidence and safety boundary

Last reviewed: 2026-11-21

## Target identity

This project targets the wired AJAZZ AK680 MAX HE identified on the user's Ubuntu system as:

- User/board designation: **RY1B-2255 / board ID 2255**
- USB VID:PID: **3151:502D**
- HID interfaces observed locally: control candidate interface 2 and analog-input candidate interface 1
- Physical read-only Identify result: **2255**

The local hardware observations above are project history from the user's physical keyboard. They are not results of this GitHub CI run.

## Evidence classes

Keep these categories separate:

1. **Target-board hardware evidence** — a capture or test performed on this exact 3151:502D / board-2255 keyboard.
2. **Family-level hardware evidence** — a plugged-in board of the same protocol family, but a different device ID.
3. **Firmware-image evidence** — reverse engineering of a named firmware image. This describes that image, not automatically every board in its family.
4. **Host-software evidence** — a vendor driver or third-party configurator's code/registry. It can suggest intended support but is not proof that a particular stock firmware build behaves identically.

The public Sharkfin protocol document explicitly marks evidence as `[HW]` (a plugged-in board), `[FW]` (a named firmware image), or `[JS]` (vendor host code only). It also warns that command families share opcode numbers and must be resolved from a device record, not guessed from USB PID alone.

## What the public board registry says

The Sharkfin AK680 MAX board page lists four revisions under the same marketing name, and explicitly says they are different controllers:

| Board ID | USB VID:PID | Registry family | Registry controller |
|---:|---|---|---|
| 2255 | 3151:502D | gen2 | `ry5088_sg9005_rt004_dm_hall_8k` |
| 2336 | 3151:502F | gen2 | `ry5088_sg9005_8k_8k_002` |
| 2343 | 3151:502F | gen2 | `ry5088_sg9005_8k_1k_002` |
| 2371 | 3151:502F | gen2 | `ry5088_sg9005_ns68_002_8k_1k_nolight` |

For board 2255 the third-party registry marks settings support as writable and the key layout as requiring automatic confirmation. That is a compatibility claim from an independent host application, not an instruction to write settings and not a target-board protocol capture.

The same USB PID 3151:502D is also listed for other board IDs/models, including AJAZZ ALUX68 PLUS 2303, AJAZZMOUSE ALUX60 2621/2622, and AttackShark X65HE 2268. Therefore **3151:502D by itself is not enough to identify the board or justify a protocol command**. The locally observed Identify result 2255 is the distinguishing evidence.

The 2336/2343/2371 AK680 MAX revisions use PID 3151:502F and have different controller strings. Do not silently treat them as identical to this 2255 unit.

## Protocol evidence matrix

| Area | Public evidence | Target-2255 status | Project decision |
|---|---|---|---|
| Identify `0x8F` | Shared GET; public protocol gives a 32-bit little-endian device ID | **Physically verified**: user's keyboard returned 2255 | Keep the existing user-initiated read-only Identify path |
| Active profile GET `0x84` | Public protocol labels gen2 profile GET as hardware evidence; reply byte 1 is a zero-based index | **Physically verified once**: send returned 65/65; 65-byte response began `00 84 00`; parser accepted profile index 0 | Keep it read-only; one capture verifies basic framing/profile field only, not other states or reconnect behavior |
| Keymap GET `0x8A` | Public gen2 protocol describes eight raw 64-byte pages; the byte-4 nonzero meaning is not consistent across references | **Physically verified once** for page 0 only; a new GUI path now requests pages 0–7 with byte 4 = 0 after fresh same-handle Identify | Decode only documented four-byte entry shapes; unknown/composite entries remain raw. The additional pages still need physical acceptance testing |
| Keymap request byte 4 | Public gen2 references differ between host-layer (`os`) and sub-layer terminology; the Rust helper ties sub-layer interpretation to the 2268 firmware handler | **Nonzero values are not confirmed on 2255** | The live reader sends only byte 4 = 0, the shared Windows/base value under either interpretation. Nonzero layer requests remain disabled |
| Magnetic GET `0xE5` | The upstream protocol section is marked firmware-derived and cites gen2 images for device IDs 2268, 2116, and 3708. It describes raw pages without opcode echo; sub-operation 0 has four pages of 32 u16 values | **Physically verified once** for sub-operation 0/page 0; the GUI path now requests pages 0–3, but only page 0 has prior physical evidence | Keep raw values; pages 1–3 need physical acceptance testing, and units/value ranges remain unverified |
| Analog stream `0x1B` | Upstream notes derive handlers from images 2268, 2116, and 3708; the cited physical travel-stream observations are from other hardware (including GamaKay TK75HE-V2, device 3833) | **One bounded probe accepted on board 2255**: temporary start Feature report sent; 16 valid Report ID 5 samples parsed (slot 15, raw counts 32–165); stop request sent and both handles closed | Basic host send/report parsing is confirmed for this bounded run only. Keep the monitor experimental; sustained behavior, stop effectiveness, disconnect recovery, and raw travel units/range remain unverified |

The upstream protocol source distinguishes family-level GET evidence from firmware-image-derived storage/handler details. Its magnetic-switch section says the column format follows family but whether columns exist depends on firmware. That is not enough to prove the exact stock firmware on this board supports the same pages.

### Analog transport caveat

The current Linux implementation sends its temporary `0x1B` control packet using hidapi `send_feature_report` on interface 2 and reads Report ID 5 on interface 1. The third-party protocol notes describe the travel sender in terms of a USB input endpoint and report ID 5 on a vendor input collection. Before any experimental stream attempt, the application re-identifies the exact opened control handle that receives the command. One bounded target-board run has now completed: the 65-byte hidapi Feature report send returned its full length, 16 valid 32-byte Report ID 5 samples were parsed (all observed on slot 15, raw travel values 32–165), the stop Feature report send returned successfully, and both handles closed. This confirms the current host send path and basic report framing for that run. Sustained analog monitoring is not verified on board 2255. It does not independently prove that the board ceased streaming after stop, nor does it validate sustained polling, key press/hold/release semantics, disconnect recovery, or the physical travel scale. The raw counts must not be converted to millimetres or presented as calibrated distance.

## Stock firmware versus host software or custom firmware

- The public protocol notes are reverse-engineering documentation. Their named firmware-image findings are from other device IDs (2268, 2116, 3708, etc.), not a published board-2255 stock image.
- Sharkfin is a GPL-3.0-or-later **host configurator**. Its README says it never flashes firmware, and its board page says it is not affiliated with or endorsed by keyboard vendors. Its support registry and protocol source are therefore not custom firmware for this keyboard.
- The AJAZZ UK software page currently lists two distinct AK680 MAX wired entries: “Single-Mode Wired Dual-Mode Magnetic Switch” and “Single-Mode Wired RGB with Magnetic Switch”. It does not map either entry to USB PID 3151:502D or device ID 2255, and it does not publish a stock firmware image/hash. The AJAZZ driver listing separately labels AK680 Max Wireless packages as 8+1K and 8+8K and links an online driver; these are host-software/variant listings, not a firmware manifest for this RY1B-2255 unit. Neither page supplies a cryptographic stock-image hash or confirms which binary belongs to board 2255. A host driver download is not a firmware binary.
- This project has not flashed firmware or installed custom firmware. The Identify result 2255 proves the board's reported ID, not the provenance or hash of every byte in its firmware. Do not label the physical unit's firmware “stock” or “custom” without a matching image/hash or vendor confirmation.
- No firmware update, bootloader, reset, calibration, or flash path is part of this project.

## Explicit exclusions

- Do not borrow the incompatible **3151:502C** lightless-board protocol.
- Do not borrow the unrelated **0C45:80B2** RGB protocol.
- Do not infer board identity from the AK680 MAX marketing name or PID alone.
- Do not send magnetic setting writes (`0x65`), keymap writes (`0x0A`), RGB/per-key colour, macro, calibration, reset, or firmware commands. Persistent writes remain prohibited until exact stock board-2255 behavior is verified and the user explicitly authorizes them.

## Current software boundary

- `active_profile.py`, `keymap.py`, and `magnetic_settings.py` contain pure GET packet builders/parsers only; they do not open HID or send commands.
- `keymap_write.py` and `magnetic_write.py` contain pure, validated single-slot SET packet builders for future editor work. They do not open HID, are not imported by the live reader, and are not connected to a GUI apply action. No `0x0A` or `0x65` write has been sent.
- `live_configuration.py` is the only live configuration acquisition path. It runs only after a user clicks Read Configuration, verifies board 2255 on the same open interface-2 handle, then sends 13 GETs (0x84, eight 0x8A base-layer pages with byte 4 = 0, and four 0xE5 sub-operation-0 pages). It sends no write opcode, does not switch profiles, and never retries a GET. Pages beyond the previously captured 0x8A page 0 and 0xE5 page 0 still need physical validation.
- `read_only_snapshot.py` validates the returned payloads and assembles complete snapshots before display.
- `hardware_verification.py` assesses manually supplied byte captures or copied hex text offline; it never opens HID, sends a command, retries, or persists a capture.
- `offline_snapshot_import.py` validates complete, strict JSON bundles and assembles an in-memory snapshot; target metadata is self-declared and unknown fields (including serial metadata) are rejected.
- `capture_active_profile.py` is an optional CLI requiring an explicit confirmation flag. It opens one unique interface-2 handle, performs the read-only `0x8F` Identify on that handle, and only for ID 2255 sends one `0x84` GET on the same handle; it is not run by the GUI, installer, or background refresh. One physical capture has been accepted.
- `capture_keymap_page.py` is a separate, opt-in one-shot `0x8A` page-0 probe. It is not run by the GUI, installer, or background refresh, and requires its own explicit confirmation flag. One target-board capture was accepted as 16 opaque four-byte entries; its initial wire byte 4 is zero, so it cannot resolve the host-layer/sub-layer ambiguity.
- `capture_magnetic_page.py` is a separate, opt-in one-shot `0xE5` sub-operation-0/page-0 probe. It requires its own confirmation flag, performs a fresh same-handle Identify, and never retries or sends a setting write. One target-board capture has been accepted as a raw 64-byte page containing 32 little-endian u16 values, all 200; their meanings remain unverified.
- `snapshot_panel.py` and `snapshot_view.py` render only a validated in-memory snapshot and do not perform HID I/O. Known gen2 keymap entry shapes receive readable labels; unknown or composite entries stay raw. Magnetic values remain raw protocol counts.
- The Analog Monitor is opt-in and experimental. Before an attempt it re-identifies the exact opened control handle as board 2255. One bounded run confirmed the host-side `0x1B` Feature send and Report ID 5 parsing, and sent the stop request before closing both handles. Stop effectiveness, sustained streaming, volatility, press/hold/release behavior, disconnect recovery, and travel scale remain unverified. Its GUI must keep these limitations visible and must not convert raw counts into millimetres.

## Sources reviewed

All Sharkfin source links below are pinned to repository commit `8c999ba7d44254f5206fb0ff25ed7cea6ebbb496` so the research record is reproducible.

- [Sharkfin AK680 MAX board page](https://getsharkfin.com/boards/ajazzmouse-ak680-max) — exact device ID/PID/controller registry and model revisions.
- [Sharkfin board matrix](https://github.com/dniminenn/sharkfin/blob/8c999ba7d44254f5206fb0ff25ed7cea6ebbb496/docs/BOARDS.md) — board IDs, PIDs, protocol family, and layout coverage.
- [Sharkfin ROYUAN protocol notes](https://github.com/dniminenn/sharkfin/blob/8c999ba7d44254f5206fb0ff25ed7cea6ebbb496/docs/PROTOCOL.md) — evidence markers and family-level protocol research.
- [Sharkfin gen2 keymap implementation](https://github.com/dniminenn/sharkfin/blob/8c999ba7d44254f5206fb0ff25ed7cea6ebbb496/app/src-tauri/src/protocol/gen2.rs) — source of the sub-layer interpretation for byte 4, tied to device 2268 firmware.
- [Sharkfin magnetic/analog implementation](https://github.com/dniminenn/sharkfin/blob/8c999ba7d44254f5206fb0ff25ed7cea6ebbb496/app/src-tauri/src/protocol/hall.rs) — host-side request builders and analog stream notes.
- [Sharkfin README](https://github.com/dniminenn/sharkfin/blob/8c999ba7d44254f5206fb0ff25ed7cea6ebbb496/README.md) — open-source host configurator; states that it never flashes firmware.
- [AJAZZ UK software page](https://ajazz.co.uk/pages/ajazz-software) — lists two distinct wired AK680 MAX variants, but does not identify a matching USB PID/device ID or provide a firmware image/hash.
- [AJAZZ driver listing](https://ajazz.net/pages/ajazz-drivers) — separates 8+1K and 8+8K wireless packages and an online driver; it does not map a package to board 2255 or provide a stock firmware manifest.
- [shorekeeper/ajazzdesktopify](https://github.com/shorekeeper/ajazzdesktopify) — its protocol reconstruction explicitly covers the lightless 3151:502C variant and the RGB 0C45:80B2 variant, not this 3151:502D / board-2255 unit. It is independent host-driver research and does not establish target-board stock firmware or protocol evidence; these protocol branches remain excluded.

## Next evidence gate

One `0xE5` sub-operation-0/page-0 exchange has been captured once and accepted on this exact 3151:502D / ID-2255 unit. The new GUI reader now requests all four pages of that column and all eight 0x8A pages, but only page 0 of each command has prior target-board physical acceptance. Other sub-operations/pages and value meanings remain unverified. The reader uses byte 4 = 0 for every keymap page, the common zero value under either host-layer or sub-layer interpretation; nonzero layers remain disabled. The first `0x84` exchange and one `0x8A` page-0 exchange have each been accepted. The bounded, opt-in `capture_analog_stream.py` probe has now been run once with explicit confirmation: it sent the temporary start request, parsed 16 valid Report ID 5 samples (slot 15; raw counts 32–165), sent the stop request, and closed handles. This establishes basic host send/report parsing only. Further sustained streaming, press/hold/release, stop effectiveness, disconnect recovery, and raw travel scale remain hardware gates. No persistent setting writes were sent.
