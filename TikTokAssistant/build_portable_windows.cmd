@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
echo =======================================================
echo Ven0m v6.3.1 Beta - Windows 64-bit local build
 echo Python 3.12 x64 is needed ONLY on the build PC.
echo =======================================================
echo.
where py >nul 2>nul
if errorlevel 1 goto missing_python
py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32" >nul 2>nul
if errorlevel 1 goto missing_python
set "VENV=.venv-build-py312"
set "VENV_PY=%CD%\%VENV%\Scripts\python.exe"
if not exist "%VENV_PY%" (
  py -3.12 -m venv "%VENV%"
  if errorlevel 1 goto failed
)
"%VENV_PY%" -c "import sys; assert sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32" >nul 2>nul
if errorlevel 1 (
 echo Existing %VENV% uses incompatible Python. Rename that folder then retry.
 goto failed
)
REM Both GitHub and local builds use the EXACT same PowerShell source, asset and test rules.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build_windows.ps1" -PythonPath "%VENV_PY%"
if errorlevel 1 goto failed
echo.
echo BUILD SUCCESS. Copy the ENTIRE folder under dist, not the EXE alone.
echo    %CD%\dist\Ven0m_TikTok_LIVE_Assistant
echo.
explorer "dist\Ven0m_TikTok_LIVE_Assistant"
pause
exit /b 0

:missing_python
echo ERROR: Python 3.12 64-bit is missing on this BUILD computer.
echo If you do not want to install Python locally, build using GitHub Actions instead.
:failed
echo.
echo BUILD FAILED. Please send the FIRST error message from the log.
pause
exit /b 1
