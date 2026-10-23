"""Regression checks for v6.2 single canvas and Windows host setup."""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hosts_setup import status, install, read_elevation_result, main, manual_instructions
from visual_schema import normalize_elements


class SingleCanvasTests(unittest.TestCase):
    def test_editor_has_one_webengine_canvas_and_live_geometry(self):
        editor = (ROOT / 'visual_editor.py').read_text(encoding='utf-8')
        widget = (ROOT / 'visual_live_preview.py').read_text(encoding='utf-8')
        html = (ROOT / 'visual_live_preview.html').read_text(encoding='utf-8')
        ast.parse(editor)
        ast.parse(widget)
        self.assertEqual(editor.count('VisualLivePreview('), 1)
        self.assertNotIn('QGraphicsView', editor)
        self.assertIn('QIntValidator', editor)
        self.assertIn('self.live.layer_moved.connect', editor)
        self.assertIn('self.live.set_layers(self.layers)', editor)
        self.assertIn('window.updateVisual=', html)
        self.assertIn('window.selectVisual=', html)
        self.assertIn('window.setPreviewPlaying=', html)
        self.assertIn('window.QWebChannel', html)
        self.assertIn("inner.style.unicodeBidi='plaintext'", html)
        self.assertIn('direction', html)
        self.assertIn('pointerdown', html)
        self.assertIn('video', html)

    def test_arabic_remains_logical_unicode_order(self):
        original = 'شكرًا {user} على هدية الأسد 🦁'
        element = normalize_elements([{'type':'text', 'text':original,
                                       'direction':'rtl','align':'right',
                                       'w':365,'h':155}])[0]
        self.assertEqual(element['text'], original)
        self.assertEqual(element['w'], 365)
        self.assertEqual(element['h'], 155)
        self.assertEqual(element['direction'], 'rtl')


class HostInstallResultTests(unittest.TestCase):
    def test_result_state_is_not_assumed_success(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'result.json'
            output.write_text(json.dumps({'state':'pending'}), encoding='utf-8')
            self.assertEqual(read_elevation_result(output)['state'], 'pending')
            with patch('hosts_setup.install', return_value='conflict'):
                self.assertEqual(main(['--apply','--result-file',str(output)]), 1)
            self.assertEqual(read_elevation_result(output)['state'], 'conflict')
            with patch('hosts_setup.install', return_value='ready'):
                self.assertEqual(main(['--apply','--result-file',str(output)]), 0)
            self.assertEqual(read_elevation_result(output)['state'], 'ready')

    def test_hosts_safe_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / 'hosts'
            f.write_text('127.0.0.1 localhost\n', encoding='utf-8')
            self.assertEqual(status(f), 'missing')
            self.assertEqual(install(f), 'ready')
            self.assertEqual(install(f), 'ready')
            self.assertEqual(f.read_text(encoding='utf-8').count('overlay.test'), 1)
            f.write_text('127.0.0.1 overlay.test\n192.168.1.10 overlay.test\n', encoding='utf-8')
            self.assertEqual(status(f), 'conflict')
            self.assertEqual(install(f), 'conflict')
            f.write_bytes(b'\xff\xfe' + '127.0.0.1 overlay.test'.encode('utf-16le'))
            self.assertEqual(status(f), 'unavailable')
        self.assertIn('127.0.0.1 overlay.test', manual_instructions())

if __name__ == '__main__':
    unittest.main()
