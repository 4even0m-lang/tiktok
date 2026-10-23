"""Loopback Overlay plus optional read-only LAN display for local testing."""
import json
import re
import asyncio
import ipaddress
import os
from pathlib import Path
from aiohttp import web, WSMsgType
from settings_store import load_settings, get_gift_settings, normalize_coin_rule, clamp
from rules_engine import RuleEngine
from leaderboards import Leaderboards
from gift_catalog import update_catalog, presentation_items, set_override
from event_bus import EventBus

ROOT = Path(__file__).resolve().parent
clients = set()
leaderboard_clients = set()
leaderboard_state = Leaderboards()
IMAGE_EXT = {'.png','.jpg','.jpeg','.gif','.webp'}
AUDIO_EXT = {'.wav','.mp3','.ogg','.m4a','.aac'}
VIDEO_EXT = {'.mp4','.webm'}
session_total_coins = 0
session_total_likes = 0
session_total_follows = 0
rule_engine = RuleEngine()
live_event_bus = EventBus()
awarded_stream_thresholds = set()


def valid_asset(path_value,suffixes):
    if not path_value or not isinstance(path_value,str): return None
    candidate = Path(path_value).expanduser()
    return candidate if candidate.suffix.lower() in suffixes and candidate.is_file() else None


def selected_rule(settings, kind, index_or_name):
    if kind == 'action':
        return next((a.get('alert') for a in settings.get('actions',[]) if a.get('id')==str(index_or_name)), None)
    if kind == 'coin':
        index = int(index_or_name)
        rules = settings.get('coin_rules',[])
        if index < 0 or index >= len(rules): return None
        return normalize_coin_rule(rules[index])
    return get_gift_settings(settings,str(index_or_name))


def media_path(settings, kind, key, media):
    alert = selected_rule(settings,kind,key)
    if alert is None: return None
    if media == 'sound':
        return (valid_asset(alert.get('sound_file'),AUDIO_EXT)
            or valid_asset(settings.get('sound_file'),AUDIO_EXT)
            or valid_asset(str(ROOT/'assets'/'gift.wav'),AUDIO_EXT))
    if media == 'image': return valid_asset(alert.get('image_file'),IMAGE_EXT)
    if media == 'video': return valid_asset(alert.get('video_file'),VIDEO_EXT)
    return None


def media_response(request, media):
    kind = request.query.get('kind','gift')
    if kind not in ('gift','coin','action'): raise web.HTTPBadRequest()
    key = request.query.get('key',request.query.get('gift',''))[:80]
    try: path = media_path(load_settings(),kind,key,media)
    except (TypeError,ValueError): raise web.HTTPBadRequest()
    if path is None: raise web.HTTPNotFound()
    result = web.FileResponse(path)
    result.headers['Cache-Control'] = 'no-store'
    return result

async def overlay(request):
    response = web.FileResponse(ROOT/'overlay.html')
    response.headers['Cache-Control'] = 'no-store'
    return response

async def leaderboard_page(request):
    response = web.FileResponse(ROOT/'leaderboards.html')
    response.headers['Cache-Control']='no-store'
    return response

async def board_socket(request):
    ws=web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    leaderboard_clients.add(ws)
    try:
        await ws.send_json(board_payload())
        async for msg in ws:
            if msg.type == WSMsgType.ERROR:break
    finally:
        leaderboard_clients.discard(ws)
    return ws


def board_payload():
    settings=load_settings()
    return dict(leaderboard_state.snapshot(settings.get('leaderboards',{}).get('top_n',5)),
                display=settings.get('leaderboards',{}))


async def board_data(request):return web.json_response(board_payload())


async def broadcast_board():
    value=json.dumps(board_payload(),ensure_ascii=False)
    for ws in list(leaderboard_clients):
        try:await ws.send_str(value)
        except Exception:leaderboard_clients.discard(ws)


async def gift_catalog_get(request):return web.json_response({'items':presentation_items()})


async def gift_catalog_update(request):
    obj=await request.json()
    if not isinstance(obj,dict) or not isinstance(obj.get('gifts'),list):
        raise web.HTTPBadRequest(text='Expected gifts array')
    count=update_catalog(obj['gifts'])
    return web.json_response({'ok':True,'changed':count})


async def gift_catalog_override(request):
    obj=await request.json()
    if not isinstance(obj,dict):raise web.HTTPBadRequest()
    try:set_override(obj.get('name',''),obj.get('coins',0))
    except ValueError:raise web.HTTPBadRequest(text='Gift name required')
    return web.json_response({'ok':True})


async def element_asset(request):
    """Only serve paths explicitly configured in a saved Action layer."""
    action_id=request.query.get('action','')[:64]
    element_id=request.query.get('element','')[:60]
    s=load_settings()
    action=next((a for a in s.get('actions',[]) if a.get('id')==action_id),None)
    if not action:raise web.HTTPNotFound()
    layer=next((e for e in action.get('alert',{}).get('elements',[])
                if e.get('id')==element_id and e.get('type') in ('image','video')),None)
    if layer is None:raise web.HTTPNotFound()
    allowed=IMAGE_EXT if layer['type']=='image' else VIDEO_EXT
    file=valid_asset(layer.get('file'),allowed)
    if not file:raise web.HTTPNotFound()
    response=web.FileResponse(file)
    response.headers['Cache-Control']='no-store'
    return response

async def sound(request):return media_response(request,'sound')
async def image(request):return media_response(request,'image')
async def video(request):return media_response(request,'video')

async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    clients.add(ws)
    try:
        async for msg in ws:
            if msg.type == WSMsgType.ERROR: break
    finally: clients.discard(ws)
    return ws


def alert_payload(settings, rule, kind, key, username, gift_name, quantity, coins=0, coins_total=0):
    prefix = {'username':username,'gift_name':gift_name,'quantity':quantity,
              'coins':coins,'coins_total':coins_total,
              'type':'gift' if kind=='gift' else 'coin_milestone',
              'show_overlay':rule['overlay'],
              'play_sound':bool(settings['sound_enabled'] and rule['sound']),
              'volume':rule['volume'] if rule['volume'] is not None else settings['volume'],
              'template':rule['template'],
              'accent':rule['accent'],
              'icon':rule['icon'],
              'message':rule['message'],
              'duration_ms':rule['duration_ms'],
              'video_audio':rule.get('video_audio',False),
              'video_only':rule.get('video_only',False),
              'language':settings['language'],
              'media_kind':kind, 'media_key':str(key),
              'has_image':bool(media_path(settings,kind,key,'image')),
              'has_video':bool(media_path(settings,kind,key,'video')),
              'has_sound':bool(media_path(settings,kind,key,'sound'))}
    if kind=='coin':
        prefix['threshold'] = rule['threshold']
        prefix['basis'] = rule['basis']
    return prefix

async def broadcast(payload):
    serialized = json.dumps(payload,ensure_ascii=False)
    for ws in list(clients):
        try: await ws.send_str(serialized)
        except Exception: clients.discard(ws)

def make_action_payload(settings, action, rule, event_data, context):
    from settings_store import normalize_alert
    cfg=normalize_alert(action.get('alert',{}))
    payload=alert_payload(settings,cfg,'action',action['id'],
        str(event_data.get('username') or 'Viewer')[:80],
        str(event_data.get('gift_name') or 'Gift')[:80],
        clamp(event_data.get('quantity',1),1,100000,1),
        clamp(event_data.get('coins',0),0,1000000000,0),
        context.get('coins_total',0))
    payload.update({'type':'action','trigger_type':rule.get('trigger','gift'),
        'action_id':action['id'],'event_id':rule['id'],
        'threshold':rule.get('threshold',0),
        'likes':event_data.get('count',0),
        'total_likes':context.get('total_likes',0),
        'comment':str(event_data.get('comment') or '')[:240],
        'visual_layout':cfg.get('visual_layout',False),
        'elements':cfg.get('elements',[])})
    return payload


async def event(request):
    global session_total_coins, session_total_likes, session_total_follows
    try:
        data=await request.json()
        if not isinstance(data,dict):raise ValueError('Expected JSON object')
        settings=load_settings()
        kind=str(data.get('type') or 'gift')
        if kind not in ('gift','follow','like','comment'):raise ValueError('Unknown event type')
        username=str(data.get('username') or 'Viewer')[:80]
        gift_name=str(data.get('gift_name') or 'Gift')[:80]
        quantity=clamp(data.get('quantity',1),1,100000,1)
        coins=clamp(data.get('coins',0),0,1000000000,0)
        likes=clamp(data.get('count',0),0,1000000,0)
        test_mode=data.get('test_mode') is True
        live_event={'type':kind,'username':username,
                    'user_id':str(data.get('user_id') or '')[:80],
                    'gift_name':gift_name,
                    'quantity':quantity,'coins':coins,'count':likes,
                    'comment':str(data.get('comment') or '')[:240]}
        if not test_mode:
            leaderboard_changed=leaderboard_state.record(live_event)
            if kind=='gift':session_total_coins=min(1000000000,session_total_coins+coins)
            elif kind=='like':session_total_likes=min(1000000000,session_total_likes+likes)
            elif kind=='follow':session_total_follows+=1
        context={'coins_total':session_total_coins,'total_likes':session_total_likes,
                 'total_follows':session_total_follows}
        if settings.get('automations_enabled'):
            matches=rule_engine.match(settings,live_event,context,test=test_mode)
            messages=[make_action_payload(settings,action,rule,live_event,context)
                      for rule,action in matches]
        else:
            # Retain v4 legacy behavior for existing installations until migration.
            messages=[]
            if kind=='gift':
                gift_rule=get_gift_settings(settings,gift_name)
                messages=[alert_payload(settings,gift_rule,'gift',gift_name,username,gift_name,
                                        quantity,coins,session_total_coins)]
                if not test_mode and coins>0:
                    reached=[]
                    for index,raw in enumerate(settings.get('coin_rules',[])):
                        rule=normalize_coin_rule(raw)
                        if not rule['enabled']:continue
                        threshold=rule['threshold']
                        if rule['basis']=='stream':
                            key=('stream',threshold)
                            if key in awarded_stream_thresholds or session_total_coins<threshold:continue
                            awarded_stream_thresholds.add(key);reached.append((index,rule))
                        elif coins>=threshold:reached.append((index,rule))
                    stream=[(i,r) for i,r in reached if r['basis']=='stream']
                    per_gift=[(i,r) for i,r in reached if r['basis']=='gift']
                    if stream:
                        i,r=max(stream,key=lambda pair:pair[1]['threshold'])
                        messages.append(alert_payload(settings,r,'coin',i,username,gift_name,
                                           quantity,coins,session_total_coins))
                    for i,r in per_gift:
                        messages.append(alert_payload(settings,r,'coin',i,username,gift_name,
                                           quantity,coins,session_total_coins))
    except (ValueError,TypeError,AttributeError,OverflowError):
        raise web.HTTPBadRequest(text='Invalid payload')
    # Provider-neutral diagnostics/event consumers receive the normalized event.
    await live_event_bus.publish(live_event, simulated=test_mode)
    for msg in messages:await broadcast(msg)
    if not test_mode and leaderboard_changed:
        await broadcast_board()
    if kind=='gift':print(f'[GIFT] {gift_name} x{quantity}, coins={coins}, alerts={len(messages)}',flush=True)
    elif kind=='like':print(f'[LIKE] +{likes}, session={session_total_likes}, alerts={len(messages)}',flush=True)
    elif kind=='follow':print(f'[FOLLOW] {username}, alerts={len(messages)}',flush=True)
    return web.json_response({'ok':True,'clients':len(clients),'alerts':len(messages),
        'session_total_coins':session_total_coins,'session_total_likes':session_total_likes})


async def test_action(request):
    """Loopback-only simulator: do not change counters or cooldown state."""
    data=await request.json()
    if not isinstance(data,dict):raise web.HTTPBadRequest()
    settings=load_settings()
    action=next((a for a in settings.get('actions',[]) if a['id']==data.get('id')),None)
    if action is None:raise web.HTTPNotFound(text='Action not found')
    rule={'id':'test','trigger':'gift','threshold':1000}
    live={'type':'gift','username':'TestViewer','gift_name':'Rose','quantity':1,'coins':1}
    msg=make_action_payload(settings,action,rule,live,{'coins_total':0,'total_likes':0})
    await broadcast(msg)
    return web.json_response({'ok':True,'clients':len(clients),'alerts':1})


async def test_event_rule(request):
    data=await request.json()
    if not isinstance(data,dict):raise web.HTTPBadRequest()
    settings=load_settings()
    rule=next((e for e in settings.get('events',[]) if e['id']==data.get('id')),None)
    if rule is None:raise web.HTTPNotFound(text='Event not found')
    ids=rule.get('action_ids',[])
    all_actions={a['id']:a for a in settings.get('actions',[])}
    selected=[all_actions[i] for i in ids if i in all_actions]
    if rule.get('mode')=='random' and selected:
        import random
        selected=[random.choice(selected)]
    sample={'type':rule['trigger'],'username':'TestViewer','gift_name':rule.get('gift_name') or 'Rose',
            'quantity':1,'coins':rule.get('threshold',1),'count':rule.get('threshold',1000),
            'comment':rule.get('keyword') or 'Hello'}
    context={'coins_total':rule.get('threshold',1000),'total_likes':rule.get('threshold',1000)}
    msgs=[make_action_payload(settings,a,rule,sample,context) for a in selected]
    for msg in msgs:await broadcast(msg)
    return web.json_response({'ok':True,'clients':len(clients),'alerts':len(msgs)})

async def test_alert(request):
    try:
        data = await request.json()
        if not isinstance(data,dict): raise ValueError()
        index = int(data.get('index',-1))
        settings = load_settings()
        rule = selected_rule(settings,'coin',index)
        if rule is None: raise ValueError()
        threshold = rule['threshold']
        msg = alert_payload(settings,rule,'coin',index,'TestUser','Test Gift',1,
                            threshold,threshold)
    except (ValueError,TypeError): raise web.HTTPBadRequest(text='Unknown rule')
    await broadcast(msg)
    return web.json_response({'ok':True,'clients':len(clients)})

async def reset_coins(request):
    global session_total_coins, session_total_likes, session_total_follows
    session_total_coins = 0
    session_total_likes = 0
    session_total_follows = 0
    rule_engine.reset()
    awarded_stream_thresholds.clear()
    leaderboard_state.reset()
    await broadcast_board()
    print('[COINS] reset total=0',flush=True)
    return web.json_response({'ok':True,'session_total_coins':0})

async def stats(request):
    return web.json_response({'session_total_coins':session_total_coins,
                              'clients':len(clients),'session_total_likes':session_total_likes,
                              'milestones_reached':len(awarded_stream_thresholds),
                              'event_bus_sequence':live_event_bus.sequence})

async def config(request):
    s = load_settings()
    return web.json_response({'volume':s['volume'],'sound_enabled':s['sound_enabled'],
                              'language':s['language']})

async def health(request):
    return web.json_response({'status':'running','clients':len(clients),
                              'session_total_coins':session_total_coins,'session_total_likes':session_total_likes})

app = web.Application(client_max_size=512*1024)
app.router.add_get('/',overlay)
app.router.add_get('/overlay',overlay)
app.router.add_get('/leaderboards',leaderboard_page)
app.router.add_get('/top-likers',leaderboard_page)
app.router.add_get('/top-supporters',leaderboard_page)
app.router.add_get('/leaderboards/data',board_data)
app.router.add_get('/ws/leaderboards',board_socket)
app.router.add_get('/assets/element',element_asset)
app.router.add_get('/gift_catalog',gift_catalog_get)
app.router.add_post('/gift_catalog/update',gift_catalog_update)
app.router.add_post('/gift_catalog/override',gift_catalog_override)
app.router.add_get('/ws',ws_handler)
app.router.add_get('/assets/sound',sound)
app.router.add_get('/assets/image',image)
app.router.add_get('/assets/video',video)
app.router.add_get('/assets/gift.wav',sound)
app.router.add_get('/health',health)
app.router.add_get('/stats',stats)
app.router.add_get('/config',config)
app.router.add_post('/event',event)
app.router.add_post('/test_action',test_action)
app.router.add_post('/test_event_rule',test_event_rule)
app.router.add_post('/test_alert',test_alert)
app.router.add_post('/reset_coins',reset_coins)

# DISPLAY-ONLY routes on the optional LAN listener: NO /event, /reset_coins,
# /test_alert or /config. Administrative operations stay loopback-only.
def is_rfc1918_address(value):
    try:
        candidate = ipaddress.IPv4Address(str(value).strip())
    except ipaddress.AddressValueError:
        return False
    return any(candidate in block for block in (
        ipaddress.IPv4Network('10.0.0.0/8'),
        ipaddress.IPv4Network('172.16.0.0/12'),
        ipaddress.IPv4Network('192.168.0.0/16'),
    ))

def create_lan_display_app():
    display = web.Application(client_max_size=16384)
    for route, handler in (
        ('/', overlay), ('/overlay', overlay), ('/leaderboards',leaderboard_page),('/top-likers',leaderboard_page),('/top-supporters',leaderboard_page),
        ('/leaderboards/data',board_data), ('/ws/leaderboards',board_socket), ('/assets/element',element_asset), ('/health', health),
        ('/ws', ws_handler),
        ('/assets/sound', sound), ('/assets/image', image),
        ('/assets/video', video), ('/assets/gift.wav', sound),
    ):
        display.router.add_get(route, handler)
    return display

async def run_servers(lan_ip=''):
    private_runner = web.AppRunner(app, access_log=None)
    await private_runner.setup()
    display_runner = None
    try:
        private_site = web.TCPSite(private_runner, '127.0.0.1', 8765)
        await private_site.start()
        print('OVERLAY_LOCAL_READY: http://127.0.0.1:8765/overlay',flush=True)
        if lan_ip:
            if not is_rfc1918_address(lan_ip):
                raise ValueError('LAN IP must be an RFC1918 private IPv4 address')
            display_runner = web.AppRunner(create_lan_display_app(), access_log=None)
            await display_runner.setup()
            display_site = web.TCPSite(display_runner, lan_ip, 8766)
            await display_site.start()
            print(f'OVERLAY_LAN_READY: http://{lan_ip}:8766/overlay',flush=True)
            print('LAN listener is display-only; gift events and admin routes stay local.',flush=True)
        await asyncio.Event().wait()
    finally:
        if display_runner is not None:
            await display_runner.cleanup()
        await private_runner.cleanup()

if __name__=='__main__':
    lan_ip = os.environ.get('TIKTOK_OVERLAY_LAN_IP','').strip()
    if lan_ip and not is_rfc1918_address(lan_ip):
        raise SystemExit('Invalid TIKTOK_OVERLAY_LAN_IP: expected private IPv4 (10.x, 172.16-31.x, 192.168.x)')
    try:
        asyncio.run(run_servers(lan_ip))
    except KeyboardInterrupt:
        pass
