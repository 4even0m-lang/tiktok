"""In-memory LIVE leaderboards, per-account; no guessed identities or scores."""
from collections import defaultdict

MAX_USERS = 10000
class Leaderboards:
    def __init__(self): self.reset()
    def reset(self):
        self.users={};self.totals={'gift_coins':0,'likes':0}
    def record(self,event):
        typ=event.get('type')
        if typ not in ('gift','like'):return False
        ident=str(event.get('user_id') or event.get('username') or '').strip().casefold()[:100]
        if not ident:return False
        if ident not in self.users and len(self.users)>=MAX_USERS:return False
        row=self.users.setdefault(ident,{'user_id':ident,'name':'','likes':0,'coins':0,'gifts':0})
        row['name']=str(event.get('username') or row['name'] or ident)[:80]
        if typ=='gift':
            row['coins']+=max(0,int(event.get('coins') or 0))
            row['gifts']+=max(1,int(event.get('quantity') or 1))
            self.totals['gift_coins']+=max(0,int(event.get('coins') or 0))
        elif typ=='like':
            amount=max(0,int(event.get('count') or 0))
            if amount<=0:return False
            row['likes']+=amount
            self.totals['likes']+=amount
        return True
    def snapshot(self,limit=10):
        limit=max(1,min(10,int(limit)))
        users=list(self.users.values())
        supporters=sorted((u for u in users if u['gifts']>0),key=lambda u:(-u['coins'],-u['gifts'],u['name']))[:limit]
        likers=sorted((u for u in users if u['likes']>0),key=lambda u:(-u['likes'],u['name']))[:limit]
        return {'type':'leaderboards','supporters':[dict(u) for u in supporters],
                'likers':[dict(u) for u in likers],'totals':dict(self.totals)}
