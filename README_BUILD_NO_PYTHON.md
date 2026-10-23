# Ven0m TikTok LIVE Assistant — Windows EXE without Python installation for viewers

This folder is the complete **source project + release automation**, **NOT** a compiled Windows EXE. Linux cannot build and certify this PyInstaller/Qt Windows executable directly. A Windows build environment (a GitHub-hosted Windows runner or a Windows computer) performs the one-time compilation.

## What users get when the build succeeds

- **`Ven0m_TikTok_LIVE_Assistant_Setup_x64.exe`**: ONE offline Windows installer. It contains Python 3.12 runtime, PySide6/Qt WebEngine, TikTokLive, 786 gift icons, Overlay pages, and an FFmpeg executable for chroma-key processing. Users need only this EXE to install the program. Installation does not call pip or download app dependencies.
- **`Ven0m_TikTok_LIVE_Assistant_Portable_x64.zip`**: extract once and run `Ven0m_TikTok_LIVE_Assistant.exe`. This is a complete folder-based portable distribution: **copy the whole folder**, not just the EXE. No installed Python required.

Both are intended for **Windows 10/11 x64**. Running needs Internet to use TikTok LIVE; Internet is not needed for installing program dependencies. System security restrictions, antivirus/SmartScreen warnings for unsigned software, or particular multimedia/driver issues may still require attention. The setup and program do **not** silently edit Windows `hosts`: approve the in-app one-time UAC prompt to map `overlay.test` if required.

**Do not give your audience the build kit as if it were an executable.** Distribute one of the TWO build outputs above.

## Build WITHOUT installing Python on your own computer (GitHub Actions)

1. Create a **private repository** on GitHub (so you can decide who receives the source). Upload the full contents of this ZIP, preserving the structure `TikTokAssistant/` and `.github/workflows/build-windows.yml`. The repository must contain ALL 786 files in `TikTokAssistant/assets/gifts/`.
2. Open that repository on GitHub: **Actions → Build Ven0m Windows EXE and Installer → Run workflow**.
3. Wait for the Windows runner to install its tools, run the source tests, build with PyInstaller, verify the actual frozen Overlay endpoints, and package the two outputs.
4. Open the workflow run's **Artifacts**, download `Ven0m_Windows_Release_v6_3_0_Beta`, and unpack it to obtain the installer EXE and Portable ZIP.
5. Install the Setup EXE on a Windows computer for a final visual TikTok LIVE Studio test before distributing it more widely.

The Windows runner downloads all build tools **on the runner only**; neither your own computer nor the end user's computer needs to install Python. GitHub may require you to sign in to download workflow artifacts, and artifact retention is limited. Never put private credentials, session files, or personal settings.json into the repository.

You can also build locally on Windows 10/11 x64 with Python 3.12 x64 by running `TikTokAssistant/tools/build_windows.ps1` and compiling `Ven0m_Setup.iss` with Inno Setup 6, but local development tools are **not needed** when using GitHub Actions.

## Quality and scope

- Automated source tests and syntax checks can run on Linux. The final EXE + Inno Setup creation requires Windows.
- The GitHub Windows workflow runs smoke tests on the **compiled EXE** for hosts diagnostics and `/health`, `/overlay`, `/leaderboards`, `/top-likers`, `/top-supporters`.
- Before production use, manually check the GUI, Qt WebEngine animated preview, TikTokLive real connectivity and Alpha playback inside LIVE Studio. These are not guaranteed by the smoke tests.
- FFmpeg comes from `imageio-ffmpeg` and requires checking applicable binary/license terms before public redistribution, especially commercial distribution. Keep notices/licenses for all bundled third-party components.
- Your privately imported music/video files and settings are **not** bundled into a distributed installer by default. Keep those assets and import/configure them per machine.


## Latest v6.3 full-source GitHub instructions
See `UPLOAD_TO_GITHUB_AR.md`. UTF-8 handling has been patched in the project tests and Windows workflow. Upload the **extracted repository contents**, not this ZIP as a single file.
