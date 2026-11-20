# Development Roadmap

## Foundation and safety
- [x] PySide6 desktop application and user-local installer.
- [x] USB/HID enumeration and interface-role inspection.
- [x] Physical board-2255 read-only Identify handshake.
- [x] Scoped udev access and libusb-backed HID open verified.
- [x] Privacy-filtered diagnostic export.
- [x] Automated installer and protocol regression tests.

## Connection and analog input
- [x] Conservative connection-state classification.
- [x] Automatic metadata-only USB/HID connection refresh.
- [x] Ensure background refresh sends no device commands.
- [x] Automatically abort analog monitoring when the paired interfaces disappear or input/enumeration fails.
- [x] Stop polling, clear stale samples, restore GUI controls, and attempt temporary stream stop during abort.
- [ ] Verify analog start/stop, press/hold/release, and disconnect recovery on the physical keyboard.
- [ ] Establish raw travel units and calibrated range.

## Read-only configuration foundation
- [x] Pure magnetic-settings GET request builder and response parsers.
- [x] Pure keymap GET request builder and opaque-page parser.
- [x] Pure active-profile GET request builder and parser.
- [ ] Validate 0xE5, 0x8A, and 0x84 response framing and values on physical board 2255 before connecting these reads to the GUI.
- [ ] Decode the physical key layout before enabling remapping.

## User-facing controls
- [ ] Build a clear settings interface only for capabilities verified on board 2255.
- [ ] Verify lighting capabilities and safe controls.
- [ ] Verify actuation, Rapid Trigger, DKS, and macro capabilities.
- [ ] Design read-back verification and recovery before any persistent write feature.
- [ ] Physical acceptance testing and versioned release.

## Evidence and safety
- Physical Identify result 2255 is verified; analog streaming and configuration reads are not yet physically verified.
- Similar AJAZZ model names do not guarantee protocol compatibility. Use only evidence applicable to USB 3151:502D / board 2255.
- Do not send guessed commands or implement persistent writes without exact protocol verification and explicit user authorization.
- Preserve user settings and keep installation within the dedicated application directories.

## Current handoff
The latest completed CI run passed **74 tests**: https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44766036781. Automatic connection refresh is metadata-only and does not issue Identify or configuration commands. Physical analog stream validation remains the next hardware gate.
