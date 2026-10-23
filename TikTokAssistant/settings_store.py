"""Versioned, backwards-compatible, validated local settings."""
import copy
import json
import os
import re
import tempfile
from pathlib import Path
from app_paths import writable_file, migrate_legacy_file
from presets import PRESETS

CONFIG_PATH = writable_file('settings.json')
TEMPLATES = set(PRESETS)

DEFAULT_ALERT = {
    'overlay': True, 'sound': True, 'template': 'neon', 'accent': '#ac70ff',
    'icon': '🎁', 'message': '', 'duration_ms': 4500, 'image_file': '',
    'video_file': '', 'video_audio': False, 'video_only': False, 'sound_file': '', 'volume': None,
    'coin_value': 0, 'visual_layout': False, 'elements': [],
}
DEFAULT_GIFT = DEFAULT_ALERT
DEFAULTS = {
    'username':'', 'language':'ar', 'theme':'dark', 'sound_enabled':True, 'volume':70, 'sound_file':'',
    'lan_enabled':False, 'lan_ip':'', 'hosts_setup_prompted':False,
    'leaderboards': {'show_likers':True,'show_supporters':True,'top_n':5,'theme':'dark'},
    'automations_enabled': False, 'actions': [], 'events': [],
    'gifts': {
        'Rose':{'template':'neon','accent':'#ed70aa','icon':'🌹'},
        'Lion':{'template':'gold','accent':'#ffca56','icon':'🦁'},
        'Crown':{'template':'royal','accent':'#a78bfa','icon':'👑'},
        'Teddy Bear':{'template':'minimal','accent':'#6be0c5','icon':'🧸'},
        'Star':{'template':'fire','accent':'#ff8758','icon':'⭐'},
    },
    'coin_rules': [],
}

def clamp(value, minimum, maximum, default):
    try: return min(maximum, max(minimum, int(value)))
    except (ValueError, TypeError, OverflowError): return default


def normalize_alert(value):
    out = copy.deepcopy(DEFAULT_ALERT)
    if isinstance(value, dict):
        out.update({k: v for k,v in value.items() if k in out})
    out['overlay'] = bool(out['overlay'])
    out['sound'] = bool(out['sound'])
    out['video_audio'] = bool(out['video_audio'])
    out['video_only'] = bool(out['video_only'])
    if out['template'] not in TEMPLATES: out['template'] = 'neon'
    if not isinstance(out['accent'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',out['accent']):
        out['accent'] = DEFAULT_ALERT['accent']
    out['duration_ms'] = clamp(out['duration_ms'],1500,30000,4500)
    out['coin_value'] = clamp(out['coin_value'],0,1000000,0)
    out['visual_layout'] = bool(out['visual_layout'])
    from visual_schema import normalize_elements
    out['elements'] = normalize_elements(out['elements'])
    if out['volume'] is not None: out['volume'] = clamp(out['volume'],0,100,70)
    for key in ('icon','message','image_file','video_file','sound_file'):
        out[key] = str(out[key] or '')
    out['icon'] = out['icon'][:12]
    out['message'] = out['message'][:240]
    return out


def normalize_gift(value):
    return normalize_alert(value)


def normalize_coin_rule(value):
    data = value if isinstance(value,dict) else {}
    out = normalize_alert(data)
    out['threshold'] = clamp(data.get('threshold'),1,1000000000,100)
    out['basis'] = data.get('basis') if data.get('basis') in ('stream','gift') else 'stream'
    out['enabled'] = bool(data.get('enabled',True))
    return out


def load_settings():
    if CONFIG_PATH == writable_file('settings.json'):
        migrate_legacy_file('settings.json', CONFIG_PATH)
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding='utf-8-sig'))
        if not isinstance(saved,dict): saved = {}
    except (OSError,ValueError,TypeError): saved = {}
    out = copy.deepcopy(DEFAULTS)
    for key in ('username','language','theme','sound_enabled','volume','sound_file','lan_enabled','lan_ip','hosts_setup_prompted'):
        if key in saved: out[key] = saved[key]
    from leaderboard_settings import normalize_leaderboards
    out['leaderboards'] = normalize_leaderboards(saved.get('leaderboards', {}))
    if out['language'] not in ('ar','en'): out['language'] = 'ar'
    if out['theme'] not in ('dark','light'): out['theme'] = 'dark'
    out['username'] = str(out['username'] or '')
    out['sound_file'] = str(out['sound_file'] or '')
    out['volume'] = clamp(out['volume'],0,100,70)
    out['sound_enabled'] = bool(out['sound_enabled'])
    out['lan_enabled'] = bool(out['lan_enabled'])
    out['hosts_setup_prompted'] = bool(out['hosts_setup_prompted'])
    out['lan_ip'] = str(out['lan_ip'] or '').strip()[:50]
    gifts = saved.get('gifts') if isinstance(saved.get('gifts'),dict) else {}
    names = dict(DEFAULTS['gifts']); names.update(gifts)
    out['gifts'] = {}
    for name in names:
        if not isinstance(name,str) or not name.strip(): continue
        default = DEFAULTS['gifts'].get(name,{})
        override = gifts.get(name,{})
        merged = dict(default)
        if isinstance(override,dict): merged.update(override)
        out['gifts'][name] = normalize_gift(merged)
    from rules_engine import normalize_action, normalize_event
    out['automations_enabled'] = bool(saved.get('automations_enabled', False))
    raw_actions = saved.get('actions', [])
    out['actions'] = [normalize_action(a) for a in raw_actions[:200] if isinstance(a,dict)] if isinstance(raw_actions,list) else []
    raw_events = saved.get('events', [])
    out['events'] = [normalize_event(e) for e in raw_events[:300] if isinstance(e,dict)] if isinstance(raw_events,list) else []
    raw_rules = saved.get('coin_rules')
    out['coin_rules'] = [normalize_coin_rule(r) for r in raw_rules[:100] if isinstance(r,dict)] if isinstance(raw_rules,list) else []
    return out


def get_gift_settings(settings,gift_name):
    for name, data in settings.get('gifts',{}).items():
        if isinstance(name,str) and name.casefold() == str(gift_name).casefold():
            return normalize_gift(data)
    return normalize_gift({})


def save_settings(settings):
    """Atomically replace settings in the writable per-user data directory."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         prefix='settings.', suffix='.tmp',
                                         dir=CONFIG_PATH.parent, delete=False) as fp:
            tmp = Path(fp.name)
            json.dump(settings, fp, indent=2, ensure_ascii=False)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp, CONFIG_PATH)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
