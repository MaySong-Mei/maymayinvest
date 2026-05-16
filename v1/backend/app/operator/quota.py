"""Per-actor rate + notional quotas. In-process for v1 (single process).

A Redis-backed implementation can drop in by replacing _Bucket without touching
the @capability decorator.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal
from threading import Lock


@dataclass
class _CallBucket:
    window_s: int = 60
    timestamps: deque[float] = field(default_factory=deque)

    def add_and_count(self) -> int:
        now = time.monotonic()
        cutoff = now - self.window_s
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()
        self.timestamps.append(now)
        return len(self.timestamps)


@dataclass
class _NotionalBucket:
    day_epoch: int = 0
    total: Decimal = Decimal("0")

    def add(self, amount: Decimal) -> Decimal:
        today = int(time.time() // 86400)
        if today != self.day_epoch:
            self.day_epoch = today
            self.total = Decimal("0")
        self.total += amount
        return self.total


class QuotaStore:
    def __init__(self) -> None:
        self._calls: dict[tuple[str, str], _CallBucket] = defaultdict(_CallBucket)
        self._notional: dict[str, _NotionalBucket] = defaultdict(_NotionalBucket)
        self._lock = Lock()

    def record_call(self, actor_id: str, capability_name: str) -> int:
        with self._lock:
            return self._calls[(actor_id, capability_name)].add_and_count()

    def record_notional(self, actor_id: str, amount: Decimal) -> Decimal:
        with self._lock:
            return self._notional[actor_id].add(amount)


_store = QuotaStore()


def quota_store() -> QuotaStore:
    return _store
