# Development Roadmap

This roadmap is ordered by dependencies. Complete and verify each stage before moving to the next.

## Phase 1 — Safe foundation
- [x] Create the initial PySide6 application scaffold.
- [x] Add USB/HID discovery UI scaffold.
- [x] Add a dedicated, staged Ubuntu installer with rollback protection.
- [ ] Confirm installation on the user's Ubuntu machine.
- [ ] Confirm the app launches and detects the actual AK680 MAX.
- [ ] Record exact USB VID/PID, interfaces, hidraw nodes, and report descriptors.

## Phase 2 — Hardware protocol investigation
- [ ] Identify the exact AK680 MAX hardware/firmware revision.
- [ ] Research vendor software, official documentation, Linux driver support, and credible community protocol findings.
- [ ] Capture and analyze descriptors and safe read-only traffic where possible.
- [ ] Document verified report formats and device communication constraints.
- [ ] Define a safe protocol test plan; do not send guessed configuration reports.

## Phase 3 — Core keyboard controls
Only begin after the relevant protocol is verified.
- [ ] Device connection/status and clear error handling.
- [ ] RGB lighting controls.
- [ ] Key remapping and per-key settings, if supported by the hardware.
- [ ] Save/load profiles.

## Phase 4 — Advanced features
Only implement features supported by verified firmware/protocol behavior.
- [ ] Per-key actuation settings.
- [ ] Rapid Trigger.
- [ ] DKS.
- [ ] Macro editor and playback.
- [ ] Additional supported modes and profile management.

## Phase 5 — Quality and release
- [ ] Validate behavior on the actual keyboard.
- [ ] Add automated tests for protocol encoding/decoding and application logic.
- [ ] Improve accessibility, UI polish, logging, and recovery behavior.
- [ ] Document installation, usage, compatibility, and limitations.
- [ ] Publish a versioned release when stable.

## Progress tracking rules
- Mark a task complete only after evidence or a reproducible test supports it.
- Record test environment, observed result, and known limitations.
- Update this roadmap and `PROJECT_STATUS.md` after meaningful changes.
- Add a dated session handoff to `PROJECT_STATUS.md` before ending a development session.
