"""Backtest demo: synthetic uptrend + downturn, run DualMATrend, print stats.

No Alpaca needed. Use this to sanity-check the backtest runner.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.backtest.runner import run_backtest
from app.domain.bar import Bar
from app.strategy.examples.dual_ma_trend import DualMATrend


def synth_bars(symbol: str, days: int = 180) -> list[Bar]:
    """Three regimes to force a golden + dead cross:
       0..60   sideways around 100 (so fast & slow MAs converge)
       60..120 rally to 160        (fast crosses ABOVE slow -> entry)
       120..180 decline back to 110 (fast crosses BELOW slow -> exit)
    """
    import math

    base = datetime(2025, 1, 1, 21, 0, tzinfo=timezone.utc)
    bars: list[Bar] = []
    for i in range(days):
        if i < 60:
            price = 100 + 2 * math.sin(i / 4)
        elif i < 120:
            price = 100 + (60 * (i - 60) / 60)
        else:
            price = 160 - (50 * (i - 120) / 60)
        ts = base + timedelta(days=i)
        bars.append(
            Bar(
                symbol=symbol,
                freq="1d",
                ts=ts,
                open=Decimal(str(price - 0.5)),
                high=Decimal(str(price + 1.0)),
                low=Decimal(str(price - 1.0)),
                close=Decimal(str(price)),
                volume=Decimal("1000000"),
            )
        )
    return bars


def main():
    symbol = "AAPL"
    bars = synth_bars(symbol, days=180)
    strat = DualMATrend(symbol=symbol, fast=10, slow=30, qty=Decimal("10"))
    result = run_backtest(strat, bars, starting_cash=Decimal("100000"))

    print("=== DualMATrend backtest ===")
    print(f"bars:           {len(bars)}")
    print(f"starting cash:  ${result.starting_cash}")
    print(f"final cash:     ${result.final_cash:.2f}")
    print(f"final equity:   ${result.final_equity:.2f}")
    print(f"fills:          {result.fills}")
    print(f"equity points:  {len(result.equity_curve)}")
    if result.equity_curve:
        print("\nfirst & last equity:")
        print(f"  {result.equity_curve[0].ts.date()}  ${result.equity_curve[0].equity:.2f}")
        print(f"  {result.equity_curve[-1].ts.date()}  ${result.equity_curve[-1].equity:.2f}")


if __name__ == "__main__":
    main()
