# رفع مشروع Ven0m الكامل إلى GitHub ثم إنشاء Windows EXE

هذه الحزمة تحتوي **المشروع كاملاً** وليست ملف EXE جاهزاً.

## خطوات البناء السحابي (لا تتطلب Python على حاسوبك)

1. فك ضغط ملف الحزمة الجديدة على جهازك. يجب أن ترى مجلد `TikTokAssistant` ومجلد `.github` المخفي وملف `.gitignore`.
2. ارفع **محتويات المجلد بعد فك الضغط** إلى مستودع GitHub الخاص. **لا ترفع ملف ZIP نفسه** ولا الأجزاء المضغوطة القديمة.
3. لتفادي حد رفع الملفات في موقع GitHub (هناك 786 أيقونة)، استخدم GitHub Desktop أو git:

   ```powershell
   cd C:\PATH\TO\EXTRACTED\REPOSITORY
   git init
   git add .
   git commit -m "Ven0m Windows release - full UTF8 corrected source"
   git branch -M main
   git remote add origin https://github.com/YOUR_USER/YOUR_PRIVATE_REPOSITORY.git
   git push -u origin main
   ```

   إذا كان المستودع الحالي يحتوي على المشروع، يمكنك **استبدال ملفاته بالمحتويات الجديدة** ثم تنفيذ `git add .`, `git commit`, `git push` بدلاً من إنشاء مستودع آخر. لا تنشئ remote جديداً إذا كان موجوداً.
4. تأكد من ظهور `.github/workflows/build-windows.yml` و`TikTokAssistant/tools/build_windows.ps1` و`TikTokAssistant/tests/test_v61.py` في المستودع.
5. افتح **Actions → Build Ven0m Windows EXE and Installer → Run workflow** لإنشاء تشغيل جديد على آخر commit (لا تعمل Re-run للمحاولة القديمة).
6. بعد نجاح Windows Build وSmoke tests وInno Setup، حمّل Artifacts الناتجة، وستحصل على نسخة Installer EXE وPortable ZIP كاملة.

> لا ترفع `settings.json` الشخصي أو مفاتيح الوصول أو ملفات جلسات TikTok. تعتمد إعدادات التشغيل على الإذن المحلي ويمكن ضبطها بعد تثبيت البرنامج.

## إصلاح مشكلة UnicodeDecodeError / cp1252

تم تغيير القراءة في `tests/test_v61.py` إلى `read_text(encoding="utf-8")` وإصلاح مواضع أخرى بالاختبارات، وإضافة `PYTHONUTF8=1` إلى GitHub Actions وأداة البناء على Windows.

## عند ظهور Failure مرة أخرى

انسخ **أول Traceback** من خطوة الفشل (وليس سطر `Project unit tests failed` الأخير) حتى نصلح المرحلة التالية بدقة. لا يمكن اعتماد نجاح PyInstaller وInno Setup النهائيين إلا بعد البناء على Windows.
