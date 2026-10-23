"""TikFinity-inspired event/action configuration UI (original implementation).

Two independent overview tables, and focused modal editors. Uses existing v5 rules
schema and engine; does not add fake integrations or an online account dependency.
"""
from __future__ import annotations
import copy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QDialogButtonBox, QGroupBox,
    QCheckBox, QLineEdit, QComboBox, QFormLayout, QSpinBox, QScrollArea,
    QFileDialog, QMessageBox, QRadioButton, QButtonGroup, QGridLayout,
    QListWidget, QListWidgetItem, QAbstractItemView, QSplitter,
)
from rules_engine import make_id, normalize_action, normalize_event
from settings_store import normalize_alert
from presets import PRESETS
from preview_data import build_preview_action_payload
from preview_widget import AlertPreviewWidget
from visual_action_ui import VisualActionDialog
from gift_catalog_ui import GiftCatalogDialog

WORDS = {
    'ar': {
        'title':'Actions & Events — الإجراءات والأحداث',
        'intro':'1) أنشئ إجراءً يحدد ما سيظهر أو يُسمع.  2) أنشئ حدثًا يحدد متى ومن يستطيع تشغيله.  3) اربط أي حدث بإجراء واحد أو أكثر.',
        'actions':'Actions — الإجراءات', 'action_desc':'ماذا تريد أن يحدث؟ أنشئ إجراءات مستقلة ثم اربطها بالأحداث أدناه.',
        'events':'Events — الأحداث', 'event_desc':'متى ينفذ البرنامج الإجراءات؟ حدد المحفّز والإجراءات المرتبطة به.',
        'new_action':'＋ إنشاء Action', 'new_event':'＋ إنشاء Event', 'edit':'تعديل', 'copy':'نسخ',
        'delete':'حذف', 'preview':'معاينة', 'test':'اختبار على Overlay',
        'active':'مفعل', 'name':'الاسم', 'screen':'الشاشة', 'duration':'المدة', 'picture':'صورة',
        'sound':'صوت', 'video':'فيديو', 'summary':'الوصف', 'audience':'المستخدمون',
        'trigger':'المحفّز', 'linked':'الإجراء/الإجراءات', 'cooldown':'الانتظار',
        'no_actions':'لا توجد إجراءات. اضغط «إنشاء Action» للبدء.',
        'no_events':'لا توجد أحداث. أنشئ Event واربطه بـAction.',
        'all':'الجميع', 'specific':'حساب محدد', 'unsupported':'غير متاح حاليًا مع البيانات المستقبَلة',
        'follower':'المتابعون', 'subscriber':'المشتركون', 'moderator':'المشرفون', 'topgifter':'أكثر المهدين',
        'action_editor':'إنشاء / تعديل إجراء', 'event_editor':'إنشاء / تعديل حدث',
        'choose_action':'ماذا تريد أن يحدث؟ (يمكن تحديد عدة خيارات)',
        'show_anim':'عرض تصميم متحرك', 'show_img':'عرض صورة / GIF',
        'play_sound':'تشغيل صوت', 'play_video':'تشغيل فيديو', 'show_text':'عرض إشعار (اسم + نص)',
        'video_only':'فيديو فقط دون بطاقة', 'template':'تصميم الإشعار',
        'icon':'الرمز', 'accent':'لون الإطار (#RRGGBB)', 'message':'نص الإشعار',
        'image_file':'ملف صورة / GIF', 'video_file':'ملف فيديو MP4 / WebM',
        'sound_file':'ملف الصوت', 'browse':'استعراض', 'global_volume':'استخدام الصوت العام',
        'volume':'مستوى الصوت', 'video_audio':'تشغيل صوت الفيديو',
        'enabled':'تفعيل الإجراء / الحدث', 'who':'من يستطيع تفعيل الحدث؟',
        'who_note':'الخيارات التي تحتاج بيانات إضافية من TikTok تظهر معطلة حتى لا نَعِد بوظيفة غير مدعومة.',
        'which':'ما الحدث الذي يشغّل الإجراءات؟', 'gift':'إرسال هدية',
        'follow':'متابعة جديدة', 'likes':'بلوغ عدد إعجابات',
        'coins':'بلوغ عدد عملات', 'comment':'تعليق يحتوي كلمة',
        'gift_name':'اسم الهدية (فارغ = أي هدية)', 'min_coins':'الحد الأدنى لعملات الهدية',
        'threshold':'العدد المستهدف', 'keyword':'الكلمة المطلوبة',
        'coin_basis':'طريقة حساب العملات', 'stream':'مجموع البث', 'single':'هدية واحدة',
        'user_id':'معرّف TikTok (بدون @)', 'cooldown_s':'فاصل التكرار بالثواني',
        'fallback':'قاعدة احتياطية لأي هدية لا تطابق قاعدة مخصصة',
        'mode':'عند وجود أكثر من إجراء', 'all_actions':'نفّذ جميع الإجراءات',
        'random':'اختر إجراءً عشوائيًا', 'link_label':'اربط الإجراءات (يمكن اختيار أكثر من واحد)',
        'save':'حفظ', 'cancel':'إلغاء', 'delete_confirm':'حذف العنصر المحدد؟',
        'missing_action':'أنشئ Action أولًا قبل إنشاء Event.',
        'select_one':'اختر عنصرًا من الجدول أولًا.',
        'not_linked':'غير مرتبط', 'none':'بدون', 'ready':'جاهز',
        'saved':'تم حفظ التعديل.', 'test_note':'للاختبار على Overlay شغّل الخادم أولًا.',
        'preview_title':'معاينة Action (بدون بدء بث)',
        'message_tip':'متغيرات النص: {user} {gift} {count} {coins} {total_likes}',
    },
    'en': {
        'title':'Actions & Events',
        'intro':'1) Create an action to define what happens.  2) Create an event to define when it happens.  3) Link one or more actions to an event.',
        'actions':'Actions', 'action_desc':'What should happen? Create reusable actions and link them to events below.',
        'events':'Events', 'event_desc':'When should an action run? Configure the trigger and link actions.',
        'new_action':'＋ Create new Action', 'new_event':'＋ Create new Event', 'edit':'Edit', 'copy':'Duplicate',
        'delete':'Delete', 'preview':'Preview', 'test':'Test on Overlay',
        'active':'Enabled', 'name':'Name', 'screen':'Display', 'duration':'Duration', 'picture':'Picture',
        'sound':'Sound', 'video':'Video', 'summary':'Description', 'audience':'Audience',
        'trigger':'Trigger', 'linked':'Action(s)', 'cooldown':'Cooldown',
        'no_actions':'No actions defined. Select Create new Action.',
        'no_events':'No events defined. Create an Event and link an Action.',
        'all':'Everyone', 'specific':'A specific user', 'unsupported':'Not yet available from captured TikTok data',
        'follower':'Any follower', 'subscriber':'Any subscriber', 'moderator':'Any moderator', 'topgifter':'Top gifter',
        'action_editor':'New / Edit Action', 'event_editor':'New / Edit Event',
        'choose_action':'What should happen? (Multiple options selectable)',
        'show_anim':'Show animation', 'show_img':'Show picture / GIF',
        'play_sound':'Play audio', 'play_video':'Play video file', 'show_text':'Show alert (user + text)',
        'video_only':'Video only, no card', 'template':'Alert template',
        'icon':'Icon', 'accent':'Accent color (#RRGGBB)', 'message':'Alert message',
        'image_file':'Image / GIF file', 'video_file':'MP4 / WebM video',
        'sound_file':'Audio file', 'browse':'Browse', 'global_volume':'Use global volume',
        'volume':'Audio volume', 'video_audio':'Enable video audio',
        'enabled':'Enable this action / event', 'who':'Who can trigger the event?',
        'who_note':'Audience types that require unavailable TikTok metadata are disabled.',
        'which':'What triggers the event?', 'gift':'Sending a gift',
        'follow':'Follow', 'likes':'Likes milestone', 'coins':'Coins milestone',
        'comment':'Comment with keyword', 'gift_name':'Gift name (blank = any)',
        'min_coins':'Minimum gift coins', 'threshold':'Target count', 'keyword':'Comment keyword',
        'coin_basis':'Coin counting mode', 'stream':'Stream total', 'single':'Single gift',
        'user_id':'TikTok username (without @)', 'cooldown_s':'Cooldown in seconds',
        'fallback':'Fallback gift rule only when no specific rule matches',
        'mode':'With multiple actions', 'all_actions':'Run all actions',
        'random':'Pick one at random', 'link_label':'Link existing Actions (multiple allowed)',
        'save':'Save', 'cancel':'Cancel', 'delete_confirm':'Delete the selected item?',
        'missing_action':'Create an Action before creating an Event.',
        'select_one':'Select an item in the table first.',
        'not_linked':'Not linked', 'none':'None', 'ready':'Ready',
        'saved':'Changes saved.', 'test_note':'Start the Overlay server before using Test on Overlay.',
        'preview_title':'Action preview (no live stream needed)',
        'message_tip':'Text variables: {user} {gift} {count} {coins} {total_likes}',
    },
}


def tr(lang, key):
    return WORDS.get(lang,WORDS['ar']).get(key,key)


def spin(mn, mx, value, step=1):
    s=QSpinBox();s.setRange(mn,mx);s.setValue(int(value));s.setSingleStep(step);return s


def section(text):
    title=QLabel(text)
    title.setStyleSheet('font-size:15px;font-weight:700;')
    return title


def pick_file(dialog, field, extensions):
    file_path,_=QFileDialog.getOpenFileName(dialog,'Choose file','',extensions)
    if file_path:field.setText(file_path)


def media_row(dialog, current, filter_text):
    holder=QWidget();row=QHBoxLayout(holder);row.setContentsMargins(0,0,0,0)
    edit=QLineEdit(current);edit.setClearButtonEnabled(True)
    button=QPushButton('…');button.setFixedWidth(40)
    button.clicked.connect(lambda:pick_file(dialog,edit,filter_text))
    row.addWidget(edit,1);row.addWidget(button)
    return holder,edit


def scrolled_form(dialog, inner):
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(inner)
    dialog.layout().addWidget(scroll,1)


class ActionDialog(QDialog):
    def __init__(self, settings, language, action=None, parent=None):
        super().__init__(parent)
        self.language=language;self._=lambda key:tr(language,key)
        self.settings=settings
        self.original=copy.deepcopy(action) if action else None
        self.setWindowTitle(self._('action_editor'))
        self.resize(670,730);self.setMinimumSize(540,540)
        self.setModal(True)
        outer=QVBoxLayout(self)
        content=QWidget();lay=QVBoxLayout(content);lay.setSpacing(12)
        lay.addWidget(section(self._('action_editor')))
        a=normalize_action(action or {'name':'New Action','alert':{}})
        cfg=a['alert']
        head=QFormLayout()
        self.name=QLineEdit(a['name']);head.addRow(self._('name'),self.name)
        self.enabled=QCheckBox(self._('enabled'));self.enabled.setChecked(a['enabled']);head.addRow('',self.enabled)
        lay.addLayout(head)
        group=QGroupBox(self._('choose_action'));opts=QVBoxLayout(group)
        self.show_anim=QCheckBox(self._('show_anim'))
        self.show_img=QCheckBox(self._('show_img'))
        self.play_sound=QCheckBox(self._('play_sound'))
        self.play_video=QCheckBox(self._('play_video'))
        self.show_text=QCheckBox(self._('show_text'))
        self.show_anim.setChecked(bool(cfg['overlay'] and cfg['template']!='video'))
        self.show_img.setChecked(bool(cfg.get('image_file')))
        self.play_sound.setChecked(bool(cfg['sound']))
        self.play_video.setChecked(bool(cfg.get('video_file')))
        self.show_text.setChecked(bool(cfg['message']))
        for chk in (self.show_anim,self.show_img,self.play_sound,self.play_video,self.show_text):opts.addWidget(chk)
        lay.addWidget(group)
        form=QFormLayout();form.setSpacing(11)
        self.template=QComboBox()
        for key, info in PRESETS.items():
            self.template.addItem(str(info.get('ar' if language=='ar' else 'en',key)),key)
        self.template.setCurrentIndex(max(0,self.template.findData(cfg['template'])))
        form.addRow(self._('template'),self.template)
        self.icon=QLineEdit(cfg['icon']);form.addRow(self._('icon'),self.icon)
        self.accent=QLineEdit(cfg['accent']);form.addRow(self._('accent'),self.accent)
        self.message=QLineEdit(cfg['message']);form.addRow(self._('message'),self.message)
        lay.addWidget(QLabel(self._('message_tip')))
        self.duration=spin(1500,30000,cfg['duration_ms'],500)
        form.addRow(self._('duration')+' (ms)',self.duration)
        image_row,self.image=media_row(self,cfg['image_file'],'Images (*.png *.jpg *.jpeg *.gif *.webp)')
        video_row,self.video=media_row(self,cfg['video_file'],'Videos (*.mp4 *.webm)')
        audio_row,self.audio=media_row(self,cfg['sound_file'],'Audio (*.wav *.mp3 *.ogg *.aac *.m4a)')
        form.addRow(self._('image_file'),image_row)
        form.addRow(self._('video_file'),video_row)
        form.addRow(self._('sound_file'),audio_row)
        self.video_only=QCheckBox(self._('video_only'));self.video_only.setChecked(cfg['video_only'])
        form.addRow('',self.video_only)
        self.video_audio=QCheckBox(self._('video_audio'));self.video_audio.setChecked(cfg['video_audio'])
        form.addRow('',self.video_audio)
        self.global_volume=QCheckBox(self._('global_volume'));self.global_volume.setChecked(cfg['volume'] is None)
        form.addRow('',self.global_volume)
        self.volume=spin(0,100,settings['volume'] if cfg['volume'] is None else cfg['volume'],5)
        form.addRow(self._('volume'),self.volume)
        lay.addLayout(form)
        self.global_volume.toggled.connect(lambda state:self.volume.setEnabled(not state))
        self.volume.setEnabled(not self.global_volume.isChecked())
        self.show_img.toggled.connect(image_row.setEnabled)
        self.play_video.toggled.connect(video_row.setEnabled)
        self.play_sound.toggled.connect(audio_row.setEnabled)
        self.show_text.toggled.connect(self.message.setEnabled)
        self.show_anim.toggled.connect(self.template.setEnabled)
        image_row.setEnabled(self.show_img.isChecked())
        video_row.setEnabled(self.play_video.isChecked())
        audio_row.setEnabled(self.play_sound.isChecked())
        self.message.setEnabled(self.show_text.isChecked())
        self.template.setEnabled(self.show_anim.isChecked())
        self.image.textChanged.connect(lambda value:self.show_img.setChecked(bool(value.strip())))
        self.video.textChanged.connect(lambda value:self.play_video.setChecked(bool(value.strip())))
        self.audio.textChanged.connect(lambda value:self.play_sound.setChecked(bool(value.strip())))
        scrolled_form(self,content)
        footer=QHBoxLayout()
        prev=QPushButton(self._('preview'));prev.clicked.connect(self.preview)
        footer.addWidget(prev);footer.addStretch()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(self._('save'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self._('cancel'))
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        footer.addWidget(buttons);outer.addLayout(footer)
        self.value=None

    def collect(self):
        previous=self.original or normalize_action({'alert':{}})
        alert=copy.deepcopy(previous['alert'])
        alert.update({
            'overlay':any((self.show_anim.isChecked(),self.show_img.isChecked(),
                           self.play_video.isChecked(),self.show_text.isChecked())),
            'sound':self.play_sound.isChecked(),
            'template':self.template.currentData() or 'neon',
            'icon':self.icon.text().strip() or '🎁', 'accent':self.accent.text().strip(),
            'message':self.message.text() if self.show_text.isChecked() else '',
            'duration_ms':self.duration.value(),
            'image_file':self.image.text().strip() if self.show_img.isChecked() else '',
            'video_file':self.video.text().strip() if self.play_video.isChecked() else '',
            'sound_file':self.audio.text().strip() if self.play_sound.isChecked() else '',
            'video_only':self.video_only.isChecked() and self.play_video.isChecked(),
            'video_audio':self.video_audio.isChecked() and self.play_video.isChecked(),
            'volume':None if self.global_volume.isChecked() else self.volume.value(),
        })
        return normalize_action({'id':previous['id'],'name':self.name.text().strip() or 'New Action',
                                 'enabled':self.enabled.isChecked(),'alert':alert})

    def accept(self):
        value=self.collect();cfg=value['alert']
        if self.show_img.isChecked() and not cfg['image_file']:
            QMessageBox.warning(self,self._('action_editor'),self._('image_file'));return
        if self.play_video.isChecked() and not cfg['video_file']:
            QMessageBox.warning(self,self._('action_editor'),self._('video_file'));return
        self.value=value
        super().accept()

    def preview(self):
        value=self.collect()
        settings=copy.deepcopy(self.settings)
        settings['actions']=[a for a in settings.get('actions',[]) if a['id']!=value['id']]+[value]
        try:
            payload=build_preview_action_payload(settings,value['id'],with_sound=True)
        except Exception as ex:
            QMessageBox.warning(self,self._('preview'),str(ex));return
        dialog=QDialog(self);dialog.setWindowTitle(self._('preview_title'));dialog.resize(820,460)
        layout=QVBoxLayout(dialog)
        widget=AlertPreviewWidget(dialog);layout.addWidget(widget,1)
        widget.show_alert(payload)
        close=QPushButton(self._('cancel'));close.clicked.connect(dialog.accept);layout.addWidget(close)
        dialog.exec();widget.stop()


class EventDialog(QDialog):
    def __init__(self,settings,language,event=None,parent=None):
        super().__init__(parent)
        self.language=language;self._=lambda key:tr(language,key)
        self.original=copy.deepcopy(event) if event else None
        self.setWindowTitle(self._('event_editor'))
        self.resize(690,730);self.setMinimumSize(540,540)
        root=QVBoxLayout(self)
        content=QWidget();body=QVBoxLayout(content);body.setSpacing(12)
        cfg=normalize_event(event or {'name':'New Event','trigger':'gift'})
        form=QFormLayout()
        self.name=QLineEdit(cfg['name']);form.addRow(self._('name'),self.name)
        self.enabled=QCheckBox(self._('enabled'));self.enabled.setChecked(cfg['enabled']);form.addRow('',self.enabled)
        body.addLayout(form)
        # TikFinity-like audience radio section. Unsupported roles are explicitly disabled.
        audience_group=QGroupBox(self._('who'));aud=QVBoxLayout(audience_group)
        self.audience_buttons=QButtonGroup(self);self.audience_buttons.setExclusive(True)
        self.all_users=QRadioButton(self._('all'));self.specific_user=QRadioButton(self._('specific'))
        for btn in (self.all_users,self.specific_user):self.audience_buttons.addButton(btn)
        self.all_users.setChecked(not bool(cfg.get('user_filter')))
        self.specific_user.setChecked(bool(cfg.get('user_filter')))
        aud.addWidget(self.all_users)
        for key in ('follower','subscriber','moderator','topgifter'):
            disabled=QRadioButton(self._(key));disabled.setEnabled(False)
            disabled.setToolTip(self._('unsupported'))
            aud.addWidget(disabled)
        aud.addWidget(self.specific_user)
        self.user_id=QLineEdit(cfg.get('user_filter',''))
        self.user_id.setPlaceholderText('@username')
        aud.addWidget(self.user_id)
        self.specific_user.toggled.connect(self.user_id.setEnabled)
        self.user_id.setEnabled(self.specific_user.isChecked())
        note=QLabel(self._('who_note'));note.setWordWrap(True);note.setObjectName('muted');aud.addWidget(note)
        body.addWidget(audience_group)
        trigger_group=QGroupBox(self._('which'));triggers=QVBoxLayout(trigger_group)
        self.trigger_buttons={};self.trigger_group=QButtonGroup(self)
        for key in ('gift','follow','likes','coins','comment'):
            btn=QRadioButton(self._(key));self.trigger_group.addButton(btn)
            self.trigger_buttons[key]=btn
            triggers.addWidget(btn)
        self.trigger_buttons[cfg['trigger']].setChecked(True)
        body.addWidget(trigger_group)
        details=QGroupBox('');f=QFormLayout(details)
        self.gift_name=QLineEdit(cfg['gift_name'])
        gift_row=QWidget();gift_line=QHBoxLayout(gift_row);gift_line.setContentsMargins(0,0,0,0)
        gift_line.addWidget(self.gift_name,1)
        self.catalog_button=QPushButton('🎁 Catalog');self.catalog_button.clicked.connect(self.choose_gift)
        gift_line.addWidget(self.catalog_button);f.addRow(self._('gift_name'),gift_row)
        self.min_coins=spin(0,1000000000,cfg['min_coins']);f.addRow(self._('min_coins'),self.min_coins)
        self.threshold=spin(1,1000000000,cfg['threshold'],100);f.addRow(self._('threshold'),self.threshold)
        self.keyword=QLineEdit(cfg['keyword']);f.addRow(self._('keyword'),self.keyword)
        self.coin_basis=QComboBox()
        self.coin_basis.addItem(self._('stream'),'stream')
        self.coin_basis.addItem(self._('single'),'gift')
        self.coin_basis.setCurrentIndex(max(0,self.coin_basis.findData(cfg['coin_basis'])))
        f.addRow(self._('coin_basis'),self.coin_basis)
        self.cooldown=spin(0,3600,cfg['cooldown_sec']);f.addRow(self._('cooldown_s'),self.cooldown)
        self.fallback=QCheckBox(self._('fallback'));self.fallback.setChecked(cfg['fallback_only']);f.addRow('',self.fallback)
        self.mode=QComboBox()
        self.mode.addItem(self._('all_actions'),'all');self.mode.addItem(self._('random'),'random')
        self.mode.setCurrentIndex(max(0,self.mode.findData(cfg['mode'])))
        f.addRow(self._('mode'),self.mode)
        body.addWidget(details)
        self.detail_form=f;self.gift_row=gift_row
        body.addWidget(section(self._('link_label')))
        self.action_list=QListWidget();self.action_list.setMinimumHeight(120)
        for action in settings['actions']:
            item=QListWidgetItem(action['name']);item.setData(Qt.ItemDataRole.UserRole,action['id'])
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if action['id'] in cfg['action_ids'] else Qt.CheckState.Unchecked)
            self.action_list.addItem(item)
        body.addWidget(self.action_list)
        for button in self.trigger_buttons.values():button.toggled.connect(self.refresh_fields)
        self.refresh_fields()
        scrolled_form(self,content)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(self._('save'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self._('cancel'))
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.value=None

    def choose_gift(self):
        dialog=GiftCatalogDialog(self.language,self)
        if dialog.exec()==QDialog.DialogCode.Accepted and dialog.selection:
            self.gift_name.setText(dialog.selection)

    def refresh_fields(self):
        kind=next((key for key,btn in self.trigger_buttons.items() if btn.isChecked()),'gift')
        # Hide irrelevant fields *and* their labels, not merely disable them.
        for widget,visible in ((self.gift_row,kind=='gift'),
            (self.min_coins,kind=='gift'),(self.threshold,kind in ('likes','coins')),
            (self.keyword,kind=='comment'),(self.coin_basis,kind=='coins'),
            (self.fallback,kind=='gift')):
            widget.setVisible(visible)
            label=self.detail_form.labelForField(widget)
            if label:label.setVisible(visible)
        # Cooldown and action mode apply to all trigger types.

    def accept(self):
        ids=[self.action_list.item(i).data(Qt.ItemDataRole.UserRole)
             for i in range(self.action_list.count())
             if self.action_list.item(i).checkState()==Qt.CheckState.Checked]
        if not ids:
            QMessageBox.warning(self,self._('event_editor'),self._('missing_action'));return
        trigger=next((key for key,btn in self.trigger_buttons.items() if btn.isChecked()),'gift')
        if trigger=='comment' and not self.keyword.text().strip():
            QMessageBox.warning(self,self._('event_editor'),self._('keyword'));return
        if self.specific_user.isChecked() and not self.user_id.text().strip().lstrip('@'):
            QMessageBox.warning(self,self._('event_editor'),self._('user_id'));return
        cfg=self.original or normalize_event({})
        trigger=next((key for key,btn in self.trigger_buttons.items() if btn.isChecked()),'gift')
        raw={**cfg,'name':self.name.text().strip() or 'New Event','enabled':self.enabled.isChecked(),
             'trigger':trigger,'gift_name':self.gift_name.text().strip() if trigger=='gift' else '',
             'min_coins':self.min_coins.value() if trigger=='gift' else 0,
             'threshold':self.threshold.value() if trigger in ('likes','coins') else 100,
             'keyword':self.keyword.text().strip() if trigger=='comment' else '',
             'coin_basis':self.coin_basis.currentData() if trigger=='coins' else 'stream',
             'cooldown_sec':self.cooldown.value(),'fallback_only':self.fallback.isChecked() if trigger=='gift' else False,
             'mode':self.mode.currentData(),'action_ids':ids,
             'user_filter':self.user_id.text().strip().lstrip('@') if self.specific_user.isChecked() else ''}
        self.value=normalize_event(raw)
        super().accept()


class AutomationPage(QWidget):
    def __init__(self,settings,language,save_callback,preview_callback,test_action_callback,test_event_callback,parent=None):
        super().__init__(parent)
        self.settings=settings;self.language=language
        self._=lambda key:tr(self.language,key)
        self.save_callback=save_callback
        self.preview_callback=preview_callback
        self.test_action_callback=test_action_callback
        self.test_event_callback=test_event_callback
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(10)
        self.heading=section(self._('title'));root.addWidget(self.heading)
        self.intro=QLabel(self._('intro'));self.intro.setWordWrap(True)
        self.intro.setObjectName('muted');root.addWidget(self.intro)
        split=QSplitter(Qt.Vertical)
        self.action_panel,self.action_table,self.action_labels=self._make_panel('actions','action_desc',
            'new_action',['active','name','screen','duration','picture','sound','video','summary'],
            self.new_action,self.edit_action,self.copy_action,self.delete_action,
            self.preview_action,self.test_action)
        self.event_panel,self.event_table,self.event_labels=self._make_panel('events','event_desc',
            'new_event',['active','audience','trigger','linked','cooldown'],
            self.new_event,self.edit_event,self.copy_event,self.delete_event,
            None,self.test_event)
        split.addWidget(self.action_panel);split.addWidget(self.event_panel)
        split.setStretchFactor(0,1);split.setStretchFactor(1,1)
        split.setSizes([380,390]);root.addWidget(split,1)
        self.action_table.itemDoubleClicked.connect(lambda *_:self.edit_action())
        self.event_table.itemDoubleClicked.connect(lambda *_:self.edit_event())
        self.refresh()

    def _make_panel(self,title_key,desc_key,new_key,columns,create,edit,duplicate,remove,preview,test):
        panel=QGroupBox();panel.setObjectName('automationGroup')
        layout=QVBoxLayout(panel);layout.setSpacing(8)
        name=section(self._(title_key));desc=QLabel(self._(desc_key));desc.setWordWrap(True)
        desc.setObjectName('muted')
        layout.addWidget(name);layout.addWidget(desc)
        row=QHBoxLayout()
        create_btn=QPushButton(self._(new_key));create_btn.setObjectName('primary');create_btn.clicked.connect(create)
        row.addWidget(create_btn)
        buttons=[]
        for key,callback in (('edit',edit),('copy',duplicate),('delete',remove),('preview',preview),('test',test)):
            if callback is None:continue
            btn=QPushButton(self._(key));btn.clicked.connect(callback)
            if key=='delete':btn.setObjectName('danger')
            row.addWidget(btn);buttons.append((btn,key))
        row.addStretch();layout.addLayout(row)
        table=QTableWidget(0,len(columns))
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(135)
        layout.addWidget(table,1)
        return panel,table,(name,title_key,desc,desc_key,create_btn,new_key,buttons,columns)

    def retranslate(self,language):
        self.language=language
        self.heading.setText(self._('title'))
        self.intro.setText(self._('intro'))
        for name,namekey,desc,desckey,create,createkey,buttons,cols in (self.action_labels,self.event_labels):
            name.setText(self._(namekey));desc.setText(self._(desckey));create.setText(self._(createkey))
            for btn,key in buttons:btn.setText(self._(key))
        self.refresh()

    def selected_id(self,kind):
        table=self.action_table if kind=='actions' else self.event_table
        row=table.currentRow()
        if row<0:return None
        item=table.item(row,0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def selected(self,kind):
        identity=self.selected_id(kind)
        return next((v for v in self.settings[kind] if v['id']==identity),None)

    def refresh(self):
        act_id=self.selected_id('actions')
        evt_id=self.selected_id('events')
        self._fill_actions(act_id)
        self._fill_events(evt_id)

    def _cell(self,text,identity=None):
        item=QTableWidgetItem(str(text))
        if identity is not None:item.setData(Qt.ItemDataRole.UserRole,identity)
        return item

    def _fill_actions(self,selected_id=None):
        table=self.action_table;table.setSortingEnabled(False)
        table.setRowCount(0)
        cols=self.action_labels[-1]
        table.setHorizontalHeaderLabels([self._(key) for key in cols])
        for idx,action in enumerate(self.settings['actions']):
            cfg=action['alert'];table.insertRow(idx)
            custom=cfg.get('visual_layout',False)
            layers=cfg.get('elements',[]) if custom else []
            text=['●' if action['enabled'] else '○',action['name'],
                '✓' if cfg['overlay'] else '—',str(round(cfg['duration_ms']/1000,1))+'s',
                '✓' if cfg.get('image_file') or any(layer.get('type')=='image' for layer in layers) else '—',
                '✓' if cfg['sound'] else '—',
                '✓' if cfg.get('video_file') or any(layer.get('type')=='video' for layer in layers) else '—',
                ('🖌 Visual canvas · '+str(len(layers))+' layers') if custom else (cfg['message'][:60] or cfg['template'])]
            for c,val in enumerate(text):table.setItem(idx,c,self._cell(val,action['id'] if c==0 else None))
        self._restore(table,selected_id)

    def _fill_events(self,selected_id=None):
        table=self.event_table;table.setSortingEnabled(False);table.setRowCount(0)
        table.setHorizontalHeaderLabels([self._(key) for key in self.event_labels[-1]])
        action_names={a['id']:a['name'] for a in self.settings['actions']}
        for idx,event in enumerate(self.settings['events']):
            table.insertRow(idx)
            kind=event['trigger']
            condition={'gift':event['gift_name'] or self._('gift'),
                       'follow':self._('follow'),
                       'likes':f"{self._('likes')} ≥ {event['threshold']}",
                       'coins':f"{self._('coins')} ≥ {event['threshold']}",
                       'comment':f"{self._('comment')}: {event['keyword']}"}.get(kind,kind)
            action_list=', '.join(action_names.get(i,'?') for i in event['action_ids']) or self._('not_linked')
            values=['●' if event['enabled'] else '○',
                    ('@'+event['user_filter']) if event.get('user_filter') else self._('all'),
                    event['name']+' — '+condition,action_list,f"{event['cooldown_sec']}s"]
            for c,val in enumerate(values):table.setItem(idx,c,self._cell(val,event['id'] if c==0 else None))
        self._restore(table,selected_id)

    @staticmethod
    def _restore(table,identity):
        if table.rowCount()==0:return
        row=0
        for index in range(table.rowCount()):
            if table.item(index,0).data(Qt.ItemDataRole.UserRole)==identity:row=index;break
        table.selectRow(row)

    def changed(self,kind,identity=None):
        self.save_callback()
        self._fill_actions(identity if kind=='actions' else self.selected_id('actions'))
        self._fill_events(identity if kind=='events' else self.selected_id('events'))

    def new_action(self):
        dialog=VisualActionDialog(self.settings,self.language,parent=self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.settings['actions'].append(dialog.value)
            self.changed('actions',dialog.value['id'])

    def edit_action(self):
        old=self.selected('actions')
        if not old:return
        editor=VisualActionDialog if old.get('alert',{}).get('visual_layout') else ActionDialog
        dialog=editor(self.settings,self.language,old,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            old.update(dialog.value);self.changed('actions',old['id'])

    def copy_action(self):
        old=self.selected('actions')
        if old:
            value=copy.deepcopy(old);value['id']=make_id();value['name']+=' (copy)'
            self.settings['actions'].append(value);self.changed('actions',value['id'])

    def delete_action(self):
        old=self.selected('actions')
        if not old:return
        if QMessageBox.question(self,self._('delete'),self._('delete_confirm'))!=QMessageBox.StandardButton.Yes:return
        self.settings['actions']=[a for a in self.settings['actions'] if a['id']!=old['id']]
        for event in self.settings['events']:
            event['action_ids']=[i for i in event['action_ids'] if i!=old['id']]
        self.changed('actions')

    def new_event(self):
        if not self.settings['actions']:
            QMessageBox.information(self,self._('events'),self._('missing_action'));return
        dialog=EventDialog(self.settings,self.language,parent=self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.settings['events'].append(dialog.value);self.changed('events',dialog.value['id'])

    def edit_event(self):
        old=self.selected('events')
        if not old:return
        dialog=EventDialog(self.settings,self.language,old,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            old.update(dialog.value);self.changed('events',old['id'])

    def copy_event(self):
        old=self.selected('events')
        if old:
            value=copy.deepcopy(old);value['id']=make_id();value['name']+=' (copy)'
            self.settings['events'].append(value);self.changed('events',value['id'])

    def delete_event(self):
        old=self.selected('events')
        if not old:return
        if QMessageBox.question(self,self._('delete'),self._('delete_confirm'))!=QMessageBox.StandardButton.Yes:return
        self.settings['events']=[e for e in self.settings['events'] if e['id']!=old['id']]
        self.changed('events')

    def preview_action(self):
        old=self.selected('actions')
        if old:self.preview_callback(old['id'])

    def test_action(self):
        old=self.selected('actions')
        if old:self.test_action_callback(old['id'])

    def test_event(self):
        old=self.selected('events')
        if old:self.test_event_callback(old['id'])
