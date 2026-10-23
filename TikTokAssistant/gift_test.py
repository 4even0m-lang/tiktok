"""TikTok LIVE event connector. Emits status markers consumed by PySide6."""
import asyncio
import os
import sys
import traceback
import aiohttp
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, GiftEvent, FollowEvent, LikeEvent, CommentEvent
from settings_store import load_settings, get_gift_settings
from gift_catalog import price_for

USERNAME = os.environ.get('TIKTOK_USERNAME', '').strip().lstrip('@')
OVERLAY_URL = 'http://127.0.0.1:8765/event'
_catalog_seen = {}

def gift_unit_coins(gift):
    """Best-effort public gift metadata, not a billing or wallet figure."""
    info=_field(gift,'info')
    candidates = (_field(gift, 'diamond_count'),_field(info, 'diamond_count'),
                  _field(gift, 'coin_count'),_field(info, 'coin_count'),
                  _field(gift, 'diamondCount'),_field(info, 'diamondCount'))
    for value in candidates:
        try:
            count = int(value)
            if count > 0: return count
        except (TypeError, ValueError, OverflowError): pass
    return 0


def _field(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def gift_metadata(gift):
    """Best-effort extraction: TikTokLive objects vary across library versions."""
    if gift is None:return None
    image = _field(gift,'image') or _field(gift,'icon')
    url = _field(image,'url') or _field(image,'url_list') or _field(gift,'image_url') or ''
    if isinstance(url,(list,tuple)):url=next((x for x in url if isinstance(x,str)), '')
    return {'id':str(_field(gift,'id') or _field(gift,'gift_id') or ''),
        'name':str(_field(gift,'name') or ''),
        'coins':gift_unit_coins(gift), 'image_url':str(url or '')}


def catalog_from_client(client):
    source = getattr(client,'gift_info',None)
    if callable(source):return []
    if isinstance(source,dict):source=source.values()
    if not isinstance(source,(list,tuple,set)) and source is not None:
        source = _field(source,'gifts') or _field(source,'gift_list') or []
    if not isinstance(source,(list,tuple,set)):return []
    return [record for g in source if (record:=gift_metadata(g)) and record['name']]


async def send_catalog(entries):
    if not entries:return
    pending=[]
    for record in entries[:1500]:
        key=str(record.get('id') or record.get('name') or '')
        fingerprint=(record.get('name'),record.get('coins'),record.get('image_url'))
        if not key or _catalog_seen.get(key)==fingerprint:continue
        pending.append((key,fingerprint,record))
    if not pending:return
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
            # Batches avoid overflowing the server's JSON request-size limit.
            for start in range(0,len(pending),40):
                subset=pending[start:start+40]
                async with session.post('http://127.0.0.1:8765/gift_catalog/update',
                                       json={'gifts':[row[2] for row in subset]}) as response:
                    if response.status!=200:return
                for key,fingerprint,_ in subset:_catalog_seen[key]=fingerprint
        print(f'GIFT_CATALOG: cached {len(pending)} gift metadata records',flush=True)
    except (aiohttp.ClientError, asyncio.TimeoutError):pass


async def send_event(event_data):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.post(OVERLAY_URL, json=event_data) as response:
                if response.status != 200:
                    print(f'OVERLAY_ERROR: HTTP {response.status}', flush=True)
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(f'OVERLAY_ERROR: {type(exc).__name__}: {exc}', flush=True)

async def main():
    if not USERNAME or USERNAME == 'YOUR_USERNAME':
        print('TIKTOK_ERROR: Set TIKTOK_USERNAME', flush=True)
        return 2

    # Keep the proven working connection constructor unchanged.
    client = TikTokLiveClient(unique_id=f'@{USERNAME}')
    connected_once = False

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        nonlocal connected_once
        connected_once = True
        print('TIKTOK_CONNECTED', flush=True)
        print(f'Connected to @{USERNAME}', flush=True)
        await send_catalog(catalog_from_client(client))

    @client.on(GiftEvent)
    async def on_gift(event: GiftEvent):
        gift = event.gift
        if gift is None:
            return
        if getattr(gift, 'type', None) == 1 and getattr(event, 'streaking', False):
            return
        user = getattr(event, 'user', None)
        sender = getattr(user, 'nickname', None) or getattr(user, 'unique_id', 'Viewer')
        name = getattr(gift, 'name', 'Gift')
        quantity = max(1, int(getattr(event, 'repeat_count', 1) or 1))
        override = get_gift_settings(load_settings(),name).get('coin_value',0)
        identifier = str(_field(gift,'id') or _field(gift,'gift_id') or '')
        unit_coins = override if override > 0 else (price_for(name,identifier) or gift_unit_coins(gift))
        metadata=gift_metadata(gift)
        if metadata:await send_catalog([metadata])
        coins = unit_coins * quantity
        print(f'[GIFT] {sender} sent {name} x{quantity} coins={coins}', flush=True)
        if not coins:
            print(f'COINS_UNAVAILABLE: {name} has no usable coin count in TikTokLive metadata', flush=True)
        await send_event({'type':'gift','username':sender,'gift_name':name,
                          'quantity':quantity,'coins':coins,
                          'user_id':str(getattr(user,'unique_id','') or '')})

    @client.on(FollowEvent)
    async def on_follow(event: FollowEvent):
        user=getattr(event,'user',None)
        sender=getattr(user,'nickname',None) or getattr(user,'unique_id','Viewer')
        print(f'[FOLLOW] {sender}',flush=True)
        await send_event({'type':'follow','username':sender,
                          'user_id':str(getattr(user,'unique_id','') or '')})

    @client.on(LikeEvent)
    async def on_like(event: LikeEvent):
        user=getattr(event,'user',None)
        sender=getattr(user,'nickname',None) or getattr(user,'unique_id','Viewer')
        try: count=max(0,int(getattr(event,'count',0) or 0))
        except (ValueError,TypeError):count=0
        if count:
            print(f'[LIKE] {sender} +{count}',flush=True)
            await send_event({'type':'like','username':sender,'count':count,
                              'user_id':str(getattr(user,'unique_id','') or '')})

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        user=getattr(event,'user',None)
        sender=getattr(user,'nickname',None) or getattr(user,'unique_id','Viewer')
        comment=str(getattr(event,'comment','') or '')[:240]
        # Avoid spamming the log with chat; the rule engine filters by keyword.
        await send_event({'type':'comment','username':sender,'comment':comment,
                          'user_id':str(getattr(user,'unique_id','') or '')})

    print('TIKTOK_CONNECTING', flush=True)
    try:
        await client.connect()
        if connected_once:
            print('TIKTOK_CLIENT_STOPPED: connection ended', flush=True)
        else:
            print('TIKTOK_ERROR: client.connect() returned without ConnectEvent', flush=True)
        return 0 if connected_once else 3
    except Exception as exc:
        print(f'TIKTOK_ERROR: {type(exc).__name__}: {exc}', flush=True)
        traceback.print_exc()
        return 1
    finally:
        try:
            if client.connected:
                await client.disconnect()
        except Exception as exc:
            print(f'TIKTOK_DISCONNECT_ERROR: {type(exc).__name__}: {exc}', flush=True)

if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print('TIKTOK_STOPPED_BY_USER', flush=True)
        sys.exit(130)
    except Exception as exc:
        print(f'TIKTOK_FATAL: {type(exc).__name__}: {exc}', flush=True)
        traceback.print_exc()
        sys.exit(1)
