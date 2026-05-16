from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.bar import Bar


def test_bar_requires_tz_aware_ts():
    with pytest.raises(ValueError):
        Bar(
            symbol="AAPL",
            freq="1d",
            ts=datetime(2026, 1, 2, 21, 0, 0),  # naive
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("0"),
        )


def test_bar_accepts_utc_close_ts():
    b = Bar(
        symbol="AAPL",
        freq="1d",
        ts=datetime(2026, 1, 2, 21, 0, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
    )
    assert b.ts.tzinfo is not None
