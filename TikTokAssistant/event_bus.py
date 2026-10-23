"""Ven0m 6.3 core event contract and bounded local delivery bus.

All future providers should emit this provider-neutral shape. This module
never connects to external services and does not require PySide6.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
import asyncio
import inspect
import logging

ALLOWED_TYPES = frozenset({'gift', 'follow', 'like', 'comment', 'share'})


@dataclass(frozen=True)
class LiveEvent:
    sequence: int
    kind: str
    username: str
    payload: dict[str, Any]
    simulated: bool
    created_at: str


class EventBus:
    """In-process event fan-out for local features/analytics.

    Per-handler failures are isolated. No disk/network operations are implied.
    Event IDs supplied by a future connector can be deduplicated at the source.
    """
    def __init__(self, *, history_limit: int = 250):
        if not 1 <= history_limit <= 10000:
            raise ValueError('Invalid history limit')
        self._history = deque(maxlen=history_limit)
        self._subscribers: list[Callable] = []
        self._sequence = 0

    def subscribe(self, listener: Callable):
        if listener not in self._subscribers:
            self._subscribers.append(listener)
        return lambda: self.unsubscribe(listener)

    def unsubscribe(self, listener: Callable) -> None:
        if listener in self._subscribers:
            self._subscribers.remove(listener)

    async def publish(self, payload: dict, *, simulated: bool = False) -> LiveEvent:
        if not isinstance(payload, dict) or payload.get('type') not in ALLOWED_TYPES:
            raise ValueError('Unsupported event')
        self._sequence += 1
        event = LiveEvent(
            sequence=self._sequence,
            kind=payload['type'],
            username=str(payload.get('username') or 'Viewer')[:80],
            payload=dict(payload),
            simulated=bool(simulated),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._history.append(event)
        for callback in tuple(self._subscribers):
            try:
                result = callback(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logging.exception('Ven0m event listener failed; subsequent listeners still run')
        return event

    @property
    def sequence(self) -> int:
        return self._sequence

    def recent(self, *, count: int = 50) -> list[LiveEvent]:
        return list(self._history)[-max(0, min(count, 250)):]

    def reset(self) -> None:
        self._history.clear()
