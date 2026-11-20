import sys, subprocess
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame
def collect():
    parts=[]
    for cmd,label in [(["lsusb"],"USB DEVICES"),(["bash","-lc",'for d in /sys/class/hidraw/hidraw*; do [ -e "$d" ] || continue; echo "$d: $(readlink -f "$d/device")"; done'],"HIDRAW DEVICES")]:
        try: parts.append(label+"\n"+subprocess.run(cmd,capture_output=True,text=True,timeout=5).stdout)
        except Exception as e: parts.append(label+" error: "+str(e))
    return "\n\n".join(parts)
class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("AK680 Control"); self.resize(900,650)
        self.setStyleSheet("QMainWindow,QWidget{background:#101218;color:#e8eaf0;} QLabel#hero{font-size:28px;font-weight:700;} QLabel#sub{color:#9aa3b2;} QFrame#panel{background:#191d26;border:1px solid #2a303c;border-radius:14px;} QPushButton{background:#6c5ce7;color:white;border:0;border-radius:9px;padding:11px 18px;font-weight:600;} QPushButton:hover{background:#8275f0;} QTextEdit{background:#0b0d12;border:1px solid #2b303a;border-radius:10px;color:#cbd5e1;font-family:monospace;}")
        root=QWidget(); lay=QVBoxLayout(root); lay.setContentsMargins(28,28,28,28); lay.setSpacing(16)
        h=QLabel("AK680 CONTROL"); h.setObjectName("hero"); sub=QLabel("Linux companion for AJAZZ AK680 MAX · Hardware discovery stage"); sub.setObjectName("sub")
        lay.addWidget(h); lay.addWidget(sub); panel=QFrame(); panel.setObjectName("panel"); pl=QVBoxLayout(panel); pl.addWidget(QLabel("DEVICE INSPECTOR"))
        self.log=QTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(400); pl.addWidget(self.log); lay.addWidget(panel)
        row=QHBoxLayout(); btn=QPushButton("Scan USB / HID"); btn.clicked.connect(self.scan); row.addWidget(btn); row.addStretch(); lay.addLayout(row)
        info=QLabel("Safe discovery only: no configuration writes are sent yet."); info.setObjectName("sub"); lay.addWidget(info)
        self.setCentralWidget(root); self.scan()
    def scan(self): self.log.setPlainText(collect())
app=QApplication(sys.argv); win=Main(); win.show(); sys.exit(app.exec())
