@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
echo Ven0m v6.3.1 Beta - one-time setup for SOURCE testing
where py >nul 2>nul
if errorlevel 1 goto missing_python
py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>nul
if errorlevel 1 goto missing_python
if not exist ".venv\Scripts\python.exe" (
 py -3.12 -m venv ".venv"
 if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32" >nul 2>nul
if errorlevel 1 (
 echo ERROR: The existing .venv has an incompatible Python version.
 echo Rename the .venv directory and run this script again.
 goto failed
)
echo Installing and checking required Python packages in project virtual environment...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Starting Ven0m v6.3.1 Beta...
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto failed
exit /b 0
:missing_python
echo ERROR: Python 3.12 x64 was not found on this computer.
echo This is a SOURCE release; Python is needed only for this type of test.
echo A finished Windows Setup.exe does NOT require Python for the end user.
goto failed
:failed
echo.
echo Could not start Ven0m. Copy the FIRST error shown above.
pause
exit /b 1
