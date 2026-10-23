# TikTok LIVE Assistant v6.1 — User test build

## Added
- Visual Action Editor: inline live media preview on a checkerboard stage, including playback/pause for image/GIF/video. Updates happen as layer properties change. Qt WebEngine is loaded only while editing.
- Text direction and alignment for each text layer: Arabic RTL / English LTR / auto and right/center/left. Multiline Arabic text supported. The same settings are applied to the actual Web Page Overlay.
- Optional *offline* green-screen conversion using locally installed FFmpeg into transparent WebM VP9. Results depend on the footage and browser decoder.
- Independent Web Page Sources: `/top-likers` and `/top-supporters` (existing `/leaderboards` remains).
- 786 user-supplied local PNG gift icons included, with local thumbnails and optional live price metadata. Distinct ambiguous icon variants remain accessible without guessing TikTok IDs.
- Optional Windows setup assistant for `127.0.0.1 overlay.test` in `hosts`, with explicit consent, elevation when needed, backup, conflict detection, and a manual retry button.
- New v6.1 tests for the above functionality.

## Preserved
- Live TikTok connector using `await client.connect()`.
- Local alerts URL `http://overlay.test:8765/overlay`.
- Event → Action rules and old saved settings; existing Actions do not get forcibly redesigned.
- Transparent backgrounds for actual live Overlay pages.

## Known limitations
- A live WYSIWYG media preview uses Qt WebEngine; video codecs and alpha depend on its installed decoder. Windows / TikTok LIVE Studio need live tests.
- AI segmentation of backgrounds with complex scenery **is not included**. Use an externally preprocessed transparent file; FFmpeg chroma key is for reasonably uniform greens/solid colors only.
- Green-screen conversion requires a separate FFmpeg installation on PATH. It runs on import, not during stream.
- Local icon filenames do **not** contain official TikTok gift IDs or verified prices. `0` means unavailable, not a free gift; check live metadata.
- Open-source build remains Python/PySide6, **not** EXE/installer (per user preference).
