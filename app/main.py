import sys
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame,
)

from protocol import (
    IdentifyError,
    identify_keyboard,
    inspect_keyboard_interfaces,
    paired_keyboard_interfaces,
)


def _hid_inventory_text():
    try:
        inventory = inspect_keyboard_interfaces()
    except IdentifyError as exc:
        return "HIDAPI COLLECTIONS\n" + str(exc)

    if not inventory:
        return (
            "HIDAPI COLLECTIONS\n"
            "No hidapi entries found for VID:PID 3151:502D. "
            "Check that the keyboard is connected by USB."
        )

    lines = []
    for item in inventory:
        lines.append(
            "Interface {interface!r}: {role}\n"
            "  path: {path}\n"
            "  usage_page: {usage_page!r}, usage: {usage!r}\n"
            "  USB parent: {usb_parent!r}".format(**item)
        )

    pair = paired_keyboard_interfaces(inventory)
    if pair:
        lines.append(
            "\nPAIRING CHECK: PASS — control interface 2 and analog-input "
            "interface 1 belong to the same USB device ({})".format(
                pair[0]["usb_parent"]
            )
        )
    else:
        lines.append(
            "\nPAIRING CHECK: NOT CONFIRMED — a unique interface 2 / interface 1 "
            "pair with a shared sysfs USB parent was not found. This does not "
            "block the read-only Identify request; it blocks future analog-stream work."
        )
    return "HIDAPI COLLECTIONS\n" + "\n\n".join(lines)


def collect():
    parts = []
    commands = [
        (["lsusb"], "USB DEVICES"),
        (
            [
                "bash", "-lc",
                'for d in /sys/class/hidraw/hidraw*; do '
                '[ -e "$d" ] || continue; '
                'echo "$d: $(readlink -f "$d/device")"; done',
            ],
            "HIDRAW DEVICES",
        ),
    ]
    for cmd, label in commands:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5, check=False
            )
            parts.append(label + "\n" + result.stdout)
            if result.stderr:
                parts.append(label + " STDERR\n" + result.stderr)
        except Exception as exc:
            parts.append(label + " error: " + str(exc))
    parts.append(_hid_inventory_text())
    return "\n\n".join(parts)


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AK680 Control")
        self.resize(900, 650)
        self.setStyleSheet(
            "QMainWindow,QWidget{background:#101218;color:#e8eaf0;}"
            "QLabel#hero{font-size:28px;font-weight:700;}"
            "QLabel#sub{color:#9aa3b2;}"
            "QFrame#panel{background:#191d26;border:1px solid #2a303c;"
            "border-radius:14px;}"
            "QPushButton{background:#6c5ce7;color:white;border:0;"
            "border-radius:9px;padding:11px 18px;font-weight:600;}"
            "QPushButton:hover{background:#8275f0;}"
            "QPushButton:disabled{background:#45415f;color:#aaa;}"
            "QTextEdit{background:#0b0d12;border:1px solid #2b303a;"
            "border-radius:10px;color:#cbd5e1;font-family:monospace;}"
        )

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        hero = QLabel("AK680 CONTROL")
        hero.setObjectName("hero")
        subtitle = QLabel(
            "Linux companion for AJAZZ AK680 MAX · Safe hardware discovery"
        )
        subtitle.setObjectName("sub")
        layout.addWidget(hero)
        layout.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("DEVICE INSPECTOR"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(400)
        panel_layout.addWidget(self.log)
        layout.addWidget(panel)

        row = QHBoxLayout()
        scan_button = QPushButton("Scan USB / HID")
        scan_button.clicked.connect(self.scan)
        row.addWidget(scan_button)

        self.identify_button = QPushButton("Identify Keyboard (read-only)")
        self.identify_button.clicked.connect(self.identify)
        row.addWidget(self.identify_button)
        row.addStretch()
        layout.addLayout(row)

        info = QLabel(
            "Identify sends one 0x8F read request and polls for its reply. "
            "No keyboard settings are changed."
        )
        info.setObjectName("sub")
        layout.addWidget(info)

        self.setCentralWidget(root)
        self.scan()

    def scan(self):
        self.log.setPlainText(collect())

    def identify(self):
        self.identify_button.setEnabled(False)
        self.identify_button.setText("Identifying…")
        self.log.append("\n\nIDENTIFICATION (read-only)")
        try:
            device_id = identify_keyboard()
            expected = 2255
            self.log.append(f"Board-reported device ID: {device_id}")
            if device_id == expected:
                self.log.append(
                    "Matches the public AK680 MAX board record (gen2)."
                )
            else:
                self.log.append(
                    "This ID differs from the public AK680 MAX candidate "
                    f"({expected}); no family-specific command will be sent."
                )
        except IdentifyError as exc:
            self.log.append(f"Identification not completed: {exc}")
        except Exception as exc:
            self.log.append(f"Unexpected identification error: {exc}")
        finally:
            self.identify_button.setEnabled(True)
            self.identify_button.setText("Identify Keyboard (read-only)")


app = QApplication(sys.argv)
window = Main()
window.show()
sys.exit(app.exec())
