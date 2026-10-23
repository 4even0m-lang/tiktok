"""Simple reusable Action editor with blank visual canvas by default."""
import copy
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLineEdit,QCheckBox,
    QSpinBox,QPushButton,QFileDialog,QDialogButtonBox,QMessageBox,QHBoxLayout,QLabel,QWidget)
from rules_engine import normalize_action
from visual_editor import VisualEditor
from preview_data import build_preview_action_payload
from preview_widget import AlertPreviewWidget

class VisualActionDialog(QDialog):
    def __init__(self,settings,language,action=None,parent=None):
        super().__init__(parent)
        self.settings=settings;self.language=language
        self.original=copy.deepcopy(action)
        base=normalize_action(action or {'name':'New Action', 'alert':{'visual_layout':True,'elements':[],'overlay':True,'sound':False}})
        self.elements=copy.deepcopy(base['alert'].get('elements',[]))
        self.setWindowTitle('تصميم Action جديد' if language=='ar' else 'Visual Action Editor')
        self.resize(590,370)
        v=QVBoxLayout(self);form=QFormLayout()
        self.name=QLineEdit(base['name']);form.addRow('اسم الإجراء / Action name',self.name)
        self.enabled=QCheckBox('مفعل / Enabled');self.enabled.setChecked(base['enabled']);form.addRow('',self.enabled)
        self.duration=QSpinBox();self.duration.setRange(1500,30000);self.duration.setSingleStep(500)
        self.duration.setValue(base['alert'].get('duration_ms',4500));form.addRow('مدة الظهور (ms)',self.duration)
        self.audio=QLineEdit(base['alert'].get('sound_file',''))
        audio_row=QWidget();a=QHBoxLayout(audio_row);a.setContentsMargins(0,0,0,0)
        a.addWidget(self.audio,1);btn=QPushButton('…');btn.clicked.connect(self.pick_audio);a.addWidget(btn)
        form.addRow('ملف صوت مستقل',audio_row)
        self.sound=QCheckBox('تشغيل صوت الإشعار');self.sound.setChecked(base['alert'].get('sound',False));form.addRow('',self.sound)
        self.video_audio=QCheckBox('السماح بصوت الفيديو / Video audio')
        self.video_audio.setChecked(base['alert'].get('video_audio',False))
        form.addRow('',self.video_audio)
        v.addLayout(form)
        edit=QPushButton('🎨 افتح لوحة التصميم الفارغة / Edit blank canvas');edit.clicked.connect(self.edit_canvas)
        v.addWidget(edit)
        self.count=QLabel();v.addWidget(self.count);self.refresh_count()
        hint=QLabel('المعاينة تستخدم نفس صفحة Overlay. لا يضاف أي صندوق أو نص افتراضي.')
        hint.setWordWrap(True);v.addWidget(hint)
        buttons_row=QHBoxLayout();preview=QPushButton('معاينة / Preview');preview.clicked.connect(self.preview)
        buttons_row.addWidget(preview);buttons_row.addStretch();v.addLayout(buttons_row)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);v.addWidget(buttons)
        self.base=base;self.value=None
    def refresh_count(self):self.count.setText(f'عدد عناصر اللوحة / Layers: {len(self.elements)}')
    def pick_audio(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose audio','','Audio (*.mp3 *.wav *.ogg *.aac *.m4a)')
        if path:self.audio.setText(path);self.sound.setChecked(True)
    def edit_canvas(self):
        dialog=VisualEditor(self.elements,self.language,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.elements=dialog.value;self.refresh_count()
    def collect(self):
        alert=copy.deepcopy(self.base['alert'])
        alert.update({'visual_layout':True,'elements':self.elements,'overlay':True,
                      'sound':self.sound.isChecked(),'sound_file':self.audio.text().strip(),
                      'duration_ms':self.duration.value(), 'message':'', 'icon':'',
                      'image_file':'','video_file':'','video_only':False,'video_audio':self.video_audio.isChecked()})
        return normalize_action({'id':self.base['id'],'name':self.name.text().strip() or 'New Action',
            'enabled':self.enabled.isChecked(),'alert':alert})
    def preview(self):
        value=self.collect();settings=copy.deepcopy(self.settings)
        settings['actions']=[a for a in settings['actions'] if a['id']!=value['id']]+[value]
        payload=build_preview_action_payload(settings,value['id'],with_sound=True)
        dialog=QDialog(self);dialog.setWindowTitle('Preview');dialog.resize(950,555)
        box=QVBoxLayout(dialog);widget=AlertPreviewWidget(dialog);box.addWidget(widget,1)
        widget.show_alert(payload);close=QPushButton('Close');close.clicked.connect(dialog.accept);box.addWidget(close)
        dialog.exec();widget.stop()
    def accept(self):
        self.value=self.collect();super().accept()
