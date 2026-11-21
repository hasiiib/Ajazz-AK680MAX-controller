# AJAZZ AK680 MAX Controller for Linux

A native desktop companion for the wired **AJAZZ AK680 MAX HE**. Development prioritizes safe hardware identification, careful protocol verification, and a clean Linux experience.

## Install or update

Open Terminal and run:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/hasiiib/Ajazz-AK680MAX-controller/main/install.sh)
```

If Ubuntu says that `curl` or Git is missing:

```bash
sudo apt update
sudo apt install -y curl git python3 python3-venv
```

Launch **AJAZZ AK680 Controller** from the applications menu, or run:

```bash
~/.local/bin/ak680-controller
```

Run the installer again to update.

## Current status

The physical keyboard has completed the read-only Identify handshake and reported board ID `2255`, matching the public AK680 MAX gen2 record. The Linux application can enumerate the keyboard, verify the paired HID interfaces, and display the identity/firmware metadata available in the Identify response.

An opt-in Analog Monitor is present and remains **experimental**; sustained analog monitoring is **not verified on physical board 2255** as a complete feature. A bounded, explicitly confirmed physical probe has now run on board 2255: the temporary 0x1B start Feature report was sent successfully, 16 valid Report ID 5 samples were parsed (slot 15 was observed, with raw values from 32 to 165), the stop request was sent, and both HID handles were closed. This confirms the basic host transport and report framing for this bounded test only. Sustained streaming, press/hold/release behavior, stop effectiveness, disconnect recovery, and the travel scale remain unverified. Samples are raw counts, not millimetres; their physical unit and calibrated range are unknown. Related gen2 firmware evidence describes the 0x1B flag as volatile, but that effect is not confirmed on board 2255. No persistent setting-write opcode is used. The GUI keeps these limitations visible next to the control.

Read-only protocol groundwork includes gen2 request builders/parsers for magnetic settings pages (`0xE5`), keymap pages (`0x8A`), and active-profile metadata (`0x84`). One standalone `0x84` GET was physically accepted on board 2255 (Profile 1 / index 0), and the live GUI reader now uses it. One `0x8A` page-0 GET was physically accepted (16 four-byte entries); documented gen2 entry shapes now receive readable labels, while unknown/composite entries remain raw. Nonzero byte-4 interpretation is still unresolved for board 2255; the live reader sends byte 4 = 0 only. One `0xE5` sub-operation-0/page-0 GET was physically accepted (32 raw little-endian u16 values, all 200); the live reader requests all four pages, but pages 1–3 have not yet been physically validated. The **Configuration (read-only)** tab now has a user-triggered **Read Configuration (read-only)** action. After a fresh Identify on the same opened control handle confirms board 2255, the worker performs 13 bounded GETs: active profile (`0x84`), eight base keymap pages (`0x8A`, byte 4 = 0; shared zero layer), and four pages of magnetic sub-operation 0 (`0xE5`, actuation-travel column). The acquisition runs off the GUI thread, never switches profiles, and contains no write opcode. The resulting snapshot is validated before display. Known gen2 keymap entry shapes receive human-readable labels; unknown/composite entries retain their raw bytes. Magnetic values remain raw protocol units, not millimetres. Only the active profile, base layer, and actuation column are read; Fn and advanced magnetic columns are not yet included. Pure profile-select, single-slot keymap, magnetic-setting, and board-2255 LED parameter packet helpers now exist for future editor work. They are offline-only, not connected to HID or the GUI; no write command has been sent. The seven additional keymap pages and magnetic pages 1–3 have not yet been physically validated on board 2255, so the first GUI read is a required bounded hardware acceptance test. The tab can also import a strict, complete offline capture bundle; imported target metadata is self-declared and does not establish device or firmware provenance; see [offline bundle format](docs/OFFLINE_CAPTURE_BUNDLE.md). Public protocol research is family-level or firmware-image-derived from other board IDs, not a board-2255 capture. See [board-2255 protocol evidence](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).

The GUI now includes **Export Diagnostics**. It saves a local text report of USB/HID discovery, redacts common USB serial-number fields, and records the current analog evidence boundary: one bounded probe succeeded, while sustained behavior and calibration remain unverified. Exporting diagnostics does not send a device command.

USB connection status refreshes automatically every 1.5 seconds using HID enumeration only. Background refresh does not open device handles or send Identify/configuration commands. If the analog monitor is active and its paired input/control interfaces disappear, the app stops polling, attempts a best-effort stream-clear command, closes both handles, clears stale samples, and restores the controls. Read errors and manual stops also clear stale samples; each poll batch is bounded. The session now performs read-only Identify on the exact opened control handle before any experimental 0x1B attempt, avoiding a separate identify/open race. This identity guard does not establish the 0x1B effect on board 2255.

RGB, remapping, profiles, per-key actuation, Rapid Trigger, DKS, macros, and calibration are not advertised as working. Persistent configuration writes remain disabled pending exact stock board-2255 protocol verification and explicit user authorization. The research note also excludes incompatible 3151:502C and 0C45:80B2 protocols.

## Installation and data safety

- Application files: `~/.local/opt/ak680-controller`.
- Launcher: `~/.local/bin/ak680-controller`.
- Desktop shortcut: `~/.local/share/applications`.
- User configuration: `~/.config/ak680-controller`.
- Updates stage the application and launcher metadata before activation; a post-swap failure restores the previous application directory.
- The installer does not use sudo and does not modify unrelated system directories.
- Do not launch the GUI with sudo.

## Optional HID permissions

This Python hidapi build uses libusb, so the matching USB device node needs access in addition to the vendor HID collection. The repository includes `udev/70-ak680-controller.rules`, scoped to VID:PID `3151:502d` and the relevant interface. This rule was installed and the user's libusb-backed hidapi open was verified on the target Ubuntu system.

To install or refresh it manually, copy the repository rule to:

```text
/etc/udev/rules.d/70-ak680-controller.rules
```

Then reload udev rules and reconnect the keyboard. Do not use broad chmod rules.

## Tests

From a local clone:

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs this suite on pushes and pull requests. It includes response-to-snapshot integration, offline capture assessment and bundle import, documentation safety checks, read-only Qt viewer coverage, safe diagnostics for unusable HID Feature responses, opt-in keymap/magnetic capture helpers, and a regression guard against incompatible 3151:502C / 0C45:80B2 protocol IDs in application code. CI installs the application dependencies and runs the Qt tests in offscreen mode. The current suite count and latest CI run are recorded in [PROJECT_STATUS.md](PROJECT_STATUS.md).

https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions

## Project status

- [Project status](PROJECT_STATUS.md)
- [Development roadmap](ROADMAP.md)

No unique keyboard serial number is stored in this repository.


The first physical active-profile (`0x84`) capture is accepted. One `0x8A` page-0 capture has been accepted; its entries remain opaque and byte-4 semantics unresolved. One `0xE5` sub-operation-0/page-0 capture has also been accepted; its 32 raw u16 values are all 200, but their meanings and other pages remain unverified. The offline capture assessor is available in `app/hardware_verification.py`, and the complete offline capture bundle import is documented in [OFFLINE_CAPTURE_BUNDLE.md](docs/OFFLINE_CAPTURE_BUNDLE.md); see [the verification plan](docs/HARDWARE_VERIFICATION.md) and [the board-specific evidence audit](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).
