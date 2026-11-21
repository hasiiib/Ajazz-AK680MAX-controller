import sys
import subprocess
from threading import Thread
from datetime import datetime
from time import monotonic
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QFileDialog, QTabWidget,
)

from analog_stream import AnalogStreamError, AnalogStreamSession
from diagnostics import build_diagnostic_report
from device_state import evaluate_connection

from snapshot_panel import ReadOnlySnapshotPanel

from protocol import (
    IdentifyError,
    identify_keyboard_details,
    inspect_keyboard_interfaces,
    paired_keyboard_interfaces,
)


def _hid_inventory_text(inventory=None, inventory_error=None):
    if inventory_error:
        return "HIDAPI COLLECTIONS\n" + inventory_error
    if inventory is None:
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
            "Interface {interface_number!r}: {role}\n"
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


def collect(inventory=None, inventory_error=None):
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
    parts.append(_hid_inventory_text(inventory, inventory_error))
    return "\n\n".join(parts)


class StreamStopNotifier(QObject):
    """Deliver completion of a potentially blocking HID stop off the GUI thread."""

    finished = Signal(object)


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AK680 Control")
        self.resize(900, 650)
        self.setStyleSheet(
            "QMainWindow,QWidget{background:#101218;color:#e8eaf0;}"
            "QLabel#hero{font-size:28px;font-weight:700;}"
            "QLabel#sub{color:#9aa3b2;}"
            "QLabel#warning{color:#ffd08a;background:#2b2118;border:1px solid #694c2a;"
            "border-radius:8px;padding:10px;}"
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

        tabs = QTabWidget()
        inspector_tab = QWidget()
        inspector_layout = QVBoxLayout(inspector_tab)
        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("DEVICE INSPECTOR"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(400)
        panel_layout.addWidget(self.log)
        inspector_layout.addWidget(panel)

        self.snapshot_panel = ReadOnlySnapshotPanel()
        tabs.addTab(inspector_tab, "Device Inspector")
        tabs.addTab(self.snapshot_panel, "Configuration (read-only)")
        layout.addWidget(tabs)

        self.connection_status = QLabel("USB connection: not scanned")
        self.connection_status.setObjectName("sub")
        layout.addWidget(self.connection_status)

        self.analog_status = QLabel("Analog monitor: stopped")
        self.analog_status.setObjectName("sub")
        layout.addWidget(self.analog_status)

        row = QHBoxLayout()
        scan_button = QPushButton("Scan USB / HID")
        scan_button.clicked.connect(self.scan)
        row.addWidget(scan_button)

        self.identify_button = QPushButton("Identify Keyboard (read-only)")
        self.identify_button.clicked.connect(self.identify)
        row.addWidget(self.identify_button)

        self.stream_button = QPushButton("Start Analog Monitor")
        self.stream_button.clicked.connect(self.toggle_analog_stream)
        row.addWidget(self.stream_button)

        export_button = QPushButton("Export Diagnostics")
        export_button.clicked.connect(self.export_diagnostics)
        row.addWidget(export_button)
        row.addStretch()
        layout.addLayout(row)

        self.analog_warning = QLabel(
            "Identify sends one read-only 0x8F request. A bounded physical probe on "
            "board 2255 successfully sent the temporary 0x1B start request, received "
            "16 valid Report ID 5 samples (slot 15 observed), sent the stop request, "
            "and closed both HID handles. SUSTAINED ANALOG MONITORING IS NOT VERIFIED ON PHYSICAL BOARD 2255 as a complete feature. The monitor remains EXPERIMENTAL: sustained "
            "streaming, press/hold/release behavior; disconnect recovery; stop effectiveness "
            "are not yet verified. Values are raw counts; their "
            "physical unit and calibrated range are unknown. No persistent setting-write opcode is used; "
            "the effect/volatility of the temporary stream flag is not fully "
            "characterized."
        )
        self.analog_warning.setObjectName("warning")
        self.analog_warning.setWordWrap(True)
        layout.addWidget(self.analog_warning)

        self.setCentralWidget(root)
        self.stream_session = AnalogStreamSession()
        self.stream_stop_notifier = StreamStopNotifier(self)
        self.stream_stop_notifier.finished.connect(self._on_analog_stop_finished)
        self.stream_stop_thread = None
        self.latest_samples = {}
        self.analog_samples_received = 0
        self.last_analog_sample_at = None
        self.stream_timer = QTimer(self)
        self.stream_timer.setInterval(33)
        self.stream_timer.timeout.connect(self.poll_analog_stream)

        # Re-enumerate metadata only. This timer never opens a HID handle or
        # sends Identify/configuration/stream commands.
        self.connection_timer = QTimer(self)
        self.connection_timer.setInterval(1500)
        self.connection_timer.timeout.connect(self.refresh_connection_status)

        self.scan()
        self.connection_timer.start()

    def scan(self):
        try:
            inventory = inspect_keyboard_interfaces()
            inventory_error = None
            state = evaluate_connection(inventory)
            self.connection_status.setText(f"USB connection: {state.message}")
        except IdentifyError as exc:
            inventory = None
            inventory_error = str(exc)
            self.connection_status.setText(f"USB connection scan failed: {exc}")
        self.log.setPlainText(collect(inventory, inventory_error))

    def refresh_connection_status(self):
        """Refresh HID presence and stop streaming if its interface pair disappears."""
        try:
            inventory = inspect_keyboard_interfaces()
            state = evaluate_connection(inventory)
            self.connection_status.setText(f"USB connection: {state.message}")
            if self.stream_session.active and not state.analog_pair_candidate:
                self._abort_analog_stream(
                    "Keyboard connection lost or analog interface pair is no longer unique."
                )
        except IdentifyError as exc:
            self.connection_status.setText(f"USB connection scan failed: {exc}")
            if self.stream_session.active:
                self._abort_analog_stream(
                    "USB/HID enumeration failed while the analog monitor was running."
                )

    def _abort_analog_stream(self, reason):
        """Close a lost stream promptly; stop command is best-effort on disconnect."""
        self.stream_timer.stop()
        try:
            self.stream_session.stop()
        except AnalogStreamError as exc:
            self.log.append(f"\n\nANALOG MONITOR STOP WARNING: {exc}")
        finally:
            self.latest_samples.clear()
            self.stream_button.setText("Start Analog Monitor")
            self.stream_button.setEnabled(True)
            self.identify_button.setEnabled(True)
            self.analog_status.setText("Analog monitor: stopped — connection lost")
            self.log.append(f"\n\nANALOG MONITOR: {reason}")

    def export_diagnostics(self):
        """Save a privacy-filtered support report; this performs no HID I/O."""
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        default_name = f"ak680-controller-diagnostics-{stamp}.txt"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Diagnostic Report",
            str(Path.home() / default_name),
            "Text files (*.txt)",
        )
        if not filename:
            return
        try:
            report = build_diagnostic_report(collect())
            Path(filename).write_text(report, encoding="utf-8")
        except OSError as exc:
            self.statusBar().showMessage(f"Diagnostic export failed: {exc}", 10000)
            self.log.append(f"\n\nDIAGNOSTIC EXPORT ERROR: {exc}")
            return
        self.statusBar().showMessage(f"Diagnostic report saved: {filename}", 10000)
        self.log.append(f"\n\nDIAGNOSTICS EXPORTED: {filename}")

    def toggle_analog_stream(self):
        if self.stream_session.active:
            self.stop_analog_stream()
            return
        self.stream_button.setEnabled(False)
        try:
            self.stream_session.start()
            self.latest_samples.clear()
            self.analog_samples_received = 0
            self.last_analog_sample_at = None
            self.stream_timer.start()
            self.stream_button.setText("Stop Analog Monitor")
            self.identify_button.setEnabled(False)
            self.analog_status.setText("Analog monitor: running; press and release keys to view raw travel.")
            self.log.append("\n\nANALOG MONITOR: started (experimental; target-board 0x1B effect unverified)")
        except AnalogStreamError as exc:
            self.analog_status.setText("Analog monitor: could not start")
            self.log.append(f"\n\nANALOG MONITOR ERROR: {exc}")
        finally:
            self.stream_button.setEnabled(True)

    def poll_analog_stream(self):
        try:
            samples = self.stream_session.poll(max_reports=16)
            if samples:
                self.last_analog_sample_at = monotonic()
            self.analog_samples_received += len(samples)
            for sample in samples:
                self.latest_samples[sample.slot] = sample.raw_travel
            observed = sorted(self.latest_samples.items())
            preview = ", ".join(f"{slot}:{value}" for slot, value in observed[:8])
            if self.last_analog_sample_at is None:
                freshness = "waiting for first sample"
            else:
                age_ms = max(0, int((monotonic() - self.last_analog_sample_at) * 1000))
                freshness = f"last sample {age_ms} ms ago"
            suffix = f" | latest slot:raw counts {preview}" if preview else ""
            self.analog_status.setText(
                f"Analog monitor: running | samples: {self.analog_samples_received} "
                f"| slots observed: {len(observed)} | {freshness}{suffix}"
            )
        except AnalogStreamError as exc:
            self._abort_analog_stream(f"Analog input error: {exc}")
            self.analog_status.setText("Analog monitor: stopped after input error")

    def stop_analog_stream(self):
        """Stop HID streaming in a worker so a slow Feature report cannot freeze Qt."""
        self.stream_timer.stop()
        self.stream_button.setEnabled(False)
        self.identify_button.setEnabled(False)
        self.analog_status.setText("Analog monitor: stopping…")
        self.stream_stop_thread = Thread(
            target=self._stop_analog_stream_worker,
            name="ak680-analog-stop",
            daemon=True,
        )
        self.stream_stop_thread.start()

    def _stop_analog_stream_worker(self):
        error = None
        try:
            self.stream_session.stop()
        except AnalogStreamError as exc:
            error = str(exc)
        except Exception as exc:
            error = f"Unexpected stop error: {exc}"
        self.stream_stop_notifier.finished.emit(error)

    def _on_analog_stop_finished(self, error):
        """Restore controls only after the worker has closed its HID handles."""
        self.latest_samples.clear()
        if error is None:
            self.analog_status.setText("Analog monitor: stopped")
            self.log.append("\\n\\nANALOG MONITOR: stopped")
        else:
            self.analog_status.setText("Analog monitor: stop attempted; check device connection")
            self.log.append(f"\\n\\nANALOG MONITOR STOP WARNING: {error}")
        self.stream_button.setText("Start Analog Monitor")
        self.stream_button.setEnabled(True)
        self.identify_button.setEnabled(True)
        self.stream_stop_thread = None

    def closeEvent(self, event):
        if self.stream_stop_thread is not None and self.stream_stop_thread.is_alive():
            self.statusBar().showMessage(
                "Please wait for the analog monitor stop operation to finish."
            )
            event.ignore()
            return
        self.stream_timer.stop()
        self.connection_timer.stop()
        try:
            self.stream_session.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def identify(self):
        self.identify_button.setEnabled(False)
        self.identify_button.setText("Identifying…")
        self.log.append("\n\nIDENTIFICATION (read-only)")
        try:
            result = identify_keyboard_details()
            device_id = result.device_id
            expected = 2255
            self.log.append(f"Board-reported device ID: {device_id}")
            if result.firmware_revision is not None:
                self.log.append(
                    f"Firmware revision (gen2 Identify metadata): {result.firmware_revision}"
                )
            else:
                self.log.append(
                    "Firmware revision: not reported / not safely decodable "
                    "from Identify metadata."
                )
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
