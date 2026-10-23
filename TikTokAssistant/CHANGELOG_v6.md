# v6.0 changes

- New Actions use a transparent blank canvas; drag, resize via properties, fonts, shapes, images/GIF/video, text placeholders, preview and separate sound.
- v5 saved Action designs stay functional; no default popup in fresh installs.
- Dynamic Event-specific UI: hide irrelevant fields; clean stale conditions when switching triggers.
- TikTok gift catalog cache with images/IDs/coin prices when metadata exists; editable overrides; search and Event selection.
- Permanent leaderboards (`/leaderboards`) independent of alert Overlay (`/overlay`), with separate WebSocket and read-only LAN display routes.
- Top Likers and Top Supporters with session reset, ranks and top 3/5/10; unknown coin values remain unknown.
- Preserves `client.connect()`, original localhost server and `overlay.test` compatibility.
- Added `test_v6.py` for catalog, visual layers, board event isolation and sample WebSocket traffic.

Caveats: Full PySide6 on Windows and TikTok live metadata could not be integration-tested here.
