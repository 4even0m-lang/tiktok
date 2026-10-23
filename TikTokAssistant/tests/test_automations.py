"""Event/action engine regression tests; no desktop or TikTok credentials required."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import settings_store as store
from rules_engine import RuleEngine, migrate_legacy, normalize_event, normalize_action
from overlay_server import make_action_payload

class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.engine=RuleEngine()
        self.first=normalize_action({'id':'sound','name':'Sound','alert':{'template':'neon','message':'Thanks {user}!'}})
        self.second=normalize_action({'id':'video','name':'Video','alert':{'template':'video','video_only':True}})
        self.settings={**copy.deepcopy(store.DEFAULTS), 'automations_enabled':True,
                       'actions':[self.first,self.second], 'events':[]}
    def add(self,**options):
        rule=normalize_event({'id':'rule'+str(len(self.settings['events'])),'action_ids':['sound','video'],**options})
        self.settings['events'].append(rule)
        return rule
    def test_gift_link_to_two_actions(self):
        self.add(trigger='gift',gift_name='Lion',min_coins=500)
        self.assertEqual(len(self.engine.match(self.settings,{'type':'gift','gift_name':'Rose','coins':1000})),0)
        found=self.engine.match(self.settings,{'type':'gift','gift_name':'Lion','coins':600})
        self.assertEqual([a['id'] for _,a in found],['sound','video'])
    def test_gift_fallback_disappears_when_specific_rule(self):
        self.add(trigger='gift',gift_name='',fallback_only=True)
        self.add(trigger='gift',gift_name='Rose')
        self.assertEqual(len(self.engine.match(self.settings,{'type':'gift','gift_name':'Rose','coins':5})),2)
        self.assertEqual(len(self.engine.match(self.settings,{'type':'gift','gift_name':'Lion','coins':5})),2)
    def test_fallback_used_if_specific_rule_minimum_not_reached(self):
        self.add(trigger='gift',gift_name='',fallback_only=True)
        self.add(trigger='gift',gift_name='Rose',min_coins=100)
        self.assertEqual(len(self.engine.match(self.settings,{'type':'gift','gift_name':'Rose','coins':5})),2)
        self.assertEqual(len(self.engine.match(self.settings,{'type':'gift','gift_name':'Rose','coins':101})),2)
    def test_follow_and_comments(self):
        self.add(trigger='follow')
        self.add(trigger='comment',keyword='GG')
        self.assertEqual(len(self.engine.match(self.settings,{'type':'follow','username':'Ali'})),2)
        self.assertEqual(len(self.engine.match(self.settings,{'type':'comment','comment':'good GAME'})),0)
        self.assertEqual(len(self.engine.match(self.settings,{'type':'comment','comment':'gg team'})),2)
    def test_likes_threshold_once_even_if_event_called_like(self):
        self.add(trigger='likes',threshold=1000)
        event={'type':'like','count':25,'username':'A'}
        self.assertEqual(self.engine.match(self.settings,event,{'total_likes':999}),[])
        self.assertEqual(len(self.engine.match(self.settings,event,{'total_likes':1001})),2)
        self.assertEqual(self.engine.match(self.settings,event,{'total_likes':2000}),[])
        self.engine.reset()
        self.assertEqual(len(self.engine.match(self.settings,event,{'total_likes':2000})),2)
    def test_coin_stream_and_gift(self):
        self.add(trigger='coins',threshold=100,coin_basis='stream')
        self.add(trigger='coins',threshold=40,coin_basis='gift')
        event={'type':'gift','gift_name':'Rose','coins':80}
        self.assertEqual(len(self.engine.match(self.settings,event,{'coins_total':80})),2)
        self.assertEqual(len(self.engine.match(self.settings,event,{'coins_total':105})),4)
        self.assertEqual(len(self.engine.match(self.settings,event,{'coins_total':110})),2)
    def test_random_action_selection_and_cooldown(self):
        self.add(trigger='gift',cooldown_sec=30,mode='random')
        event={'type':'gift','gift_name':'Rose','coins':5}
        self.assertEqual(len(self.engine.match(self.settings,event)),1)
        self.assertEqual(len(self.engine.match(self.settings,event)),0)
        self.assertEqual(len(self.engine.match(self.settings,event,test=True)),1)
    def test_action_payload_media_keys(self):
        rule=self.add(trigger='follow')
        payload=make_action_payload(self.settings,self.first,rule,
                {'type':'follow','username':'Ahmed'}, {'coins_total':0,'total_likes':7})
        self.assertEqual(payload['media_kind'],'action')
        self.assertEqual(payload['media_key'],'sound')
        self.assertEqual(payload['trigger_type'],'follow')
        self.assertEqual(payload['message'],'Thanks {user}!')
    def test_specific_username_filter_and_fallback(self):
        # Match against stable TikTok unique_id, not mutable display nickname.
        self.add(trigger='gift',gift_name='Rose',user_filter='user_one')
        self.add(trigger='gift',gift_name='',fallback_only=True)
        other={'type':'gift','gift_name':'Rose','coins':5,'username':'Display Name','user_id':'user_two'}
        self.assertEqual(len(self.engine.match(self.settings,other)),2)
        correct={**other,'user_id':'user_one'}
        self.assertEqual(len(self.engine.match(self.settings,correct)),2)
        # Exactly one rule should match either sender; both rules have two actions.
        self.assertEqual(self.engine.match(self.settings,{'type':'gift','gift_name':'Rose','coins':5})[0][0]['fallback_only'],True)

    def test_migrate_legacy_without_destroying_rules(self):
        s=copy.deepcopy(store.DEFAULTS)
        s['coin_rules']=[store.normalize_coin_rule({'threshold':150,'basis':'stream','template':'gold'})]
        self.assertTrue(migrate_legacy(s))
        self.assertTrue(s['automations_enabled'])
        self.assertTrue(any(e['trigger']=='coins' for e in s['events']))
        self.assertTrue(any(e['trigger']=='gift' for e in s['events']))
        self.assertTrue(any(e['trigger']=='likes' and not e['enabled'] for e in s['events']))
        previous=copy.deepcopy(s)
        self.assertFalse(migrate_legacy(s))
        self.assertEqual(previous,s)
    def test_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            prior=store.CONFIG_PATH
            try:
                store.CONFIG_PATH=Path(directory)/'settings.json'
                self.add(trigger='gift',gift_name='Rose')
                store.save_settings(self.settings)
                loaded=store.load_settings()
                self.assertEqual(len(loaded['actions']),2)
                self.assertEqual(len(loaded['events']),1)
                self.assertEqual(loaded['events'][0]['action_ids'],['sound','video'])
            finally:store.CONFIG_PATH=prior

if __name__=='__main__':unittest.main()
