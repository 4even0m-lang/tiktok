"""TikTok LIVE Assistant v5 — simplified Event → Action desktop UI."""
from __future__ import annotations
import copy
import ipaddress
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSpinBox, QStackedWidget, QTabWidget, QVBoxLayout, QWidget, QSplitter,
    QGridLayout, QAbstractItemView, QDialog,
)

from portable_runtime import subprocess_launch, missing_bundle_resources
from simulation_studio import sample_event
from connection_manager import TikTokConnectionManager
from preview_widget import AlertPreviewWidget, WEBENGINE_AVAILABLE
from preview_data import build_preview_action_payload
from presets import PRESETS
from rules_engine import migrate_legacy, make_id, normalize_action, normalize_event
from settings_store import load_settings, save_settings, CONFIG_PATH
from automation_ui import AutomationPage
from gift_catalog_ui import GiftCatalogDialog
from hosts_setup import (
    status as hosts_status, request_admin_install, read_elevation_result,
    resolved_address, manual_instructions, diagnose as hosts_diagnose,
)

ROOT=Path(__file__).resolve().parent
LOCAL_URL='http://127.0.0.1:8765/overlay'
ALIAS_URL='http://overlay.test:8765/overlay'
BOARD_ALIAS_URL='http://overlay.test:8765/leaderboards'
BOARD_LOCAL_URL='http://127.0.0.1:8765/leaderboards'
LIKERS_URL='http://overlay.test:8765/top-likers'
SUPPORTERS_URL='http://overlay.test:8765/top-supporters'

AR={
 'home':'⌂  الرئيسية','automation':'⚡  الأحداث والإجراءات','overlay':'▣  Overlay','settings':'⚙  الإعدادات',
 'subtitle':'أتمتة الإشعارات للبث المباشر','ready':'جاهز','connected':'متصل','connecting':'جاري الاتصال',
 'disconnected':'غير متصل','connection':'الاتصال','server':'خادم الإشعارات','start_server':'تشغيل الخادم',
 'stop_server':'إيقاف الخادم','start_live':'بدء الاتصال','stop_live':'قطع الاتصال',
 'user':'حساب TikTok','log':'سجل الأحداث المباشر','clear':'مسح السجل','save':'حفظ التعديلات',
 'events':'الأحداث Events','actions':'الإجراءات Actions','event_help':'حدد متى يحدث شيء في البث، واربطه بإجراء أو أكثر.',
 'action_help':'أنشئ إشعارًا قابلًا لإعادة الاستخدام: فيديو أو GIF أو تصميم وصوت.',
 'add_event':'＋ حدث جديد','add_action':'＋ إجراء جديد','delete':'حذف','duplicate':'نسخ',
 'edit_event':'تحرير الحدث','edit_action':'تحرير الإجراء','name':'الاسم','enabled':'مُفعّل',
 'event_type':'نوع الحدث','gift':'هدية','follow':'متابعة جديدة','likes':'هدف إعجابات',
 'coins':'هدف عملات','comment':'تعليق بكلمة','gift_name':'اسم الهدية (اتركه فارغًا لأي هدية)',
 'min_coins':'الحد الأدنى لعملات الهدية','threshold':'القيمة المستهدفة','basis':'طريقة حساب العملات',
 'stream':'مجموع البث','per_gift':'هدية واحدة','keyword':'الكلمة داخل التعليق',
 'cooldown':'فاصل التكرار (ثانية)','linked':'الإجراءات المرتبطة (اختر واحدًا أو أكثر)',
 'mode':'تنفيذ الإجراءات','all':'كل الإجراءات بالترتيب','random':'إجراء عشوائي واحد',
 'fallback':'تشغيل هذا الحدث فقط إذا لم تطابق الهدية قاعدة محددة',
 'preview_event':'تجربة الحدث على Overlay','preview_action':'معاينة الإجراء داخل البرنامج',
 'send_action':'اختبار الإجراء على Overlay','preview':'معاينة فورية',
 'style':'تصميم الإشعار','icon':'الرمز','accent':'لون الإطار','message':'نص التنبيه',
 'message_tip':'متغيرات متاحة: {user} {gift} {count} {coins} {total} {threshold} {total_likes} {comment}',
 'duration':'مدة العرض (مللي ثانية)','show':'إظهار الإشعار','sound':'تشغيل الصوت',
 'video_audio':'تشغيل صوت الفيديو','video_only':'الفيديو فقط بدون بطاقة',
 'image':'صورة / GIF','video':'فيديو MP4 / WebM','audio':'ملف صوت','browse':'استعراض',
 'volume':'مستوى الصوت (0 = صامت)','use_general':'الصوت العام','path_tip':'اترك المسار فارغًا لاستخدام الملف الافتراضي إن توفر.',
 'overlay_intro':'أضف الرابط الذي نجح مع TikTok LIVE Studio كمصدر Web Page. يلزم تشغيل الخادم.',
 'alias':'رابط TikTok LIVE Studio (overlay.test)','local':'الرابط المحلي لـ OBS / المتصفح',
 'lan':'خادم عرض اختياري للشبكة المحلية','lan_ip':'عنوان IPv4 الخاص بالجهاز','lan_warning':'استخدم شبكة خاصة موثوقة فقط. منافذ التحكم تبقى على localhost.',
 'open':'فتح في المتصفح','copy':'نسخ الرابط','health':'فحص الخادم','reset':'تصفير عدادات الجلسة',
 'notice':'حالة الخادم','general':'عام','language':'لغة البرنامج','theme':'مظهر البرنامج',
 'dark':'داكن','light':'فاتح','general_sound':'تفعيل أصوات التنبيهات','general_volume':'المستوى الافتراضي للصوت',
 'general_path':'الصوت الافتراضي','info':'التحرير داخل الأحداث والإجراءات يحفظ عند الضغط على حفظ أو تجربة. التغيير يُطبّق على الإشعار التالي.',
 'preview_note':'المعاينة الداخلية تستخدم نفس صفحة Overlay، بلا الحاجة لبث مباشر أو خادم.',
 'event_types':'أنواع الأحداث المتاحة: هدايا، متابعات، إعجابات، عملات، تعليقات.',
 'reopen_server':'لتطبيق تغيير عنوان LAN أعد تشغيل الخادم.',
 'missing_server':'خادم Overlay متوقف. شغّله ثم أعد الاختبار.','preview_unavailable':'المعاينة المرئية تحتاج PySide6-Addons (Qt WebEngine).',
 'server_on':'الخادم يعمل','server_off':'الخادم متوقف','test_ok':'أُرسلت تجربة الإشعار',
 'hosts_button':'فحص وإعداد رابط overlay.test','hosts_help':'يتطلب تعديل hosts موافقتك وصلاحيات المسؤول مرة واحدة فقط.','saved':'حُفظت الإعدادات','confirm_delete':'هل تريد حذف العنصر المحدد؟',
 'choose_event':'اختر حدثًا أو أنشئ حدثًا جديدًا','choose_action':'اختر إجراءً أو أنشئ إجراءً جديدًا',
 'empty_actions':'أنشئ إجراءً أولًا لربطه بهذا الحدث.','new_event':'حدث جديد', 'new_action':'إجراء جديد',
 'no_live':'أدخل اسم حساب TikTok أولًا.','report':'رسالة', 'error':'خطأ',
 'status':'الحالة','gifts_received':'الهدايا المستلمة','actions_count':'الإجراءات','rules_count':'قواعد الأحداث',
 'examples':'مثال: عند هدية Lion → فيديو ذهبي + صوت، وعند 5000 إعجاب → احتفال.',
 'simulator':'محاكي الأحداث',
 'autostart_note':'قم بتشغيل Overlay قبل بدء البث حتى تظهر التنبيهات.',
}
EN={
 'simulator':'Event Simulator',
 'home':'⌂  Dashboard','automation':'⚡  Events & Actions','overlay':'▣  Overlay','settings':'⚙  Settings',
 'subtitle':'Live stream alert automation','ready':'Ready','connected':'Connected','connecting':'Connecting',
 'disconnected':'Disconnected','connection':'Live connection','server':'Alert server','start_server':'Start server',
 'stop_server':'Stop server','start_live':'Connect','stop_live':'Disconnect',
 'user':'TikTok account','log':'Live event log','clear':'Clear log','save':'Save changes',
 'events':'Events','actions':'Actions','event_help':'Choose a stream trigger and link one or more actions.',
 'action_help':'Create reusable video, GIF, sound and template alerts.',
 'add_event':'＋ New event','add_action':'＋ New action','delete':'Delete','duplicate':'Duplicate',
 'edit_event':'Edit event','edit_action':'Edit action','name':'Name','enabled':'Enabled',
 'event_type':'Event type','gift':'Gift','follow':'New follower','likes':'Likes milestone',
 'coins':'Coins milestone','comment':'Comment keyword','gift_name':'Gift name (blank = any gift)',
 'min_coins':'Min. gift coins','threshold':'Target amount','basis':'Coin counting mode',
 'stream':'Stream total','per_gift':'Single gift','keyword':'Keyword in comment',
 'cooldown':'Cooldown (seconds)','linked':'Linked actions (select one or more)',
 'mode':'Action execution','all':'All actions in order','random':'One random action',
 'fallback':'Only if no more specific gift rule matches',
 'preview_event':'Test event on Overlay','preview_action':'Preview action in app',
 'send_action':'Test action on Overlay','preview':'Live preview',
 'style':'Alert style','icon':'Icon','accent':'Border color','message':'Alert message',
 'message_tip':'Variables: {user} {gift} {count} {coins} {total} {threshold} {total_likes} {comment}',
 'duration':'Display duration (milliseconds)','show':'Display alert','sound':'Play sound',
 'video_audio':'Play video audio','video_only':'Video only (no card)',
 'image':'Image / GIF','video':'MP4 / WebM video','audio':'Audio file','browse':'Browse',
 'volume':'Volume (0 = muted)','use_general':'Use global volume','path_tip':'Leave blank to use the default asset when available.',
 'overlay_intro':'Use the working overlay.test URL in TikTok LIVE Studio Web Page Source. Start the server first.',
 'alias':'TikTok LIVE Studio URL (overlay.test)','local':'Local URL for OBS / browser',
 'lan':'Optional LAN display server','lan_ip':'Your computer IPv4 address','lan_warning':'Trusted private network only. Admin endpoints remain on localhost.',
 'open':'Open browser','copy':'Copy URL','health':'Check server','reset':'Reset session totals',
 'notice':'Server status','general':'General','language':'Application language','theme':'Application theme',
 'dark':'Dark','light':'Light','general_sound':'Enable alert sounds','general_volume':'Default alert volume',
 'general_path':'Default sound file','info':'Saving or testing an item persists its changes. New settings apply to the next alert.',
 'preview_note':'In-app preview uses the same Overlay HTML without a live session or running server.',
 'event_types':'Available triggers: gifts, follows, likes, coins, comments.',
 'reopen_server':'Restart the server to apply LAN IP changes.',
 'missing_server':'Overlay server is not running. Start it and retry.','preview_unavailable':'In-app preview requires PySide6-Addons (Qt WebEngine).',
 'server_on':'Server running','server_off':'Server stopped','test_ok':'Test alert sent',
 'hosts_button':'Check and set up overlay.test','hosts_help':'Windows hosts editing requires your consent and one-time administrator permission.','saved':'Settings saved','confirm_delete':'Delete selected item?',
 'choose_event':'Select or create an event','choose_action':'Select or create an action',
 'empty_actions':'Create an action first, then link it to an event.','new_event':'New event','new_action':'New action',
 'no_live':'Enter a TikTok username first.','report':'Message','error':'Error',
 'status':'Status','gifts_received':'Gifts received','actions_count':'Actions','rules_count':'Event rules',
 'examples':'Example: Lion gift → golden video + sound; 5,000 likes → celebration.',
 'autostart_note':'Start the Overlay server before you go live.',
}
AR.update({'board_label':'قوائم المتصدرين — رابط ثابت مستقل',
  'board_local':'رابط المتصدرين المحلي',
  'board_help':'يبقى هذا المصدر ظاهرًا ويتحدث تلقائيًا دون التأثير على إشعارات الهدايا. رابط مستقل في LIVE Studio.',
  'board_likers':'إظهار أكثر المكبسين','board_supporters':'إظهار أكثر الداعمين',
  'board_top':'أفضل عدد','board_theme':'مظهر قائمة المتصدرين',
  'likers_url':'رابط أكثر المكبسين','supporters_url':'رابط أكثر الداعمين',
  'save_board':'حفظ إعدادات المتصدرين','open_catalog':'مكتبة الهدايا 🎁'})
EN.update({'board_label':'Leaderboards — independent persistent source',
  'board_local':'Local leaderboards URL',
  'board_help':'This separate Web Page Source remains visible without interrupting gift alerts.',
  'board_likers':'Show Top Likers','board_supporters':'Show Top Supporters',
  'board_top':'Show top','board_theme':'Leaderboard theme',
  'likers_url':'Top Likers URL','supporters_url':'Top Supporters URL',
  'save_board':'Save leaderboards','open_catalog':'Gift Catalog 🎁'})
TRIGGER_KEYS=['gift','follow','likes','coins','comment']

DARK='''
QWidget { color:#edf1fa; background:#0d1421; font-family:'Segoe UI'; font-size:13px; }
QMainWindow { background:#0a101b; }
QFrame#top, QFrame#sidebar, QFrame#panel { background:#151f30; border:1px solid #28374f; border-radius:13px; }
QFrame#stat { background:#17253b; border:1px solid #31415d; border-radius:12px; }
QLabel#brand { font-size:19px; font-weight:800; color:#f0e9ff; }
QLabel#heading { font-size:17px; font-weight:750; color:#ffffff; }
QLabel#muted { color:#b5c6e0; font-size:12px; }
QLabel#big { font-size:26px; color:#ffffff; font-weight:800; }
QPushButton { background:#273952; color:#fff; border:1px solid #405477; border-radius:8px; padding:9px 11px; font-weight:650; }
QPushButton:hover { background:#354c6c; }
QPushButton:checked, QPushButton#primary { background:#7050bc; color:white; border:1px solid #8e71d6; }
QPushButton#danger { background:#753545; border:1px solid #b55a68; }
QPushButton:disabled { color:#7f90a9; background:#1a283c; }
QLineEdit,QPlainTextEdit,QListWidget,QComboBox,QSpinBox { background:#101c2d; color:#f8fbff; border:1px solid #3d5172; border-radius:7px; padding:6px; selection-background-color:#6959bc; }
QListWidget::item {padding:8px;} QListWidget::item:selected { background:#4f458c; }
QCheckBox { color:#f4f6ff; spacing:8px; } QCheckBox::indicator {width:18px;height:18px;}
QTabWidget::pane { border:1px solid #304360; background:#151f30; border-radius:8px; }
QTabBar::tab { background:#202d43; color:#c1d3ef; padding:10px 20px; margin-right:4px; border-top-left-radius:7px;border-top-right-radius:7px; }
QTabBar::tab:selected { background:#6752a7; color:#fff; }
QScrollArea { border:0;background:transparent; }
QMessageBox {background:#151f30;} QToolTip {color:white;background:#293b53;}
QPlainTextEdit#log { background:#07111e; color:#f5f8ff; border:1px solid #52749b; font-family:Consolas,'Segoe UI'; font-size:13px; }
QGroupBox#automationGroup { background:#151f30; color:#edf1fa; border:1px solid #405477; border-radius:12px; margin-top:4px; padding:10px; }
QTableWidget { background:#101c2d; alternate-background-color:#192940; color:#f8fbff; border:1px solid #3d5172; gridline-color:#31445f; selection-background-color:#4f458c; selection-color:#ffffff; }
QTableWidget::item { padding:6px; }
QHeaderView::section { background:#263952; color:#f4f7fd; padding:8px; border:1px solid #3a4f69; font-weight:700; }
'''
LIGHT='''
QWidget { color:#202b3e; background:#f3f6fb; font-family:'Segoe UI'; font-size:13px; }
QMainWindow { background:#ebf1f8; }
QFrame#top, QFrame#sidebar, QFrame#panel { background:#ffffff; border:1px solid #d1daeb; border-radius:13px; }
QFrame#stat { background:#f8faff; border:1px solid #d2dcef; border-radius:12px; }
QLabel#brand { font-size:19px; font-weight:800; color:#32215e; }
QLabel#heading { font-size:17px; font-weight:750; color:#1e283b; }
QLabel#muted { color:#53647d; font-size:12px; }
QLabel#big { font-size:26px; color:#232941; font-weight:800; }
QPushButton { background:#e3e9f5; color:#1c2840; border:1px solid #bac9df; border-radius:8px; padding:9px 11px; font-weight:650; }
QPushButton:hover { background:#cedbf0; }
QPushButton:checked, QPushButton#primary { background:#6346ad; color:white; border:1px solid #694cc1; }
QPushButton#danger { background:#f5dadd; color:#8e2135; border:1px solid #d98997; }
QPushButton:disabled { color:#8694aa; background:#edf0f4; }
QLineEdit,QPlainTextEdit,QListWidget,QComboBox,QSpinBox { background:#fff; color:#182137; border:1px solid #b5c5dd; border-radius:7px; padding:6px; selection-background-color:#b5a3ed; }
QListWidget::item {padding:8px;} QListWidget::item:selected { background:#c2b1f3;color:#182137; }
QCheckBox { color:#1f2b40; spacing:8px;} QCheckBox::indicator {width:18px;height:18px;}
QTabWidget::pane { border:1px solid #cad5e8; background:white; border-radius:8px; }
QTabBar::tab { background:#e0e8f5; color:#33445e; padding:10px 20px; margin-right:4px; border-top-left-radius:7px;border-top-right-radius:7px; }
QTabBar::tab:selected { background:#7458bd; color:#fff; }
QScrollArea { border:0;background:transparent; }
QMessageBox {background:#ffffff;} QToolTip {color:#1c2b45;background:#e5ecf9;}
QPlainTextEdit#log { background:#fff; color:#142236; border:1px solid #859ab4; font-family:Consolas,'Segoe UI'; font-size:13px; }
QGroupBox#automationGroup { background:#fff; color:#1e283b; border:1px solid #d1daeb; border-radius:12px; margin-top:4px; padding:10px; }
QTableWidget { background:#fff; alternate-background-color:#edf3fb; color:#19283b; border:1px solid #b5c5dd; gridline-color:#d0dcec; selection-background-color:#c2b1f3; selection-color:#162038; }
QTableWidget::item { padding:6px; }
QHeaderView::section { background:#dbe5f5; color:#1e2a3d; padding:8px; border:1px solid #bac9df; font-weight:700; }
'''


def frame(obj='panel'):
    f=QFrame(); f.setObjectName(obj)
    l=QVBoxLayout(f);l.setContentsMargins(16,15,16,16);l.setSpacing(10)
    return f,l

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings=load_settings()
        # Fresh v6 projects start with NO visible alerts; legacy installs keep
        # their saved v5 actions and can edit them with the legacy editor.
        if not CONFIG_PATH.exists():
            self.settings['automations_enabled']=True
            save_settings(self.settings)
        if migrate_legacy(self.settings):
            save_settings(self.settings)
        self.language=self.settings['language']
        self.theme=self.settings['theme']
        self.widgets=[]
        self.loading=False
        self.selected_event=None
        self.selected_action=None
        self.server_process=None
        self.gift_count=0
        self.status='disconnected'
        self.manager=TikTokConnectionManager(self)
        self.manager.status_changed.connect(self.on_status)
        self.manager.log_received.connect(self.on_connector_log)
        self.setWindowTitle('Ven0m | TikTok LIVE Assistant 6.3.1 Beta')
        logo_file = ROOT / 'assets' / 'branding' / 'ven0m_icon.png'
        if logo_file.is_file():
            self.setWindowIcon(QIcon(str(logo_file)))
        self.resize(1370,900)
        self.setMinimumSize(1040,740)
        self.build_ui()
        self.retranslate()
        self.load_all()
        self.apply_theme()
        self.log('Ven0m v6.3.1 Beta ready / البرنامج جاهز')
        if sys.platform=='win32' and not self.settings.get('hosts_setup_prompted'):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500,self.first_hosts_check)

    def tr(self,key): return (AR if self.language=='ar' else EN).get(key,key)
    def label(self,key,mode='normal'):
        l=QLabel();self.widgets.append((l,key));l.setText(self.tr(key))
        if mode!='normal':l.setObjectName(mode)
        l.setWordWrap(True)
        return l
    def btn(self,key,callback,style=''):
        b=QPushButton();self.widgets.append((b,key));b.setText(self.tr(key));b.clicked.connect(callback)
        if style:b.setObjectName(style)
        return b
    def field(self,layout,key,widget):
        lbl=self.label(key)
        layout.addRow(lbl,widget)
        return widget
    def scroll(self,widget):
        area=QScrollArea();area.setWidgetResizable(True);area.setWidget(widget)
        return area
    def pick_file(self,edit,kind):
        flt={'image':'Images (*.png *.jpg *.jpeg *.gif *.webp)',
             'video':'Videos (*.mp4 *.webm)',
             'audio':'Audio (*.mp3 *.wav *.ogg *.m4a *.aac)'}[kind]
        path,_=QFileDialog.getOpenFileName(self,self.tr('browse'),'',flt)
        if path: edit.setText(path)
    def file_row(self,kind):
        widget=QWidget();box=QHBoxLayout(widget);box.setContentsMargins(0,0,0,0)
        edit=QLineEdit();edit.setClearButtonEnabled(True)
        box.addWidget(edit,1);box.addWidget(self.btn('browse',lambda:self.pick_file(edit,kind)))
        return widget,edit
    def spin(self,minimum,maximum,step=1):
        s=QSpinBox();s.setRange(minimum,maximum);s.setSingleStep(step);return s
    def build_ui(self):
        root=QWidget();self.setCentralWidget(root)
        outer=QVBoxLayout(root);outer.setContentsMargins(12,12,12,12);outer.setSpacing(10)
        top,t=frame('top');t.setContentsMargins(16,8,16,8)
        line=QHBoxLayout()
        self.brand_image = QLabel()
        self.brand_image.setObjectName('brandImage')
        self.brand_image.setFixedSize(42, 42)
        logo_file = ROOT / 'assets' / 'branding' / 'ven0m_icon.png'
        if logo_file.is_file():
            pm = QPixmap(str(logo_file))
            if not pm.isNull():
                self.brand_image.setPixmap(pm.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                line.addWidget(self.brand_image)
        brand=QLabel('Ven0m  •  TikTok LIVE Assistant');brand.setObjectName('brand')
        line.addWidget(brand);line.addStretch()
        self.status_badge=QLabel('●');line.addWidget(self.status_badge)
        self.theme_button=QPushButton();self.theme_button.clicked.connect(self.toggle_theme)
        line.addWidget(self.theme_button)
        t.addLayout(line);outer.addWidget(top)
        body=QHBoxLayout();body.setSpacing(10);outer.addLayout(body,1)
        side,s=frame('sidebar');side.setFixedWidth(210)
        self.nav=[]
        for index,key in enumerate(('home','automation','overlay','settings')):
            b=self.btn(key,lambda checked=False,i=index:self.goto(i))
            b.setCheckable(True);self.nav.append(b);s.addWidget(b)
        s.addStretch();s.addWidget(self.label('subtitle','muted'))
        body.addWidget(side)
        self.pages=QStackedWidget();body.addWidget(self.pages,1)
        self.pages.addWidget(self.build_home())
        self.pages.addWidget(self.build_automation())
        self.pages.addWidget(self.build_overlay())
        self.pages.addWidget(self.build_settings())
        self.goto(0)
    def goto(self,index):
        # Changes are committed to the settings object, but only persisted on Save/Test.
        if getattr(self,'pages',None) and self.pages.currentIndex()==1 and index!=1:
            self.commit_current()
        self.pages.setCurrentIndex(index)
        for i,b in enumerate(self.nav):b.setChecked(i==index)

    def build_home(self):
        w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(0,0,0,0)
        stats=QGridLayout();stats.setSpacing(10)
        self.conn_value=QLabel('—');self.conn_value.setObjectName('big')
        self.gift_value=QLabel('0');self.gift_value.setObjectName('big')
        self.rules_value=QLabel('0');self.rules_value.setObjectName('big')
        self.actions_value=QLabel('0');self.actions_value.setObjectName('big')
        for idx,(label,value) in enumerate((('status',self.conn_value),('gifts_received',self.gift_value),
                  ('rules_count',self.rules_value),('actions_count',self.actions_value))):
            p,l=frame('stat');l.addWidget(self.label(label,'muted'));l.addWidget(value)
            stats.addWidget(p,0,idx)
        v.addLayout(stats)
        col=QHBoxLayout()
        p,l=frame();l.addWidget(self.label('connection','heading'))
        l.addWidget(self.label('user','muted'))
        self.username=QLineEdit();self.username.setPlaceholderText('@username');l.addWidget(self.username)
        line=QHBoxLayout()
        line.addWidget(self.btn('start_live',self.start_live,'primary'))
        line.addWidget(self.btn('stop_live',self.manager.disconnect_live,'danger'))
        l.addLayout(line);col.addWidget(p)
        p,l=frame();l.addWidget(self.label('server','heading'))
        self.home_server_status=QLabel('—');l.addWidget(self.home_server_status)
        line=QHBoxLayout();line.addWidget(self.btn('start_server',self.start_server,'primary'))
        line.addWidget(self.btn('stop_server',self.stop_server,'danger'))
        l.addLayout(line);col.addWidget(p)
        v.addLayout(col)
        p,l=frame();l.addWidget(self.label('log','heading'))
        self.log_edit=QPlainTextEdit();self.log_edit.setObjectName('log');self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumBlockCount(800)
        self.log_edit.setLayoutDirection(Qt.LeftToRight)
        l.addWidget(self.log_edit,1)
        l.addWidget(self.btn('clear',self.log_edit.clear))
        v.addWidget(p,1)
        return w

    def build_automation(self):
        self.automation_page=AutomationPage(
            self.settings, self.language,
            save_callback=lambda: self.save_all(False),
            preview_callback=self.preview_action_by_id,
            test_action_callback=self.test_action_by_id,
            test_event_callback=self.test_event_by_id,
            parent=self,
        )
        return self.automation_page

    def build_overlay(self):
        w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(0,0,0,0)
        p,l=frame();l.addWidget(self.label('overlay','heading'))
        l.addWidget(self.label('overlay_intro','muted'))
        for key,url in (('alias',ALIAS_URL),('local',LOCAL_URL),
                        ('board_label',BOARD_ALIAS_URL),('board_local',BOARD_LOCAL_URL),
                        ('likers_url',LIKERS_URL),('supporters_url',SUPPORTERS_URL)):
            l.addWidget(self.label(key,'heading'))
            row=QHBoxLayout();box=QLineEdit(url);box.setReadOnly(True);row.addWidget(box)
            row.addWidget(self.btn('copy',lambda unused=False,u=url:QApplication.clipboard().setText(u)))
            row.addWidget(self.btn('open',lambda unused=False,u=url:QDesktopServices.openUrl(QUrl(u))))
            l.addLayout(row)
        row=QHBoxLayout();row.addWidget(self.btn('start_server',self.start_server,'primary'))
        row.addWidget(self.btn('stop_server',self.stop_server))
        row.addWidget(self.btn('health',self.check_server));row.addWidget(self.btn('reset',self.reset_counts))
        row.addWidget(self.btn('simulator',self.open_simulator))
        l.addLayout(row)
        self.overlay_status=QLabel('—');l.addWidget(self.overlay_status)
        v.addWidget(p)
        p2,b=frame();b.addWidget(self.label('board_label','heading'))
        b.addWidget(self.label('board_help','muted'))
        self.board_likers=QCheckBox(self.tr('board_likers'));self.widgets.append((self.board_likers,'board_likers'))
        self.board_supporters=QCheckBox(self.tr('board_supporters'));self.widgets.append((self.board_supporters,'board_supporters'))
        b.addWidget(self.board_likers);b.addWidget(self.board_supporters)
        board_form=QFormLayout()
        self.board_top=QComboBox()
        for n in (3,5,10):self.board_top.addItem(str(n),n)
        self.field(board_form,'board_top',self.board_top)
        self.board_theme=QComboBox()
        for value,text in (('dark','Dark'),('light','Light'),('transparent','Transparent')):
            self.board_theme.addItem(text,value)
        self.field(board_form,'board_theme',self.board_theme)
        b.addLayout(board_form)
        actions=QHBoxLayout()
        actions.addWidget(self.btn('save_board',lambda:self.save_all(True)))
        actions.addWidget(self.btn('open_catalog',self.open_catalog))
        b.addLayout(actions);v.addWidget(p2)
        p,l=frame();self.lan_enabled=QCheckBox(self.tr('lan'));self.widgets.append((self.lan_enabled,'lan'))
        l.addWidget(self.lan_enabled)
        self.lan_ip=QLineEdit();self.lan_ip.setPlaceholderText('192.168.1.105');l.addWidget(self.lan_ip)
        l.addWidget(self.label('lan_warning','muted'));l.addWidget(self.label('reopen_server','muted'))
        v.addWidget(p);v.addStretch()
        return self.scroll(w)

    def build_settings(self):
        w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(0,0,0,0)
        p,l=frame();l.addWidget(self.label('settings','heading'))
        form=QFormLayout()
        self.language_select=QComboBox();self.field(form,'language',self.language_select)
        self.theme_select=QComboBox();self.field(form,'theme',self.theme_select)
        self.global_sound=QCheckBox();self.field(form,'general_sound',self.global_sound)
        self.global_volume=self.field(form,'general_volume',self.spin(0,100,5))
        file_row,self.global_audio=self.file_row('audio');self.field(form,'general_path',file_row)
        l.addLayout(form)
        l.addWidget(self.btn('hosts_button',self.setup_hosts))
        l.addWidget(self.label('hosts_help','muted'))
        l.addWidget(self.label('info','muted'))
        l.addWidget(self.btn('save',self.save_all,'primary'))
        v.addWidget(p);v.addStretch()
        self.language_select.currentIndexChanged.connect(self.language_changed)
        self.theme_select.currentIndexChanged.connect(self.theme_changed)
        return w

    def combo(self,widget,options,key):
        # Preserve currently selected machine-readable item when translation changes.
        current=widget.currentData()
        widget.blockSignals(True);widget.clear()
        for value,label_key in options:
            widget.addItem(self.tr(label_key),value)
        idx=widget.findData(current if current is not None else key)
        widget.setCurrentIndex(max(0,idx));widget.blockSignals(False)

    def retranslate(self):
        for widget,key in self.widgets:
            widget.setText(self.tr(key))
        self.combo(self.language_select,[('ar','language'),('en','language')],'ar')
        self.language_select.setItemText(0,'العربية')
        self.language_select.setItemText(1,'English')
        self.combo(self.theme_select,[('dark','dark'),('light','light')],self.theme)
        if hasattr(self,'automation_page'):
            self.automation_page.retranslate(self.language)
        self.theme_button.setText('☀ Light' if self.theme=='dark' else '☾ Dark')
        self.refresh_counters()
        self.on_status(self.status)

    def apply_theme(self):
        QApplication.instance().setStyleSheet(DARK if self.theme=='dark' else LIGHT)
        self.theme_button.setText('☀ Light' if self.theme=='dark' else '☾ Dark')
    def toggle_theme(self):
        self.set_theme('light' if self.theme=='dark' else 'dark')
    def set_theme(self,mode):
        self.theme=mode;self.settings['theme']=mode;self.apply_theme()
        self.theme_select.blockSignals(True);self.theme_select.setCurrentIndex(self.theme_select.findData(mode))
        self.theme_select.blockSignals(False);save_settings(self.settings)
    def theme_changed(self):
        if self.loading:return
        data=self.theme_select.currentData()
        if data in ('dark','light'):self.set_theme(data)
    def language_changed(self):
        if self.loading:return
        data=self.language_select.currentData()
        if data not in ('ar','en') or data==self.language:return
        self.language=data;self.settings['language']=data
        self.retranslate()
        save_settings(self.settings)
    def first_hosts_check(self):
        # A failed or canceled setup must be easy to retry from Settings.
        self.settings['hosts_setup_prompted'] = True
        save_settings(self.settings)
        state = hosts_status()
        if state != 'ready':
            reason = ('لم يتم إعداد overlay.test بصورة صحيحة. هل تريد فحصه وإصلاحه الآن؟'
                      if self.language == 'ar' else
                      'overlay.test is not configured correctly. Check and fix now?')
            if QMessageBox.question(self, 'Overlay URL', reason) == QMessageBox.StandardButton.Yes:
                self.setup_hosts()

    def _hosts_report(self):
        report = hosts_diagnose()
        lines = [
            f"hosts mapping: {report['mapping']}",
            f"Resolved IP: {report['resolved_ip'] or 'not found'}",
            f"Local server (127.0.0.1): {report['server_local']}",
            f"Alias (overlay.test): {report['server_alias']}",
        ]
        return report, '\n'.join(lines)

    def setup_hosts(self):
        if sys.platform != 'win32':
            QMessageBox.information(self, 'Windows hosts', 'هذه الميزة مخصصة لنظام Windows.')
            return
        report, details = self._hosts_report()
        current = report['mapping']
        self.log('Windows hosts diagnosis: ' + details.replace('\n', ' | '))
        if current == 'ready':
            if report['resolved_ip'] == '127.0.0.1':
                message = ('ربط hosts صحيح.\n' + details + '\n\n'
                           'إذا كان خادم Overlay متوقفًا، شغّله ثم افحص الرابط.\n'
                           'http://overlay.test:8765/overlay')
                QMessageBox.information(self, 'Windows hosts', message)
            else:
                QMessageBox.warning(self, 'Windows hosts',
                                    'السطر موجود لكنه لا يُحل إلى 127.0.0.1.\n'
                                    + details + '\n\n'
                                    'نفّذ ipconfig /flushdns وأعد تشغيل TikTok LIVE Studio.')
            return
        if current == 'unavailable':
            QMessageBox.warning(self, 'Windows hosts',
                                'لا يمكن قراءة ملف hosts أو أن ترميزه غير مدعوم.\n'
                                + details + '\n\n' + manual_instructions())
            return
        if current == 'conflict':
            prompt = ('اكتُشف ربط متعارض للاسم overlay.test.\n'
                      'هل توافق على إصلاح أسطر overlay.test فقط وإضافة الربط الصحيح؟\n'
                      'ستُحفظ نسخة احتياطية قبل التعديل، وسيطلب Windows صلاحية المسؤول.\n\n'
                      + details)
            repair = True
        else:
            prompt = ('الربط overlay.test غير موجود.\n'
                      'هل توافق على إضافة 127.0.0.1 overlay.test؟\n'
                      'ستُحفظ نسخة احتياطية وسيطلب Windows صلاحية المسؤول.\n\n'
                      + details)
            repair = False
        if QMessageBox.question(self, 'Windows hosts', prompt) != QMessageBox.StandardButton.Yes:
            return
        result_file = request_admin_install(repair=repair)
        if result_file is None:
            QMessageBox.warning(self, 'Windows hosts',
                                'لم يتم تشغيل عملية التعديل بصلاحيات المسؤول، أو ألغيت نافذة UAC.\n\n'
                                + manual_instructions())
            return
        self._hosts_result_file = result_file
        self._hosts_checks = 0
        if not hasattr(self, '_hosts_check_timer'):
            self._hosts_check_timer = QTimer(self)
            self._hosts_check_timer.timeout.connect(self._check_hosts_result)
        self._hosts_check_timer.start(650)
        self.log('Windows hosts: waiting for administrator confirmation / انتظار موافقة المسؤول')

    def _check_hosts_result(self):
        self._hosts_checks += 1
        data = read_elevation_result(self._hosts_result_file)
        state = data.get('state')
        if state == 'pending' and self._hosts_checks < 180:
            return
        self._hosts_check_timer.stop()
        try:
            self._hosts_result_file.unlink(missing_ok=True)
        except OSError:
            pass
        report, details = self._hosts_report()
        if (state == 'ready' or (state == 'pending' and report['mapping'] == 'ready')) and report['mapping'] == 'ready':
            if report['resolved_ip'] == '127.0.0.1':
                self.log('Windows hosts mapping verified: overlay.test -> 127.0.0.1')
                QMessageBox.information(self, 'Windows hosts',
                                        'تم إصلاح الربط بنجاح!\n' + details + '\n\n'
                                        'إذا ظهرت حالة server unavailable، شغّل خادم Overlay أولًا.\n'
                                        'http://overlay.test:8765/overlay')
            else:
                QMessageBox.warning(self, 'Windows hosts',
                                    'تم تعديل ملف hosts، لكن حل الاسم لا يزال مختلفًا.\n'
                                    + details + '\n\n'
                                    'جرّب ipconfig /flushdns ثم أغلق LIVE Studio وافتحه.')
        elif state == 'pending':
            QMessageBox.warning(self, 'Windows hosts',
                                'انتهت مهلة انتظار صلاحيات Windows. لم يتم تأكيد نجاح التعديل.\n'
                                + details + '\n\n' + manual_instructions())
        else:
            detail = str(data.get('detail') or state)
            QMessageBox.warning(self, 'Windows hosts',
                                'فشل تعديل hosts أو التحقق منه.\n' + detail + '\n'
                                + details + '\n\n' + manual_instructions())

    def load_all(self):
        self.loading=True
        self.username.setText(self.settings.get('username',''))
        self.global_sound.setChecked(self.settings.get('sound_enabled',True))
        self.global_volume.setValue(self.settings.get('volume',70))
        self.global_audio.setText(self.settings.get('sound_file',''))
        board=self.settings.get('leaderboards',{})
        self.board_likers.setChecked(board.get('show_likers',True))
        self.board_supporters.setChecked(board.get('show_supporters',True))
        self.board_top.setCurrentIndex(max(0,self.board_top.findData(board.get('top_n',5))))
        self.board_theme.setCurrentIndex(max(0,self.board_theme.findData(board.get('theme','dark'))))
        self.lan_enabled.setChecked(self.settings.get('lan_enabled',False))
        self.lan_ip.setText(self.settings.get('lan_ip',''))
        self.loading=False
        self.automation_page.refresh();self.update_links()
        self.combo(self.language_select,[('ar','language'),('en','language')],self.language)
        self.language_select.blockSignals(True);self.language_select.setCurrentIndex(self.language_select.findData(self.language));self.language_select.blockSignals(False)
        self.combo(self.theme_select,[('dark','dark'),('light','light')],self.theme)
        self.theme_select.blockSignals(True);self.theme_select.setCurrentIndex(self.theme_select.findData(self.theme));self.theme_select.blockSignals(False)
    def refresh_counters(self):
        self.rules_value.setText(str(len(self.settings['events'])))
        self.actions_value.setText(str(len(self.settings['actions'])))
    def commit_current(self):
        # Event and Action editors save atomically when their dialogs close.
        pass

    def sync_general(self):
        self.settings.update({'username':self.username.text().strip().lstrip('@'),
            'sound_enabled':self.global_sound.isChecked(),'volume':self.global_volume.value(),
            'sound_file':self.global_audio.text().strip(),
            'lan_enabled':self.lan_enabled.isChecked(),'lan_ip':self.lan_ip.text().strip(),
            'language':self.language,'theme':self.theme,
            'leaderboards':{'show_likers':self.board_likers.isChecked(),
                'show_supporters':self.board_supporters.isChecked(),
                'top_n':self.board_top.currentData(),
                'theme':self.board_theme.currentData()}})
    def save_all(self,show=True):
        self.sync_general()
        save_settings(self.settings)
        self.refresh_counters()
        if show:self.log(self.tr('saved'))

    def preview_action_by_id(self,action_id):
        # Qt WebEngine is loaded only on demand to minimize broadcast overhead.
        try:
            payload=build_preview_action_payload(self.settings,action_id,with_sound=True)
            dialog=QDialog(self)
            dialog.setWindowTitle('Action Preview' if self.language=='en' else 'معاينة الإجراء')
            dialog.resize(840,480)
            layout=QVBoxLayout(dialog)
            widget=AlertPreviewWidget(dialog);layout.addWidget(widget,1)
            widget.show_alert(payload)
            close=QPushButton('Close' if self.language=='en' else 'إغلاق')
            close.clicked.connect(dialog.accept);layout.addWidget(close)
            dialog.exec();widget.stop()
        except Exception as exc:self.warn(str(exc))

    def open_simulator(self):
        """Local test events using the exact same /event path as live events."""
        dialog=QDialog(self)
        dialog.setWindowTitle('Ven0m Simulation Studio (Beta)')
        dialog.resize(470,325)
        outer=QVBoxLayout(dialog)
        description=QLabel('اختبار أحداث البث دون الاتصال بـTikTok؛ لا يغيّر أرقام الجلسة.'
                           if self.language=='ar' else
                           'Simulate events locally without TikTok. Session totals are unchanged.')
        description.setWordWrap(True)
        outer.addWidget(description)
        form=QFormLayout()
        kind=QComboBox()
        for value,text in (('gift','Gift / هدية'),('follow','Follow / متابعة'),
                           ('like','Like / إعجاب'),('comment','Comment / تعليق')):
            kind.addItem(text,value)
        user=QLineEdit('TestViewer')
        gift=QLineEdit('Rose')
        count=QSpinBox();count.setRange(1,1000000);count.setValue(100)
        coins=QSpinBox();coins.setRange(0,1000000000);coins.setValue(1)
        comment=QLineEdit('Hello')
        for label,widget in (('Event / الحدث',kind),('User / المستخدم',user),
                             ('Gift / الهدية',gift),('Likes / اللايكات',count),
                             ('Coins / العملات',coins),('Comment / التعليق',comment)):
            form.addRow(label,widget)
        outer.addLayout(form)
        status=QLabel('');status.setWordWrap(True);outer.addWidget(status)
        def send():
            payload=sample_event(kind.currentData(),username=user.text(),gift_name=gift.text(),
                                 coins=coins.value(),count=count.value(),comment=comment.text())
            result=self.post_json('/event',payload)
            if result is not None:
                n=result.get('alerts',0)
                status.setText(f'Sent test event. Matching alerts: {n} / عدد الإشعارات المطابقة: {n}')
                self.log(f'[Simulator] {payload["type"]}: {n} matching alerts')
        submit=QPushButton('Send test event / إرسال حدث تجريبي')
        submit.clicked.connect(send)
        outer.addWidget(submit)
        dialog.exec()

    def post_json(self,path,body):
        payload=json.dumps(body).encode('utf-8')
        req=Request('http://127.0.0.1:8765'+path,data=payload,
                    headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(req,timeout=2.5) as res:return json.load(res)
        except (OSError,URLError,ValueError) as exc:
            self.warn(self.tr('missing_server')+f'\n{exc}')
            return None
    def test_action_by_id(self,action_id):
        self.save_all(False)
        result=self.post_json('/test_action',{'id':action_id})
        if result:self.log(self.tr('test_ok')+f": {result['alerts']}")

    def test_event_by_id(self,event_id):
        self.save_all(False)
        result=self.post_json('/test_event_rule',{'id':event_id})
        if result:self.log(self.tr('test_ok')+f": {result['alerts']}")

    def start_live(self):
        self.sync_general();save_settings(self.settings)
        if not self.settings['username']:
            self.warn(self.tr('no_live'));return
        self.manager.connect_live(self.settings['username'])
    def on_status(self,status):
        self.status=status
        display={'متصل':'connected','جاري الاتصال':'connecting',
                 'غير متصل':'disconnected'}.get(status,None)
        label=self.tr(display) if display else status
        if hasattr(self,'conn_value'):self.conn_value.setText(label)
        if hasattr(self,'status_badge'):self.status_badge.setText('● '+label)
    def on_connector_log(self,text):
        self.log(text)
        if text.startswith('[GIFT]'):
            self.gift_count+=1;self.gift_value.setText(str(self.gift_count))
    def log(self,message):
        self.log_edit.appendPlainText(datetime.now().strftime('%H:%M:%S')+'  '+str(message))
    def warn(self,message):QMessageBox.warning(self,self.tr('error'),str(message))
    def open_catalog(self):
        GiftCatalogDialog(self.language,self).exec()

    def update_links(self):
        self.home_server_status.setText(self.tr('server_on') if self.server_process and self.server_process.state()!=QProcess.ProcessState.NotRunning else self.tr('server_off'))
        self.overlay_status.setText(self.home_server_status.text())
    def start_server(self):
        if self.server_process and self.server_process.state()!=QProcess.ProcessState.NotRunning:
            self.log(self.tr('server_on'));return
        self.sync_general();save_settings(self.settings)
        script=ROOT/'overlay_server.py'
        if not getattr(sys, "frozen", False) and not script.exists():self.warn(str(script));return
        process=QProcess(self);process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        env=QProcessEnvironment.systemEnvironment();env.insert('PYTHONUNBUFFERED','1')
        if self.settings.get('lan_enabled'):
            try:
                ip=ipaddress.IPv4Address(self.settings['lan_ip'])
                if not ip.is_private:raise ValueError()
            except ValueError:
                self.warn('Enter an RFC1918 private LAN IPv4 address');return
            env.insert('TIKTOK_OVERLAY_LAN_IP',self.settings['lan_ip'])
        else:env.remove('TIKTOK_OVERLAY_LAN_IP')
        process.setProcessEnvironment(env);process.setWorkingDirectory(str(ROOT))
        process.readyReadStandardOutput.connect(self.read_server_log)
        process.finished.connect(self.server_stopped)
        self.server_process=process
        program, arguments = subprocess_launch('overlay', script)
        process.start(program, arguments)
        self.log('Overlay server starting…');self.update_links()
    def read_server_log(self):
        if not self.server_process:return
        data=bytes(self.server_process.readAllStandardOutput()).decode('utf-8',errors='replace')
        for line in data.splitlines():
            if line:self.log('[Overlay] '+line)
        self.update_links()
    def server_stopped(self,*_):
        self.log('Overlay server stopped');self.update_links()
    def stop_server(self):
        if self.server_process and self.server_process.state()!=QProcess.ProcessState.NotRunning:
            self.server_process.terminate()
            QTimer.singleShot(1500,self._stop_server_force)
    def _stop_server_force(self):
        if self.server_process and self.server_process.state()!=QProcess.ProcessState.NotRunning:
            self.server_process.kill()
    def check_server(self):
        try:
            with urlopen('http://127.0.0.1:8765/health',timeout=1.5) as response:
                self.log('Overlay health: '+response.read().decode('utf-8'))
        except OSError as exc:self.warn(self.tr('missing_server')+'\n'+str(exc))
    def reset_counts(self):
        if self.post_json('/reset_coins',{}) is not None:self.log('Session counters reset')
    def closeEvent(self,event):
        self.save_all(False)
        self.manager.disconnect_live()
        if self.manager.process.state()!=QProcess.ProcessState.NotRunning:
            if not self.manager.process.waitForFinished(600):
                self.manager.process.kill()
                self.manager.process.waitForFinished(900)
        if self.server_process and self.server_process.state()!=QProcess.ProcessState.NotRunning:
            self.server_process.terminate()
            if not self.server_process.waitForFinished(400):
                self.server_process.kill()
                self.server_process.waitForFinished(900)
        super().closeEvent(event)


def main():
    from diagnostics import install_crash_logging
    install_crash_logging()
    app=QApplication(sys.argv)
    # Bundled Python modules have no standalone .py file. Report actual data
    # packaging errors early, before a user configures an unusable Overlay.
    if getattr(sys, 'frozen', False):
        missing = missing_bundle_resources(ROOT)
        if missing:
            QMessageBox.critical(
                None, 'Ven0m — Incomplete Windows Build',
                'ملفات البرنامج المجمّع ناقصة.\n'
                'This EXE was packaged without required Overlay resources.\n\n'
                + '\n'.join(missing[:8]) + '\n\n'
                'Use the project build_windows.ps1 / GitHub Actions workflow\n'
                'and launch Ven0m_TikTok_LIVE_Assistant.exe from the FULL\n'
                'distributed folder, not dist\\main\\main.exe.'
            )
            return 2
    app.setFont(QFont('Segoe UI',10))
    window=MainWindow();window.show()
    return app.exec()

if __name__ == '__main__':
    # Compatibility for users who accidentally froze main.py directly.
    # Their EXE can still dispatch --worker, but complete resources MUST be
    # bundled using the official portable_entry.py build configuration.
    if getattr(sys, 'frozen', False) and sys.argv[1:3] and sys.argv[1] == '--worker':
        from portable_entry import dispatch
        sys.exit(dispatch())
    sys.exit(main())
