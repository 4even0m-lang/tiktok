"""Diagnostic for local Overlay URLs; runs without PySide6 or TikTok LIVE."""
import json
import socket
from pathlib import Path
from settings_store import CONFIG_PATH
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def test_url(url):
    try:
        with urlopen(url, timeout=2) as response:
            print(f'OK   HTTP {response.status}  {url}')
            return True
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print(f'FAIL {url}  ({exc})')
        return False


def main():
    print('\nTikTok LIVE Assistant - local address check')
    test_url('http://127.0.0.1:8765/health')
    try:
        address = socket.gethostbyname('overlay.test')
    except OSError:
        print('INFO overlay.test is not mapped yet; add 127.0.0.1 overlay.test in Windows hosts.')
    else:
        print(f'INFO overlay.test resolves to {address}')
        test_url('http://overlay.test:8765/health')
    config = CONFIG_PATH
    if config.is_file():
        try:
            settings = json.loads(config.read_text(encoding='utf-8-sig'))
            if settings.get('lan_enabled') and settings.get('lan_ip'):
                test_url(f"http://{settings['lan_ip']}:8766/health")
        except (OSError, ValueError, TypeError):
            pass
    print('\nIf local URLs open here but LIVE Studio rejects them, the restriction is probably in LIVE Studio URL validation.')


if __name__ == '__main__':
    main()
