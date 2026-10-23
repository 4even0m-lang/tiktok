"""Process spawning shared between development and Windows packaged builds."""
from __future__ import annotations
import sys
from pathlib import Path

ALLOWED_WORKERS = frozenset({'gift', 'overlay', 'hosts'})

def subprocess_launch(worker: str, script: Path):
    """Return (program, args). Frozen builds must launch themselves as workers."""
    if worker not in ALLOWED_WORKERS:
        raise ValueError(f"Unknown child process: {worker}")
    if getattr(sys, 'frozen', False):
        return sys.executable, ['--worker', worker]
    return sys.executable, ['-u', str(script)]


# Resources distributed as data files rather than Python modules.
# On PyInstaller releases ``__file__`` points to the bundle data directory,
# which is NOT necessarily the same directory as the executable.
REQUIRED_BUNDLE_FILES = (
    'overlay.html',
    'leaderboards.html',
    'visual_live_preview.html',
    'assets/branding/ven0m_icon.png',
)


def missing_bundle_resources(bundle_dir: Path) -> list[str]:
    """Return paths omitted by an incomplete PyInstaller invocation.

    This intentionally does not require ``overlay_server.py`` on disk: frozen
    Python modules are stored inside the PyInstaller archive, not as .py files.
    """
    bundle_dir = Path(bundle_dir)
    missing = [path for path in REQUIRED_BUNDLE_FILES
               if not (bundle_dir / path).is_file()]
    gifts_dir = bundle_dir / 'assets' / 'gifts'
    if not gifts_dir.is_dir() or len(list(gifts_dir.glob('*.png'))) < 786:
        missing.append('assets/gifts/ (786 PNG files)')
    return missing
