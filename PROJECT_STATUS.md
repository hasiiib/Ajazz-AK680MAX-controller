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
