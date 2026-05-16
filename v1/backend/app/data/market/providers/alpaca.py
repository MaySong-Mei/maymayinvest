"""Alpaca market data provider.

Bar timestamp convention: Alpaca returns bars with `timestamp` = bar OPEN.
We normalize to CLOSE by adding the bar duration. Rate limit (free tier =
200 req/min for stocks) is encoded in the constructor, not scattered sleeps.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from app.core.config import get_settings
from app.core.time import ensure_utc
from app.domain.bar import Bar

_FREQ_TIMEDELTA = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}


def _freq_to_alpaca(freq: str):
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    return {
        "1m": TimeFrame(1, TimeFrameUnit.Minute),
        "5m": TimeFrame(5, TimeFrameUnit.Minute),
        "15m": TimeFrame(15, TimeFrameUnit.Minute),
        "1h": TimeFrame(1, TimeFrameUnit.Hour),
        "1d": TimeFrame(1, TimeFrameUnit.Day),
    }[freq]


class AlpacaMarketDataProvider:
    name = "alpaca"

    def __init__(self, req_per_min: int = 180) -> None:
        self._req_interval = 60.0 / max(req_per_min, 1)
        self._last_call = 0.0
        self._client: Any = None
        self._lock = asyncio.Lock()

    async def _throttle(self) -> None:
        async with self._lock:
            loop = asyncio.get_event_loop()
            now = loop.time()
            wait = self._req_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = loop.time()

    def _client_lazy(self):
        if self._client is None:
            from alpaca.data.historical import StockHistoricalDataClient

            s = get_settings()
            self._client = StockHistoricalDataClient(
                api_key=s.alpaca_api_key.get_secret_value(),
                secret_key=s.alpaca_api_secret.get_secret_value(),
            )
        return self._client

    async def historical_bars(
        self, symbol: str, freq: str, start: datetime, end: datetime
    ) -> list[Bar]:
        from alpaca.data.requests import StockBarsRequest

        if freq not in _FREQ_TIMEDELTA:
            raise ValueError(f"unsupported freq: {freq}")
        await self._throttle()
        client = self._client_lazy()
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=_freq_to_alpaca(freq),
            start=ensure_utc(start),
            end=ensure_utc(end),
            feed=get_settings().alpaca_data_feed,
        )
        resp = client.get_stock_bars(req)
        raw = resp[symbol] if hasattr(resp, "__getitem__") else resp.data.get(symbol, [])
        delta = _FREQ_TIMEDELTA[freq]
        out: list[Bar] = []
        for r in raw:
            # Alpaca's timestamp is bar OPEN; normalize to CLOSE.
            close_ts = ensure_utc(r.timestamp) + delta
            out.append(
                Bar(
                    symbol=symbol,
                    freq=freq,
                    ts=close_ts,
                    open=Decimal(str(r.open)),
                    high=Decimal(str(r.high)),
                    low=Decimal(str(r.low)),
                    close=Decimal(str(r.close)),
                    volume=Decimal(str(r.volume or 0)),
                )
            )
        return out

    async def stream_bars(self, symbols: list[str], freq: str) -> AsyncIterator[Bar]:
        # WebSocket streaming wired in phase 1.5; intentionally a stub here.
        raise NotImplementedError("realtime streaming arrives in phase 1.5")
        yield  # type: ignore[unreachable]
