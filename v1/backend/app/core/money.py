"""Money handling — Decimal everywhere outside vectorbt math kernels.

Invariant: any monetary value crossing a layer boundary (domain ↔ persistence,
domain ↔ API, domain ↔ broker) is Decimal, quantized to PRICE_Q or QTY_Q.
"""
from decimal import ROUND_HALF_EVEN, Decimal

PRICE_Q = Decimal("0.0001")
QTY_Q = Decimal("0.00000001")
NOTIONAL_Q = Decimal("0.01")


def price(x: Decimal | int | float | str) -> Decimal:
    return Decimal(str(x)).quantize(PRICE_Q, rounding=ROUND_HALF_EVEN)


def qty(x: Decimal | int | float | str) -> Decimal:
    return Decimal(str(x)).quantize(QTY_Q, rounding=ROUND_HALF_EVEN)


def notional(x: Decimal | int | float | str) -> Decimal:
    return Decimal(str(x)).quantize(NOTIONAL_Q, rounding=ROUND_HALF_EVEN)
