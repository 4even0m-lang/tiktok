"""Ven0m 6.3: deterministic *foundation* for exclusive cross-screen playback.

This is a pure scheduler. Integration with browser/WebSocket acknowledgments
belongs to v6.4, so this file must not be described as active overlay locking.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any
import time
import uuid


@dataclass(frozen=True)
class Playback:
    id: str
    screen: str
    payload: dict[str, Any]
    max_duration_ms: int


class PlaybackCoordinator:
    """One active playback globally; round-robin fairness per screen.

    The UI/server must call `take_next` and `complete` when the browser confirms
    finish, and `expire` when an acknowledgement is missing. Until integrated,
    this class does not change existing HTML overlay behavior.
    """
    def __init__(self, *, default_capacity: int = 5, clock=None):
        if not 1 <= default_capacity <= 100:
            raise ValueError('capacity outside 1..100')
        self.default_capacity = default_capacity
        self._clock = clock or time.monotonic
        self._queues: dict[str, deque[Playback]] = {}
        self._capacity: dict[str, int] = {}
        self._rotation: deque[str] = deque()
        self.active: Playback | None = None
        self.deadline: float | None = None

    def register(self, screen: str, *, capacity: int | None = None):
        if not screen or len(screen) > 64:
            raise ValueError('Invalid screen identifier')
        cap = self.default_capacity if capacity is None else capacity
        if not isinstance(cap, int) or not 1 <= cap <= 100:
            raise ValueError('capacity outside 1..100')
        if screen not in self._queues:
            self._queues[screen] = deque()
            self._rotation.append(screen)
        self._capacity[screen] = cap

    def enqueue(self, screen: str, payload: dict, *, duration_ms: int = 4500) -> Playback | None:
        if screen not in self._queues:
            raise KeyError('Unregistered screen')
        if not isinstance(payload, dict):
            raise TypeError('payload must be a dictionary')
        if not isinstance(duration_ms, int) or not 250 <= duration_ms <= 30000:
            raise ValueError('Invalid duration')
        queue = self._queues[screen]
        if len(queue) >= self._capacity[screen]:
            return None  # Caller can record a dropped/overflow event.
        task = Playback(uuid.uuid4().hex, screen, dict(payload), duration_ms)
        queue.append(task)
        return task

    def take_next(self) -> Playback | None:
        if self.active is not None:
            return None
        for _ in range(len(self._rotation)):
            screen = self._rotation[0]
            self._rotation.rotate(-1)
            if self._queues[screen]:
                self.active = self._queues[screen].popleft()
                # 2s grace for DOM closing transition and acknowledgements.
                self.deadline = self._clock() + self.active.max_duration_ms / 1000 + 2
                return self.active
        return None

    def complete(self, playback_id: str) -> bool:
        if self.active is None or self.active.id != playback_id:
            return False  # Reject stale acknowledgements.
        self.active = None
        self.deadline = None
        return True

    def expire(self) -> bool:
        if self.active is not None and self.deadline is not None and self._clock() >= self.deadline:
            self.active = None
            self.deadline = None
            return True
        return False

    def unregister(self, screen: str) -> None:
        self._queues.pop(screen, None)
        self._capacity.pop(screen, None)
        try:
            self._rotation.remove(screen)
        except ValueError:
            pass
        if self.active and self.active.screen == screen:
            self.complete(self.active.id)

    def status(self) -> dict:
        return {
            'active_screen': self.active.screen if self.active else None,
            'pending': {screen: len(queue) for screen, queue in self._queues.items()},
            'capacity': dict(self._capacity),
        }
