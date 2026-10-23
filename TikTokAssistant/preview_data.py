"""Build an offline test notification using the exact live Overlay payload and local assets.

No TikTok session or HTTP server is needed, and no counters or settings are modified.
"""
from pathlib import Path

from overlay_server import alert_payload, media_path
from settings_store import get_gift_settings, normalize_coin_rule


def build_preview_payload(settings, kind, key, username='TestViewer', with_sound=False):
    if kind == 'gift':
        if str(key) not in settings['gifts']:
            raise ValueError('Gift is no longer configured')
        rule=get_gift_settings(settings,str(key))
        gift_name=str(key)
        quantity=1
        coins=int(rule.get('coin_value') or 0)
        total=coins
    elif kind == 'coin':
        key=int(key)
        rules=settings.get('coin_rules',[])
        if key < 0 or key >= len(rules):
            raise ValueError('Coin milestone no longer exists')
        rule=normalize_coin_rule(rules[key])
        gift_name='Rose'
        quantity=1
        coins=rule['threshold']
        total=coins
    else:
        raise ValueError('Unsupported preview event')
    payload=alert_payload(settings,rule,kind,key,username,gift_name,quantity,coins,total)
    # The preview deliberately displays disabled alerts too, allowing their designs
    # to be reviewed before enabling. User-triggered sound remains opt-in.
    payload['show_overlay']=True
    payload['play_sound']=bool(with_sound and payload['play_sound'])
    assets={}
    for media in ('image','video','sound'):
        path=media_path(settings,kind,key,media)
        if path is not None and Path(path).is_file():
            assets[media]=Path(path).resolve().as_uri()
    payload['preview_assets']=assets
    payload['preview_mode']=True
    return payload


def build_preview_action_payload(settings, action_id, with_sound=False):
    """Preview a reusable action without a running server."""
    from overlay_server import make_action_payload
    action=next((a for a in settings.get('actions',[]) if a.get('id')==action_id),None)
    if action is None:
        raise ValueError('Action not found')
    rule={'id':'preview','trigger':'gift','threshold':100}
    event={'type':'gift','username':'TestViewer','gift_name':'Rose',
           'quantity':1,'coins':1,'count':100,'comment':'Hello'}
    payload=make_action_payload(settings,action,rule,event,
        {'coins_total':100,'total_likes':1000})
    payload['show_overlay']=True
    payload['play_sound']=bool(with_sound and payload['play_sound'])
    assets={}
    for media in ('image','video','sound'):
        path=media_path(settings,'action',action_id,media)
        if path is not None and Path(path).is_file():
            assets[media]=Path(path).resolve().as_uri()
    layers={}
    for layer in action.get('alert',{}).get('elements',[]):
        if layer.get('type') in ('image','video'):
            path=Path(layer.get('file') or '')
            if path.is_file():layers[layer['id']]=path.resolve().as_uri()
    assets['elements']=layers
    payload['preview_assets']=assets
    payload['preview_mode']=True
    return payload
