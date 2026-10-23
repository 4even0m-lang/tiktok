"""Release-specific regressions: don't search for frozen .py files on disk."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from portable_runtime import missing_bundle_resources, subprocess_launch


class FrozenWorkerTests(unittest.TestCase):
    def test_frozen_worker_runs_inside_same_executable(self):
        for worker in ('overlay', 'gift', 'hosts'):
            with patch.object(sys, 'frozen', True, create=True), patch.object(
                    sys, 'executable', r'C:\Ven0m\Ven0m_TikTok_LIVE_Assistant.exe'):
                program, args = subprocess_launch(worker, ROOT / (worker + '.py'))
            self.assertEqual(program, r'C:\Ven0m\Ven0m_TikTok_LIVE_Assistant.exe')
            self.assertEqual(args, ['--worker', worker])

    def test_source_worker_uses_python_script(self):
        with patch.object(sys, 'frozen', False, create=True):
            program, args = subprocess_launch('overlay', ROOT / 'overlay_server.py')
        self.assertEqual(program, sys.executable)
        self.assertEqual(args[-1], str(ROOT / 'overlay_server.py'))

    def test_invalid_worker_rejected(self):
        with self.assertRaises(ValueError):
            subprocess_launch('wrong', ROOT / 'main.py')

    def test_missing_bundle_does_not_require_python_files(self):
        with tempfile.TemporaryDirectory() as name:
            bundle = Path(name)
            for item in ('overlay.html', 'leaderboards.html', 'visual_live_preview.html',
                         'assets/branding/ven0m_icon.png'):
                filename = bundle / item
                filename.parent.mkdir(parents=True, exist_ok=True)
                filename.write_text('demo', encoding='utf-8')
            gifts = bundle / 'assets/gifts'
            gifts.mkdir(parents=True)
            for i in range(786):
                (gifts / f'{i:03d}.png').touch()
            self.assertEqual(missing_bundle_resources(bundle), [])

    def test_missing_resources_error_for_wrong_pyinstaller_build(self):
        with tempfile.TemporaryDirectory() as name:
            missing = missing_bundle_resources(Path(name) / '_internal')
            self.assertIn('overlay.html', missing)
            self.assertIn('assets/gifts/ (786 PNG files)', missing)

    def test_main_supports_frozen_worker_dispatch(self):
        source = (ROOT / 'main.py').read_text(encoding='utf-8')
        self.assertIn('from portable_entry import dispatch', source)
        self.assertIn('missing_bundle_resources(ROOT)', source)
        script = (ROOT / 'tools/build_windows.ps1').read_text(encoding='utf-8')
        self.assertIn("'portable_entry.py'", script)
        self.assertIn("'--add-data=overlay.html;.'", script)


if __name__ == '__main__':
    unittest.main()
