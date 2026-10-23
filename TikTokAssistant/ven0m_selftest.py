"""Frozen executable self-test for release QA; never touches actual user data.

Requires VEN0M_DATA_DIR to point to an isolated test directory, set by the
Windows CI smoke test. Does not connect to TikTok or change the Windows hosts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def run() -> int:
    if not os.environ.get('VEN0M_DATA_DIR'):
        print('Self-test requires isolated VEN0M_DATA_DIR; refusing to touch user settings.')
        return 2
    from app_paths import writable_file
    from settings_store import load_settings, save_settings, CONFIG_PATH
    from gift_catalog import CATALOG_PATH, set_override, price_for, local_gift_images

    assert CONFIG_PATH == writable_file('settings.json')
    assert CATALOG_PATH == writable_file('gift_catalog.json')
    settings = load_settings()
    settings['username'] = 'Ven0m build test — اختبار'
    save_settings(settings)
    assert load_settings()['username'] == settings['username']
    set_override('Test Gift', 4)
    assert price_for('Test Gift') == 4
    icons = len(local_gift_images())
    if icons < 780:
        raise RuntimeError(f'Missing gift icons: {icons}')
    print(json.dumps({'ok': True, 'gift_icons': icons,
                      'writable_settings': CONFIG_PATH.is_file(),
                      'writable_catalog': CATALOG_PATH.is_file()}, ensure_ascii=False), flush=True)
    return 0
