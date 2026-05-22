"""Repository for the events table.

Two functions:
  - save_event: idempotent on external_id (dedupe at write time)
  - get_event_by_external_id: lookup for analyzer-side reads

Append-only at the application level. We don't UPDATE event rows; if a
source publishes a corrected version, that's a new event row (the
source's external_id should reflect the revision, e.g. "...-amend-1").

Idempotency note: the unique index on external_id guarantees one row per
canonical event. save_event returns the existing row if external_id is
already known, rather than raising — pollers re-running over the same
window should be safe.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.event import Event as EventDomain
from app.persistence.models import Event as EventRow


async def save_event(session: AsyncSession, event: EventDomain) -> EventRow:
    """Persist an Event. Idempotent on external_id.

    If an event with the same external_id is already stored, the existing
    row is returned and no INSERT happens. This makes pollers safe to
    re-run over overlapping windows.
    """
    existing = await get_event_by_external_id(session, event.external_id)
    if existing is not None:
        return existing

    row = EventRow(
        id=event.id,
        kind=event.kind.value,
        external_id=event.external_id,
        ts=event.ts,
        ingested_at=event.ingested_at,
        source=event.source,
        symbols=list(event.symbols),
        headline=event.headline,
        payload=event.payload,
    )
    session.add(row)
    await session.flush()
    return row


async def get_event_by_external_id(
    session: AsyncSession, external_id: str
) -> EventRow | None:
    stmt = select(EventRow).where(EventRow.external_id == external_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
