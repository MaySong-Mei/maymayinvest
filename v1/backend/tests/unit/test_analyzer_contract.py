"""EventAnalyzer contract tests.

What this proves (against StubAnalyzer, but the assertions are contract-
level and any real analyzer must also satisfy them):

  1. analyze() returns a DecisionDossier
  2. dossier.event_id matches event.external_id (caller can join back)
  3. dossier.event_kind matches event.kind.value
  4. dossier.actor_id matches ctx.actor_id (provenance preserved)
  5. dossier.confidence is a Decimal in [0, 1]
  6. dossier.proposed is well-formed:
       - if intent is None, no_action_reason MUST be set
       - if intent is set, no_action_reason MUST be None
  7. dossier is persistable through save_dossier without modification
     (round-trip through the storage layer)
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.decision import DecisionDossier
from app.domain.event import Event, EventKind
from app.intel.analyzer.base import AnalyzerContext
from app.intel.analyzer.stub import StubAnalyzer
from app.persistence.models import Base
from app.persistence.repositories.decisions import save_dossier


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


def _make_event() -> Event:
    return Event(
        kind=EventKind.EDGAR_8K,
        external_id="edgar:0000320193-26-000123",
        ts=datetime(2026, 5, 22, 14, 30, tzinfo=UTC),
        source="sec_edgar",
        symbols=["AAPL"],
        headline="Apple announces $90B buyback program",
        payload={"accession": "0000320193-26-000123"},
    )


@pytest.mark.asyncio
async def test_analyzer_returns_dossier():
    analyzer = StubAnalyzer()
    ctx = AnalyzerContext(actor_id="stub-analyzer-test")
    dossier = await analyzer.analyze(_make_event(), ctx)
    assert isinstance(dossier, DecisionDossier)


@pytest.mark.asyncio
async def test_dossier_event_id_matches_external_id():
    analyzer = StubAnalyzer()
    ctx = AnalyzerContext(actor_id="stub-analyzer-test")
    event = _make_event()
    dossier = await analyzer.analyze(event, ctx)
    assert dossier.event_id == event.external_id


@pytest.mark.asyncio
async def test_dossier_event_kind_matches():
    analyzer = StubAnalyzer()
    ctx = AnalyzerContext(actor_id="stub-analyzer-test")
    event = _make_event()
    dossier = await analyzer.analyze(event, ctx)
    assert dossier.event_kind == event.kind.value


@pytest.mark.asyncio
async def test_dossier_actor_id_matches_context():
    analyzer = StubAnalyzer()
    ctx = AnalyzerContext(actor_id="stub-analyzer-test-provenance")
    dossier = await analyzer.analyze(_make_event(), ctx)
    assert dossier.actor_id == "stub-analyzer-test-provenance"


@pytest.mark.asyncio
async def test_dossier_confidence_in_valid_range():
    analyzer = StubAnalyzer()
    ctx = AnalyzerContext(actor_id="stub-analyzer-test")
    dossier = await analyzer.analyze(_make_event(), ctx)
    assert isinstance(dossier.confidence, Decimal)
    assert Decimal("0") <= dossier.confidence <= Decimal("1")


@pytest.mark.asyncio
async def test_dossier_proposed_no_action_well_formed():
    """If intent is None, no_action_reason must be set (and vice versa).

    This is the contract for "explicit no-action decision": the analyzer
    must explain why nothing was proposed. A null intent without a reason
    is an incomplete dossier.
    """
    analyzer = StubAnalyzer()
    ctx = AnalyzerContext(actor_id="stub-analyzer-test")
    dossier = await analyzer.analyze(_make_event(), ctx)

    if dossier.proposed.intent is None:
        assert dossier.proposed.no_action_reason, (
            "no-action dossier MUST have a no_action_reason; "
            f"got intent={dossier.proposed.intent!r}, "
            f"reason={dossier.proposed.no_action_reason!r}"
        )
    else:
        assert dossier.proposed.no_action_reason is None, (
            "dossier with an intent MUST NOT also have a no_action_reason"
        )


@pytest.mark.asyncio
async def test_dossier_persistable_through_save_dossier(session):
    """The dossier the analyzer returns can be written through save_dossier
    without modification. This is the integration check that the analyzer
    contract and the persistence contract agree on field shapes."""
    analyzer = StubAnalyzer()
    ctx = AnalyzerContext(actor_id="stub-analyzer-test")
    dossier = await analyzer.analyze(_make_event(), ctx)
    row = await save_dossier(session, dossier)
    assert row.id == dossier.id
    assert row.event_kind == dossier.event_kind
