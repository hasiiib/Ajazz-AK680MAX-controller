# Project Status

Last updated: 2026-11-20

## Project goal
Build a polished, user-friendly Ubuntu application for the wired AJAZZ AK680 MAX keyboard.

## Working rules
- Keep all meaningful progress, decisions, tests, and handoff notes in this public GitHub repository.
- Commit focused changes with descriptive commit messages.
- Update this file and `ROADMAP.md` when project state or priorities change.
- Do not claim a keyboard feature works until it has been implemented and verified on the actual hardware.
- Never write speculative HID reports to the keyboard. Protocol discovery and safe read-only identification come first.
- Installation and updates must stay inside the app's dedicated user directories and must not delete unrelated files or directories.

## Current implementation
- PySide6 desktop GUI scaffold exists in `app/main.py`.
- Current app stage: USB/HID device discovery and display.
- `requirements.txt` includes PySide6 and hidapi.
- `install.sh` installs under `~/.local/opt/ak680-controller`, with launcher at `~/.local/bin/ak680-controller`.
- Installer uses a staged update/rollback approach and does not use sudo.
- User reports that the application UI has launched; the USB/HID scan output confirms the keyboard is visible. Full install/runtime verification is still pending.

## Latest hardware detection result (2026-11-20)
User provided the application's USB/HID scan output from Ubuntu.

Observed USB device:
- VID:PID: `3151:502D`
- Product string: `Gaming Keyboard`
- USB path: `1-1`
- Interfaces exposed in sysfs: `1.0`, `1.1`, and `1.2`

Observed hidraw nodes:
- `/dev/hidraw2` — USB interface `1-1:1.0`, HID ID `3151:502D`
- `/dev/hidraw3` — USB interface `1-1:1.1`, HID ID `3151:502D`
- `/dev/hidraw4` — USB interface `1-1:1.2`, HID ID `3151:502D`

Interpretation:
- The keyboard is successfully visible to the Linux USB stack.
- Three HID interfaces are exposed. Their purposes and report descriptors are not yet established.
- The reported product string is generic ("Gaming Keyboard"); exact marketing model/revision still needs confirmation.
- No configuration protocol or writable report format has been verified.

## HID metadata and permissions check (2026-11-20)
User ran `udevadm info` and `ls -l` for hidraw2, hidraw3, and hidraw4.

Observed:
- All three nodes report `ID_VENDOR_ID=3151` and `ID_MODEL_ID=502d`.
- The requested grep did not return `HID_ID`, `HID_NAME`, or `HID_UNIQ` for these nodes.
- All three nodes are character devices owned by `root:root` with mode `0600`; ordinary users cannot currently open them directly.
- No permission changes have been made.

Implications:
- If direct application access is required later, design a narrowly scoped udev rule for the verified VID/PID and intended interfaces; do not use broad chmod or run the GUI as root.

## USB interface descriptor analysis (2026-11-20)
User provided filtered output from `sudo lsusb -v -d 3151:502d`.

Device:
- VID:PID `3151:502d`
- Three interfaces total.

Interface 0:
- HID class (3), Boot Interface subclass (1), Keyboard protocol (1)
- Report descriptor length: 59 bytes
- Interrupt IN endpoint `0x81`, max packet 64 bytes, interval 1

Interface 1:
- HID class (3), Boot Interface subclass (1), Keyboard protocol (1)
- Report descriptor length: 171 bytes
- Interrupt IN endpoint `0x82`, max packet 64 bytes, interval 1

Interface 2:
- HID class (3), subclass 0, protocol 0
- Report descriptor length: 20 bytes
- Interrupt IN endpoint `0x83`, max packet 64 bytes, interval 1

Interpretation / caveats:
- Interfaces 0 and 1 identify as boot-keyboard HID interfaces.
- Interface 2 is a non-boot HID interface and a candidate for vendor-specific functions, but its purpose is not proven.
- The shown interrupt endpoints are IN only. This does not establish the device's configuration-write path; HID control transfers or other mechanisms may exist, but must be established from descriptors/documentation.
- No reports have been sent to the keyboard and no configuration changes have been attempted.

## HID report descriptor retrieval (2026-11-20)
- The user checked `/sys/bus/usb/devices/1-1/1-1:1.{0,1,2}/report_descriptor`; none of those paths exposed a readable `report_descriptor` file.
- This is a sysfs exposure limitation, not evidence of a keyboard fault.
- The user confirmed `/usr/bin/usbhid-dump` is installed and reviewed its help output.
- `usbhid-dump` supports VID:PID filtering with `-m` and descriptor-only mode with `-e descriptor`.
- The descriptor-only command has been provided but its output has not yet been received:
  `sudo usbhid-dump -m 3151:502d -e descriptor`
- Do not use stream mode for this step. Do not send guessed output/feature reports.

## Verified hardware features
- USB enumeration and presence of three HID interfaces are verified from the user's scan output.
- Raw report descriptor bytes have now been retrieved for all three interfaces using `sudo usbhid-dump -m 3151:502d -e descriptor`.
- Interface 0 descriptor: standard keyboard application collection; 5 LED output bits plus 3 padding bits; 8 modifier input bits plus 6-byte key array input.
- Interface 1 descriptor: input reports include Report ID 1 keyboard bitmap (120 key-usage bits), ID 2 system-control usage, ID 3 consumer/media usage, ID 5 vendor-defined 31-byte input payload, and ID 6 mouse input.
- Interface 2 descriptor: vendor-defined Usage Page `0xFFFF`, Usage `0x02`, 64-byte Feature report (8-bit report size × 64 count), no Report ID.
- Interface 2's Feature report is a promising protocol-investigation candidate, but its command semantics and whether it controls configuration are unknown. The descriptor does not prove RGB or advanced features.
- No keyboard configuration features (RGB control, remapping, macros, actuation adjustment, Rapid Trigger, DKS, or profiles) have been verified.

## Session handoff
Next action: identify the exact hardware/firmware revision and search for official AJAZZ software/protocol documentation or credible community protocol evidence for VID:PID `3151:502d`. Then plan passive/read-only observation if feasible. The 64-byte Feature report on Interface 2 is a candidate only; do not send any Feature/Output report or guessed payload. Update this handoff with evidence and source links.


## HID report descriptor analysis (2026-11-20)
User ran `sudo usbhid-dump -m 3151:502d -e descriptor` and supplied descriptor bytes for interfaces 2, 1, and 0.

Verified descriptor facts:
- Interface 0 (59 bytes): Generic Desktop / Keyboard application collection. It defines 5 LED output bits with 3 padding bits, 8 modifier input bits, and a 6-byte key array input.
- Interface 1 (171 bytes): multiple input collections/reports. Report ID 1 is a keyboard bitmap covering 120 usages; Report ID 2 is System Control; Report ID 3 is Consumer Control/media; Report ID 5 is a 31-byte vendor-defined input report; Report ID 6 is a mouse report with buttons and X/Y/wheel-style fields.
- Interface 2 (20 bytes): Vendor-defined Usage Page `0xFFFF`, Usage `0x02`, with a 64-byte Feature report (8-bit items × 64) and no Report ID.

Interpretation / safety:
- The Interface 2 Feature report is a strong candidate for further protocol research, but its semantics are unknown. Descriptor presence alone does not establish RGB control, remapping, actuation, Rapid Trigger, DKS, macros, or profiles.
- Interface 1's vendor-defined Report ID 5 is input-only according to this descriptor; do not assume it is a configuration channel.
- No Feature or Output reports have been sent. No keyboard settings have been changed.
- Do not probe with guessed payloads. Seek official software/documentation or credible protocol evidence first.


## External protocol research and USB identity discrepancy (2026-11-20)
Initial public research surfaced a potentially important model/USB-ID mismatch:
- The community reverse-engineering repository `shorekeeper/ajazzdesktopify` describes AK680 MAX lightless as VID:PID `3151:502C` and AK680 MAX RGB as `0C45:80B2`; it explicitly documents different protocols for those variants. Source: https://github.com/shorekeeper/ajazzdesktopify
- A separate OpenRGB issue reports the same USB ID `3151:502D` and the same three-interface descriptor lengths (59/171/20) for an Epomaker HE68 Mag. Source: https://gitlab.com/CalcProgrammer1/OpenRGB/-/work_items/5703
- A device database result also associates `3151:502D` with Attack Shark X82HE. Source: https://getsharkfin.com/boards/attack-shark-x82he
- Official AJAZZ driver pages list multiple AK680 MAX wired/magnetic variants, reinforcing that exact model/variant selection matters: https://ajazz.net/pages/ajazz-drivers and https://www.a-jazz.com/en/col.jsp?id=160

Caution:
- The user's detected VID:PID is `3151:502D`, which does not match the two AK680 MAX IDs described in the cited reverse-engineering repository.
- Similar descriptor layout does not prove identical firmware or command protocol. Do not apply the `3151:502C` or `0C45:80B2` protocol to this device.
- Treat the keyboard identity as unresolved until the physical label/packaging and full USB device descriptor (including bcdDevice, manufacturer/product strings where present) are checked.
- The 64-byte vendor-defined Feature report found on Interface 2 is only a structural observation; no command semantics are known and no reports have been sent.

Next handoff:
1. Ask the user to confirm the exact model/variant printed on the keyboard underside or box (and whether it is RGB or no-backlight).
2. Obtain full USB identity fields with `sudo lsusb -v -d 3151:502d | grep -E '(^Bus|bcdUSB|bcdDevice|iManufacturer|iProduct|iSerial|idVendor|idProduct|bNumInterfaces)'`.
3. Reconcile the hardware identity before any protocol-specific implementation. Continue read-only; do not send Feature/Output reports.


## External protocol research: AK680 MAX match found (2026-11-20)
A public open-source keyboard utility's AK680 MAX board page identifies:
- AK680 MAX USB IDs: `3151:502d` and `3151:502f`.
- Device IDs listed: 2255, 2336, 2343, 2371.
- Protocol family: `gen2`.
- For USB ID `3151:502d`, the listed revision is device ID 2255 with controller label `ry5088_sg9005_rt004_dm_hall_8k`.
- The utility states that multiple AK680 MAX revisions exist and identifies the exact command family from the board-reported device ID, not USB PID alone.
Source: https://getsharkfin.com/boards/ajazzmouse-ak680-max

The same project's public protocol document describes the vendor collection used by this keyboard class:
- Usage Page `0xFFFF`, Usage `0x02`.
- 64-byte HID Feature reports, report ID 0 (no Report ID prefix in the descriptor).
- Identify GET opcode `0x8F`; documented reply begins `[0x8F, device_id:u32 little-endian, ...]`.
- It explicitly warns that gen2 and yc500 command opcodes collide and must be selected from the device record; never infer family from USB PID.
Source: https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md

Assessment:
- The user's VID:PID `3151:502d`, AK680 MAX marking, and Interface 2 vendor Feature report are consistent with the public AK680 MAX listing. This resolves the earlier concern that this PID necessarily indicated another keyboard.
- The exact device ID must still be read from the board before selecting commands. Public listing suggests 2255 for this USB PID, but the app must verify the live device response.
- The user's bcdDevice `3.06` is recorded as USB device revision, not assumed to be the same thing as the protocol's board-reported device ID or controller firmware version.
- No protocol command has yet been sent to the keyboard. No settings have been changed.
- User's unique serial number was intentionally not copied into this public repository.

Next step:
1. Implement a read-only identification transaction for opcode `0x8F` on Interface 2 using the documented 64-byte Feature-report transport, with strict VID/PID/interface checks and no fallback writes.
2. Decode and validate the returned device ID; expect 2255 as a hypothesis, not a hardcoded assumption.
3. Only after device ID/family verification, implement GET-only reads and compare replies. Keep all SET/configuration operations disabled until a separate reviewed test plan exists.


## Read-only Identify implementation (2026-11-20)
Implemented and committed the first protocol-aware UI step:
- Added `app/protocol.py` with a narrowly scoped HID Identify operation.
- The operation enumerates only VID:PID `3151:502D`, then requires interface 2 with Usage Page `0xFFFF` and Usage `0x0002`. It refuses zero or multiple matches.
- The only transmitted payload is the documented 64-byte `0x8F` Identify GET packet with the Bit7 checksum, using the unnumbered report-ID convention required by hidapi.
- The response parser accepts the documented 32-bit little-endian board ID and rejects malformed replies / the documented refusal echo.
- Added an “Identify Keyboard (read-only)” button to the desktop UI. It reports the live board ID and compares it with 2255 as a reference hypothesis; it does not select a command family or send any family-specific command.
- Added standard-library unit tests for packet construction, checksum, response decoding, refusal handling, and hidapi report framing in `tests/test_protocol.py`.

Safety and verification:
- No configuration SET command, RGB command, keymap command, calibration command, reset, or firmware command is implemented or sent.
- The new operation has not yet been run against the user's physical keyboard. Unit tests are committed but have not yet been run in the user's Ubuntu environment.
- The user's earlier permissions output showed hidraw nodes as `root:root` mode `0600`; therefore the Identify button may currently report an access/udev permission error. The app deliberately does not request sudo and no permission rule has been installed.
- Next: user updates the app and clicks Identify. If access is denied, inspect the udev attribute hierarchy and add a narrowly scoped rule for the verified settings interface only; do not loosen permissions on all keyboard interfaces.
- Public reference implementation inspected for the transport framing and Identify behavior: https://github.com/dniminenn/sharkfin/blob/master/app/src-tauri/src/hid.rs and https://github.com/dniminenn/sharkfin/blob/master/app/src-tauri/src/protocol/mod.rs


## Current session handoff (2026-11-20)
Code is committed. The pure packet-builder / response-parser smoke checks passed in the development environment. The committed unittest suite has not yet been run in the target Ubuntu installation, and no physical-device Identify transaction has been attempted.

User's next action:
1. Reinstall/update from the latest main branch using the documented installer command.
2. Launch the app and click **Identify Keyboard (read-only)** once.
3. Share the exact result shown in the inspector.

Expected possible blocker: the earlier `root:root 0600` hidraw permissions may prevent opening the settings interface. If so, the app will explain this without elevating privileges. Then request the udev attribute walk for `/dev/hidraw4` and design a precise rule; do not add a broad permission rule.
