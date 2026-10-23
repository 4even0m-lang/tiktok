"""Integration smoke tests: python -m unittest discover -s tests -v"""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import settings_store as store
import overlay_server as server
from aiohttp.test_utils import TestClient, TestServer
from aiohttp import web


class OverlayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_config = store.CONFIG_PATH
        store.CONFIG_PATH = Path(self.temp.name) / 'settings.json'
        self.settings = store.load_settings()
        self.settings['gifts']['Rose']['template'] = 'video'
        self.settings['gifts']['Rose']['video_file'] = str(Path(self.temp.name)/'alert.mp4')
        self.settings['gifts']['Rose']['coin_value'] = 1
        self.settings['coin_rules'] = [
            store.normalize_coin_rule({'threshold':100,'basis':'stream','template':'gold','icon':'🏆'}),
            store.normalize_coin_rule({'threshold':250,'basis':'stream','template':'cyber'}),
            store.normalize_coin_rule({'threshold':40,'basis':'gift','template':'fire'}),
        ]
        (Path(self.temp.name)/'alert.mp4').write_bytes(b'fake MP4 bytes for serving test')
        store.save_settings(self.settings)
        server.session_total_coins = 0
        server.awarded_stream_thresholds.clear()
        fresh=web.Application()
        for method,path,handler in (
            ('GET','/overlay',server.overlay),('GET','/assets/video',server.video),
            ('GET','/stats',server.stats),('GET','/ws',server.ws_handler),
            ('POST','/event',server.event),('POST','/test_alert',server.test_alert),
            ('POST','/reset_coins',server.reset_coins)):
            fresh.router.add_route(method,path,handler)
        self.client = TestClient(TestServer(fresh))
        await self.client.start_server()
        self.ws = await self.client.ws_connect('/ws')

    async def asyncTearDown(self):
        await self.ws.close()
        await self.client.close()
        store.CONFIG_PATH = self.old_config
        self.temp.cleanup()

    async def take(self):
        return json.loads((await asyncio.wait_for(self.ws.receive(),1)).data)

    async def test_transparent_page_and_video_asset(self):
        r = await self.client.get('/overlay')
        html = await r.text()
        self.assertIn('background:transparent!important',html)
        self.assertIn('id="clip"',html)
        asset = await self.client.get('/assets/video?kind=gift&key=Rose')
        self.assertEqual(asset.status,200)
        self.assertEqual(await asset.read(),b'fake MP4 bytes for serving test')
        self.assertEqual(asset.headers.get('Cache-Control'),'no-store')

    async def test_coin_milestones_and_unique_session_fires(self):
        r=await self.client.post('/event',json={'username':'A','gift_name':'Rose','quantity':1,'coins':80})
        self.assertEqual(r.status,200)
        self.assertEqual((await r.json())['alerts'],2) # gift + per-event 40 threshold
        msgs = [await self.take(),await self.take()]
        self.assertEqual([v['type'] for v in msgs],['gift','coin_milestone'])
        self.assertTrue(msgs[0]['has_video'])
        self.assertEqual(msgs[0]['coins_total'],80)
        r=await self.client.post('/event',json={'username':'B','gift_name':'Rose','quantity':1,'coins':30})
        self.assertEqual((await r.json())['alerts'],2) # crosses 100; <40 per-gift
        msg1,msg2=await self.take(),await self.take()
        self.assertEqual(msg2['threshold'],100)
        r=await self.client.post('/event',json={'username':'C','gift_name':'Rose','quantity':1,'coins':160})
        self.assertEqual((await r.json())['alerts'],3) # gift + 250 stream + 40 gift
        msgs=[await self.take() for _ in range(3)]
        self.assertEqual([m['threshold'] for m in msgs[1:]],[250,40])
        self.assertEqual(msgs[1]['coins_total'],270)
        r=await self.client.post('/event',json={'username':'D','gift_name':'Rose','coins':5})
        self.assertEqual((await r.json())['alerts'],1)
        self.assertEqual((await self.take())['type'],'gift')
        resp=await self.client.get('/stats')
        self.assertEqual((await resp.json())['session_total_coins'],275)

    async def test_test_alert_and_reset_do_not_corrupt_totals(self):
        r=await self.client.post('/event',json={'gift_name':'Rose','coins':100000,'test_mode':True})
        self.assertEqual((await r.json())['session_total_coins'],0)
        self.assertEqual((await self.take())['type'],'gift')
        r=await self.client.post('/test_alert',json={'index':1})
        self.assertEqual(r.status,200)
        msg=await self.take()
        self.assertEqual(msg['type'],'coin_milestone')
        self.assertEqual(msg['threshold'],250)
        r=await self.client.post('/reset_coins',json={})
        self.assertEqual((await r.json())['session_total_coins'],0)
        self.assertEqual(len(server.awarded_stream_thresholds),0)

    async def test_media_bad_paths(self):
        self.assertEqual((await self.client.get('/assets/video?kind=gift&key=Unknown')).status,404)
        self.assertEqual((await self.client.get('/assets/video?kind=coin&key=not-a-number')).status,400)


if __name__=='__main__': unittest.main()
