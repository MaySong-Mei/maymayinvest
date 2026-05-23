"""Decision router invariants — three modes, three behaviors.

Critical guarantees:
  - notify NEVER calls the broker, even when dossier has a real intent
  - dry_run NEVER calls the broker, even when dossier has a real intent
  - auto calls the broker iff intent is set and risk gate passes
  - notify and dry_run enqueue a pending_signal
  - auto NEVER enqueues a pending_signal (executed or blocked, not queued)
  - unknown mode raises ValueError (no silent fallthrough)
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    ProposedOrder,
)
from app.domain.order import Order, OrderIntent, OrderSide, OrderState, OrderType
from app.intel.router import (
    OrderSubmitter,
    RouterContext,
    route_decision,
)
from app.persistence.models import Base, Decision, PendingSignal


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


class _FakeSubmitter(OrderSubmitter):
    """Records calls; returns a synthetic filled Order."""

    def __init__(self):
        self.calls: list[tuple[OrderIntent, str]] = []

    async def submit(self, intent: OrderIntent, reasoning: str) -> Order:
        self.calls.append((intent, reasoning))
        return Order(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            qty=intent.qty,
            type=intent.type,
            tif=intent.tif,
            state=OrderState.FILLED,
            submitted_at=datetime.now(UTC),
            acked_at=datetime.now(UTC),
            closed_at=datetime.now(UTC),
            sub_portfolio_id=intent.sub_portfolio_id,
        )


def _intent(symbol: str = "AAPL", qty: str = "5") -> OrderIntent:
    return OrderIntent(
        symbol=symbol,
        side=OrderSide.BUY,
        qty=Decimal(qty),
        type=OrderType.MARKET,
    )


def _dossier(mode: str, *, with_intent: bool) -> DecisionDossier:
    proposed = (
        ProposedOrder(intent=_intent())
        if with_intent
        else ProposedOrder(intent=None, no_action_reason="hold for confirmation")
    )
    return DecisionDossier(
        actor_id="test-actor",
        actor_type="agent",
        event_id="test:1",
        event_kind="test_synthetic",
        event_summary="test event",
        available_info_snapshot={"x": 1},
        reasoning_chain="test reasoning",
        alternatives_considered=[
            AlternativeConsidered(action="hold", rejected_because="x"),
        ],
        confidence=Decimal("0.6"),
        skills_invoked=[],
        proposed=proposed,
        mode=mode,
        latency_ms=10,
    )


def _ctx(session, submitter) -> RouterContext:
    return RouterContext(session=session, submitter=submitter, actor_id="test-actor")


# ---------- notify ----------


@pytest.mark.asyncio
async def test_notify_with_intent_does_not_call_broker(session):
    submitter = _FakeSubmitter()
    result = await route_decision(_ctx(session, submitter), _dossier("notify", with_intent=True))
    assert submitter.calls == [], "notify must NEVER call the broker, even with intent"
    assert result.mode == "notify"
    assert result.pending_signal_id is not None
    assert result.order is None
    assert result.no_action is False


@pytest.mark.asyncio
async def test_notify_no_intent_still_enqueues(session):
    submitter = _FakeSubmitter()
    result = await route_decision(_ctx(session, submitter), _dossier("notify", with_intent=False))
    assert result.pending_signal_id is not None
    assert result.no_action is True


# ---------- dry_run ----------


@pytest.mark.asyncio
async def test_dry_run_with_intent_does_not_call_broker(session):
    submitter = _FakeSubmitter()
    result = await route_decision(
        _ctx(session, submitter), _dossier("dry_run", with_intent=True)
    )
    assert submitter.calls == [], "dry_run must NEVER call the broker, even with intent"
    assert result.mode == "dry_run"
    assert result.pending_signal_id is not None
    assert result.order is None


@pytest.mark.asyncio
async def test_dry_run_no_intent_enqueues_as_no_action(session):
    submitter = _FakeSubmitter()
    result = await route_decision(
        _ctx(session, submitter), _dossier("dry_run", with_intent=False)
    )
    assert result.pending_signal_id is not None
    assert result.no_action is True


# ---------- auto ----------


@pytest.mark.asyncio
async def test_auto_with_intent_calls_broker(session):
    submitter = _FakeSubmitter()
    dossier = _dossier("auto", with_intent=True)
    result = await route_decision(_ctx(session, submitter), dossier)

    assert len(submitter.calls) == 1
    intent, reasoning = submitter.calls[0]
    assert intent.symbol == "AAPL"
    assert reasoning == dossier.reasoning_chain

    assert result.mode == "auto"
    assert result.order is not None
    assert result.order.client_order_id == intent.client_order_id
    assert result.pending_signal_id is None, "auto must NOT enqueue a pending_signal"


@pytest.mark.asyncio
async def test_auto_no_intent_does_not_call_broker(session):
    submitter = _FakeSubmitter()
    result = await route_decision(_ctx(session, submitter), _dossier("auto", with_intent=False))
    assert submitter.calls == []
    assert result.mode == "auto"
    assert result.no_action is True
    assert result.pending_signal_id is None
    assert result.order is None


# ---------- persistence side-effects ----------


@pytest.mark.asyncio
async def test_all_modes_persist_dossier(session):
    submitter = _FakeSubmitter()
    for mode in ("notify", "dry_run", "auto"):
        dossier = _dossier(mode, with_intent=True)
        await route_decision(_ctx(session, submitter), dossier)

    stmt = select(Decision)
    rows = (await session.execute(stmt)).scalars().all()
    assert len(rows) == 3
    modes = sorted(r.mode for r in rows)
    assert modes == ["auto", "dry_run", "notify"]


@pytest.mark.asyncio
async def test_only_notify_and_dry_run_enqueue(session):
    submitter = _FakeSubmitter()
    for mode in ("notify", "dry_run", "auto"):
        await route_decision(
            _ctx(session, submitter), _dossier(mode, with_intent=True)
        )

    stmt = select(PendingSignal)
    rows = (await session.execute(stmt)).scalars().all()
    queued_modes = sorted(r.mode for r in rows)
    assert queued_modes == ["dry_run", "notify"], (
        "auto must not enqueue; notify and dry_run must"
    )


# ---------- error paths ----------


@pytest.mark.asyncio
async def test_unknown_mode_raises(session):
    submitter = _FakeSubmitter()
    dossier = _dossier("auto", with_intent=True)
    # Bypass pydantic to inject invalid mode (it accepts any str right now)
    object.__setattr__(dossier, "mode", "totally_made_up")
    with pytest.raises(ValueError, match="unknown mode"):
        await route_decision(_ctx(session, submitter), dossier)
