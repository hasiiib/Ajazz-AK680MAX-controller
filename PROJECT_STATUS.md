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

## Verified hardware features
No keyboard configuration features have been verified yet. USB/HID discovery in the application is a software capability; it does not prove that configuration protocols are understood.

## Pending verification
- User installation result and application launch.
- Whether the AK680 MAX is detected consistently through USB and hidraw.
- Exact USB VID/PID, interfaces, report descriptors, and safe protocol documentation.

## Session handoff
Next action: collect the user's installer output or screenshot, confirm the app launches, then record the observed device identifiers and discovery results. Continue with read-only protocol research before implementing any keyboard settings.
