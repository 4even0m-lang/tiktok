"""Integration test: incoming TikTok-style events -> action payloads -> WebSocket."""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import overlay_server as server
import settings_store as store
from rules_engine import normalize_action,normalize_event

class AutomationApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=store.CONFIG_PATH
        store.CONFIG_PATH=Path(self.temp.name)/'settings.json'
        cfg=store.load_settings()
        cfg['automations_enabled']=True
        (Path(self.temp.name)/'intro.webm').write_bytes(b'video test')
        cfg['actions']=[normalize_action({'id':'fire','name':'Fire','alert':{'template':'fire','message':'{user} sent {gift}'}}),
                        normalize_action({'id':'movie','name':'Movie','alert':{'template':'video',
                            'video_file':str(Path(self.temp.name)/'intro.webm'),'video_only':True}})]
        cfg['events']=[normalize_event({'id':'e1','name':'Gift Lion','trigger':'gift',
                        'gift_name':'Lion','action_ids':['fire','movie']}),
                       normalize_event({'id':'e2','name':'Follow','trigger':'follow','action_ids':['fire']}),
                       normalize_event({'id':'e3','name':'Likes 500','trigger':'likes','threshold':500,'action_ids':['fire']}),
                       normalize_event({'id':'e4','name':'Comment GG','trigger':'comment','keyword':'gg','action_ids':['fire']})]
        store.save_settings(cfg)
        server.session_total_coins=0
        server.session_total_likes=0
        server.session_total_follows=0
        server.rule_engine.reset()
        routes=web.Application()
        routes.router.add_get('/ws',server.ws_handler)
        routes.router.add_get('/assets/video',server.video)
        routes.router.add_post('/event',server.event)
        routes.router.add_post('/test_action',server.test_action)
        routes.router.add_post('/test_event_rule',server.test_event_rule)
        routes.router.add_post('/reset_coins',server.reset_coins)
        self.client=TestClient(TestServer(routes))
        await self.client.start_server()
        self.ws=await self.client.ws_connect('/ws')
    async def asyncTearDown(self):
        await self.ws.close();await self.client.close()
        store.CONFIG_PATH=self.path
        self.temp.cleanup()
    async def pull(self):
        return json.loads((await asyncio.wait_for(self.ws.receive(),2)).data)
    async def test_gift_two_actions_with_video_asset(self):
        resp=await self.client.post('/event',json={'type':'gift','username':'Ali',
                      'gift_name':'Lion','quantity':1,'coins':299})
        self.assertEqual((await resp.json())['alerts'],2)
        first,second=await self.pull(),await self.pull()
        self.assertEqual([first['action_id'],second['action_id']],['fire','movie'])
        self.assertTrue(second['has_video']);self.assertTrue(second['video_only'])
        video=await self.client.get('/assets/video?kind=action&key=movie')
        self.assertEqual(await video.read(),b'video test')
    async def test_follow_like_and_keyword_rules(self):
        resp=await self.client.post('/event',json={'type':'follow','username':'Sami'})
        self.assertEqual((await resp.json())['alerts'],1)
        self.assertEqual((await self.pull())['trigger_type'],'follow')
        resp=await self.client.post('/event',json={'type':'like','username':'Sami','count':400})
        self.assertEqual((await resp.json())['alerts'],0)
        resp=await self.client.post('/event',json={'type':'like','username':'Sami','count':250})
        self.assertEqual((await resp.json())['alerts'],1)
        self.assertEqual((await self.pull())['total_likes'],650)
        resp=await self.client.post('/event',json={'type':'like','count':300})
        self.assertEqual((await resp.json())['alerts'],0)
        resp=await self.client.post('/event',json={'type':'comment','comment':'gg wp'})
        self.assertEqual((await resp.json())['alerts'],1)
        self.assertEqual((await self.pull())['trigger_type'],'comment')
    async def test_on_demand_preview_does_not_change_counters(self):
        resp=await self.client.post('/test_event_rule',json={'id':'e3'})
        self.assertEqual((await resp.json())['alerts'],1)
        self.assertEqual((await self.pull())['type'],'action')
        resp=await self.client.post('/test_action',json={'id':'movie'})
        self.assertEqual((await resp.json())['alerts'],1)
        self.assertEqual((await self.pull())['media_key'],'movie')
        self.assertEqual(server.session_total_likes,0)

if __name__=='__main__':unittest.main()
