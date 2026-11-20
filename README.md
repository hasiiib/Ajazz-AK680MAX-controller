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

**Phase 1 — USB/HID discovery.** The app lists USB devices and available Linux HID raw interfaces. This helps identify the exact keyboard USB identity and interfaces before protocol work begins.

Features such as RGB control, per-key actuation, Rapid Trigger, DKS, macros, remapping, and profiles are not claimed as supported yet. They will be added only after the AK680 MAX's actual USB protocol and firmware behavior are verified.

## Troubleshooting

If the app does not open, run it from Terminal:

```bash
~/.local/bin/ak680-controller
```

Copy the error output when reporting a problem. Do not run the application with `sudo`.
