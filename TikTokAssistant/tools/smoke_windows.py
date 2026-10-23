"""Windows-runner smoke checks for the FROZEN EXE, not source Python."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "Ven0m_TikTok_LIVE_Assistant" / "Ven0m_TikTok_LIVE_Assistant.exe"
URLS = ("/health", "/overlay", "/leaderboards", "/top-likers", "/top-supporters")


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("Smoke test must run on Windows")
    if not EXE.is_file():
        raise FileNotFoundError(EXE)
    print("Checking frozen per-user data and bundled gift assets...")
    with tempfile.TemporaryDirectory(prefix='ven0m-ci-data-') as isolated:
        env = dict(os.environ, VEN0M_DATA_DIR=isolated)
        check = subprocess.run([str(EXE), '--worker', 'selftest'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=90, text=True, errors='replace', env=env)
        if check.returncode:
            raise RuntimeError(f'Frozen selftest failed ({check.returncode}):\n'
                               f'{check.stdout}\n{check.stderr}')
        lines = [line for line in check.stdout.splitlines() if line.startswith('{')]
        result = json.loads(lines[-1]) if lines else {}
        if not result.get('ok') or not result.get('writable_settings') or not result.get('writable_catalog'):
            raise RuntimeError(f'Unexpected frozen self-test output: {check.stdout}')
        print('Frozen settings/catalog + icons: OK',result['gift_icons'])

    print("Checking frozen hosts worker...")
    check = subprocess.run([str(EXE), "--worker", "hosts", "--diagnose"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
                           text=True, errors="replace")
    if check.returncode:
        raise RuntimeError(f"hosts worker failed ({check.returncode}):\n{check.stderr}")
    result = json.loads(check.stdout)
    assert "mapping" in result and "resolved_ip" in result, result
    print("Frozen hosts worker OK")
    # Complete standalone package: the optional chroma-key video editor
    # must not force viewers to download a separate FFmpeg installer.
    ffmpeg_bins = list(EXE.parent.rglob("ffmpeg*.exe"))
    if not ffmpeg_bins:
        raise RuntimeError("Bundled FFmpeg executable missing from Windows app")
    print("Bundled FFmpeg:", ffmpeg_bins[0].name)

    print("Starting frozen overlay worker...")
    # Separate worker is launched by the GUI via QProcess in the same way.
    process = subprocess.Popen([str(EXE), "--worker", "overlay"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for route in URLS:
            success = False
            last_error = None
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError(f"Overlay worker exited early: {process.returncode}")
                try:
                    with urlopen("http://127.0.0.1:8765" + route, timeout=1.5) as r:
                        if r.status == 200:
                            success = True
                            break
                        last_error = f"HTTP {r.status}"
                except (URLError, TimeoutError, OSError) as exc:
                    last_error = repr(exc)
                time.sleep(.25)
            if not success:
                raise RuntimeError(f"Frozen overlay {route} failed: {last_error}")
            print(f"Frozen overlay {route}: OK")
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
