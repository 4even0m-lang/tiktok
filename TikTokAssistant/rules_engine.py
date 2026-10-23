"""Independent, reusable LIVE event -> action rule engine (no Qt/network dependency).

All inputs are received LIVE metadata; the system does not infer locations or users.
"""
import copy
import random
import time
import uuid

TRIGGERS = ('gift', 'follow', 'likes', 'coins', 'comment')

def make_id():
    return uuid.uuid4().hex[:14]


def normalize_action(data):
    from settings_store import normalize_alert
    source = data if isinstance(data, dict) else {}
    return {
        'id': str(source.get('id') or make_id())[:64],
        'name': str(source.get('name') or 'New action')[:90],
        'enabled': bool(source.get('enabled', True)),
        'alert': normalize_alert(source.get('alert', {})),
    }


def normalize_event(data):
    from settings_store import clamp
    source = data if isinstance(data, dict) else {}
    trigger = source.get('trigger', 'gift')
    if trigger not in TRIGGERS: trigger = 'gift'
    mode = source.get('mode', 'all')
    if mode not in ('all','random'): mode = 'all'
    basis = source.get('coin_basis', 'stream')
    if basis not in ('stream','gift'): basis='stream'
    ids = source.get('action_ids', [])
    ids = [str(i)[:64] for i in ids[:20] if isinstance(i,(str,int))] if isinstance(ids,list) else []
    result = {
        'id': str(source.get('id') or make_id())[:64],
        'name': str(source.get('name') or 'New event')[:90],
        'enabled': bool(source.get('enabled',True)),
        'trigger': trigger,
        'gift_name': str(source.get('gift_name') or '')[:80],
        'user_filter': str(source.get('user_filter') or '').strip().lstrip('@')[:80],
        'min_coins': clamp(source.get('min_coins'),0,1000000000,0),
        'threshold': clamp(source.get('threshold'),1,1000000000,100),
        'coin_basis': basis,
        'keyword': str(source.get('keyword') or '')[:100],
        'action_ids': list(dict.fromkeys(ids)),
        'mode': mode,
        'cooldown_sec': clamp(source.get('cooldown_sec'),0,3600,0),
        'fallback_only': bool(source.get('fallback_only',False)),
    }
    # Irrelevant fields cannot accidentally survive a trigger change and later
    # interfere with rule matching or user expectations.
    if trigger != 'gift':
        result.update(gift_name='',min_coins=0,fallback_only=False)
    if trigger != 'comment':result['keyword']=''
    if trigger not in ('likes','coins'):result['threshold']=100
    if trigger != 'coins':result['coin_basis']='stream'
    return result


def migrate_legacy(settings):
    """One-time opt-in migration preserving existing gift/coin alert designs.

    Does not mutate legacy gifts/coin_rules; enables the new engine after saving.
    """
    from settings_store import normalize_alert
    if settings.get('automations_enabled'):
        return False
    actions, events = [], []
    for name, old in settings.get('gifts',{}).items():
        a=normalize_action({'name':f'🎁 {name}', 'alert':old})
        e=normalize_event({'name':f'هدية {name}', 'trigger':'gift','gift_name':name,'action_ids':[a['id']]})
        actions.append(a); events.append(e)
    generic=normalize_action({'name':'🎁 أي هدية أخرى','alert':{'template':'neon','icon':'🎁'}})
    actions.append(generic)
    events.append(normalize_event({'name':'أي هدية أخرى','trigger':'gift',
                                   'gift_name':'','fallback_only':True,'action_ids':[generic['id']]}))
    for old in settings.get('coin_rules',[]):
        a=normalize_action({'name':f"🪙 {old.get('threshold',100)} coins",'alert':old})
        e=normalize_event({'name':f"بلوغ {old.get('threshold',100)} عملة",
            'trigger':'coins','threshold':old.get('threshold',100),
            'coin_basis':old.get('basis','stream'),
            'enabled':old.get('enabled',True),'action_ids':[a['id']]})
        actions.append(a);events.append(e)
    # Templates are ready to edit, but disabled until streamer deliberately enables them.
    a=normalize_action({'name':'👋 ترحيب بمتابع جديد',
       'alert':{'template':'confetti','icon':'👋','message':'شكرًا على المتابعة يا {user}!'}})
    actions.append(a)
    events.append(normalize_event({'name':'متابعة جديدة','trigger':'follow',
                                  'action_ids':[a['id']],'enabled':False}))
    a=normalize_action({'name':'❤️ إنجاز الإعجابات',
       'alert':{'template':'fire','icon':'❤️','message':'وصلنا إلى {total_likes} إعجاب!'}})
    actions.append(a)
    events.append(normalize_event({'name':'هدف 1000 إعجاب','trigger':'likes','threshold':1000,
                                  'action_ids':[a['id']],'enabled':False}))
    settings['actions']=actions;settings['events']=events
    settings['automations_enabled']=True
    return True


class RuleEngine:
    def __init__(self):
        self.fired=set()
        self.last_fired={}

    def reset(self):
        self.fired.clear();self.last_fired.clear()

    def match(self, settings, event, context=None, test=False):
        """Return ordered (event_rule,action) pairs; state changes only for live runs."""
        ctx=context or {}
        trigger=event.get('type','gift')
        if trigger == 'like': trigger = 'likes'
        actions={a['id']:a for a in settings.get('actions',[]) if a.get('enabled',True)}
        configured=settings.get('events',[])
        # A generic gift fallback is suppressed only by a *matching* specific rule.
        # An exact-name rule with an unmet min-coins condition should not suppress it.
        any_exact=trigger=='gift' and any(
            e.get('enabled',True) and e.get('trigger')=='gift' and
            (not e.get('user_filter') or str(e.get('user_filter')).casefold() == str(event.get('user_id') or '').casefold()) and
            str(e.get('gift_name','')).strip() and
            str(e.get('gift_name','')).strip().casefold()==str(event.get('gift_name','')).strip().casefold() and
            int(event.get('coins',0) or 0)>=int(e.get('min_coins',0) or 0) and
            any(i in actions for i in e.get('action_ids',[]))
            for e in configured)
        result=[]
        now=time.monotonic()
        for rule in configured:
            wanted_user = str(rule.get('user_filter') or '').strip().casefold()
            if wanted_user and wanted_user != str(event.get('user_id') or '').strip().lstrip('@').casefold():
                continue
            if not rule.get('enabled',True) or rule.get('trigger')!=trigger and not (rule.get('trigger')=='coins' and trigger=='gift'):
                continue
            typ=rule.get('trigger')
            if typ=='gift':
                name=str(rule.get('gift_name','')).strip()
                if name and name.casefold()!=str(event.get('gift_name','')).strip().casefold(): continue
                if not name and rule.get('fallback_only') and any_exact: continue
                if int(event.get('coins',0) or 0)<int(rule.get('min_coins',0) or 0):continue
            elif typ=='follow':
                pass
            elif typ=='comment':
                keyword=str(rule.get('keyword','')).strip().casefold()
                if not keyword or keyword not in str(event.get('comment','')).casefold(): continue
            elif typ=='likes':
                threshold=int(rule.get('threshold',100) or 100)
                if int(ctx.get('total_likes',0))<threshold:continue
                if ('likes',rule['id']) in self.fired and not test:continue
            elif typ=='coins':
                threshold=int(rule.get('threshold',100) or 100)
                basis=rule.get('coin_basis','stream')
                if basis=='stream':
                    if int(ctx.get('coins_total',0))<threshold:continue
                    if ('coins',rule['id']) in self.fired and not test:continue
                elif int(event.get('coins',0) or 0)<threshold:continue
            else: continue
            if not test and now-self.last_fired.get(rule['id'],-1e12) < int(rule.get('cooldown_sec',0)):continue
            selected=[actions[i] for i in rule.get('action_ids',[]) if i in actions]
            if not selected:continue
            if rule.get('mode')=='random':selected=[random.choice(selected)]
            result.extend((rule,a) for a in selected)
            if not test:
                self.last_fired[rule['id']]=now
                if typ=='likes':self.fired.add(('likes',rule['id']))
                if typ=='coins' and rule.get('coin_basis','stream')=='stream':
                    self.fired.add(('coins',rule['id']))
        return result
