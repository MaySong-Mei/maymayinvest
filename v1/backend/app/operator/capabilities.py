"""Phase-1 capabilities. Each is the SAME function for human and agent callers.

Categories:
  read: get_portfolio, get_open_orders, get_last_price
  act:  submit_order, cancel_order, kill_switch
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.config import get_settings
from app.domain.order import Order, OrderIntent
from app.domain.position import Portfolio
from app.engine.broker_registry import (
    engage_kill_switch,
    get_broker,
    kill_switch_engaged,
)
from app.operator.context import OperatorContext
from app.operator.registry import CapabilityDenied, capability

# ---------- read ----------


@capability(category="read", max_calls_per_minute=120, audits=False)
async def get_portfolio(ctx: OperatorContext) -> Portfolio:
    return await get_broker().get_portfolio()


@capability(category="read", max_calls_per_minute=120, audits=False)
async def get_open_orders(ctx: OperatorContext) -> list[Order]:
    return await get_broker().list_open_orders()


class SymbolReq(BaseModel):
    symbol: str


@capability(category="read", max_calls_per_minute=120, audits=False)
async def get_last_price(ctx: OperatorContext, req: SymbolReq) -> dict:
    price = await get_broker().get_last_price(req.symbol)
    return {"symbol": req.symbol, "price": str(price)}


# ---------- act ----------


@capability(
    category="act",
    max_calls_per_minute=get_settings().global_max_orders_per_min,
    max_notional_per_day=get_settings().global_max_notional_per_day,
    requires_reasoning_for=("agent",),
    dry_run_default_for=("agent",),
)
async def submit_order(ctx: OperatorContext, intent: OrderIntent) -> Order:
    if kill_switch_engaged():
        raise CapabilityDenied("kill switch engaged; orders blocked")
    return await get_broker().submit_order(intent)


class CancelReq(BaseModel):
    client_order_id: UUID


@capability(
    category="act",
    max_calls_per_minute=60,
    requires_reasoning_for=("agent",),
    dry_run_default_for=("agent",),
)
async def cancel_order(ctx: OperatorContext, req: CancelReq) -> dict:
    await get_broker().cancel_order(req.client_order_id)
    return {"client_order_id": str(req.client_order_id), "canceled": True}


@capability(
    category="act",
    max_calls_per_minute=5,
    requires_reasoning_for=("agent",),
    dry_run_default_for=("agent",),
)
async def kill_switch(ctx: OperatorContext) -> dict:
    engage_kill_switch()
    return {"kill_switch": True}


_ = Decimal  # keep import (used implicitly via Pydantic Decimal fields)
