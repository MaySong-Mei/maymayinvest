from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.ids import new_client_order_id
from app.core.time import utcnow


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(StrEnum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"


class OrderState(StrEnum):
    """Lifecycle. Persist transitions BEFORE the broker call where applicable."""

    PENDING_LOCAL = "pending_local"
    SUBMITTED = "submitted"
    ACK = "ack"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class OrderIntent(BaseModel):
    """What a strategy or operator wants the broker to do.

    Carries client_order_id so the broker can dedupe on resubmit.
    """

    model_config = ConfigDict(frozen=True)

    client_order_id: UUID = Field(default_factory=new_client_order_id)
    symbol: str
    side: OrderSide
    qty: Decimal
    type: OrderType = OrderType.MARKET
    limit_price: Decimal | None = None
    tif: TimeInForce = TimeInForce.DAY
    strategy_id: str | None = None
    sub_portfolio_id: str = "default"
    reasoning: str | None = None


class Order(BaseModel):
    """Server-side order record. broker_order_id is filled after submit ack."""

    model_config = ConfigDict(frozen=False)

    client_order_id: UUID
    broker_order_id: str | None = None
    symbol: str
    side: OrderSide
    qty: Decimal
    type: OrderType
    limit_price: Decimal | None = None
    tif: TimeInForce
    state: OrderState = OrderState.PENDING_LOCAL
    submitted_at: datetime | None = None
    acked_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    strategy_id: str | None = None
    sub_portfolio_id: str = "default"


class Fill(BaseModel):
    """A single execution. Append-only. Position is derived from fills."""

    model_config = ConfigDict(frozen=True)

    fill_id: str
    client_order_id: UUID
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    ts: datetime
    sub_portfolio_id: str = "default"
    strategy_id: str | None = None
