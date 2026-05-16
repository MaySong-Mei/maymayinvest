"""MarketDataProvider protocol — historical + realtime market data sources.

Invariant every provider MUST uphold:
  Bar.ts represents the BAR CLOSE in UTC. Provider-specific conventions are
  normalized at this boundary. If a provider cannot guarantee the convention,
  the adapter must raise on construction.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from app.domain.bar import Bar


class MarketDataProvider(Protocol):
    name: str

    async def historical_bars(
        self, symbol: str, freq: str, start: datetime, end: datetime
    ) -> list[Bar]: ...

    async def stream_bars(self, symbols: list[str], freq: str) -> AsyncIterator[Bar]: ...
