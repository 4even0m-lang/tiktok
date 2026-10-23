"""New v6 regression tests for live overlays, catalog, layer rendering, counters."""
import asyncio
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gift_catalog
import settings_store as store
from leaderboards import Leaderboards
from rules_engine import normalize_action, normalize_event
from overlay_server import make_action_payload
import overlay_server as server
from aiohttp import web
from aiohttp.test_utils import TestClient,TestServer

class CatalogTest(unittest.TestCase):
    def test_cache_override_and_unknown_price(self):
        with tempfile.TemporaryDirectory() as directory:
            original=gift_catalog.CATALOG_PATH
            gift_catalog.CATALOG_PATH=Path(directory)/'gift_catalog.json'
            try:
                self.assertEqual(gift_catalog.price_for('Unknown'),0)
                self.assertEqual(gift_catalog.update_catalog([
                    {'id':'10','name':'Rose','coins':1,'image_url':'https://example.com/rose.png'},
                    {'id':'20','name':'Lion','coins':29999,'image_url':'http://unsafe.invalid/p.png'}]),2)
                self.assertEqual(gift_catalog.price_for('Rose','10'),1)
                self.assertEqual(gift_catalog.price_for('Lion','20'),29999)
                self.assertEqual(gift_catalog.presentation_items()[0]['image_url'],'')
                gift_catalog.set_override('Lion',30000)
                self.assertEqual(gift_catalog.price_for('Lion','20'),30000)
                self.assertEqual(gift_catalog.update_catalog([{'id':'20','name':'Lion','coins':0}]),0)
                self.assertEqual(gift_catalog.price_for('Lion','20'),30000)
            finally:gift_catalog.CATALOG_PATH=original
    def test_visual_canvas_empty_by_default_when_requested(self):
        new=normalize_action({'name':'Custom','alert':{'visual_layout':True,'elements':[]}})
        self.assertTrue(new['alert']['visual_layout'])
        self.assertEqual(new['alert']['elements'],[])
        e=normalize_action({'id':'custom','alert':{'visual_layout':True,'elements':[
          {'id':'layer','type':'text','x':60,'y':80,'text':'{user}','font_size':52,'color':'#FFCC00'}]}})
        data=make_action_payload({**store.DEFAULTS,'actions':[e]},e,{'id':'evt','trigger':'gift'},
              {'username':'Test','gift_name':'Rose','quantity':1,'coins':1},{'coins_total':1})
        self.assertTrue(data['visual_layout']);self.assertEqual(data['elements'][0]['text'],'{user}')
        self.assertEqual(data['elements'][0]['font_size'],52)

class BoardTest(unittest.TestCase):
    def test_separate_counts_and_reset(self):
        board=Leaderboards()
        board.record({'type':'gift','user_id':'s1','username':'Sultan','coins':500,'quantity':2})
        board.record({'type':'gift','user_id':'s2','username':'Ali','coins':400,'quantity':1})
        board.record({'type':'like','user_id':'s2','username':'Ali','count':10})
        board.record({'type':'like','user_id':'s1','username':'Sultan','count':4})
        board.record({'type':'like','user_id':'s2','username':'Ali','count':15})
        result=board.snapshot(3)
        self.assertEqual(result['supporters'][0]['name'],'Sultan')
        self.assertEqual(result['supporters'][0]['gifts'],2)
        self.assertEqual(result['likers'][0]['likes'],25)
        self.assertEqual(result['totals']['likes'],29)
        board.reset();self.assertEqual(board.snapshot()['supporters'],[])

class V6ServerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old_config=store.CONFIG_PATH
        self.old_catalog=gift_catalog.CATALOG_PATH
        store.CONFIG_PATH=Path(self.temp.name)/'settings.json'
        gift_catalog.CATALOG_PATH=Path(self.temp.name)/'gift_catalog.json'
        self.settings=store.load_settings()
        self.settings['automations_enabled']=True
        self.settings['actions']=[normalize_action({'id':'visual','name':'Custom','alert':{
          'visual_layout':True,'elements':[{'id':'label','type':'text','text':'{user}'}]}})]
        self.settings['events']=[normalize_event({'id':'rose','trigger':'gift','gift_name':'Rose','action_ids':['visual']})]
        store.save_settings(self.settings)
        server.leaderboard_state.reset();server.session_total_coins=0;server.session_total_likes=0
        fresh=web.Application()
        for method,path,func in (
          ('GET','/leaderboards',server.leaderboard_page),
          ('GET','/leaderboards/data',server.board_data),
          ('GET','/ws/leaderboards',server.board_socket),
          ('GET','/gift_catalog',server.gift_catalog_get),
          ('POST','/gift_catalog/update',server.gift_catalog_update),
          ('POST','/gift_catalog/override',server.gift_catalog_override),
          ('POST','/event',server.event),('POST','/reset_coins',server.reset_coins),
          ('GET','/assets/element',server.element_asset),
          ('GET','/ws',server.ws_handler),):fresh.router.add_route(method,path,func)
        self.client=TestClient(TestServer(fresh));await self.client.start_server()
        self.board_ws=await self.client.ws_connect('/ws/leaderboards')
        self.alert_ws=await self.client.ws_connect('/ws')
        self.assertEqual((await self.board_ws.receive_json())['supporters'],[])

    async def asyncTearDown(self):
        await self.board_ws.close();await self.alert_ws.close();await self.client.close()
        gift_catalog.CATALOG_PATH=self.old_catalog;store.CONFIG_PATH=self.old_config;self.temp.cleanup()

    async def test_board_and_alert_are_isolated(self):
        for typ,payload in [('gift',{'gift_name':'Rose','coins':300,'quantity':1}),
                            ('like',{'count':7})]:
            r=await self.client.post('/event',json={'type':typ,'username':'Sultan','user_id':'sultan1',**payload})
            self.assertEqual(r.status,200)
            response=await asyncio.wait_for(self.board_ws.receive_json(),1)
            self.assertEqual(response['type'],'leaderboards')
        self.assertEqual((await self.client.get('/leaderboards/data')).status,200)
        snap=await (await self.client.get('/leaderboards/data')).json()
        self.assertEqual(snap['supporters'][0]['coins'],300)
        self.assertEqual(snap['likers'][0]['likes'],7)
        alert=await asyncio.wait_for(self.alert_ws.receive_json(),1)
        self.assertTrue(alert['visual_layout'])
        self.assertEqual(len(alert['elements']),1)
        # Test mode does not change leaderboard numbers.
        await self.client.post('/event',json={'type':'gift','username':'X','gift_name':'Rose',
                                               'coins':999999,'test_mode':True})
        snap=await (await self.client.get('/leaderboards/data')).json()
        self.assertEqual(snap['supporters'][0]['coins'],300)
        await self.client.post('/reset_coins',json={})
        reset=await asyncio.wait_for(self.board_ws.receive_json(),1)
        self.assertEqual(reset['supporters'],[])
    async def test_blank_display_and_catalog(self):
        body=await (await self.client.get('/leaderboards')).text()
        self.assertIn('background:transparent!important',body)
        bad=await self.client.get('/assets/element?action=visual&element=nonexistent')
        self.assertEqual(bad.status,404)
        r=await self.client.post('/gift_catalog/update',json={'gifts':[{'id':'g1','name':'Rose','coins':1}]})
        self.assertEqual((await r.json())['changed'],1)
        obj=await (await self.client.get('/gift_catalog')).json()
        self.assertEqual(next(g for g in obj['items'] if g['name']=='Rose')['coins'],1)

if __name__=='__main__':unittest.main()
