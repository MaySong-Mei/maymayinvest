"""Phase-1 capabilities. Each is the SAME function for human and agent callers.

Categories:
  read: get_portfolio, get_open_orders, get_last_price
  act:  submit_order, cancel_order, kill_switch, promote_signal
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
from app.persistence.models import Decision, PendingSignal
from app.persistence.repositories.pending_signals import promote as _promote_signal_row

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


# ---------- promotion (bridges router pending_signals to actual submission) ----------


class PromoteSignalReq(BaseModel):
    pending_signal_id: UUID


@capability(
    category="act",
    max_calls_per_minute=30,
    max_notional_per_day=get_settings().global_max_notional_per_day,
    requires_reasoning_for=("agent",),
    dry_run_default_for=("agent",),
)
async def promote_signal(ctx: OperatorContext, req: PromoteSignalReq) -> Order:
    """Promote a pending_signal (notify or dry_run) to a real broker submission.

    Reads the linked DecisionDossier's `proposed.intent`, submits it to the
    broker, updates pending_signals.status -> 'promoted' with the resulting
    client_order_id.

    Errors (each raises CapabilityDenied):
      - pending_signal not found
      - pending_signal already in terminal state (promoted/dismissed/expired)
      - linked dossier has null intent (no-action signal can't be promoted)
      - kill switch engaged

    Audit:
      - The capability decorator records this invocation in `actions` with
        outcome 'ok' / 'denied' / 'error' as usual.
      - On success, pending_signals row gains resulting_client_order_id, so
        the audit trail joins forward to fills.
    """
    if kill_switch_engaged():
        raise CapabilityDenied("kill switch engaged; promotion blocked")

    signal = await ctx.session.get(PendingSignal, req.pending_signal_id)
    if signal is None:
        raise CapabilityDenied(
            f"pending_signal {req.pending_signal_id} not found"
        )
    if signal.status != "pending":
        raise CapabilityDenied(
            f"pending_signal {req.pending_signal_id} is in terminal status "
            f"{signal.status!r}; cannot promote"
        )

    decision = await ctx.session.get(Decision, signal.dossier_id)
    if decision is None:
        raise CapabilityDenied(
            f"dossier {signal.dossier_id} referenced by pending_signal "
            f"{req.pending_signal_id} not found"
        )

    proposed = decision.proposed or {}
    intent_dict = proposed.get("intent")
    if intent_dict is None:
        raise CapabilityDenied(
            f"pending_signal {req.pending_signal_id} has no order intent "
            f"(no_action dossier); nothing to promote"
        )

    intent = OrderIntent.model_validate(intent_dict)
    order = await get_broker().submit_order(intent)

    # Transition pending_signals: pending -> promoted, record submitted order
    await _promote_signal_row(
        ctx.session,
        signal_id=signal.id,
        actor_id=ctx.actor_id,
        resulting_client_order_id=intent.client_order_id,
    )

    return order
