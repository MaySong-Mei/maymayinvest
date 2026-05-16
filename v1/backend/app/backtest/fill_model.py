"""Pluggable fill models for backtests.

Default = RealisticEquityFillModel: fills at the NEXT bar's open + bps slippage
+ a commission field (currently $0 for Alpaca but the field exists).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.domain.bar import Bar
from app.domain.order import OrderIntent, OrderSide


@dataclass(frozen=True)
class FillResult:
    fill_price: Decimal
    fee: Decimal


class FillModel(Protocol):
    def fill(self, intent: OrderIntent, next_bar: Bar) -> FillResult | None: ...


@dataclass(frozen=True)
class RealisticEquityFillModel:
    slippage_bps: Decimal = Decimal("5")        # 5 basis points
    commission_per_share: Decimal = Decimal("0")
    commission_min: Decimal = Decimal("0")

    def fill(self, intent: OrderIntent, next_bar: Bar) -> FillResult | None:
        slip = (Decimal(next_bar.open) * self.slippage_bps) / Decimal("10000")
        if intent.side == OrderSide.BUY:
            price = Decimal(next_bar.open) + slip
        else:
            price = Decimal(next_bar.open) - slip
        fee = max(self.commission_min, self.commission_per_share * Decimal(intent.qty))
        return FillResult(fill_price=price, fee=fee)
