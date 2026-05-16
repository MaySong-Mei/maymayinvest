"""Reference strategy: right-side dual-MA trend follower.

Long-only. Enter when ma_cross_confirmed fires; exit when fast MA crosses
back below slow MA. Demonstrates the same-code-backtest-and-live contract.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.domain.order import OrderIntent, OrderSide
from app.strategy.base import Strategy
from app.strategy.signals.trend import ma, ma_cross_confirmed


class DualMATrend(Strategy):
    horizon = "swing"
    sub_portfolio_id = "trend_swing"

    def __init__(self, symbol: str = "AAPL", fast: int = 10, slow: int = 30, qty: Decimal = Decimal("10")):
        self.symbol = symbol
        self.fast = fast
        self.slow = slow
        self.qty = qty
        self.universe = staticmethod(lambda _ts: [symbol])  # type: ignore[assignment]

    def on_bar(self, ctx) -> None:
        bars = ctx.history(self.symbol, "1d", lookback=self.slow + 5)
        if len(bars) < self.slow + 2:
            return

        pos = ctx.position(self.symbol)
        in_position = pos is not None and pos.qty > 0

        if not in_position and ma_cross_confirmed(bars, fast=self.fast, slow=self.slow):
            ctx.submit(
                OrderIntent(
                    symbol=self.symbol,
                    side=OrderSide.BUY,
                    qty=self.qty,
                    strategy_id="dual_ma_trend",
                    sub_portfolio_id=self.sub_portfolio_id,
                    reasoning="ma_cross_confirmed long entry",
                )
            )
            return

        if in_position:
            fast_v = ma(bars, self.fast)
            slow_v = ma(bars, self.slow)
            if fast_v is not None and slow_v is not None and fast_v < slow_v:
                ctx.submit(
                    OrderIntent(
                        symbol=self.symbol,
                        side=OrderSide.SELL,
                        qty=pos.qty,
                        strategy_id="dual_ma_trend",
                        sub_portfolio_id=self.sub_portfolio_id,
                        reasoning="ma cross down — close",
                    )
                )

    # Touches forward-ref so import-linter sees datetime usage at runtime.
    _t: datetime | None = None
