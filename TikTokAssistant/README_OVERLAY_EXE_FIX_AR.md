# إصلاح خطأ Overlay في ملف EXE

إذا ظهر لك مسار شبيه:

`C:\Users\...\dist\main\_internal\overlay_server.py`

فهذا غالبًا يعني أن EXE بُني مباشرةً من `main.py` بدل استخدام إعدادات البناء المعتمدة.
PyInstaller لا يحتفظ عادة بملفات Python بصيغة `.py` بجانب EXE؛ بل يضمّنها داخله.
لذلك لا تنسخ ملف `overlay_server.py` يدويًا إلى `_internal`.

## الطريقة الصحيحة (بدون تثبيت Python على جهازك)

1. فك ضغط هذه الحزمة وارفع **محتوياتها كاملة** إلى GitHub، مع مجلد `.github` المخفي.
2. افتح **Actions -> Build Ven0m Windows EXE and Installer -> Run workflow**.
3. بعد Success حمّل Artifacts وفكها.
4. شغّل `Ven0m_TikTok_LIVE_Assistant_Setup_x64.exe` للتثبيت، أو فك نسخة Portable
   وشغّل `Ven0m_TikTok_LIVE_Assistant.exe` مع إبقاء كامل مجلد Portable.
5. تجنب `main.exe` من `dist\main`، ولا تستخدم `pyinstaller main.py` مباشرة.

## الطريقة المحلية على كمبيوتر البناء

شغّل `TikTokAssistant\build_portable_windows.cmd` بعد تثبيت Python 3.12 x64.
لا يحتاج جهاز المستخدم النهائي إلى Python.

## اختبار بعد البناء

افتح البرنامج، ثم Start Overlay Server. افتح المتصفح على:
`http://127.0.0.1:8765/health`

إذا لم يعمل، أرسل سجل Overlay أو سجل Windows Actions (خطوة Test actual frozen Windows workers).
