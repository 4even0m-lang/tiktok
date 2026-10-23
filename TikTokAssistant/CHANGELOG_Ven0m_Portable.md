# Ven0m branding + Portable build kit

- Set the main window title and visible header to **Ven0m • TikTok LIVE Assistant**.
- Support loading the user's exact image as an icon if placed at `assets/branding/ven0m_icon.png`.
- Include optional ICO conversion script preserving the original image pixels.
- Add a Windows onedir PyInstaller build script; after building the whole output folder is portable without a Python install on the target Windows PC.
- Rewrite TikTokLive and Overlay sub-process launchers to use built executable worker modes, rather than `sys.executable script.py` in frozen mode.
- Update UAC elevation to use the hosts worker from the packaged EXE.
- Preserve hosts conflict repair logic and existing v6.2.1 assets, events and configuration.

**Build-status warning:** A Windows EXE cannot be compiled by PyInstaller running on Linux; this is a *build-ready source distribution*, not an already-built executable.

**Logo:** This runtime did not surface the original user image as an accessible file, so the image MUST be saved under `assets/branding/ven0m_icon.png` before building; the project does not pretend a reconstructed logo is the user's exact image.
