"""Single source of truth for writable user data in source and frozen releases.

Program assets are read-only. User preferences and gift metadata are not.
Never create writable files in the PyInstaller bundle or Program Files.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

APP_NAME = "Ven0m"
BUNDLE_ROOT = Path(__file__).resolve().parent


def user_data_dir() -> Path:
    """Windows: %LOCALAPPDATA%/Ven0m; others: XDG data home/Ven0m.

    VEN0M_DATA_DIR is useful for tests and managed/portable deployments.
    """
    override = os.environ.get('VEN0M_DATA_DIR', '').strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
    else:
        base = Path(os.environ.get('XDG_DATA_HOME') or (Path.home() / '.local' / 'share'))
    return base / APP_NAME


def writable_file(filename: str) -> Path:
    if '/' in filename or '\\' in filename or filename in ('', '.', '..'):
        raise ValueError('Only simple data filenames are permitted')
    return user_data_dir() / filename


def migrate_legacy_file(filename: str, destination: Path) -> bool:
    """Copy old root-level settings without overwriting any existing user data.

    Use a temporary file + atomic exclusive link where supported, so a worker
    cannot replace a newer preference file created by the GUI during startup.
    """
    legacy = BUNDLE_ROOT / filename
    destination = Path(destination)
    if destination.exists() or not legacy.is_file() or legacy == destination:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=destination.parent,
                                         prefix=filename + '.', suffix='.migrate',
                                         delete=False) as fp:
            temporary = Path(fp.name)
            with legacy.open('rb') as source:
                shutil.copyfileobj(source, fp)
            fp.flush()
            os.fsync(fp.fileno())
        try:
            # Creation fails if the destination is already present; never
            # overwrite the file another worker may have just written.
            os.link(temporary, destination)
            return True
        except FileExistsError:
            return False
        except OSError:
            # Filesystems without hard-link support: safe on typical desktop
            # Windows volumes, fall back only if destination still absent.
            if destination.exists():
                return False
            with destination.open('xb') as result, temporary.open('rb') as source:
                shutil.copyfileobj(source, result)
            return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
