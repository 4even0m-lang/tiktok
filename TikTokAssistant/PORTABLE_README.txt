Ven0m TikTok LIVE Assistant — Windows Portable build

Important: This ZIP is a Windows build KIT, not an already-built Windows EXE.
The build machine needs Windows 10/11 x64, Python 3.12 x64 and Internet once (to install dependencies).
The *target* machine does NOT need Python when the build is complete.

1. The uploaded Ven0m image is INCLUDED as assets\branding\ven0m_icon.png and .ico.
2. Install Python 3.12 64-bit from https://www.python.org/downloads/ if not already installed.
   Run "py -0p" to inspect installed versions.
   Double-click build_portable_windows.cmd on a Windows development machine.
   The script explicitly selects Python 3.12 x64 and uses .venv-build-py312.
3. When build succeeds, copy the entire folder
   dist\Ven0m_TikTok_LIVE_Assistant\
   to a new Windows computer (not only its EXE).
4. Run Ven0m_TikTok_LIVE_Assistant.exe.
5. From Settings, run the overlay.test hosts setup; approve the Windows UAC dialog if needed.
6. Launch Overlay server and test http://overlay.test:8765/health first.
7. Add http://overlay.test:8765/overlay to TikTok LIVE Studio Web Page.

Hosts management is opt-in and one-time (do not run the app as administrator).
Your media paths may be absolute and not valid on a different PC; relink imported videos and sound files if needed.
Keep a backup of your settings and files.

If SmartScreen warns for an unsigned new EXE, only allow it if you personally built the file
from this project and trust its source. Do not disable Windows protection.

The executable build HAS NOT been run or tested in this non-Windows environment.
The previous PySide6 application's Windows compatibility must be tested on your computer.
