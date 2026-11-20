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

An opt-in Analog Monitor is implemented. It re-identifies the board before starting, validates the control/input interface pair, temporarily requests raw travel reports, and attempts cleanup when stopped or when the application exits. **Physical analog streaming has not yet been verified**, and raw travel values have no confirmed physical unit or calibrated range.

Read-only protocol groundwork now includes pure request builders and strict response parsers for gen2 magnetic settings pages (`0xE5`), keymap pages (`0x8A`), and active-profile metadata (`0x84`). These modules are not connected to the GUI, perform no HID I/O, and have not been exercised against the physical board. They do not write or alter keyboard settings.

The GUI now includes **Export Diagnostics**. It saves a local text report of USB/HID discovery, redacts common USB serial-number fields, and clearly marks analog streaming as not yet physically verified. Exporting diagnostics does not send a device command.

USB connection status refreshes automatically every 1.5 seconds using HID enumeration only. Background refresh does not open device handles or send Identify/configuration commands. If the analog monitor is active and its paired input/control interfaces disappear, the app stops polling, attempts the temporary stream-stop command, closes both handles, clears stale samples, and restores the controls. The same cleanup runs after an input error.

RGB, remapping, profiles, per-key actuation, Rapid Trigger, DKS, macros, and calibration are not advertised as working. They require further board-specific protocol research and physical verification.

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

GitHub Actions runs this suite on pushes and pull requests. The latest full unit-test run passed: **74 tests**, including analog-monitor disconnect recovery and GUI cleanup regression checks.

https://github.com/hasiiib/Ajazz-AK680MAX-controller/actions/runs/44766230771

## Project status

- [Project status](PROJECT_STATUS.md)
- [Development roadmap](ROADMAP.md)

No unique keyboard serial number is stored in this repository.
