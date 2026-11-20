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

An opt-in Analog Monitor is present but remains **experimental and not verified on physical board 2255**. The board identity and HID interface pairing were verified, but the 0x1B command, host transport, Report ID 5 behavior, stop behavior, disconnect recovery, and travel scale have not been validated on this keyboard. Samples are raw counts, not millimetres; their physical unit and calibrated range are unknown. Related gen2 firmware evidence describes the 0x1B flag as volatile, but that effect is not confirmed on board 2255. The app sends no known persistent setting-write opcode; stopping or closing attempts to clear its stream flag. The GUI displays this warning next to the control.

Read-only protocol groundwork includes pure request builders/parsers for gen2 magnetic settings pages (`0xE5`), keymap pages (`0x8A`), and active-profile metadata (`0x84`). They are not connected to live HID reads. A separate **Configuration (read-only)** tab displays only a validated in-memory snapshot; it starts empty and performs no HID I/O. Public protocol research is family-level or firmware-image-derived from other board IDs, not a board-2255 capture; the `0x8A` byte-4 interpretation is inconsistent between upstream documentation and code. See [board-2255 protocol evidence](docs/BOARD_2255_PROTOCOL_EVIDENCE.md). Live configuration acquisition remains disabled.

The GUI now includes **Export Diagnostics**. It saves a local text report of USB/HID discovery, redacts common USB serial-number fields, and clearly marks analog streaming as not yet physically verified. Exporting diagnostics does not send a device command.

USB connection status refreshes automatically every 1.5 seconds using HID enumeration only. Background refresh does not open device handles or send Identify/configuration commands. If the analog monitor is active and its paired input/control interfaces disappear, the app stops polling, attempts a best-effort stream-clear command, closes both handles, clears stale samples, and restores the controls. Read errors and manual stops also clear stale samples; each poll batch is bounded. These safeguards do not establish the 0x1B effect on board 2255.

RGB, remapping, profiles, per-key actuation, Rapid Trigger, DKS, macros, and calibration are not advertised as working. Persistent configuration writes remain disabled pending exact stock board-2255 protocol verification and explicit user authorization. The research note also excludes incompatible 3151:502C and 0C45:80B2 protocols.

## Installation and data safety

- Application files: `~/.local/opt/ak680-controller`.
- Launcher: `~/.local/bin/ak680-controller`.
- Desktop shortcut: `~/.local/share/applications`.
- User configuration: `~/.config/ak680-controller`.
- Updates are staged before activation and include rollback protection.
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

GitHub Actions runs this suite on pushes and pull requests. The suite currently contains **151 tests**, including response-to-snapshot integration, offline capture assessment, documentation safety checks, and read-only Qt viewer coverage. CI installs the application dependencies and runs the Qt tests in offscreen mode. The latest full run passed on commit `7777f1d`; [view the run](https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44781468460).

https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions

## Project status

- [Project status](PROJECT_STATUS.md)
- [Development roadmap](ROADMAP.md)

No unique keyboard serial number is stored in this repository.


Hardware response verification is still gated on physical board-2255 captures. The offline capture assessor is available in `app/hardware_verification.py`; see [the verification plan](docs/HARDWARE_VERIFICATION.md) and [the board-specific evidence audit](docs/BOARD_2255_PROTOCOL_EVIDENCE.md).
