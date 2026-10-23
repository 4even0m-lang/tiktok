import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portable_runtime import subprocess_launch
from portable_entry import dispatch


class PortableTests(unittest.TestCase):
    def test_source_process_launch(self):
        with patch.object(sys, 'frozen', False, create=True):
            program, args = subprocess_launch('gift', Path('gift_test.py'))
        self.assertEqual(program, sys.executable)
        self.assertEqual(args, ['-u', 'gift_test.py'])

    def test_frozen_process_launch(self):
        with patch.object(sys, 'frozen', True, create=True):
            program, args = subprocess_launch('overlay', Path('overlay_server.py'))
        self.assertEqual(program, sys.executable)
        self.assertEqual(args, ['--worker', 'overlay'])

    def test_frozen_hosts_launch(self):
        with patch.object(sys, 'frozen', True, create=True):
            _, args = subprocess_launch('hosts', Path('hosts_setup.py'))
        self.assertEqual(args, ['--worker', 'hosts'])

    def test_unknown_worker_rejected(self):
        self.assertEqual(dispatch(['--worker', 'not-allowed']), 2)

    def test_header_branded(self):
        content = (Path(__file__).resolve().parents[1] / 'main.py').read_text(encoding='utf-8')
        self.assertIn('Ven0m  •  TikTok LIVE Assistant', content)
        self.assertIn('ven0m_icon.png', content)


if __name__ == '__main__':
    unittest.main()
