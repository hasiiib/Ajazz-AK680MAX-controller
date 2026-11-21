# Windows-driver feature parity: board 2255

The product goal is a native Ubuntu implementation of the Windows AJAZZ driver for the wired AK680 MAX HE (Identify ID 2255, USB 3151:502D). This is a parity target, not a promise that every feature is already operational.

## Feature inventory

| Windows-driver area | Linux implementation state | Evidence / next gate |
|---|---|---|
| Device discovery and connection | Implemented | USB VID:PID enumeration, paired HID interfaces, same-handle Identify guard |
| Active profile | Read-only GET and offline profile workspace | GET 0x84 physically accepted once; profile switching remains disabled |
| Key remapping | Read-only base-layer capture, decoder, offline SET packet builder | One 0x8A page-0 GET accepted; physical slot geometry and write/readback behavior unresolved |
| Fn layer and host OS layers | Protocol research only | Gen2 read shape documented by independent sources; target-board capture required |
| Per-key actuation | Read-only sub-operation 0 capture | One 0xE5 subop-0/page-0 response accepted; complete GUI sequence not yet physically validated |
| Rapid Trigger / lift-off / DKS / Mod-Tap / toggle / Snap Tap | Offline packet/parser groundwork only | Additional 0xE5 columns and keymap sublayers are documented by family-level research; target-board values and behavior need capture |
| RGB / lighting effects | Board-2255 LED GET/SET packet helpers | Flags 7/8 are present in vendor model metadata; no target-board LED GET or write acceptance yet |
| Macros | Offline codec and GET/SET packet builders | No target-board macro read or write acceptance yet |
| Named profiles / backup | Local offline workspace and strict snapshot import/export | Not equivalent to switching or applying a hardware profile |
| Calibration | Not implemented | Requires verified target-board command semantics and explicit user test |
| Firmware update / reset | Intentionally excluded | No firmware-update or factory-reset command is sent |

## Implementation rules

1. Only use the exact board identity 2255 after a fresh Identify on the same open control handle.
2. Keep all reads bounded, single-shot, and off the GUI thread. A failed read must not silently retry a command.
3. Treat family-level protocol research as a hypothesis until the exact target board has a capture. Do not infer semantics from a similar AK680 model or a different VID:PID.
4. Before any persistent write feature is enabled, require a complete backup, exact packet evidence, one-setting-at-a-time apply, read-back comparison, rollback/recovery design, and explicit owner approval for the first physical write.
5. Never infer physical key slots from a generic ANSI layout. Require a target-board mapping capture or a carefully validated owner mapping.
6. Keep unsupported or unknown values visible as raw data; do not invent millimetres, effect labels, or switch behavior.
7. Do not send firmware-update, flash erase, reset, or calibration commands as part of discovery.

## Reference research

- `xyzmean/ajazz-driver-electron`: the Electron repository is primarily a packaging wrapper around a pinned vendor WebHID UI snapshot; its related reverse-engineering repository is the useful protocol source.
- `xyzmean/ajazz-driver-reverse`: independently reconstructed vendor command framing and feature serializers.
- `dniminenn/sharkfin`: public protocol notes and gen2 firmware analysis. The protocol is useful for designing read-only requests, but its own evidence labels distinguish hardware, firmware-image, and vendor-JavaScript findings. Those labels must remain distinct from board-2255 physical verification.

## Release gates

- [ ] Physically validate the complete current 13-request read-only configuration acquisition.
- [ ] Capture target-board Fn/OS layers and advanced magnetic columns with a separately bounded read-only operation.
- [ ] Validate the target-board LED GET and decode its returned state.
- [ ] Validate macro GET pages and the complete macro blob shape.
- [ ] Establish physical key-slot mapping.
- [ ] Add editable UI controls only for captured and understood fields.
- [ ] Complete backup, apply, read-back, and recovery safeguards before enabling writes.
- [ ] Run owner-approved physical acceptance tests, then publish a versioned Ubuntu release.
