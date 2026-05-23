"""pending_signals lifecycle invariants.

State machine: pending → (promoted | dismissed | expired). Once
terminal, no more transitions allowed.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    ProposedOrder,
)
from app.persistence.models import Base
from app.persistence.repositories.decisions import save_dossier
from app.persistence.repositories.pending_signals import (
    dismiss,
    enqueue,
    expire,
    list_pending,
    promote,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


async def _seed_dossier(session) -> DecisionDossier:
    dossier = DecisionDossier(
        actor_id="t",
        event_id="t:1",
        event_kind="test_synthetic",
        event_summary="t",
        available_info_snapshot={},
        reasoning_chain="t",
        alternatives_considered=[
            AlternativeConsidered(action="hold", rejected_because="x"),
        ],
        confidence=Decimal("0.5"),
        skills_invoked=[],
        proposed=ProposedOrder(intent=None, no_action_reason="t"),
        mode="notify",
    )
    await save_dossier(session, dossier)
    return dossier


@pytest.mark.asyncio
async def test_enqueue_requires_notify_or_dry_run(session):
    dossier = await _seed_dossier(session)
    with pytest.raises(ValueError, match="mode must be"):
        await enqueue(session, dossier.id, mode="auto")


@pytest.mark.asyncio
async def test_enqueue_twice_for_same_dossier_fails(session):
    """DB UNIQUE on dossier_id enforces 'each dossier queued at most once'."""
    dossier = await _seed_dossier(session)
    await enqueue(session, dossier.id, mode="notify")
    with pytest.raises(IntegrityError):
        await enqueue(session, dossier.id, mode="notify")


@pytest.mark.asyncio
async def test_promote_transitions_to_promoted(session):
    dossier = await _seed_dossier(session)
    signal = await enqueue(session, dossier.id, mode="dry_run")

    order_id = uuid4()
    resolved = await promote(session, signal.id, actor_id="user-1", resulting_client_order_id=order_id)
    assert resolved.status == "promoted"
    assert resolved.resolved_by == "user-1"
    assert resolved.resulting_client_order_id == order_id
    assert resolved.resolved_at is not None


@pytest.mark.asyncio
async def test_dismiss_records_reason(session):
    dossier = await _seed_dossier(session)
    signal = await enqueue(session, dossier.id, mode="notify")

    resolved = await dismiss(session, signal.id, actor_id="user-1", reason="not enough confirmation")
    assert resolved.status == "dismissed"
    assert resolved.resolution_reason == "not enough confirmation"


@pytest.mark.asyncio
async def test_cannot_re_resolve_terminal_signal(session):
    """Promote → dismiss should fail; dismiss → promote should fail."""
    dossier = await _seed_dossier(session)
    signal = await enqueue(session, dossier.id, mode="notify")
    await dismiss(session, signal.id, actor_id="user-1")

    with pytest.raises(ValueError, match="terminal status"):
        await promote(session, signal.id, actor_id="user-1", resulting_client_order_id=uuid4())

    with pytest.raises(ValueError, match="terminal status"):
        await expire(session, signal.id)


@pytest.mark.asyncio
async def test_list_pending_excludes_resolved(session):
    """list_pending only returns rows still in 'pending' state."""
    d1 = await _seed_dossier(session)
    s1 = await enqueue(session, d1.id, mode="notify")

    # Create a second dossier + signal, then resolve it
    d2 = DecisionDossier(
        actor_id="t",
        event_id="t:2",
        event_kind="test_synthetic",
        event_summary="t2",
        available_info_snapshot={},
        reasoning_chain="t",
        alternatives_considered=[
            AlternativeConsidered(action="hold", rejected_because="x"),
        ],
        confidence=Decimal("0.5"),
        skills_invoked=[],
        proposed=ProposedOrder(intent=None, no_action_reason="t"),
        mode="dry_run",
    )
    await save_dossier(session, d2)
    s2 = await enqueue(session, d2.id, mode="dry_run")
    await dismiss(session, s2.id, actor_id="user-1", reason="dup")

    pending = await list_pending(session)
    assert [p.id for p in pending] == [s1.id]
