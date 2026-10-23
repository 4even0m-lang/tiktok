"""Constrain user visual layouts to a predictable, serializable subset.
All canvas element geometry is in virtual coordinates (1280x720).
"""
import re
VALID_TYPES={'text','rect','image','video'}
COLORS=re.compile(r'^#[0-9a-fA-F]{6}$')

def clamp(v,lo,hi,default):
    try:return max(lo,min(hi,int(v)))
    except (ValueError,TypeError,OverflowError):return default

def normalize_elements(data):
    if not isinstance(data,list):return []
    result=[]
    for index,src in enumerate(data[:30]):
        if not isinstance(src,dict) or src.get('type') not in VALID_TYPES:continue
        item={'id':str(src.get('id') or f'layer{index}')[:60],
            'type':src['type'],'x':clamp(src.get('x'),0,1279,80),
            'y':clamp(src.get('y'),0,719,100),
            'w':clamp(src.get('w'),12,1280,320),
            'h':clamp(src.get('h'),12,720,80),
            'text':str(src.get('text') or '')[:300],
            'font':str(src.get('font') or 'Segoe UI')[:60],
            'font_size':clamp(src.get('font_size'),8,160,36),
            'bold':bool(src.get('bold',False)),
            'color':str(src.get('color') or '#FFFFFF'),
            'background':str(src.get('background') or '#202A40'),
            'opacity':clamp(src.get('opacity'),0,100,100),
            'radius':clamp(src.get('radius'),0,100,12),
            'file':str(src.get('file') or '')[:1000],
            'direction':src.get('direction') if src.get('direction') in ('rtl','ltr','auto') else 'rtl',
            'align':src.get('align') if src.get('align') in ('left','right','center') else 'right'}
        if not COLORS.fullmatch(item['color']):item['color']='#FFFFFF'
        if not COLORS.fullmatch(item['background']):item['background']='#202A40'
        result.append(item)
    return result
