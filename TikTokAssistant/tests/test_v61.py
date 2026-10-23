"""V6.1 regression: gift icons, distinct board routes, RTL, hosts, chroma command."""
import sys
import unittest
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gift_catalog
from hosts_setup import status,install
from visual_schema import normalize_elements
from overlay_server import app, create_lan_display_app, leaderboard_page
from aiohttp import web
from aiohttp.test_utils import TestClient,TestServer
from video_tools import ffmpeg_command

class GiftAssetsTest(unittest.TestCase):
    def test_all_icons_offline_without_coin_guess(self):
        imgs=gift_catalog.local_gift_images()
        self.assertGreaterEqual(len(imgs),780)
        rose=imgs['rose'];self.assertEqual(rose['coins'],0)
        self.assertTrue(Path(rose['image_file']).is_file())
        presentation=gift_catalog.presentation_items()
        self.assertTrue(any(x['name']=='Lion' and Path(x['image_file']).is_file() for x in presentation))
    def test_live_data_updates_icon_record_without_touching_asset(self):
        with tempfile.TemporaryDirectory() as d:
            previous=gift_catalog.CATALOG_PATH
            gift_catalog.CATALOG_PATH=Path(d)/'catalog.json'
            try:
                gift_catalog.update_catalog([{'id':'rose-tiktok','name':'Rose','coins':1}])
                result=next(x for x in gift_catalog.presentation_items() if x['name']=='Rose')
                self.assertEqual(result['coins'],1)
                self.assertTrue(Path(result['image_file']).is_file())
                self.assertEqual(result['id'],'rose-tiktok')
            finally:gift_catalog.CATALOG_PATH=previous

class RoutesTest(unittest.TestCase):
    def test_independent_board_routes_and_separate_alert_route(self):
        paths={route.resource.canonical for route in app.router.routes()}
        self.assertTrue({'/overlay','/top-likers','/top-supporters','/leaderboards'}.issubset(paths))
        display_paths={route.resource.canonical for route in create_lan_display_app().router.routes()}
        self.assertTrue({'/top-likers','/top-supporters'}.issubset(display_paths))
        self.assertNotIn('/event',display_paths)
    def test_blank_layout_rtl_and_alignment(self):
        self.assertEqual(normalize_elements([]),[])
        layer=normalize_elements([{'type':'text','text':'أهلاً {user}','direction':'rtl','align':'right'}])[0]
        self.assertEqual(layer['direction'],'rtl');self.assertEqual(layer['align'],'right')
        layer=normalize_elements([{'type':'text','direction':'ltr','align':'center'}])[0]
        self.assertEqual(layer['direction'],'ltr');self.assertEqual(layer['align'],'center')
        html=Path(__file__).resolve().parents[1].joinpath('overlay.html').read_text(encoding='utf-8')
        self.assertIn("el.dir=layer.direction",html)
        self.assertIn("el.style.whiteSpace='pre-wrap'",html)
        self.assertTrue(Path(__file__).resolve().parents[1].joinpath('visual_live_preview.html').is_file())

class HostsTest(unittest.TestCase):
    def test_opt_in_and_conflict_safe(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'hosts';p.write_bytes(b'127.0.0.1 localhost\r\n')
            self.assertEqual(status(p),'missing')
            self.assertEqual(install(p),'ready')
            self.assertEqual(install(p),'ready')
            self.assertEqual(p.read_bytes().count(b'overlay.test'),1)
            self.assertTrue(p.with_name('hosts.tiktokassistant.bak').is_file())
            p.write_bytes(b'192.168.1.5 overlay.test\n')
            self.assertEqual(status(p),'conflict');self.assertEqual(install(p),'conflict')
            self.assertNotIn(b'127.0.0.1 overlay.test',p.read_bytes())

class BrowserSourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_independent_urls_serve_transparent_page(self):
        serverapp=web.Application()
        serverapp.router.add_get('/top-likers',leaderboard_page)
        serverapp.router.add_get('/top-supporters',leaderboard_page)
        async with TestClient(TestServer(serverapp)) as client:
            for path in ('/top-likers','/top-supporters'):
                response=await client.get(path)
                self.assertEqual(response.status,200)
                body=await response.text()
                self.assertIn("background:transparent!important",body)
                self.assertIn("location.pathname==='/top-likers'",body)

class VideoToolsTest(unittest.TestCase):
    def test_ffmpeg_optional_chroma_command(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'green.mp4';src.write_bytes(b'fake')
            args=ffmpeg_command(src,Path(d)/'alpha.webm')
            self.assertIn('libvpx-vp9',args)
            self.assertIn('-auto-alt-ref',args)
            self.assertTrue(any('colorkey=' in a for a in args))

if __name__=='__main__':unittest.main()
