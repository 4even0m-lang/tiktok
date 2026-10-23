Ven0m portable build fix for PySide6 "No matching distribution found"

Cause: The previous builder called py -3, which chooses the newest installed Python,
e.g. 3.14. Some PySide6 packages in the configured dependency range reject that Python version.

Use Python 3.12 64-bit on the BUILD PC (the target portable PC does not need Python).

Steps:
1. On Windows, run: py -0p
2. If Python 3.12 x64 is missing, install it from https://www.python.org/downloads/
3. Extract this new ZIP to a NEW folder (don't reuse old .venv).
4. Run build_portable_windows.cmd.
5. After successful build, copy the WHOLE dist\Ven0m_TikTok_LIVE_Assistant folder.

You can test interpreter explicitly with: py -3.12 -c "import sys; print(sys.version); print(sys.maxsize > 2**32)"

If this still fails: send the output of py -0p and the first pip ERROR line.

The included assets\branding\ven0m_icon.png comes from your original uploaded image.
