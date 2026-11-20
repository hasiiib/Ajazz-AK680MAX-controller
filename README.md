# AJAZZ AK680 MAX Controller for Ubuntu

A native Ubuntu desktop companion for the **wired AJAZZ AK680 MAX**. The current build focuses on safe USB/HID discovery. It does not yet send keyboard configuration commands; device support is being developed and verified before any write features are enabled.

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

After installation, launch **AJAZZ AK680 Controller** from the applications menu, or run:

```bash
~/.local/bin/ak680-controller
```

Running the install command again updates the application.

## Installation and data safety

- Application files live only in `~/.local/opt/ak680-controller`.
- The launcher and desktop shortcut live in `~/.local/bin` and `~/.local/share/applications`.
- User configuration is kept separately in `~/.config/ak680-controller`.
- Updates stage and prepare the new version before swapping the app directory.
- The installer refuses to replace an application path that is a symbolic link or a non-directory.
- It does not use sudo and does not modify system directories or unrelated user files.
- Only the previous contents of this application's dedicated install directory are eligible for cleanup during an update.

## Current status

**Phase 2 / hardware identity verified; analog monitor implementation in opt-in testing.** The physical keyboard has completed the read-only 0x8F Identify handshake and reported board ID `2255`, matching the public AK680 MAX gen2 record. Interface 2 (Feature control) and interface 1 (Report ID 5 input) are verified as belonging to the same USB device. The GUI now includes an opt-in Start / Stop Analog Monitor. It re-identifies the board before enabling the temporary stream, reads raw travel reports, and attempts to stop the stream on stop or app exit. Physical analog streaming, travel units, and full-scale range remain unverified.

Features such as RGB control, per-key actuation, Rapid Trigger, DKS, macros, remapping, and profiles are not claimed as supported yet. They will be added only after the AK680 MAX's actual USB protocol and firmware behavior are verified.

## Troubleshooting

If the app does not open, run it from Terminal:

```bash
~/.local/bin/ak680-controller
```

Copy the error output when reporting a problem. Do not run the application with `sudo`.


## Run the protocol unit tests

From a local clone of the repository:

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions also runs these tests on pushes and pull requests.


## Optional HID permissions (one-time setup)

The Python hidapi build uses libusb and therefore needs access to the matching USB device node as well as the vendor Feature collection. The narrowly scoped rule at `udev/70-ak680-controller.rules` grants `uaccess` only to USB device ID `3151:502d` and retains the interface-02-only hidraw rule. It does not grant direct hidraw access to the keyboard's standard keyboard interfaces or other USB devices.

To install the rule, create `/etc/udev/rules.d/70-ak680-controller.rules` with the contents of that repository file, reload udev rules, then unplug and reconnect the keyboard. Do not run the GUI with sudo. The rule has not been tested on the target machine until the user verifies access after reconnecting.
