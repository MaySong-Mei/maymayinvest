"""Event-driven backtest runner.

For each bar:
  1. Set ctx.now = bar.ts and append the bar (so history() sees it via the
     prior bar's ts < ctx.now rule; the just-added bar is NOT visible until
     the NEXT iteration — this is the look-ahead guard).
  2. Strategy.on_bar(ctx) → submits OrderIntents into the pending queue.
  3. Pending intents fill at the NEXT bar's open via the FillModel (so we
     never use information the strategy couldn't have had).

vectorbt is intentionally NOT used here for the v1 reference path —
event-driven keeps the same-code-live-and-backtest invariant clean.
A vectorbt fast-path can be added later behind the same Strategy contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.backtest.context import BacktestContext
from app.backtest.fill_model import FillModel, RealisticEquityFillModel
from app.domain.bar import Bar
from app.strategy.base import Strategy


@dataclass
class EquityPoint:
    ts: datetime
    equity: Decimal


@dataclass
class BacktestResult:
    starting_cash: Decimal
    final_cash: Decimal
    final_equity: Decimal
    equity_curve: list[EquityPoint] = field(default_factory=list)
    fills: int = 0


def run_backtest(
    strategy: Strategy,
    bars: list[Bar],
    starting_cash: Decimal = Decimal("100000"),
    fill_model: FillModel | None = None,
) -> BacktestResult:
    fill_model = fill_model or RealisticEquityFillModel()
    bars_sorted = sorted(bars, key=lambda b: b.ts)
    by_symbol: dict[str, list[Bar]] = {}
    for b in bars_sorted:
        by_symbol.setdefault(b.symbol, []).append(b)

    ctx = BacktestContext()
    cash = starting_cash
    pending_for_next_open: list = []  # list[OrderIntent]
    result = BacktestResult(starting_cash=starting_cash, final_cash=cash, final_equity=cash)

    for bar in bars_sorted:
        # Step 1: fill any orders queued by the prior bar's strategy decision.
        if pending_for_next_open:
            for intent in pending_for_next_open:
                fr = fill_model.fill(intent, bar)
                if fr is None:
                    continue
                signed_cost = intent.qty * fr.fill_price + fr.fee
                if intent.side.value == "buy":
                    cash -= signed_cost
                else:
                    cash += intent.qty * fr.fill_price - fr.fee
                ctx._apply_fill(intent, fr.fill_price)
                result.fills += 1
            pending_for_next_open = []

        # Step 2: strategy sees state up to and including this bar's CLOSE.
        ctx._set_now(bar.ts)
        ctx._append_bar(bar)
        # _now is set to bar.ts and bar is appended, so history() filters by
        # ts < ctx.now and the just-added bar is excluded — strategy only sees
        # already-closed bars from PRIOR steps. To let it act on this bar's
        # close, we move ctx.now forward by an epsilon equivalent by appending
        # bar first then bumping now: simplest correct approach is to include
        # this bar by advancing now one tick after append.
        # We bump now to just after bar.ts so this bar IS visible to the next on_bar call,
        # but NOT for the fill of orders the strategy submits — those fill at i+1's open.
        from datetime import timedelta

        ctx._set_now(bar.ts + timedelta(microseconds=1))
        strategy.on_bar(ctx)
        for intent in ctx._drain_pending():
            pending_for_next_open.append(intent)

        # Step 3: mark equity at this bar's close.
        mark = bar.close
        position = ctx.position(bar.symbol)
        position_value = (position.qty * mark) if position else Decimal("0")
        result.equity_curve.append(EquityPoint(ts=bar.ts, equity=cash + position_value))

    result.final_cash = cash
    last = result.equity_curve[-1].equity if result.equity_curve else cash
    result.final_equity = last
    return result
