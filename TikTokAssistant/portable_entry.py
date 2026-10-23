"""Ven0m launcher: frozen child process dispatcher and desktop GUI entry."""
from __future__ import annotations

import asyncio
import ctypes
import multiprocessing
import os
import sys
import traceback


def restore_worker_stdio():
    """Restore redirected Qt QProcess pipes in a PyInstaller --windowed child.

    PyInstaller's windowed bootloader sets sys.stdout/sys.stderr to None on
    Windows. QProcess supplies Win32 inheritable pipe handles nevertheless;
    opening those handles lets the gift connector send TIKTOK_CONNECTED markers
    back to the GUI instead of exiting with no visible output.
    """
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        return
    try:
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        get_std = kernel.GetStdHandle
        get_std.argtypes = [ctypes.c_uint32]
        get_std.restype = ctypes.c_void_p
        for attribute, win_constant in (('stdout', -11), ('stderr', -12)):
            stream = getattr(sys, attribute, None)
            if stream is not None:
                continue
            handle = get_std(win_constant & 0xFFFFFFFF)
            if handle and handle != ctypes.c_void_p(-1).value:
                fd = msvcrt.open_osfhandle(handle, os.O_WRONLY)
                setattr(sys, attribute, os.fdopen(fd, 'w', 1, encoding='utf-8', errors='replace'))
    except (OSError, AttributeError, ValueError):
        pass
    # Always provide a valid stream even when launched without QProcess pipes.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')


def dispatch(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['--worker']:
        restore_worker_stdio()
        if len(argv) < 2 or argv[1] not in ('gift', 'overlay', 'hosts', 'selftest'):
            print('Unknown worker', file=sys.stderr, flush=True)
            return 2
        name = argv[1]
        if name == 'selftest':
            from ven0m_selftest import run
            return run()
        if name == 'gift':
            import gift_test
            try:
                return asyncio.run(gift_test.main())
            except KeyboardInterrupt:
                return 130
            except Exception as exc:
                print(f'TIKTOK_FATAL: {type(exc).__name__}: {exc}', flush=True)
                traceback.print_exc()
                return 1
        if name == 'overlay':
            import overlay_server
            lan = os.environ.get('TIKTOK_OVERLAY_LAN_IP', '').strip()
            if lan and not overlay_server.is_rfc1918_address(lan):
                print('Invalid TIKTOK_OVERLAY_LAN_IP', flush=True)
                return 2
            try:
                asyncio.run(overlay_server.run_servers(lan))
                return 0
            except KeyboardInterrupt:
                return 0
            except Exception:
                traceback.print_exc()
                return 1
        import hosts_setup
        return hosts_setup.main(argv[2:])
    if argv:
        print('Unknown command line arguments: ' + str(argv), file=sys.stderr, flush=True)
        return 2
    from diagnostics import install_crash_logging
    install_crash_logging()
    from main import main
    return main()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(dispatch())
