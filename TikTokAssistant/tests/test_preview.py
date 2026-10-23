"""Smoke tests for embedded-preview payload generation without a Qt dependency."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import settings_store as store
from preview_data import build_preview_payload


class PreviewPayloadTests(unittest.TestCase):
    def test_offline_gift_preview_and_media_file_uris(self):
        with tempfile.TemporaryDirectory() as root:
            settings=store.load_settings()
            image=Path(root)/'test image.gif'
            image.write_bytes(b'GIF89a')
            settings['gifts']['Rose']['image_file']=str(image)
            settings['gifts']['Rose']['template']='image'
            settings['gifts']['Rose']['overlay']=False
            payload=build_preview_payload(settings,'gift','Rose',with_sound=False)
            self.assertTrue(payload['preview_mode'])
            self.assertTrue(payload['show_overlay'])
            self.assertFalse(payload['play_sound'])
            self.assertEqual(payload['template'],'image')
            self.assertEqual(payload['preview_assets']['image'],image.resolve().as_uri())

    def test_coin_preview_does_not_change_totals(self):
        settings=store.load_settings()
        settings['coin_rules']=[store.normalize_coin_rule({'threshold':500,'template':'gold'})]
        payload=build_preview_payload(settings,'coin',0,username='Tester',with_sound=False)
        self.assertEqual(payload['type'],'coin_milestone')
        self.assertEqual(payload['threshold'],500)
        self.assertEqual(payload['username'],'Tester')
        self.assertEqual(payload['coins_total'],500)

    def test_missing_gift_raises(self):
        with self.assertRaises(ValueError):
            build_preview_payload(store.load_settings(),'gift','Does-not-exist')

if __name__=='__main__':unittest.main()
