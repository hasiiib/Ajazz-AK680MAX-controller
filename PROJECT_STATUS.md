# Project Status

Last updated: 2026-11-20

## Goal
Build a polished Linux desktop controller for the wired AJAZZ AK680 MAX HE (board 2255), with hardware behavior verified before features are advertised.

## Verified on the user's physical Ubuntu system
- USB VID:PID: `3151:502D`.
- HID interfaces 0, 1, and 2 enumerate correctly.
- Interface 1 (vendor input Report ID 5) and interface 2 (vendor Feature control) resolve to the same USB parent.
- Read-only Identify opcode `0x8F` returned board ID `2255`, matching the public AK680 MAX gen2 board record.
- The narrowly scoped udev access rule was installed; the USB device node ACL granted the active user read/write access, and libusb-backed hidapi successfully opened interface 2.
- The GUI has launched and its USB/HID discovery and Identify workflow were confirmed by the user.

## Implemented
- PySide6 desktop application and USB/HID inventory.
- Read-only Identify with strict VID/PID/interface selection, response validation, and safe diagnostics.
- Gen2 firmware revision parsing from the Identify reply only; no extra firmware query is sent.
- Linux sysfs pairing check for control/input HID interfaces.
- Opt-in Analog Monitor with fresh board-2255 identity check, paired interface validation, temporary stream start/stop, nonblocking input polling, per-slot raw travel display, and shutdown/error cleanup.
- Staged user-local installer with rollback protection.
- Standard-library unit tests and GitHub Actions workflow.

## Automated verification
- GitHub Actions run for commit `74ea205541d894b6451332dd69d26fad248b1a6c`: **success**.
- The workflow's `unittest` job completed successfully, including regression coverage for partial Identify sends, partial stream-enable sends, input-interface open failure, uncertain stream-enable failure cleanup, and best-effort stop.
- Latest workflow: https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44760074233

## Not yet physically verified
- The analog stream has not yet been tested on the physical keyboard.
- Raw travel values have no confirmed physical unit or calibrated full-scale range.
- RGB, remapping, profiles, per-key actuation, Rapid Trigger, DKS, macros, and calibration are not implemented/verified.

## Safety boundaries
- Do not send guessed HID reports.
- Do not add configuration writes, calibration, reset, RGB, remapping, or profile commands until their exact board-2255 behavior and rollback/recovery are understood.
- The stream start/stop flag is temporary by protocol reference, but still requires actual hardware validation before advertising the monitor as working.
- Never publish the keyboard's unique serial number.
- Never run the GUI with sudo; preserve the narrowly scoped udev access model.

## Next development focus
1. Continue code review and improve GUI structure, state presentation, and error recovery without claiming untested hardware behavior.
2. Investigate additional board-2255 protocol features from credible sources, separating read-only operations from writes.
3. Keep physical analog stream validation as a clearly marked release gate.
4. Expand automated tests for lifecycle edge cases and installer safety.
5. Maintain this status and ROADMAP.md as the authoritative current handoff.


## Protocol variant guard (2026-11-20)

A further protocol comparison established that similarly named AK680 MAX variants are not interchangeable. The physical board is 3151:502D / board 2255 / RY1B-2255. A public AK680 MAX lightless implementation targets 3151:502C, while a separate RGB implementation targets 0C45:80B2 and a different 0xAA/0x55 chunk protocol. Those command sets are explicitly excluded from this project. Future controls must be sourced from board-2255 RongYuan evidence only. See [the research note](docs/research/HALLJOY_AK680MAX_PROTOCOL_REFERENCE_2026-11-20.md#variant-separation-similarly-named-ak680-max-protocols-2026-11-20).
