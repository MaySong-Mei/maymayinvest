"""Decision router — dossier → action.

This is the output side of the pipeline. After an EventAnalyzer produces
a DecisionDossier, route_decision(dossier, ctx) dispatches it according
to dossier.mode:

  notify  → persist dossier; enqueue pending_signal for user
  dry_run → persist dossier; if intent set, write reasoning to OrderIntent
            but DO NOT submit to broker; enqueue pending_signal
  auto    → persist dossier; if intent set, run risk gate; if pass, submit
            to broker via OrderSubmitter; DO NOT enqueue (already executed)

Risk gate is currently a stub returning pass for all inputs. TODO before
allowing auto-mode in production: implement risk gate with config-driven
caps (single ≤ $500, daily notional ≤ $2000, max 3 open positions). See
V1_SCOPE.md invariant #9.

OrderSubmitter is injected via RouterContext so the router itself doesn't
import brokers — this preserves the "analyzer/intel layers go through
context, not direct I/O" invariant and keeps router testable with a fake
submitter.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bar import Bar
from app.domain.decision import DecisionDossier
from app.domain.order import Order, OrderIntent, OrderSide
from app.persistence.repositories.decisions import save_dossier
from app.persistence.repositories.pending_signals import enqueue
from app.strategy.signals.trend import breakout_confirmed, ma_cross_confirmed


class OrderSubmitter(Protocol):
    """Whatever can submit an OrderIntent and return an Order.

    In production this is the operator.submit_order capability wrapped to
    expose this minimal interface; in tests, a fake. The router only ever
    sees this Protocol — never imports brokers directly.
    """

    async def submit(self, intent: OrderIntent, reasoning: str) -> Order: ...


# Optional callback to fetch recent bars for the technical confirmation gate.
# Returns the most recent N closed bars in chronological order. None means
# "no bar data available" — confirmation gate must NOT make assumptions in
# that case; it blocks the trade (right-side discipline: no data, no confirm).
BarProvider = Callable[[str], Awaitable[list[Bar] | None]]


@dataclass
class RouterContext:
    session: AsyncSession
    submitter: OrderSubmitter
    actor_id: str  # actor that produced the dossier; carried forward to broker call
    bar_provider: BarProvider | None = None
    # If None: auto-mode trades are blocked at the confirmation gate (no
    # data, no confirmation, right-side discipline rejects). Set in
    # production once a real market-data adapter is wired.


class RouteResult:
    """What happened. Returned for observability + tests."""

    def __init__(
        self,
        mode: str,
        dossier_id,
        pending_signal_id=None,
        order: Order | None = None,
        risk_blocked: bool = False,
        risk_reason: str | None = None,
        confirmation_blocked: bool = False,
        confirmation_reason: str | None = None,
        no_action: bool = False,
    ) -> None:
        self.mode = mode
        self.dossier_id = dossier_id
        self.pending_signal_id = pending_signal_id
        self.order = order
        self.risk_blocked = risk_blocked
        self.risk_reason = risk_reason
        self.confirmation_blocked = confirmation_blocked
        self.confirmation_reason = confirmation_reason
        self.no_action = no_action

    def __repr__(self) -> str:
        bits = [f"mode={self.mode}"]
        if self.no_action:
            bits.append("no_action=True")
        if self.pending_signal_id:
            bits.append(f"pending={self.pending_signal_id}")
        if self.order:
            bits.append(f"order={self.order.client_order_id}")
        if self.risk_blocked:
            bits.append(f"risk_blocked={self.risk_reason!r}")
        if self.confirmation_blocked:
            bits.append(f"confirmation_blocked={self.confirmation_reason!r}")
        return f"RouteResult({', '.join(bits)})"


# ---------- risk gate (stub) ----------


def _check_risk_gate(intent: OrderIntent) -> tuple[bool, str | None]:
    """Pre-execution risk check.

    v1 returns (True, None) for all inputs — risk gate is a separate work
    item. Caps live in config (Settings.global_max_orders_per_min and
    Settings.global_max_notional_per_day are already declared but only
    enforced inside @capability quotas, not at this layer).

    TODO before auto-mode is safe in production:
      - single-order cap (default $500)
      - daily notional cap (default $2000) — query fills today, sum
      - max open positions cap (default 3) — query open orders + positions
      - reject when caps would be breached, return reason
    """
    _ = intent  # unused in stub
    return True, None


# ---------- technical confirmation gate (right-side discipline) ----------


async def _check_technical_confirmation(
    intent: OrderIntent,
    bar_provider: BarProvider | None,
) -> tuple[bool, str | None]:
    """Right-side discipline: only execute long entries that have technical
    confirmation. Auto mode applies this gate AFTER the risk gate passes.

    Pass conditions (any of the following confirms a long entry):
      - breakout_confirmed: recent close above prior 20-bar high with vol >= 1.2x avg
      - ma_cross_confirmed: 10-MA above 30-MA, freshly crossed, confirmed >= 2 bars

    Fail conditions:
      - bar_provider is None: no data, no confirmation → block (right-side
        discipline: refuse to act without confirmation evidence)
      - bar_provider returns None: same as None provider
      - bar_provider returns too few bars: same
      - neither breakout nor MA-cross fires
      - intent.side is SELL: shorts are not handled by this gate in v1. They
        fall through (return ok) — operator is responsible for shorts via
        a separate path. v1 default is long-only per V1_SCOPE.md.

    Returns (passed, reason).
    """
    if intent.side != OrderSide.BUY:
        # v1 is long-only by default. This gate doesn't claim authority over
        # short entries; they fall through. (When v1 adds shorts, a separate
        # gate function for short-side confirmation should be added here.)
        return True, None

    if bar_provider is None:
        return False, (
            "no bar provider configured; right-side discipline requires "
            "confirmation before auto-mode execution"
        )

    bars = await bar_provider(intent.symbol)
    if bars is None or len(bars) < 31:
        # ma_cross_confirmed needs 30 + 2 + 1 = 33 bars worst case; allow 31
        # as the floor since breakout only needs 21 and is the cheaper signal.
        return False, (
            f"insufficient bar data for {intent.symbol} (got "
            f"{0 if bars is None else len(bars)} bars, need >=31); "
            "cannot establish confirmation"
        )

    if breakout_confirmed(bars):
        return True, None
    if ma_cross_confirmed(bars):
        return True, None
    return False, (
        f"no technical confirmation: neither breakout_confirmed nor "
        f"ma_cross_confirmed fires on recent {len(bars)} bars of "
        f"{intent.symbol}"
    )


# ---------- mode handlers ----------


async def _handle_notify(
    ctx: RouterContext, dossier: DecisionDossier
) -> RouteResult:
    """notify: persist dossier, enqueue for user attention. No broker call,
    no order intent realized — even if dossier.proposed.intent is set."""
    await save_dossier(ctx.session, dossier)
    pending = await enqueue(ctx.session, dossier.id, mode="notify")
    return RouteResult(
        mode="notify",
        dossier_id=dossier.id,
        pending_signal_id=pending.id,
        no_action=dossier.proposed.intent is None,
    )


async def _handle_dry_run(
    ctx: RouterContext, dossier: DecisionDossier
) -> RouteResult:
    """dry_run: persist dossier, enqueue for user. NEVER call the broker.

    If the dossier has an OrderIntent, it sits in the dossier but no order
    is submitted. The user can promote later → at promotion time, the
    pending_signals.promote() repo records which order was actually
    submitted (the promotion path is handled by a separate capability,
    not by the router).
    """
    await save_dossier(ctx.session, dossier)
    pending = await enqueue(ctx.session, dossier.id, mode="dry_run")
    return RouteResult(
        mode="dry_run",
        dossier_id=dossier.id,
        pending_signal_id=pending.id,
        no_action=dossier.proposed.intent is None,
    )


async def _handle_auto(
    ctx: RouterContext, dossier: DecisionDossier
) -> RouteResult:
    """auto: persist dossier, check risk gate, submit to broker if pass.

    Does NOT enqueue a pending_signal — auto means executed (or blocked
    by risk gate). The dashboard finds auto-executed decisions by joining
    decisions table on orders.client_order_id.
    """
    await save_dossier(ctx.session, dossier)

    if dossier.proposed.intent is None:
        # Auto mode with explicit no-action is unusual but valid; record it.
        return RouteResult(
            mode="auto",
            dossier_id=dossier.id,
            no_action=True,
        )

    intent = dossier.proposed.intent
    ok, reason = _check_risk_gate(intent)
    if not ok:
        return RouteResult(
            mode="auto",
            dossier_id=dossier.id,
            risk_blocked=True,
            risk_reason=reason,
        )

    # Right-side discipline: only execute long entries that have technical
    # confirmation on recent bars. Risk gate first (cheap), then confirmation
    # (requires bar data). Failed confirmation does NOT enqueue a
    # pending_signal — auto-mode commits to "act now or not at all"; if
    # confirmation isn't there, the operator can re-emit later (next event
    # cycle) once it is.
    conf_ok, conf_reason = await _check_technical_confirmation(
        intent, ctx.bar_provider
    )
    if not conf_ok:
        return RouteResult(
            mode="auto",
            dossier_id=dossier.id,
            confirmation_blocked=True,
            confirmation_reason=conf_reason,
        )

    # Submit. The OrderSubmitter is responsible for audit + capability
    # routing (it wraps operator.submit_order in production).
    reasoning = dossier.reasoning_chain or "auto-mode submission from dossier"
    order = await ctx.submitter.submit(intent, reasoning=reasoning)
    return RouteResult(
        mode="auto",
        dossier_id=dossier.id,
        order=order,
    )


# ---------- entrypoint ----------


_HANDLERS = {
    "notify": _handle_notify,
    "dry_run": _handle_dry_run,
    "auto": _handle_auto,
}


async def route_decision(
    ctx: RouterContext, dossier: DecisionDossier
) -> RouteResult:
    """Single entrypoint. dossier.mode determines dispatch."""
    handler = _HANDLERS.get(dossier.mode)
    if handler is None:
        raise ValueError(
            f"route_decision: unknown mode {dossier.mode!r}; "
            f"expected one of {sorted(_HANDLERS)}"
        )
    return await handler(ctx, dossier)
