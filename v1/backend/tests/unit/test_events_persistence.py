"""Events table invariants.

What this proves:
  1. save_event roundtrips a complete event
  2. save_event is idempotent on external_id (re-poll safe)
  3. get_event_by_external_id returns the row or None
  4. tz-naive datetimes are rejected at the domain layer
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.event import Event, EventKind
from app.persistence.models import Base
from app.persistence.repositories.events import (
    get_event_by_external_id,
    save_event,
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


def _make_event(external_id: str = "edgar:0000320193-26-000123") -> Event:
    return Event(
        kind=EventKind.EDGAR_8K,
        external_id=external_id,
        ts=datetime(2026, 5, 22, 14, 30, tzinfo=UTC),
        source="sec_edgar",
        symbols=["AAPL"],
        headline="Apple announces $90B buyback program",
        payload={
            "filing_url": "https://www.sec.gov/...",
            "accession": "0000320193-26-000123",
        },
    )


@pytest.mark.asyncio
async def test_save_event_roundtrip(session):
    event = _make_event()
    row = await save_event(session, event)

    assert row.id == event.id
    assert row.kind == "edgar_8k"
    assert row.external_id == "edgar:0000320193-26-000123"
    assert row.source == "sec_edgar"
    assert row.symbols == ["AAPL"]
    assert "buyback" in row.headline
    assert row.payload["accession"] == "0000320193-26-000123"


@pytest.mark.asyncio
async def test_save_event_is_idempotent_on_external_id(session):
    e1 = _make_event(external_id="edgar:dup-test")
    e2 = _make_event(external_id="edgar:dup-test")
    # Different domain IDs, same external_id
    assert e1.id != e2.id

    row1 = await save_event(session, e1)
    row2 = await save_event(session, e2)

    # Returned row is the same persisted entity both times
    assert row1.id == row2.id
    # The first id wins; the second call returns the existing row
    assert row1.id == e1.id


@pytest.mark.asyncio
async def test_get_event_by_external_id_returns_none_when_missing(session):
    row = await get_event_by_external_id(session, "edgar:nonexistent")
    assert row is None


@pytest.mark.asyncio
async def test_event_rejects_tz_naive_datetime():
    with pytest.raises(ValueError, match="naive datetime"):
        Event(
            kind=EventKind.TEST_SYNTHETIC,
            external_id="test:naive",
            ts=datetime(2026, 5, 22, 14, 30),  # no tzinfo
            source="test",
            symbols=[],
            headline="x",
            payload={},
        )
