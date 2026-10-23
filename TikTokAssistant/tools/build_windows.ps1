# Build the complete Ven0m Windows app on a Windows x64 build machine.
# No Python, pip or FFmpeg are needed on the COMPUTER RUNNING the final app.
param(
  [switch]$SkipTests,
  [string]$PythonPath = "python"
)
$ErrorActionPreference = 'Stop'
# Normalise default text encoding for third-party tools and test output.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-StrictMode -Version Latest
$Project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $Project
try {
  Write-Host "[Ven0m] Building Windows executable from $Project"
  & $PythonPath -c "import sys; assert sys.version_info[:2] == (3,12), 'Python 3.12 required'; assert sys.maxsize > 2**32, '64-bit required'"
  if ($LASTEXITCODE -ne 0) { throw 'This build requires Python 3.12 x64 on the BUILD machine.' }

  & $PythonPath -m pip install --disable-pip-version-check -r requirements.txt 'pyinstaller>=6.11,<7' Pillow
  if ($LASTEXITCODE -ne 0) { throw 'Could not install build dependencies.' }

  if (-not $SkipTests) {
    Write-Host '[Ven0m] Running full UTF-8 unit test suite...'
    & $PythonPath -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Project unit tests failed.' }
  }

  $Icon = Join-Path $Project 'assets\branding\ven0m_icon.ico'
  if (-not (Test-Path $Icon)) { throw "Icon not found: $Icon" }
  $Args = @(
    '-m','PyInstaller',
    '--noconfirm','--clean','--onedir','--windowed',
    '--contents-directory','.',
    '--name','Ven0m_TikTok_LIVE_Assistant',
    "--icon=$Icon",
    '--hidden-import=main',
    '--hidden-import=gift_test',
    '--hidden-import=overlay_server',
    '--hidden-import=hosts_setup',
    '--hidden-import=ven0m_selftest',
    '--hidden-import=PySide6.QtWebEngineWidgets',
    '--hidden-import=PySide6.QtWebEngineCore',
    '--hidden-import=PySide6.QtWebChannel',
    '--collect-all=TikTokLive',
    '--collect-all=imageio_ffmpeg',
    '--collect-data=certifi',
    '--add-data=assets;assets',
    '--add-data=overlay.html;.',
    '--add-data=leaderboards.html;.',
    '--add-data=visual_live_preview.html;.',
    'portable_entry.py'
  )
  & $PythonPath @Args
  if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed. Check the full build log.' }

  $Dist = Join-Path $Project 'dist\Ven0m_TikTok_LIVE_Assistant'
  $Exe = Join-Path $Dist 'Ven0m_TikTok_LIVE_Assistant.exe'
  if (-not (Test-Path $Exe)) { throw "Missing built EXE: $Exe" }
  Copy-Item 'PORTABLE_README.txt' (Join-Path $Dist 'README-Portable.txt') -Force
  # Do not bundle real user configuration or private media paths into the release.
  foreach ($Config in @('settings.json','gift_catalog.json')) {
    $Bundled = Join-Path $Dist $Config
    if (Test-Path $Bundled) { Remove-Item $Bundled -Force }
  }
  $Icons = @(Get-ChildItem (Join-Path $Dist 'assets\gifts') -Filter '*.png' -File -ErrorAction Stop).Count
  if ($Icons -lt 786) { throw "Only $Icons gift icons bundled; expected >= 786" }
  Write-Host "[Ven0m] EXE ready: $Exe"
  Write-Host "[Ven0m] Gift icons bundled: $Icons"
} finally {
  Pop-Location
}
