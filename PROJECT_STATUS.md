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
- User has been given the public install command, but successful installation and runtime behavior have not yet been confirmed in this project log.

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

## Verified hardware features
USB enumeration and presence of three HID interfaces are verified from the user's scan output. No keyboard configuration features have been verified yet.

## Pending verification
- User installation result and application launch.
- Whether the AK680 MAX is detected consistently through USB and hidraw.
- Exact USB VID/PID, interfaces, report descriptors, and safe protocol documentation.

## Session handoff
Next action: inspect the three HID report descriptors and kernel metadata using read-only commands, then map interface roles. Do not send output reports or modify keyboard settings until protocol behavior is documented.


## HID metadata and permissions check (2026-11-20)
User ran `udevadm info` and `ls -l` for hidraw2, hidraw3, and hidraw4.

Observed:
- All three nodes report `ID_VENDOR_ID=3151` and `ID_MODEL_ID=502d`.
- The requested grep did not return `HID_ID`, `HID_NAME`, or `HID_UNIQ` for these nodes.
- All three nodes are character devices owned by `root:root` with mode `0600`; ordinary users cannot currently open them directly.
- No permission changes have been made.

Implications:
- Need inspect USB interface descriptors and HID report descriptors to distinguish interface roles.
- Later, if direct application access is required, design a narrowly scoped udev rule for the verified VID/PID and intended interfaces; do not use broad chmod or run the GUI as root.


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
- Interface 2 is a non-boot HID interface and is a candidate for vendor-specific functions, but its purpose is not proven.
- The shown interrupt endpoints are IN only. This does not establish the device's configuration-write path; HID control transfers or other mechanisms may exist, but must be established from descriptors/documentation.
- No reports have been sent to the keyboard and no configuration changes have been attempted.

Next investigation:
- Obtain the actual report descriptor bytes for each interface (prefer sysfs/kernel-exposed descriptors or a safe HID descriptor inspection utility).
- Decode report usages, report IDs, and input/output/feature report sizes.
- Do not probe by sending guessed SET_REPORT or vendor commands.


## HID report descriptor sysfs check (2026-11-20)
User checked `/sys/bus/usb/devices/1-1/1-1:1.{0,1,2}/report_descriptor`; none of the three paths exposed a readable `report_descriptor` file.
- This is a sysfs exposure limitation, not evidence of a keyboard fault.
- Descriptor lengths remain known from lsusb (59, 171, and 20 bytes), but raw descriptor bytes have not yet been retrieved.
- Next: check whether `usbhid-dump` is available, inspect its help/options, then use descriptor-only mode for the matching VID:PID/interface. Avoid stream mode and do not send reports.
