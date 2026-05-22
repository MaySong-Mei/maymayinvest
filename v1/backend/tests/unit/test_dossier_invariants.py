"""Invariants for the DecisionDossier persistence layer.

What this proves:
  1. save_dossier round-trips a complete dossier (all required fields present)
  2. save_review requires an existing decision (no orphan reviews)
  3. save_llm_call requires exactly one of decision_id/review_id
  4. build_reviewer_input STRIPS outcome-leak fields from the snapshot
     (this is the architectural enforcement of reviewer outcome-blindness)
  5. build_reviewer_input does NOT include actor_id or latency_ms
     (information-only basis: reviewer should not know who decided or how long it took)

Uses an in-memory aiosqlite DB and runs the alembic baseline + 0002 migration
to construct schema. This is heavier than a unit test usually is, but the
repository layer's whole job is correctness of DB writes — testing it without
a real DB would test nothing.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    DecisionReview,
    DecisionVerdict,
    LlmCall,
    ProposedOrder,
    SkillInvocation,
)
from app.domain.order import OrderIntent, OrderSide, OrderType
from app.persistence.models import Base
from app.persistence.repositories.decisions import (
    _OUTCOME_LEAK_FIELDS,
    build_reviewer_input,
    save_dossier,
    save_llm_call,
    save_review,
)


@pytest_asyncio.fixture
async def session():
    """Fresh in-memory aiosqlite DB with full schema, per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


def _make_dossier(**overrides) -> DecisionDossier:
    """Realistic-shape dossier for tests. Outcome-leak fields intentionally
    seeded into the snapshot to verify they get stripped at reviewer time."""
    base_intent = OrderIntent(
        symbol="AAPL",
        side=OrderSide.BUY,
        qty=Decimal("5"),
        type=OrderType.MARKET,
    )
    return DecisionDossier(
        actor_id="claude-instance-1",
        actor_type="agent",
        event_id="edgar:0000320193-26-000123",
        event_kind="edgar_8k",
        event_summary="Apple announces $90B buyback",
        available_info_snapshot={
            "event_payload": {"headline": "Apple announces $90B buyback"},
            "recent_prices": {"AAPL": [220.50, 220.75, 221.10]},
            "portfolio": {"cash": "100000", "positions": []},
            # Outcome-leak fields seeded — they must be stripped at reviewer time:
            "realized_pnl": "999.99",  # MUST be stripped
            "filled_price": "221.50",  # MUST be stripped
            "outcome": "won",  # MUST be stripped
            "subsequent_prices": [222.0, 223.0],  # MUST be stripped
        },
        reasoning_chain="Buyback announcement is a structural bullish signal...",
        alternatives_considered=[
            AlternativeConsidered(action="hold", rejected_because="no upside capture"),
            AlternativeConsidered(action="buy full size", rejected_because="risk cap"),
        ],
        confidence=Decimal("0.7"),
        skills_invoked=[
            SkillInvocation(name="breakout_confirmed", version="0.1.0"),
        ],
        proposed=ProposedOrder(intent=base_intent),
        mode="dry_run",
        latency_ms=2350,
        **overrides,
    )


@pytest.mark.asyncio
async def test_save_dossier_persists_all_fields(session):
    dossier = _make_dossier()
    row = await save_dossier(session, dossier)

    assert row.id == dossier.id
    assert row.actor_id == "claude-instance-1"
    assert row.event_kind == "edgar_8k"
    assert row.reasoning_chain.startswith("Buyback announcement")
    assert row.confidence == Decimal("0.7")
    assert len(row.alternatives_considered) == 2
    assert row.alternatives_considered[0]["action"] == "hold"
    assert row.skills_invoked[0]["name"] == "breakout_confirmed"
    assert row.proposed["intent"]["symbol"] == "AAPL"
    assert row.proposed["intent"]["qty"] == "5"
    assert row.mode == "dry_run"
    assert row.latency_ms == 2350


@pytest.mark.asyncio
async def test_save_review_requires_existing_decision(session):
    """A review of a non-existent decision is a programmer error."""
    review = DecisionReview(
        decision_id=uuid4(),  # never persisted
        reviewer_id="reviewer-v1",
        reviewer_prompt_version="prompt-v1-2026-05-22",
        verdict=DecisionVerdict.RIGHT_BET,
        reasoning="Buyback signals durable bullish structure.",
        flags=[],
        confidence=Decimal("0.8"),
    )
    with pytest.raises(ValueError, match="does not exist"):
        await save_review(session, review)


@pytest.mark.asyncio
async def test_save_review_succeeds_for_real_decision(session):
    dossier = _make_dossier()
    await save_dossier(session, dossier)

    review = DecisionReview(
        decision_id=dossier.id,
        reviewer_id="reviewer-v1",
        reviewer_prompt_version="prompt-v1-2026-05-22",
        verdict=DecisionVerdict.RIGHT_BET,
        reasoning="Sound process; alternatives considered; appropriate size.",
        flags=[],
        confidence=Decimal("0.8"),
    )
    row = await save_review(session, review)
    assert row.decision_id == dossier.id
    assert row.verdict == "right_bet"


@pytest.mark.asyncio
async def test_save_llm_call_requires_exactly_one_link(session):
    dossier = _make_dossier()
    await save_dossier(session, dossier)

    # Neither link → error
    floating = LlmCall(
        purpose="analyze_event",
        model="claude-haiku-4-5",
        prompt="...",
        response="...",
    )
    with pytest.raises(ValueError, match="exactly one"):
        await save_llm_call(session, floating)

    # Both links → error
    review = DecisionReview(
        decision_id=dossier.id,
        reviewer_id="reviewer-v1",
        reviewer_prompt_version="v1",
        verdict=DecisionVerdict.AMBIGUOUS,
        reasoning="x",
        flags=[],
        confidence=Decimal("0.5"),
    )
    await save_review(session, review)
    both = LlmCall(
        decision_id=dossier.id,
        review_id=review.id,
        purpose="x",
        model="claude-haiku-4-5",
        prompt="x",
        response="x",
    )
    with pytest.raises(ValueError, match="exactly one"):
        await save_llm_call(session, both)

    # Decision-only → ok
    decision_only = LlmCall(
        decision_id=dossier.id,
        purpose="analyze_event",
        model="claude-haiku-4-5",
        prompt="...",
        response="...",
    )
    row = await save_llm_call(session, decision_only)
    assert row.decision_id == dossier.id
    assert row.review_id is None


@pytest.mark.asyncio
async def test_build_reviewer_input_strips_outcome_leak_fields(session):
    """Architectural enforcement of reviewer outcome-blindness.

    The dossier we seeded has outcome-leak fields inside its snapshot
    (realized_pnl, filled_price, outcome, subsequent_prices). Reviewer input
    MUST NOT contain any of them.
    """
    dossier = _make_dossier()
    await save_dossier(session, dossier)

    reviewer_in = await build_reviewer_input(session, dossier.id)

    snapshot = reviewer_in["available_info_snapshot"]
    for leak in _OUTCOME_LEAK_FIELDS:
        assert leak not in snapshot, (
            f"reviewer input MUST NOT contain outcome-leak field {leak!r}; "
            f"got: {list(snapshot.keys())}"
        )

    # Sanity: non-leak fields ARE preserved
    assert "event_payload" in snapshot
    assert "recent_prices" in snapshot
    assert "portfolio" in snapshot


@pytest.mark.asyncio
async def test_build_reviewer_input_omits_actor_and_latency(session):
    """Reviewer should not know who decided or how long it took.

    actor_id could bias the reviewer (e.g. trust a senior CC more).
    latency_ms is a timing channel that could correlate with model used,
    market state at decision time, etc — all information that wasn't
    "available at decision time" in the sense the reviewer should use.
    """
    dossier = _make_dossier()
    await save_dossier(session, dossier)

    reviewer_in = await build_reviewer_input(session, dossier.id)
    assert "actor_id" not in reviewer_in
    assert "latency_ms" not in reviewer_in


@pytest.mark.asyncio
async def test_build_reviewer_input_unknown_decision_raises(session):
    with pytest.raises(ValueError, match="not found"):
        await build_reviewer_input(session, uuid4())
