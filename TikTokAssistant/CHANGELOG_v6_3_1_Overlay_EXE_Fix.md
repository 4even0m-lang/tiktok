# Ven0m v6.3.1 Beta — Overlay EXE packaging fix

- Clarified a wrong-build failure on Windows: `dist/main/main.exe` comes from
  compiling `main.py` without the release configuration.
- Packaged executable processes run `--worker overlay` within the SAME EXE;
  `overlay_server.py` is an imported Python module, not a physical file.
- Added fallback worker dispatch when someone compiles `main.py` as the entry
  point and bundle validation explaining missing Overlay/branding/gift assets.
- Kept official `portable_entry.py` and existing GitHub Actions packaging
  unchanged so correct releases still use the reviewed Windows build workflow.
- Added regression tests for worker commands and the bundled-data validation.

**IMPORTANT:** This is a SOURCE release. To obtain the Windows EXE, run the
workflow and download the resulting Setup / Portable artifact. Building
`pyinstaller main.py` directly is **not** the supported release path.
