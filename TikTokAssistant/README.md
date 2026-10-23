# Ven0m TikTok LIVE Assistant v6.3.1 Beta

**النسخة التجريبية كاملة المصدر للتجربة قبل GitHub.**

**v6.3.1:** إصلاح تشخيص حزم EXE غير المكتملة وتفعيل مسار تشغيل Worker احتياطي عند بناء `main.exe`. اقرأ `README_OVERLAY_EXE_FIX_AR.md`. إصدار Setup/Portable الصحيح يُبنى عبر GitHub Actions أو `tools/build_windows.ps1`، وليس عبر `pyinstaller main.py` مباشرة.
 اقرأ `../ابدأ_من_هنا.txt` لتثبيت المكتبات وتشغيلها على Windows. تفاصيل التعديلات وحدود النسخة موجودة في `CHANGELOG_v6_3_0_Beta.md`.

يُحفظ ملف الإعدادات في `%LOCALAPPDATA%\Ven0m` على Windows. النسخة الجديدة لا تضمّن إعداداتك الشخصية أو الوسائط التي تختارها من مجلدات جهازك. **هذه نسخة مصدر وليست EXE جاهزًا.**

---

# TikTok LIVE Assistant v6.2.1 (hosts hotfix)

**New:** Verified and consent-based Windows hosts repair. See `CHANGELOG_v6_2_1.md`.

# TikTok LIVE Assistant v6.2 (test release)

**v6.2 changes:** Single-canvas live editor (Arabic RTL, immediate video/GIF/text preview, freely typed width/height) and confirmed Windows hosts setup. See `CHANGELOG_v6_2.md`.

# TikTok LIVE Assistant v6.0 — Windows / PySide6

**Personal Windows LIVE overlay tool.** An independent Python project, inspired by event/action workflows, not affiliated with TikTok or TikFinity. Live reception uses the **unofficial** TikTokLive Python package; TikTok can change availability and metadata without notice.

## Important: upgrade without losing v5.1 settings

1. Close the old assistant and Overlay server completely.
2. Make a copy of your **old** `settings.json`, `gift_catalog.json` (if any), and all your media files.
3. Extract **this ZIP** into a **new** folder. Copy the old `settings.json` into the new `TikTokAssistant` folder. Keep external MP4/GIF/audio files at their original locations or update their paths.
4. Open PowerShell in `TikTokAssistant` and run:

```powershell
python -m pip install -r requirements.txt
python main.py
```

5. Keep the `hosts` mapping that already worked on your PC: `127.0.0.1 overlay.test`.
6. Start the Overlay server, then start TikTok LIVE connection. The connection still uses `await client.connect()`.

**Brand new installs:** No default popup/card/text is enabled. New Actions start with an empty visual canvas.
**Upgrades:** Previously saved v5/v5.1 cards and media actions remain usable, preserving your designs; new Actions use the blank visual editor. There is no silent destructive migration.

## Four main pages

- **Dashboard**: connect/disconnect, server control, clear log, counters.
- **Events & Actions**: two separate overview tables; create/reuse Actions, bind them to Events.
- **Overlay**: ready-to-copy URLs for Alerts and Leaderboards, catalog shortcut, session reset, board display settings.
- **Settings**: Arabic/English, Dark/Light, sound and volume.

## New v6 Visual Alert Editor

Go to **Events & Actions → Create new Action → Edit blank canvas**.

The canvas is initially empty and transparent. Add a text, rectangle, image/GIF, or MP4/WebM layer. Drag layers with the mouse. Change X/Y, width/height, font, font size, foreground color, rectangle fill, opacity and radius in the properties panel. The virtual canvas is 1280×720. Save the Action, then create an Event to trigger it.

Dynamic text variables include `{user}`, `{gift}`, `{count}`, `{coins}`, `{total}`, `{threshold}`, `{likes}`, `{total_likes}`, `{comment}`. A special audio file can be assigned to each Action, and the video may use audio if the source browser permits autoplay. Preview inside the app using Qt WebEngine; animation/video playback takes place there (the Qt layer editor uses static image/video placeholders). Browser audio autoplay may need permission.

**Old saved Actions** use the older design editor to keep compatibility; **new Actions** use the new blank editor. If you want a fresh visual design for an old Alert, create a new visual Action and link the old Event to it.

## Dynamic Event conditions

Choose a trigger in **Create Event**:

| Trigger | Visible specialized conditions |
|---|---|
| Gift | Name, minimum coins, fallback logic, link to Gift Catalog |
| Follow | No gift, coin, or keyword fields |
| Like milestone | Target likes |
| Coin milestone | Threshold and stream-total/single-gift counting |
| Comment keyword | Nonempty text to search for |

Shared fields (username filter, cooldown, attached Actions and execution mode) remain available. Non-applicable fields are hidden and cleared from saved rules. Unsupported audience categories remain disabled instead of appearing operational.

## Gift Catalog

Open **Overlay → Gift Catalog** or **Event → Gift → Catalog**. Search gifts by name/ID, view image and coin count where available, choose a gift for the Event, and set a manual override if an observed coin value is wrong. Metadata is cached in a separate `gift_catalog.json` file. Gift metadata is obtained **best effort** from TikTokLive when connecting or receiving gifts; not all accounts/libraries expose the full catalog, icons, or prices. Unknown prices show as unavailable (not an invented number).

**Coin limitations:** This tool records per-gift TikTokLive metadata and received events, not a billing statement. Streak gifts are processed on their final repeat event in the connector; missed events, disconnects, duplicate delivery or TikTok changes can affect totals. Manual price overrides are possible.

## Separate LIVE sources — no OBS required

In TikTok LIVE Studio, create **two Web Page sources** (you already confirmed the `overlay.test` alias works):

**Temporary event alerts:**

`http://overlay.test:8765/overlay`

**Persistent Top Likers / Top Supporters:**

`http://overlay.test:8765/leaderboards`

Both pages are transparent outside their content and run from the **same local server**. The leaderboards update over WebSocket independently of temporary alerts. Position and size each source separately in LIVE Studio to prevent overlap.

To configure the persistent boards go to **Overlay** page, select Top 3 / 5 / 10, enable either board, choose its theme, and save. The leaderboards update after actual gift/like events. The session reset button also resets the boards and re-arms milestones. When coins cannot be determined for a supporter, the board displays a gift count instead of asserting a coin value.

**Like limitation:** Ranking individuals by likes is possible only where TikTokLive delivers LikeEvent counts with sender identity. A missing like stream does not permit an accurate Top Likers ranking. Top supporters uses observed user IDs and gifts/coin metadata.

## Performance and privacy

- Server listens on 127.0.0.1:8765 by default. `overlay.test` points to the same local loopback address via Windows hosts file.
- Optional LAN display uses the separate read-only port 8766 with no admin endpoints. Use only on private trusted networks; do not port-forward it.
- No service account, IP tracking or access to TikTok viewers' IP addresses is required.
- Alert video/GIF complexity affects CPU/GPU. In-app preview loads only when requested; use a sensible video resolution and duration.
- Catalog prices and leaderboard totals are best effort, not official TikTok account balance or certified payment data.

## Diagnostics

Check health: `http://127.0.0.1:8765/health`.

You can test code without a live stream (requires aiohttp):

```powershell
python -m unittest discover -s tests -v
```

**Tested here:** Python syntax, HTML JavaScript syntax, and automated aiohttp/WebSocket/logic tests. **Not tested here:** running PySide6 UI in a Windows desktop, rendering WebEngine media inside TikTok LIVE Studio, or connecting to a real LIVE session. Test with a private/low-risk stream before using it for production broadcasts.

---
## What's new in v6.1 (test release)

* **Inline editor preview:** Action → Create/Edit → blank Visual Editor. The top editing canvas supports dragging; the bottom live preview renders the moving GIF/video and RTL text without saving. Playback can be paused. `PySide6-Addons` supplies Qt WebEngine.
* **Arabic text:** Add a text layer, enter Arabic, choose `العربية RTL` and right alignment. Variables `{user}`, `{gift}` can be placed anywhere in the text. The live overlay respects the text direction.
* **Green-screen video:** Select a video layer and attach a source file, adjust key similarity and edge softness, then press `إزالة الخلفية الخضراء ← WebM Alpha`. Requires external FFmpeg installed and on PATH. Output WebM is selected for the layer when conversion succeeds. Test alpha rendering in LIVE Studio; not all browser engines support it. For varied and complex backgrounds, preprocess outside the app; AI background removal is **not installed** in this release.
* **Gift catalog:** Bundles the user's 786 gift PNG icons from `assets/gifts`, indexed by names. Prices and actual gift IDs are loaded from TikTokLive when available, with optional manual overrides. File number is NOT the TikTok gift ID. The icon list remains accessible without a live connection.
* **Three separate URLs:**
  * Alerts: `http://overlay.test:8765/overlay`
  * Top likers: `http://overlay.test:8765/top-likers`
  * Top supporters: `http://overlay.test:8765/top-supporters`
  * Combined compatibility: `http://overlay.test:8765/leaderboards`
* **Windows hosts assistant:** Settings → `فحص وإعداد رابط overlay.test`. On first run the app can offer to set the mapping with your consent; it requests admin rights only for the system change and will not silently overwrite conflicts. A backup of hosts is created (`hosts.tiktokassistant.bak`). Program continues without elevation after setup.

**Migration:** Make a copy of your existing folder and `settings.json` including your own media assets. Extract v6.1 into a new folder, then copy `settings.json` and any custom audio/video/image files into the same relative locations. Existing absolute paths pointing to the old machine may need to be reselected.

**Run:** `python -m pip install -r requirements.txt` then `python main.py`. This is a Python source distribution, not a Windows executable. Do not expose the loopback administration endpoints through a public tunnel.
