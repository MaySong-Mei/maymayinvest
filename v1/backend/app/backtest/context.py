"""BacktestContext — implements strategy.Context for event-driven backtests.

Enforces no-look-ahead via an assertion: history() returns only bars whose
ts < ctx.now. Tests cover the violation case.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from app.domain.bar import Bar
from app.domain.order import OrderIntent
from app.domain.position import Position


class BacktestContext:
    """Mutated by the runner as it walks the bar timeline."""

    def __init__(self) -> None:
        self._now: datetime | None = None
        self._bars_by_symbol: dict[str, list[Bar]] = defaultdict(list)
        self._positions: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        self._avg_cost: dict[str, Decimal] = {}
        self._pending: list[OrderIntent] = []

    @property
    def now(self) -> datetime:
        assert self._now is not None, "runner must set ctx.now before each on_bar"
        return self._now

    def _set_now(self, ts: datetime) -> None:
        self._now = ts

    def _append_bar(self, bar: Bar) -> None:
        self._bars_by_symbol[bar.symbol].append(bar)

    def history(self, symbol: str, freq: str, lookback: int) -> list[Bar]:
        all_bars = self._bars_by_symbol.get(symbol, [])
        # Look-ahead guard: only bars strictly older than now are visible.
        visible = [b for b in all_bars if b.ts < self.now]
        assert all(b.ts < self.now for b in visible), "BacktestContext.history leaked future bars"
        return visible[-lookback:] if lookback > 0 else visible

    def position(self, symbol: str) -> Position | None:
        q = self._positions[symbol]
        if q == 0:
            return None
        return Position(symbol=symbol, qty=q, avg_cost=self._avg_cost.get(symbol, Decimal("0")))

    def submit(self, intent: OrderIntent) -> None:
        self._pending.append(intent)

    def _drain_pending(self) -> list[OrderIntent]:
        out = self._pending
        self._pending = []
        return out

    def _apply_fill(self, intent: OrderIntent, fill_price: Decimal) -> None:
        signed = intent.qty if intent.side.value == "buy" else -intent.qty
        cur = self._positions[intent.symbol]
        new = cur + signed
        if intent.side.value == "buy":
            prev_cost = self._avg_cost.get(intent.symbol, Decimal("0"))
            total = (cur * prev_cost) + (intent.qty * fill_price)
            self._avg_cost[intent.symbol] = (total / new) if new != 0 else Decimal("0")
        elif new == 0:
            self._avg_cost.pop(intent.symbol, None)
        self._positions[intent.symbol] = new
