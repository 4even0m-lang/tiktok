"""Offline-safe sample events for the Ven0m test-mode HTTP endpoint.

The simulator never connects to TikTok and does not modify live counters.
Only the loopback /event endpoint accepts these test payloads.
"""
from __future__ import annotations

from typing import Any

KINDS = ('gift', 'follow', 'like', 'comment')


def sample_event(kind: str, *, username: str = 'TestViewer', gift_name: str = 'Rose',
                 quantity: int = 1, coins: int = 1, count: int = 100,
                 comment: str = 'Hello') -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError('Unsupported simulation kind')
    username = str(username).strip()[:80] or 'TestViewer'
    payload = {'type': kind, 'username': username, 'user_id': 'ven0m-simulator',
               'test_mode': True}
    if kind == 'gift':
        payload.update(gift_name=str(gift_name).strip()[:80] or 'Rose',
                       quantity=max(1,min(int(quantity),100000)),
                       coins=max(0,min(int(coins),1_000_000_000)))
    elif kind == 'like':
        payload['count'] = max(1, min(int(count), 1_000_000))
    elif kind == 'comment':
        payload['comment'] = str(comment)[:240]
    return payload
