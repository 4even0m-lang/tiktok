"""Single-canvas WYSIWYG visual alert editor.

One WebEngine canvas is both the interactive editor and live preview. Text/GIF/video
stay in the exact same position while properties are edited. New actions are blank.
"""
from __future__ import annotations
import copy
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QColor, QIntValidator, QTextOption
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter,
    QLineEdit, QSpinBox, QComboBox, QListWidget, QPushButton, QLabel,
    QDialogButtonBox, QFileDialog, QColorDialog, QCheckBox, QTextEdit,
    QMessageBox, QProgressDialog, QDoubleSpinBox, QScrollArea,
)
from visual_schema import normalize_elements
from visual_live_preview import VisualLivePreview
from video_tools import ffmpeg_command


def spin(lo, hi, value):
    editor = QSpinBox()
    editor.setRange(lo, hi)
    editor.setValue(int(value))
    editor.setKeyboardTracking(False)
    return editor


def integer_line(lo, hi):
    """A free-typing field: 100-999 and 1280 can be entered in one go.

    Unlike a spinbox that is reconstructed at every keystroke, this never steals
    focus or changes the user's intermediate input.
    """
    edit = QLineEdit()
    edit.setValidator(QIntValidator(lo, hi, edit))
    edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    edit.setMinimumWidth(75)
    return edit


class VisualEditor(QDialog):
    def __init__(self, elements=None, lang='ar', parent=None):
        super().__init__(parent)
        self.lang = lang
        self.ar = lang == 'ar'
        self.layers = normalize_elements(copy.deepcopy(elements or []))
        self.loading = False
        self.converting = None
        self.setWindowTitle('محرر الإشعارات — تعديل ومعاينة مباشرة' if self.ar
                            else 'Visual Alert Editor — live editing canvas')
        self.resize(1410, 840)

        root = QVBoxLayout(self)
        heading = QLabel('لوحة واحدة للتصميم والمعاينة: اسحب العنصر بالماوس، وعدّل النص والمقاس من اليمين. '
                         'الفيديو وGIF يعملان داخل نفس اللوحة.' if self.ar else
                         'One live canvas: drag layers and edit properties on the right. Video and GIF play in place.')
        heading.setWordWrap(True)
        root.addWidget(heading)

        layout = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(layout, 1)
        canvas_panel = QWidget()
        canvas_layout = QVBoxLayout(canvas_panel)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(QLabel('Canvas 1280 × 720 — '+('خلفية مربعات للمعاينة فقط' if self.ar
                                                               else 'checkerboard is editor-only')))
        self.live = VisualLivePreview(self)
        self.live.layer_selected.connect(self.select_by_id)
        self.live.layer_moved.connect(self.moved)
        canvas_layout.addWidget(self.live, 1)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel('التحكم في الفيديو / Video playback'))
        self.pause_button = QPushButton('⏸ إيقاف / Pause')
        self.pause_button.clicked.connect(self.toggle_video)
        toolbar.addWidget(self.pause_button)
        toolbar.addStretch()
        canvas_layout.addLayout(toolbar)
        layout.addWidget(canvas_panel)

        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(7, 7, 7, 7)
        tools = QHBoxLayout()
        for name, kind in [('＋ نص', 'text'), ('＋ شكل', 'rect'), ('＋ صورة', 'image'), ('＋ فيديو', 'video')]:
            button = QPushButton(name)
            button.clicked.connect(lambda checked=False, k=kind: self.add_layer(k))
            tools.addWidget(button)
        right.addLayout(tools)
        right.addWidget(QLabel('العناصر / Layers'))
        self.list = QListWidget()
        self.list.setFixedHeight(135)
        self.list.currentRowChanged.connect(self.choose)
        right.addWidget(self.list)
        buttons = QHBoxLayout()
        delete_button = QPushButton('حذف العنصر / Delete')
        delete_button.clicked.connect(self.delete)
        buttons.addWidget(delete_button)
        buttons.addStretch()
        right.addLayout(buttons)

        form = QFormLayout()
        right.addLayout(form)
        self.text = QTextEdit()
        self.text.setMaximumHeight(100)
        form.addRow('النص / Text', self.text)

        self.file = QLineEdit()
        file_widget = QWidget()
        file_layout = QHBoxLayout(file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.addWidget(self.file)
        browse = QPushButton('…')
        browse.clicked.connect(self.pick)
        file_layout.addWidget(browse)
        form.addRow('ملف / Asset', file_widget)

        self.x = integer_line(0, 1279)
        self.y = integer_line(0, 719)
        self.w = integer_line(12, 1280)
        self.h = integer_line(12, 720)
        for name, edit in [('X', self.x), ('Y', self.y), ('Width / العرض', self.w),
                           ('Height / الارتفاع', self.h)]:
            form.addRow(name, edit)
        hint = QLabel('يمكن كتابة المقاس مباشرة (مثلاً 360 أو 1280) ثم الضغط Enter. '
                      'التغيير يظهر على اللوحة فورًا.' if self.ar else
                      'Type a dimension directly (e.g. 360 or 1280). The canvas updates instantly.')
        hint.setWordWrap(True)
        right.addWidget(hint)

        self.font = QComboBox()
        self.font.setEditable(True)
        self.font.addItems(['Segoe UI', 'Tahoma', 'Arial', 'Cairo', 'Noto Naskh Arabic', 'Consolas'])
        form.addRow('الخط / Font', self.font)
        self.direction = QComboBox()
        self.direction.addItem('العربية RTL', 'rtl')
        self.direction.addItem('English LTR', 'ltr')
        self.direction.addItem('تلقائي Auto', 'auto')
        form.addRow('اتجاه / Direction', self.direction)
        self.align = QComboBox()
        self.align.addItem('يمين / Right', 'right')
        self.align.addItem('وسط / Center', 'center')
        self.align.addItem('يسار / Left', 'left')
        form.addRow('محاذاة / Alignment', self.align)
        self.font_size = spin(8, 160, 36)
        form.addRow('حجم الخط / Font size', self.font_size)
        self.bold = QCheckBox('غامق / Bold')
        form.addRow('', self.bold)
        self.color = QPushButton('لون النص / Text color')
        self.background = QPushButton('لون الشكل / Shape fill')
        self.color.clicked.connect(lambda: self.pick_color('color'))
        self.background.clicked.connect(lambda: self.pick_color('background'))
        form.addRow('Color', self.color)
        form.addRow('Fill', self.background)
        self.opacity = spin(0, 100, 100)
        self.radius = spin(0, 100, 12)
        form.addRow('شفافية % / Opacity', self.opacity)
        form.addRow('Radius', self.radius)

        self.video_note = QLabel('لإزالة خلفية خضراء من فيديو: يلزم FFmpeg. '
                                 'الفيديوهات ذات الخلفيات المعقدة تحتاج فصل خلفية خارجي.')
        self.video_note.setWordWrap(True)
        right.addWidget(self.video_note)
        self.similarity = QDoubleSpinBox()
        self.similarity.setRange(0.01, 1.0)
        self.similarity.setSingleStep(0.03)
        self.similarity.setValue(0.18)
        self.blend = QDoubleSpinBox()
        self.blend.setRange(0, 1.0)
        self.blend.setSingleStep(0.02)
        self.blend.setValue(0.08)
        form.addRow('حساسية اللون / Key', self.similarity)
        form.addRow('نعومة الحواف / Edge', self.blend)
        self.process_video = QPushButton('إزالة الخلفية الخضراء → WebM Alpha')
        self.process_video.clicked.connect(self.convert_chroma)
        right.addWidget(self.process_video)
        right.addStretch(1)

        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setWidget(right_widget)
        panel.setMinimumWidth(380)
        layout.addWidget(panel)
        layout.setSizes([940, 425])

        for edit in (self.x, self.y, self.w, self.h, self.file):
            edit.textChanged.connect(self.apply)
        for edit in (self.x, self.y, self.w, self.h):
            edit.editingFinished.connect(self.commit_numbers)
        self.text.textChanged.connect(self.apply)
        self.font.currentTextChanged.connect(self.apply)
        self.direction.currentIndexChanged.connect(self.direction_changed)
        self.align.currentIndexChanged.connect(self.apply)
        for edit in (self.font_size, self.opacity, self.radius):
            edit.valueChanged.connect(self.apply)
        self.bold.toggled.connect(self.apply)

        footer = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                  QDialogButtonBox.StandardButton.Cancel)
        footer.accepted.connect(self.accept)
        footer.rejected.connect(self.reject)
        root.addWidget(footer)
        self.redraw()

    def current(self):
        row = self.list.currentRow()
        return self.layers[row] if 0 <= row < len(self.layers) else None

    def _name(self, item):
        detail = item.get('text', '').replace('\n', ' ')[:25] or Path(item.get('file') or '').name or item['id']
        return f"{item['type'].upper()} — {detail}"

    def redraw(self, index=None):
        if index is None:
            index = self.list.currentRow()
        self.loading = True
        self.list.clear()
        for item in self.layers:
            self.list.addItem(self._name(item))
        self.loading = False
        self.live.set_layers(self.layers)
        if 0 <= index < len(self.layers):
            self.list.setCurrentRow(index)
        else:
            self.live.select_layer('')

    def add_layer(self, kind):
        layer = {'id': uuid4().hex[:12], 'type': kind, 'x': 80, 'y': 90,
                 'w': 360, 'h': 110, 'text': '', 'font': 'Segoe UI',
                 'font_size': 40, 'bold': True, 'color': '#FFFFFF',
                 'background': '#202A40', 'opacity': 100, 'radius': 12,
                 'file': '', 'direction': 'rtl', 'align': 'right'}
        if kind == 'rect':
            layer['h'] = 130
        self.layers.extend(normalize_elements([layer]))
        self.redraw(len(self.layers)-1)

    def delete(self):
        row = self.list.currentRow()
        if row >= 0:
            del self.layers[row]
            self.redraw(min(row, len(self.layers)-1))

    def select_by_id(self, layer_id):
        for i, item in enumerate(self.layers):
            if item['id'] == layer_id:
                if self.list.currentRow() != i:
                    self.list.setCurrentRow(i)
                return

    def choose(self, row):
        if self.loading or row < 0 or row >= len(self.layers):
            return
        layer = self.layers[row]
        self.loading = True
        self.text.setPlainText(layer['text'])
        self.file.setText(layer['file'])
        for key in ('x', 'y', 'w', 'h'):
            getattr(self, key).setText(str(layer[key]))
        self.font.setCurrentText(layer['font'])
        self.direction.setCurrentIndex(max(0, self.direction.findData(layer['direction'])))
        self.align.setCurrentIndex(max(0, self.align.findData(layer['align'])))
        self.font_size.setValue(layer['font_size'])
        self.bold.setChecked(layer['bold'])
        self.opacity.setValue(layer['opacity'])
        self.radius.setValue(layer['radius'])
        self.color.setText(layer['color'])
        self.background.setText(layer['background'])
        is_text = layer['type'] == 'text'
        is_media = layer['type'] in ('image', 'video')
        self.text.setEnabled(is_text)
        self.font.setEnabled(is_text)
        self.direction.setEnabled(is_text)
        self.align.setEnabled(is_text)
        self.font_size.setEnabled(is_text)
        self.bold.setEnabled(is_text)
        self.color.setEnabled(is_text)
        self.file.setEnabled(is_media)
        self.process_video.setEnabled(layer['type'] == 'video' and self.converting is None)
        self.loading = False
        self._set_qt_text_direction(layer['direction'], layer['align'])
        self.live.select_layer(layer['id'])

    def _set_qt_text_direction(self, direction, alignment):
        # Keep logical Unicode character order; never reverse an Arabic string.
        rtl = direction != 'ltr'
        self.text.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        opts = self.text.document().defaultTextOption()
        opts.setTextDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        opts.setAlignment({'right': Qt.AlignmentFlag.AlignRight,
                           'center': Qt.AlignmentFlag.AlignHCenter,
                           'left': Qt.AlignmentFlag.AlignLeft}[alignment])
        self.text.document().setDefaultTextOption(opts)

    def direction_changed(self, *_):
        if self.loading:
            return
        self._set_qt_text_direction(self.direction.currentData(), self.align.currentData())
        self.apply()

    def moved(self, layer_id, x, y):
        for i, layer in enumerate(self.layers):
            if layer['id'] != layer_id:
                continue
            layer['x'] = min(1279, max(0, x))
            layer['y'] = min(719, max(0, y))
            if self.list.currentRow() != i:
                self.list.setCurrentRow(i)
            self.loading = True
            self.x.setText(str(layer['x']))
            self.y.setText(str(layer['y']))
            self.loading = False
            # The browser already moved the visual element; sync final bounds.
            self.live.set_layers(self.layers)
            return

    def apply(self, *_):
        if self.loading:
            return
        layer = self.current()
        if not layer:
            return
        for key, low, high in [('x', 0, 1279), ('y', 0, 719),
                               ('w', 12, 1280), ('h', 12, 720)]:
            value = getattr(self, key).text().strip()
            if value.isdecimal() and low <= int(value) <= high:
                layer[key] = int(value)
        layer.update({'text': self.text.toPlainText(), 'file': self.file.text(),
                      'font': self.font.currentText(), 'font_size': self.font_size.value(),
                      'bold': self.bold.isChecked(), 'direction': self.direction.currentData(),
                      'align': self.align.currentData(), 'opacity': self.opacity.value(),
                      'radius': self.radius.value()})
        idx = self.list.currentRow()
        if idx >= 0 and self.list.item(idx):
            self.list.item(idx).setText(self._name(layer))
        # Crucially: do NOT redraw widgets or re-select the layer during typing.
        self.live.set_layers(self.layers)

    def commit_numbers(self):
        if self.loading:
            return
        layer = self.current()
        if not layer:
            return
        self.apply()
        self.loading = True
        for key in ('x', 'y', 'w', 'h'):
            edit = getattr(self, key)
            if not edit.text().isdecimal():
                edit.setText(str(layer[key]))
        self.loading = False

    def pick(self):
        layer = self.current()
        if not layer or layer['type'] not in ('image', 'video'):
            return
        pattern = ('Images (*.png *.jpg *.jpeg *.gif *.webp)' if layer['type'] == 'image'
                   else 'Video (*.mp4 *.webm *.mov *.mkv)')
        name, _ = QFileDialog.getOpenFileName(self, 'Choose asset', '', pattern)
        if name:
            self.file.setText(name)

    def toggle_video(self):
        playing = self.live.toggle()
        self.pause_button.setText('⏸ إيقاف / Pause' if playing else '▶ تشغيل / Play')

    def convert_chroma(self):
        layer = self.current()
        if not layer or layer['type'] != 'video':
            QMessageBox.information(self, 'Video', 'اختر طبقة فيديو أولًا / Select a video layer')
            return
        source = layer.get('file', '')
        suggestion = str(Path(source).with_name(Path(source).stem + '_alpha.webm')) if source else ''
        path, _ = QFileDialog.getSaveFileName(self, 'Save transparent WebM', suggestion, 'WebM (*.webm)')
        if not path:
            return
        try:
            args = ffmpeg_command(source, path, self.similarity.value(), self.blend.value())
        except (ValueError, FileNotFoundError) as exc:
            QMessageBox.warning(self, 'FFmpeg', str(exc))
            return
        self.converting = QProcess(self)
        self.progress = QProgressDialog('FFmpeg: إزالة الخلفية الخضراء...', 'إلغاء', 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.canceled.connect(self.converting.kill)
        self.process_video.setEnabled(False)
        self.converting.finished.connect(lambda code, status: self._conversion_finished(code, path, layer))
        self.converting.start(args[0], args[1:])
        self.progress.show()

    def _conversion_finished(self, code, path, layer):
        self.progress.close()
        self.process_video.setEnabled(True)
        if code == 0 and Path(path).is_file() and Path(path).stat().st_size > 0:
            layer['file'] = path
            if self.current() is layer:
                self.file.setText(path)
            self.live.set_layers(self.layers)
            QMessageBox.information(self, 'WebM Alpha', 'تم حفظ الفيديو. اختبر الشفافية في LIVE Studio أيضًا.')
        else:
            stderr = bytes(self.converting.readAllStandardError()).decode('utf-8', errors='replace')
            QMessageBox.warning(self, 'FFmpeg', 'فشل تحويل الفيديو.\n' + stderr[-650:])
        self.converting.deleteLater()
        self.converting = None

    def pick_color(self, which):
        layer = self.current()
        if not layer:
            return
        picked = QColorDialog.getColor(QColor(layer[which]), self)
        if not picked.isValid():
            return
        layer[which] = picked.name()
        self.color.setText(layer['color'])
        self.background.setText(layer['background'])
        self.live.set_layers(self.layers)

    def accept(self):
        self.commit_numbers()
        self.value = normalize_elements(self.layers)
        self.live.stop()
        super().accept()

    def reject(self):
        self.live.stop()
        super().reject()
