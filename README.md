# AJAZZ AK680 MAX Controller for Ubuntu

Native Ubuntu utility for the wired AJAZZ AK680 MAX. This project is in early device-discovery stage: it detects and reports USB/HID interfaces safely before sending configuration reports.

## Install
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/hasiiib/Ajazz-AK680MAX-controller/main/install.sh)
```

For private repositories, authenticate GitHub CLI first (`gh auth login`).

## Safety
- Installs only under ~/.local/opt/ak680-controller and ~/.local/bin.
- Updates replace this app's own installation only.
- Never deletes unrelated files or system directories.
- Configuration data is kept in ~/.config/ak680-controller.
