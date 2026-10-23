@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" main.py
) else (
  py -3.12 main.py
)
if errorlevel 1 (
  echo.
  echo Ven0m failed to start. The actual error should be shown ABOVE.
  echo For source builds, install Python 3.12 x64, then run:
  echo py -3.12 -m pip install -r requirements.txt
  echo Do not use this .bat file with the packaged EXE; use the EXE directly.
  pause
)
