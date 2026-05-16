from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TaxLot(BaseModel):
    """Open lot — one row per buy that hasn't been fully sold. FIFO by default."""

    model_config = ConfigDict(frozen=False)

    lot_id: str
    symbol: str
    qty_open: Decimal
    cost_basis: Decimal  # per-unit, includes proportional fees
    acquired_at_fill_id: str
    sub_portfolio_id: str = "default"


class Position(BaseModel):
    """Aggregated view over open tax lots. Materialized; never written directly."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    qty: Decimal
    avg_cost: Decimal
    sub_portfolio_id: str = "default"


class Portfolio(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_id: str
    base_currency: str = "USD"
    cash: Decimal = Field(default=Decimal("0"))
    positions: list[Position] = Field(default_factory=list)
    equity: Decimal | None = None  # cash + sum(mark_to_market) when quotes available
