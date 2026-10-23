# TikTok LIVE Assistant v6.2 — single-canvas editor and hosts setup repair

## Visual Alert Editor

- Removed the old dual-pane Qt graphics canvas + separate video preview. Both editing and preview now use **one** Qt WebEngine canvas, with playback of video and GIF in position.
- Editing text, geometry, fonts, colors, and direction updates the same canvas immediately, without reconstructing input widgets or restarting the video for unrelated changes.
- Text preserves Unicode logical order, uses RTL / LTR / auto plus left / center / right alignment, and supports mixed Arabic/English text.
- Width, height, X, and Y use directly editable integer inputs; the user can type three- or four-digit values without spin wheel increments or loss of focus.
- Drag an item directly on the preview. Selection and final position flow back to the properties panel through Qt WebChannel.
- The checkerboard is only editor chrome; actual Overlay backgrounds stay transparent. New actions remain entirely blank.
- WebEngine/codec support can differ between machines; MP4 and WebM playback and WebM Alpha must be checked on Windows and in LIVE Studio.

## Windows hosts setup

- Checks the current `hosts` status, requests permission and elevation only if the mapping is missing, writes a backup, and refuses conflicting mappings.
- Waits for an actual result from the elevated helper rather than claiming success when UAC was merely opened.
- Checks `overlay.test` resolution after installation and explains DNS flushing/troubleshooting when needed.
- Provides manual instructions if elevation is blocked or protection software prevents writing. Does not require administrative rights on ordinary launches.

## Unchanged

- TikTokLive connection via `client.connect()`; local overlay URL `http://overlay.test:8765/overlay`.
- Existing Events & Actions, 786 gift icons, configurable boards (`/top-likers`, `/top-supporters`), and their independent transparent sources.
- Existing configuration files are not included in the ZIP. Back up and copy your own `settings.json` / media when upgrading.

## Limitations

No Windows desktop runtime was available during build, so **the Qt WebChannel canvas and Windows UAC dialog require an on-device test** before calling this release fully verified. FFmpeg is optional and used only for pre-processing green-screen video.
