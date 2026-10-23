"""Opt-in Windows hosts mapping for TikTok LIVE Assistant.

Never requires elevation to start the GUI. An elevated helper may only
update the single overlay.test alias after explicit user confirmation.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

ALIAS = 'overlay.test'
ENTRY = b'127.0.0.1 overlay.test  # TikTok LIVE Assistant'


def hosts_path():
    return Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'drivers' / 'etc' / 'hosts'


def _read(path):
    raw = Path(path).read_bytes()
    # A UTF-16 hosts file does not work reliably with Windows name resolution.
    # Preserve it untouched and ask the user to repair the encoding manually.
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')) or b'\x00' in raw:
        raise ValueError('Unsupported hosts encoding (UTF-16 / NUL bytes)')
    return raw


def _split_mapping(line):
    """Return (address, aliases, comment) for an uncommented hosts entry."""
    left, mark, right = line.partition('#')
    parts = left.split()
    if len(parts) < 2:
        return None
    return parts[0], parts[1:], (mark + right) if mark else ''


def status(path=None):
    """ready / missing / conflict / unavailable; no modification."""
    filename = Path(path) if path else hosts_path()
    try:
        raw = _read(filename)
    except (OSError, ValueError):
        return 'unavailable'
    addresses = set()
    for line in raw.decode('latin-1').splitlines():
        entry = _split_mapping(line)
        if entry and any(alias.casefold() == ALIAS for alias in entry[1]):
            addresses.add(entry[0])
    if not addresses:
        return 'missing'
    return 'ready' if addresses == {'127.0.0.1'} else 'conflict'


def _make_content(raw, *, repair=False):
    """Return new bytes, changing *only* the target alias when repair=True.

    Other hosts entries, comments, and IP-address aliases remain intact.
    This is not a general-purpose hosts cleanup utility.
    """
    sep = b'\r\n' if b'\r\n' in raw else b'\n'
    if repair:
        output = []
        for source_line in raw.splitlines(keepends=True):
            body = source_line.rstrip(b'\r\n')
            ending = source_line[len(body):]
            text = body.decode('latin-1')
            entry = _split_mapping(text)
            if entry is None or not any(a.casefold() == ALIAS for a in entry[1]):
                output.append(source_line)
                continue
            ip, aliases, comment = entry
            remaining = [a for a in aliases if a.casefold() != ALIAS]
            if remaining:
                replacement = f'{ip} {" ".join(remaining)}'
                if comment:
                    replacement += '  ' + comment
                output.append(replacement.encode('latin-1') + ending)
            elif comment:
                # Retain user's inline comment, but not a conflicting mapping.
                output.append(comment.encode('latin-1') + ending)
            # Otherwise remove the now-empty line.
        raw = b''.join(output)
    if raw and not raw.endswith((b'\r', b'\n')):
        raw += sep
    return raw + ENTRY + sep


def install(path=None, *, repair=False):
    """Write mapping with backup; conflicting mappings require explicit repair.

    Does not elevate itself. Elevated execution is launched separately, only
    after the user confirms the specific action in the application.
    """
    filename = Path(path) if path else hosts_path()
    state = status(filename)
    if state == 'ready':
        return 'ready'
    if state == 'unavailable' or (state == 'conflict' and not repair):
        return state
    original = _read(filename)
    updated = _make_content(original, repair=(state == 'conflict' and repair))
    backup = filename.with_name(filename.name + '.tiktokassistant.bak')
    # Never proceed without a backup of the *current* file.
    shutil.copy2(filename, backup)
    try:
        with filename.open('wb') as f:
            f.write(updated)
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        # Best-effort rollback, using the exact in-memory original bytes.
        try:
            with filename.open('wb') as f:
                f.write(original)
        except OSError:
            pass
        raise
    if path is None:
        try:
            subprocess.run(['ipconfig', '/flushdns'], capture_output=True,
                           timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return status(filename)


def resolved_address():
    try:
        return socket.gethostbyname(ALIAS)
    except OSError:
        return None


def _http_health(host):
    """Diagnostic only. Bypass system proxy for loopback host aliases."""
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(f'http://{host}:8765/health', timeout=2) as response:
            return 'ok' if response.status == 200 else f'http_{response.status}'
    except HTTPError as exc:
        return f'http_{exc.code}'
    except (URLError, OSError, TimeoutError) as exc:
        return f'unavailable: {type(exc).__name__}'


def diagnose():
    """Report distinct mapping, DNS and server states; no writes."""
    return {
        'hosts_file': str(hosts_path()),
        'mapping': status(),
        'resolved_ip': resolved_address(),
        'server_local': _http_health('127.0.0.1'),
        'server_alias': _http_health(ALIAS),
    }


def _write_result(path, state, detail=''):
    Path(path).write_text(json.dumps({'state': state, 'detail': detail},
                                    ensure_ascii=False), encoding='utf-8')


def request_admin_install(*, repair=False):
    """Spawn separate UAC helper; *does not* imply that it succeeded.

    Returns a result-file path for UI polling, or None when elevation could
    not be started / was canceled.
    """
    if sys.platform != 'win32':
        return None
    fd, result_name = tempfile.mkstemp(prefix='tiktok_hosts_', suffix='.json')
    os.close(fd)
    output = Path(result_name)
    _write_result(output, 'pending')
    script = Path(__file__).resolve()
    args = (['--worker', 'hosts'] if getattr(sys, 'frozen', False) else [str(script)]) + ['--apply', '--result-file', str(output)]
    if repair:
        args.append('--repair')
    params = subprocess.list2cmdline(args)
    try:
        shell32 = ctypes.WinDLL('shell32', use_last_error=True)
        shell32.ShellExecuteW.restype = ctypes.c_void_p
        result = shell32.ShellExecuteW(None, 'runas', sys.executable,
                                       params, str(script.parent), 1)
        code = int(result or 0)
    except (OSError, AttributeError):
        code = 0
    if code <= 32:
        output.unlink(missing_ok=True)
        return None
    return output


def read_elevation_result(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {'state': 'pending'}
    except (OSError, ValueError):
        return {'state': 'pending', 'detail': ''}


def manual_instructions():
    return (f'1. Open Notepad as Administrator.\n'
            f'2. Open {hosts_path()} (choose All Files).\n'
            f'3. Ensure a single active mapping: 127.0.0.1 {ALIAS}\n'
            '4. Remove conflicting mappings for overlay.test only (if any).\n'
            '5. Save, then run: ipconfig /flushdns\n'
            f'6. Check: http://{ALIAS}:8765/health\n'
            '7. Start Overlay server first to test the health URL.')


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if '--diagnose' in args:
        print(json.dumps(diagnose(), ensure_ascii=False, indent=2))
        return 0
    if '--apply' not in args:
        print('No changes made. Run with --diagnose for status.')
        return 2
    output = None
    if '--result-file' in args:
        i = args.index('--result-file')
        if i + 1 < len(args):
            output = Path(args[i + 1])
    try:
        state = install(repair='--repair' in args)
        detail = f'hosts mapping: {state}'
    except (OSError, ValueError) as exc:
        state, detail = 'error', f'{type(exc).__name__}: {exc}'
    if output is not None:
        try:
            _write_result(output, state, detail)
        except OSError:
            pass
    print(detail, flush=True)
    return 0 if state == 'ready' else 1


if __name__ == '__main__':
    sys.exit(main())
