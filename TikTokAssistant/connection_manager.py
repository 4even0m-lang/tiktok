import os
import sys
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, QTimer, Signal, QProcessEnvironment
from portable_runtime import subprocess_launch

class TikTokConnectionManager(QObject):
    status_changed = Signal(str)
    log_received = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.on_finished)
        self.process.errorOccurred.connect(self.on_error)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.on_timeout)
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self.force_kill)
        self.buffer = ""
        self.connected = False
        self.stopping = False
        self.preserve_status = False
        self.last_error = False

    def connect_live(self, username):
        if self.process.state() != QProcess.NotRunning:
            self.log_received.emit("الموصل يعمل بالفعل")
            return
        script = Path(__file__).resolve().parent / "gift_test.py"
        if not getattr(sys, "frozen", False) and not script.exists():
            self.status_changed.emit("خطأ")
            self.log_received.emit(f"ملف غير موجود: {script}")
            return
        self.buffer = ""
        self.connected = False
        self.stopping = False
        self.preserve_status = False
        self.last_error = False
        username = username.strip().lstrip("@")
        if not username:
            self.status_changed.emit("خطأ")
            self.log_received.emit("أدخل اسم حساب TikTok")
            return
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("TIKTOK_USERNAME", username)
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(script.parent))
        self.status_changed.emit("جاري الاتصال")
        self.log_received.emit(f"بدء الاتصال بالحساب {username}")
        program, arguments = subprocess_launch("gift", script)
        self.process.start(program, arguments)
        self.timeout.start(30000)

    def read_output(self):
        self.buffer += bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            self.log_received.emit(line)
            if line == "TIKTOK_CONNECTED":
                self.connected = True
                self.timeout.stop()
                self.status_changed.emit("متصل")
            elif line.startswith(("TIKTOK_ERROR:", "TIKTOK_FATAL:")):
                self.last_error = True
                self.timeout.stop()
                self.status_changed.emit("فشل الاتصال")

    def on_timeout(self):
        if not self.connected:
            self.log_received.emit("لم يصل إشعار نجاح الاتصال خلال 30 ثانية")
            self.status_changed.emit("انتهت مهلة الاتصال")
            self.disconnect_live(preserve_status=True)

    def disconnect_live(self, preserve_status=False):
        self.timeout.stop()
        if self.process.state() == QProcess.NotRunning:
            if not preserve_status:
                self.status_changed.emit("غير متصل")
            return
        self.stopping = True
        self.preserve_status = preserve_status
        self.process.terminate()
        self.kill_timer.start(1500)

    def force_kill(self):
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()

    def on_error(self, error):
        self.timeout.stop()
        self.log_received.emit(f"QProcess error: {error}")
        self.status_changed.emit("خطأ")

    def on_finished(self, exit_code, exit_status):
        self.timeout.stop()
        self.kill_timer.stop()
        self.read_output()
        if self.buffer.strip():
            self.log_received.emit(self.buffer.strip())
            self.buffer = ""
        if self.stopping:
            if not getattr(self, "preserve_status", False):
                self.status_changed.emit("غير متصل")
        else:
            if self.last_error or exit_code != 0:
                self.status_changed.emit("فشل الاتصال")
            elif self.connected:
                self.status_changed.emit("انقطع الاتصال")
            else:
                self.status_changed.emit("انتهى الاتصال دون نجاح")
            self.log_received.emit(f"انتهت عملية الموصل: exit_code={exit_code}, exit_status={exit_status}")
        self.connected = False
        self.stopping = False
