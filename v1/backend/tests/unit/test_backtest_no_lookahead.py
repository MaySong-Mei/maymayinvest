from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.backtest.context import BacktestContext
from app.domain.bar import Bar


def _bar(ts, close):
    return Bar(
        symbol="X",
        freq="1d",
        ts=ts,
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("1"),
    )


def test_history_excludes_bars_with_ts_at_or_after_now():
    ctx = BacktestContext()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    # Append three bars at days 0, 1, 2.
    for i in range(3):
        ctx._append_bar(_bar(base + timedelta(days=i), 100 + i))

    # Strategy is "called for" day 2. ctx.now must be strictly greater than
    # the bar.ts they're allowed to see, mirroring how the runner sets it.
    ctx._set_now(base + timedelta(days=2, microseconds=1))
    visible = ctx.history("X", "1d", 10)
    # All three bars whose ts < now are visible.
    assert len(visible) == 3

    # Move now back to the second bar's close (microsecond before).
    ctx._set_now(base + timedelta(days=1))
    visible = ctx.history("X", "1d", 10)
    # Only the day-0 bar is strictly before now.
    assert len(visible) == 1
    assert visible[0].close == Decimal("100")
