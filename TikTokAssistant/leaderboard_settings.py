def normalize_leaderboards(value):
    source=value if isinstance(value,dict) else {}
    try: top_n=int(source.get('top_n',5))
    except (ValueError,TypeError):top_n=5
    theme=source.get('theme','dark')
    return {'show_likers':bool(source.get('show_likers',True)),
            'show_supporters':bool(source.get('show_supporters',True)),
            'top_n':top_n if top_n in (3,5,10) else 5,
            'theme':theme if theme in ('dark','light','transparent') else 'dark'}
