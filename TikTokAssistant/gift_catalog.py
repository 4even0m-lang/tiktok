"""Best-effort TikTok gift metadata cache, separate from editable settings.

Prices can differ by app/region/time. Unknown coin values remain unknown.
No IP addresses, login tokens or credentials are collected.
"""
import json
import os
import re
import tempfile
import threading
from app_paths import writable_file, migrate_legacy_file
from pathlib import Path

CATALOG_PATH = writable_file('gift_catalog.json')
_LOCK = threading.RLock()
MAX_ITEMS = 1500
GIFT_IMAGES = Path(__file__).resolve().parent / 'assets' / 'gifts'

def _match_key(name):
    return re.sub(r'[^a-z0-9]+', '', str(name).casefold())

def local_gift_images():
    """Offline icon index. Numeric filename prefixes are NOT TikTok gift IDs."""
    out = {}
    if not GIFT_IMAGES.is_dir(): return out
    for image in sorted(GIFT_IMAGES.glob('*.png')):
        name = re.sub(r'^\d+_', '', image.stem).replace('_', ' ').strip()
        key = _match_key(name)
        if key:
            if key in out:
                # Keep distinct user-provided variants available without treating file order as TikTok ID.
                marker=image.stem.split('_',1)[0]
                key=f'{key}:variant:{marker}'
                name=f'{name} [icon {marker}]'
            out[key] = {'name':name, 'image_file':str(image), 'image_url':'', 'coins':0,
                        'id':'', 'updated_from':'local_icons'}
    return out



def _integer(value):
    try: return max(0, min(int(value), 1_000_000_000))
    except (ValueError, TypeError, OverflowError): return 0


def normalize_item(data):
    if not isinstance(data, dict): return None
    name = str(data.get('name') or '').strip()[:100]
    if not name: return None
    gid = str(data.get('id') or '').strip()[:60]
    # No arbitrary resource execution; only explicit HTTPS image URLs.
    url = str(data.get('image_url') or '').strip()[:1000]
    if not url.startswith('https://') or re.search(r'[\s<>"\']',url): url = ''
    result = {'id':gid,'name':name,'coins':_integer(data.get('coins')),
              'image_url':url, 'updated_from':'live'}
    return result


def read_catalog():
    if CATALOG_PATH == writable_file('gift_catalog.json'):
        migrate_legacy_file('gift_catalog.json', CATALOG_PATH)
    try:
        obj = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        if isinstance(obj,dict):
            items = obj.get('items',[])
            overrides = obj.get('overrides',{})
            return {'items':items if isinstance(items,list) else [],
                    'overrides':overrides if isinstance(overrides,dict) else {}}
    except (OSError,ValueError): pass
    return {'items':[], 'overrides':{}}


def _write(obj):
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         prefix='gift_catalog.', suffix='.tmp',
                                         dir=CATALOG_PATH.parent, delete=False) as fp:
            temporary = Path(fp.name)
            json.dump(obj, fp, ensure_ascii=False, indent=2)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(temporary, CATALOG_PATH)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update_catalog(incoming):
    if not isinstance(incoming,list): return 0
    with _LOCK:
        obj = read_catalog()
        by_key = {(str(g.get('id')) if g.get('id') else g.get('name','').casefold()):g
                  for g in obj['items'] if isinstance(g,dict)}
        changes=0
        for item in incoming[:MAX_ITEMS]:
            obj_item = normalize_item(item)
            if obj_item is None: continue
            key = obj_item['id'] or obj_item['name'].casefold()
            old=by_key.get(key)
            if old:
                # Metadata absence should not erase known icon/price.
                if not obj_item['image_url']:obj_item['image_url']=old.get('image_url','')
                if not obj_item['coins']:obj_item['coins']=old.get('coins',0)
            if old != obj_item:
                by_key[key]=obj_item
                changes+=1
        if changes:
            obj['items']=sorted(by_key.values(),key=lambda e:(e['name'].casefold(),e['id']))[:MAX_ITEMS]
            _write(obj)
        return changes


def set_override(name,coins):
    name=str(name).strip()[:100]
    if not name:raise ValueError('Gift name required')
    with _LOCK:
        obj=read_catalog()
        obj['overrides'][name.casefold()]=_integer(coins)
        _write(obj)


def price_for(name,gift_id=''):
    obj=read_catalog()
    key=str(name or '').strip().casefold()
    if key in obj['overrides']:
        return _integer(obj['overrides'][key])
    for g in obj['items']:
        if str(g.get('id'))==str(gift_id) and gift_id or str(g.get('name','')).casefold()==key:
            return _integer(g.get('coins'))
    return 0


def presentation_items():
    """Merge user-supplied local icons with available live metadata; unknown prices remain zero."""
    obj = read_catalog()
    merged = local_gift_images()
    for entry in obj['items']:
        if not isinstance(entry,dict): continue
        name=str(entry.get('name') or '').strip()
        if not name: continue
        key=_match_key(name)
        old=merged.get(key,{})
        merged[key] = dict(old, **entry)
        if old.get('image_file'): merged[key]['image_file']=old['image_file']
    return [dict(entry, coins=price_for(entry.get('name',''),entry.get('id','')),
                 manual=entry.get('name','').casefold() in obj['overrides'])
            for key,entry in sorted(merged.items(),key=lambda pair:pair[1]['name'].casefold())]
