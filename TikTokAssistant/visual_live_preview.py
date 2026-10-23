"""One interactive WebEngine canvas for both editing and instant visual preview.

The same HTML element handles text, animated GIF, and video. The checkerboard is
editor-only; saved Overlay backgrounds remain transparent. No duplicate Qt canvas.
"""
import json
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebChannel import QWebChannel
except ImportError:
    QWebEngineView = QWebEngineSettings = QWebChannel = None


class CanvasBridge(QObject):
    selected = Signal(str)
    moved = Signal(str, int, int)

    @Slot(str)
    def selectLayer(self, layer_id):
        self.selected.emit(layer_id)

    @Slot(str, int, int)
    def moveLayer(self, layer_id, x, y):
        self.moved.emit(layer_id, x, y)


class VisualLivePreview(QWidget):
    layer_selected = Signal(str)
    layer_moved = Signal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.layers = []
        self.ready = False
        self.playing = True
        self.selected_id = ''
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._sync)
        self.browser = None

        if QWebEngineView is None or QWebChannel is None:
            label = QLabel('المعاينة المباشرة تحتاج PySide6-Addons / Qt WebEngine.\n'
                           'Install: python -m pip install PySide6-Addons')
            label.setWordWrap(True)
            layout.addWidget(label)
            return

        self.browser = QWebEngineView(self)
        self.browser.setMinimumHeight(440)
        self.browser.page().setBackgroundColor(QColor('#172233'))
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        self.bridge = CanvasBridge(self)
        self.bridge.selected.connect(self.layer_selected)
        self.bridge.moved.connect(self.layer_moved)
        self.channel = QWebChannel(self.browser.page())
        self.channel.registerObject('editorBridge', self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.browser.loadFinished.connect(self._loaded)
        layout.addWidget(self.browser)
        self.browser.load(QUrl.fromLocalFile(str(Path(__file__).with_name('visual_live_preview.html'))))

    def _loaded(self, ok):
        self.ready = bool(ok)
        if ok:
            self._sync()

    def set_layers(self, layers):
        self.layers = [dict(item) for item in layers]
        if self.ready:
            self.timer.start()

    def select_layer(self, layer_id):
        self.selected_id = str(layer_id or '')
        if self.ready and self.browser:
            self.browser.page().runJavaScript('window.selectVisual(' + json.dumps(self.selected_id) + ');')

    def _sync(self):
        if not self.ready or not self.browser:
            return
        layers = []
        for layer in self.layers:
            item = dict(layer)
            if item.get('type') in ('image', 'video'):
                source = Path(item.get('file') or '')
                item['preview_uri'] = source.resolve().as_uri() if source.is_file() else ''
            layers.append(item)
        payload = json.dumps(layers, ensure_ascii=True)
        selected = json.dumps(self.selected_id)
        self.browser.page().runJavaScript('window.updateVisual(' + payload + ',' + selected + ');')

    def toggle(self):
        self.playing = not self.playing
        if self.ready and self.browser:
            self.browser.page().runJavaScript('window.setPreviewPlaying(' + str(self.playing).lower() + ');')
        return self.playing

    def stop(self):
        self.timer.stop()
        if self.ready and self.browser:
            self.browser.page().runJavaScript('window.setPreviewPlaying(false);')
