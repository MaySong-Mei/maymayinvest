"""Right-side (趋势确认) entry signal primitives.

Pure functions over a list of bars. Strategies compose them.
Inputs are domain `Bar` objects in chronological order with the last bar
being the most recent CLOSED bar (ts < ctx.now enforced upstream).
"""
from __future__ import annotations

from decimal import Decimal
from statistics import mean

from app.domain.bar import Bar


def ma(bars: list[Bar], n: int) -> Decimal | None:
    if len(bars) < n:
        return None
    return Decimal(str(mean(float(b.close) for b in bars[-n:])))


def breakout_confirmed(bars: list[Bar], lookback: int = 20, min_volume_mult: float = 1.2) -> bool:
    """Most recent close above prior `lookback`-bar high AND volume > mult * avg volume."""
    if len(bars) < lookback + 1:
        return False
    last = bars[-1]
    window = bars[-(lookback + 1) : -1]
    prior_high = max(b.high for b in window)
    avg_vol = mean(float(b.volume) for b in window)
    if avg_vol <= 0:
        return last.close > prior_high
    return last.close > prior_high and float(last.volume) >= min_volume_mult * avg_vol


def ma_cross_confirmed(bars: list[Bar], fast: int = 10, slow: int = 30, confirm_bars: int = 2) -> bool:
    """Fast MA above slow MA for at least `confirm_bars` consecutive bars, and that's a fresh state."""
    needed = slow + confirm_bars + 1
    if len(bars) < needed:
        return False
    fast_raw = [ma(bars[: -i] if i else bars, fast) for i in range(confirm_bars + 1, -1, -1)]
    slow_raw = [ma(bars[: -i] if i else bars, slow) for i in range(confirm_bars + 1, -1, -1)]
    if any(v is None for v in fast_raw + slow_raw):
        return False
    fast_vals: list[Decimal] = [v for v in fast_raw if v is not None]
    slow_vals: list[Decimal] = [v for v in slow_raw if v is not None]
    confirmed_recent = all(fast_vals[i] > slow_vals[i] for i in range(-confirm_bars - 1, 0))
    # Require a fresh cross: before the confirm window, fast was <= slow.
    before = fast_vals[-confirm_bars - 2] <= slow_vals[-confirm_bars - 2]
    return confirmed_recent and before
