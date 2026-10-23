"""Regression checks for user-approved hosts diagnosis and conflict repair."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hosts_setup as hs


class HostsV621Tests(unittest.TestCase):
    def test_conflict_repair_preserves_other_aliases_and_comments(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'hosts'
            p.write_bytes(b'127.0.0.1 localhost overlay.test # local aliases\r\n'
                          b'192.168.1.2 overlay.test\r\n'
                          b'10.0.0.3 printer # keep\r\n')
            self.assertEqual(hs.status(p), 'conflict')
            self.assertEqual(hs.install(p), 'conflict')
            self.assertEqual(hs.install(p, repair=True), 'ready')
            result = p.read_bytes()
            self.assertEqual(result.lower().count(b'overlay.test'), 1)
            self.assertIn(b'127.0.0.1 localhost', result)
            self.assertIn(b'10.0.0.3 printer # keep', result)
            self.assertIn(b'# local aliases', result)
            self.assertTrue((Path(folder) / 'hosts.tiktokassistant.bak').is_file())
            self.assertEqual(hs.install(p, repair=True), 'ready')
            self.assertEqual(result, p.read_bytes())

    def test_mixed_case_domain_recognized_and_normalized(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'hosts'
            p.write_bytes(b'127.0.0.1 LocalHost\n::1 OverLay.Test\n')
            self.assertEqual(hs.status(p), 'conflict')
            self.assertEqual(hs.install(p, repair=True), 'ready')
            self.assertNotIn(b'::1 OverLay.Test', p.read_bytes())

    def test_utf16_and_invalid_binary_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'hosts'
            raw = b'\xff\xfe' + '127.0.0.1 localhost\n'.encode('utf-16le')
            p.write_bytes(raw)
            self.assertEqual(hs.status(p), 'unavailable')
            self.assertEqual(hs.install(p, repair=True), 'unavailable')
            self.assertEqual(p.read_bytes(), raw)

    def test_missing_install_preserves_last_line_without_newline(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'hosts'
            p.write_bytes(b'127.0.0.1 localhost')
            self.assertEqual(hs.install(p), 'ready')
            self.assertIn(b'localhost\n127.0.0.1 overlay.test', p.read_bytes())

    def test_elevation_result_reports_real_error(self):
        with tempfile.TemporaryDirectory() as folder:
            result = Path(folder) / 'result.json'
            with patch.object(hs, 'install', side_effect=PermissionError('access denied')):
                code = hs.main(['--apply', '--repair', '--result-file', str(result)])
            self.assertEqual(code, 1)
            data = json.loads(result.read_text(encoding='utf-8'))
            self.assertEqual(data['state'], 'error')
            self.assertIn('PermissionError', data['detail'])

    def test_health_diagnosis_does_not_require_server(self):
        with patch.object(hs, 'status', return_value='ready'), \
             patch.object(hs, 'resolved_address', return_value='127.0.0.1'), \
             patch.object(hs, '_http_health', return_value='unavailable: URLError'):
            report = hs.diagnose()
        self.assertEqual(report['mapping'], 'ready')
        self.assertEqual(report['server_local'], 'unavailable: URLError')


if __name__ == '__main__':
    unittest.main()
