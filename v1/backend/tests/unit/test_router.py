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

from app.domain.bar import Bar
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


def _ctx(session, submitter, bar_provider=None) -> RouterContext:
    return RouterContext(
        session=session,
        submitter=submitter,
        actor_id="test-actor",
        bar_provider=bar_provider,
    )


# ---------- bar generators (for confirmation-gate tests) ----------


def _ts(i: int) -> datetime:
    """Sequential daily timestamps starting 2026-01-01, no month-boundary issues."""
    from datetime import timedelta
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i)


def _bars_breakout(symbol: str = "AAPL", n: int = 35) -> list[Bar]:
    """Generate bars where the latest close exceeds the prior 20-bar high
    on above-average volume — triggers breakout_confirmed.

    n >= 31 so the gate's bar-count check (>=31) passes. We don't need
    ma_cross to fire — breakout alone is enough for confirmation.
    """
    base = Decimal("100.00")
    bars: list[Bar] = []
    for i in range(n - 1):
        bars.append(
            Bar(
                symbol=symbol,
                freq="1d",
                ts=_ts(i),
                open=base,
                high=base + Decimal("0.50"),
                low=base - Decimal("0.50"),
                close=base,
                volume=Decimal("100000"),
            )
        )
    # Last bar: gap up + volume spike
    bars.append(
        Bar(
            symbol=symbol,
            freq="1d",
            ts=_ts(n - 1),
            open=base + Decimal("1.00"),
            high=base + Decimal("2.00"),
            low=base + Decimal("0.80"),
            close=base + Decimal("1.50"),  # > prior 20-bar high of 100.50
            volume=Decimal("150000"),  # > 1.2x average of 100k
        )
    )
    return bars


def _bars_no_confirmation(symbol: str = "AAPL", n: int = 35) -> list[Bar]:
    """Generate bars where neither breakout nor MA cross fires (flat, no
    volume spike, no MA cross)."""
    bars: list[Bar] = []
    base = Decimal("100.00")
    for i in range(n):
        bars.append(
            Bar(
                symbol=symbol,
                freq="1d",
                ts=_ts(i),
                open=base,
                high=base + Decimal("0.10"),
                low=base - Decimal("0.10"),
                close=base,
                volume=Decimal("100000"),
            )
        )
    return bars


def _bar_provider_returning(bars: list[Bar] | None):
    """Build a BarProvider that always returns the given bars list."""
    async def provider(symbol: str) -> list[Bar] | None:
        return bars
    return provider


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
async def test_auto_with_intent_and_confirmation_calls_broker(session):
    """auto + intent + breakout-confirmation passes → broker called."""
    submitter = _FakeSubmitter()
    bp = _bar_provider_returning(_bars_breakout())
    dossier = _dossier("auto", with_intent=True)
    result = await route_decision(_ctx(session, submitter, bar_provider=bp), dossier)

    assert len(submitter.calls) == 1
    intent, reasoning = submitter.calls[0]
    assert intent.symbol == "AAPL"
    assert reasoning == dossier.reasoning_chain

    assert result.mode == "auto"
    assert result.order is not None
    assert result.order.client_order_id == intent.client_order_id
    assert result.pending_signal_id is None, "auto must NOT enqueue a pending_signal"
    assert result.confirmation_blocked is False


@pytest.mark.asyncio
async def test_auto_no_intent_does_not_call_broker(session):
    submitter = _FakeSubmitter()
    result = await route_decision(_ctx(session, submitter), _dossier("auto", with_intent=False))
    assert submitter.calls == []
    assert result.mode == "auto"
    assert result.no_action is True
    assert result.pending_signal_id is None
    assert result.order is None


# ---------- technical confirmation gate (auto mode only) ----------


@pytest.mark.asyncio
async def test_auto_blocks_without_bar_provider(session):
    """auto + intent + NO bar_provider → confirmation blocked, broker NOT called."""
    submitter = _FakeSubmitter()
    result = await route_decision(_ctx(session, submitter), _dossier("auto", with_intent=True))
    assert submitter.calls == [], "auto must NOT call broker without confirmation"
    assert result.confirmation_blocked is True
    assert "no bar provider" in (result.confirmation_reason or "").lower()
    assert result.order is None


@pytest.mark.asyncio
async def test_auto_blocks_when_bars_insufficient(session):
    """auto + intent + bar_provider returns None → blocked."""
    submitter = _FakeSubmitter()
    bp = _bar_provider_returning(None)
    result = await route_decision(
        _ctx(session, submitter, bar_provider=bp), _dossier("auto", with_intent=True)
    )
    assert submitter.calls == []
    assert result.confirmation_blocked is True
    assert "insufficient" in (result.confirmation_reason or "").lower()


@pytest.mark.asyncio
async def test_auto_blocks_when_no_signal_fires(session):
    """auto + intent + flat bars (no breakout, no MA cross) → blocked."""
    submitter = _FakeSubmitter()
    bp = _bar_provider_returning(_bars_no_confirmation())
    result = await route_decision(
        _ctx(session, submitter, bar_provider=bp), _dossier("auto", with_intent=True)
    )
    assert submitter.calls == []
    assert result.confirmation_blocked is True
    assert "no technical confirmation" in (result.confirmation_reason or "").lower()


@pytest.mark.asyncio
async def test_auto_short_side_falls_through_confirmation_gate(session):
    """auto + SELL intent → confirmation gate doesn't block (long-only gate);
    risk gate is the path. v1 is long-only by default so this is a
    contract-level test: shorts don't get filtered by THIS gate."""
    submitter = _FakeSubmitter()
    # No bar_provider — that would block a BUY but should not block a SELL.
    dossier = _dossier("auto", with_intent=True)
    # Mutate the intent's side to SELL
    sell_intent = OrderIntent(
        symbol=dossier.proposed.intent.symbol,
        side=OrderSide.SELL,
        qty=dossier.proposed.intent.qty,
        type=OrderType.MARKET,
    )
    object.__setattr__(dossier.proposed, "intent", sell_intent)
    result = await route_decision(_ctx(session, submitter), dossier)
    assert result.confirmation_blocked is False, (
        "v1's confirmation gate is long-only; SELL must fall through "
        "this gate. (Shorts are not yet supported but the gate must "
        "not falsely claim to govern them.)"
    )
    assert len(submitter.calls) == 1, "SELL went through to broker"


@pytest.mark.asyncio
async def test_confirmation_blocked_auto_does_not_enqueue(session):
    """When auto is blocked by confirmation, no pending_signal is enqueued.
    Same invariant as risk-blocked auto: auto commits to act-or-skip, not
    queue-for-human. The operator emits again next event cycle if confirmation
    arrives."""
    submitter = _FakeSubmitter()
    result = await route_decision(_ctx(session, submitter), _dossier("auto", with_intent=True))
    assert result.confirmation_blocked is True
    assert result.pending_signal_id is None
    stmt = select(PendingSignal)
    rows = (await session.execute(stmt)).scalars().all()
    assert rows == []


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
