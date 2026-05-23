"""promote_signal capability + OperatorOrderSubmitter adapter tests.

Critical invariants:
  - promote_signal succeeds only when: pending exists, is pending state,
    linked dossier has non-null intent, kill switch off
  - promote_signal updates pending row to status='promoted' with
    resulting_client_order_id set
  - promote_signal records an actions audit row
  - OperatorOrderSubmitter routes through the capability with execute=True
  - submit_order audit row is written by the adapter call (not by the
    router) — i.e., audit chain is operator-side
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.brokers.paper import PaperBroker
from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    ProposedOrder,
)
from app.domain.order import OrderIntent, OrderSide, OrderState, OrderType
from app.engine.broker_registry import (
    engage_kill_switch,
    reset_kill_switch,
    set_broker,
)
from app.intel.adapters import OperatorOrderSubmitter
from app.operator.capabilities import PromoteSignalReq, promote_signal
from app.operator.context import OperatorContext
from app.operator.registry import CapabilityDenied
from app.persistence.models import Action, Base
from app.persistence.repositories.decisions import save_dossier
from app.persistence.repositories.pending_signals import dismiss, enqueue


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


@pytest.fixture(autouse=True)
def fresh_broker():
    """Each test gets a fresh in-memory PaperBroker; reset kill switch."""
    pb = PaperBroker()
    pb.set_last_price("AAPL", Decimal("220.50"))
    pb.set_last_price("MSFT", Decimal("420.00"))
    set_broker(pb)
    reset_kill_switch()
    yield
    reset_kill_switch()


def _intent(symbol: str = "AAPL", qty: str = "5") -> OrderIntent:
    return OrderIntent(
        symbol=symbol,
        side=OrderSide.BUY,
        qty=Decimal(qty),
        type=OrderType.MARKET,
    )


async def _seed_pending(session, *, with_intent: bool = True):
    """Create a dossier + pending_signal pair; return both."""
    intent = _intent() if with_intent else None
    proposed = (
        ProposedOrder(intent=intent)
        if intent
        else ProposedOrder(intent=None, no_action_reason="hold for confirmation")
    )
    dossier = DecisionDossier(
        actor_id="test-analyzer",
        event_id="test:1",
        event_kind="test_synthetic",
        event_summary="test event",
        available_info_snapshot={},
        reasoning_chain="t",
        alternatives_considered=[
            AlternativeConsidered(action="hold", rejected_because="x"),
        ],
        confidence=Decimal("0.6"),
        skills_invoked=[],
        proposed=proposed,
        mode="dry_run",
    )
    await save_dossier(session, dossier)
    signal = await enqueue(session, dossier.id, mode="dry_run")
    return dossier, signal


# ---------- promote_signal happy path ----------


@pytest.mark.asyncio
async def test_promote_signal_submits_order_and_updates_status(session):
    """Happy path: pending signal with intent gets promoted, broker fills, status->promoted."""
    dossier, signal = await _seed_pending(session, with_intent=True)
    expected_intent_id = dossier.proposed.intent.client_order_id

    ctx = OperatorContext(
        actor_id="me",
        actor_type="user",
        session=session,
        reasoning="manual promotion in test",
    )
    order = await promote_signal(ctx, PromoteSignalReq(pending_signal_id=signal.id))

    # broker actually submitted the order with the dossier's client_order_id
    assert order.client_order_id == expected_intent_id
    assert order.state == OrderState.FILLED

    # pending_signal moved to promoted with resulting_client_order_id linked
    refreshed = await session.get(type(signal), signal.id)
    assert refreshed is not None
    assert refreshed.status == "promoted"
    assert refreshed.resulting_client_order_id == expected_intent_id

    # audit row written
    actions = (await session.execute(select(Action).where(Action.capability == "promote_signal"))).scalars().all()
    assert len(actions) == 1
    assert actions[0].outcome_status == "ok"
    assert actions[0].actor_id == "me"


# ---------- promote_signal denied paths ----------


@pytest.mark.asyncio
async def test_promote_signal_rejects_unknown_signal_id(session):
    ctx = OperatorContext(actor_id="me", actor_type="user", session=session)
    with pytest.raises(CapabilityDenied, match="not found"):
        await promote_signal(ctx, PromoteSignalReq(pending_signal_id=uuid4()))


@pytest.mark.asyncio
async def test_promote_signal_rejects_terminal_signal(session):
    """A signal already dismissed cannot be re-promoted."""
    _, signal = await _seed_pending(session, with_intent=True)
    await dismiss(session, signal.id, actor_id="me", reason="changed mind")

    ctx = OperatorContext(actor_id="me", actor_type="user", session=session)
    with pytest.raises(CapabilityDenied, match="terminal status"):
        await promote_signal(ctx, PromoteSignalReq(pending_signal_id=signal.id))


@pytest.mark.asyncio
async def test_promote_signal_rejects_null_intent_dossier(session):
    """no-action dossier has no intent; nothing to promote."""
    _, signal = await _seed_pending(session, with_intent=False)
    ctx = OperatorContext(actor_id="me", actor_type="user", session=session)
    with pytest.raises(CapabilityDenied, match="no order intent"):
        await promote_signal(ctx, PromoteSignalReq(pending_signal_id=signal.id))


@pytest.mark.asyncio
async def test_promote_signal_rejects_when_kill_switch_engaged(session):
    _, signal = await _seed_pending(session, with_intent=True)
    engage_kill_switch()
    ctx = OperatorContext(actor_id="me", actor_type="user", session=session)
    with pytest.raises(CapabilityDenied, match="kill switch"):
        await promote_signal(ctx, PromoteSignalReq(pending_signal_id=signal.id))


@pytest.mark.asyncio
async def test_promote_signal_agent_without_reasoning_is_denied(session):
    """Agent must provide reasoning for any act capability. Inherited from
    the @capability decorator's reasoning gate — verified here too at the
    promote_signal level since it's a new capability."""
    _, signal = await _seed_pending(session, with_intent=True)
    ctx = OperatorContext(
        actor_id="agent-1",
        actor_type="agent",
        session=session,
        reasoning="",  # empty
    )
    with pytest.raises(CapabilityDenied, match="requires non-empty reasoning"):
        await promote_signal(
            ctx, PromoteSignalReq(pending_signal_id=signal.id), execute=True
        )

    # The denial should still be audited (per invariant in earlier work).
    actions = (await session.execute(select(Action).where(Action.capability == "promote_signal"))).scalars().all()
    assert len(actions) == 1
    assert actions[0].outcome_status == "denied"


# ---------- OperatorOrderSubmitter adapter ----------


@pytest.mark.asyncio
async def test_operator_order_submitter_routes_through_capability(session):
    """OperatorOrderSubmitter should call submit_order through the capability
    wrapper with execute=True, producing an actions audit row for submit_order."""
    adapter = OperatorOrderSubmitter(
        session=session,
        actor_id="auto-router",
        actor_type="agent",
    )

    intent = _intent("AAPL", "3")
    order = await adapter.submit(intent, reasoning="auto-mode test")

    assert order.client_order_id == intent.client_order_id
    assert order.state == OrderState.FILLED

    # audit row for submit_order, not promote_signal
    actions = (await session.execute(select(Action).where(Action.capability == "submit_order"))).scalars().all()
    assert len(actions) == 1
    assert actions[0].outcome_status == "ok"
    assert actions[0].actor_type == "agent"
    assert actions[0].reasoning == "auto-mode test"


@pytest.mark.asyncio
async def test_operator_order_submitter_passes_reasoning_to_audit(session):
    """The reasoning argument lands in the actions row; different reasoning
    per call produces different audit rows."""
    adapter = OperatorOrderSubmitter(session=session, actor_id="auto-router")

    intent_1 = _intent("AAPL", "2")
    intent_2 = _intent("MSFT", "1")
    await adapter.submit(intent_1, reasoning="dossier-1 reasoning")
    await adapter.submit(intent_2, reasoning="dossier-2 reasoning")

    rows = (await session.execute(select(Action).where(Action.capability == "submit_order").order_by(Action.ts))).scalars().all()
    assert len(rows) == 2
    assert rows[0].reasoning == "dossier-1 reasoning"
    assert rows[1].reasoning == "dossier-2 reasoning"
