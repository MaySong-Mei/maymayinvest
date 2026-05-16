"""Strategy ABC + Context protocol — the single contract for backtest AND live.

Hard invariants (enforced by import-linter + tests):
  - Strategy imports only `app.domain` and `app.strategy.signals`. Never
    `app.backtest`, `app.engine`, or anything I/O.
  - `Context.history(symbol, freq, lookback)` only returns rows with
    ts < ctx.now. Look-ahead is an assertion failure in BacktestContext.
  - `universe` is a function of `as_of`, not a static list.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Literal, Protocol

from app.domain.bar import Bar
from app.domain.order import OrderIntent
from app.domain.position import Position

Horizon = Literal["intraday", "swing", "position", "long_term"]


class Context(Protocol):
    @property
    def now(self) -> datetime: ...

    def history(self, symbol: str, freq: str, lookback: int) -> list[Bar]: ...
    def position(self, symbol: str) -> Position | None: ...
    def submit(self, intent: OrderIntent) -> None: ...


UniverseFn = Callable[[datetime], list[str]]


class Strategy(ABC):
    horizon: Horizon = "swing"
    sub_portfolio_id: str = "default"
    universe: UniverseFn = staticmethod(lambda _ts: [])

    @abstractmethod
    def on_bar(self, ctx: Context) -> None: ...
