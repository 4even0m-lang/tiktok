"""Qt WebEngine preview of the real Overlay HTML, completely offline.

If PySide6-Addons is missing, the rest of the Windows program remains usable.
"""
import json
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
    WEBENGINE_AVAILABLE=True
except ImportError:
    QWebEngineView=None
    QWebEngineSettings=None
    WEBENGINE_AVAILABLE=False

ROOT=Path(__file__).resolve().parent


class AlertPreviewWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.ready=False
        self.pending=None
        if WEBENGINE_AVAILABLE:
            self.browser=QWebEngineView(self)
            self.browser.page().setBackgroundColor(QColor('#1c2b40'))
            settings=self.browser.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,False)
            self.browser.loadFinished.connect(self._load_finished)
            layout.addWidget(self.browser)
            url=QUrl.fromLocalFile(str(ROOT/'overlay.html'))
            url.setQuery('preview=1')
            self.browser.load(url)
        else:
            self.browser=None
            label=QLabel('Qt WebEngine not available. Install PySide6-Addons.\n'
                         'لا تتوفر المعاينة: ثبّت PySide6-Addons ثم أعد التشغيل.')
            label.setWordWrap(True)
            layout.addWidget(label)

    def _load_finished(self,ok):
        self.ready=bool(ok)
        if ok and self.pending is not None:
            payload=self.pending
            self.pending=None
            self.show_alert(payload)

    def show_alert(self,payload):
        if not self.browser:
            return
        if not self.ready:
            self.pending=dict(payload)
            return
        # json.dumps safely escapes strings and file URIs for JavaScript.
        js='window.previewAlert('+json.dumps(payload,ensure_ascii=True)+');'
        self.browser.page().runJavaScript(js)

    def stop(self):
        self.pending=None
        if self.ready and self.browser:
            self.browser.page().runJavaScript('window.previewStop();')
