"""Repository for pending_signals.

Lifecycle: pending → (promoted | dismissed | expired). Once a signal
leaves 'pending', it cannot transition again. This is a state machine,
not append-only; the enforcement lives in this module.

Allowed transitions (the ONLY supported write paths):
  enqueue(dossier_id, mode)              # creates pending row
  promote(signal_id, actor_id, order_id) # pending → promoted
  dismiss(signal_id, actor_id, reason)   # pending → dismissed
  expire(signal_id, reason)              # pending → expired

Any attempt to transition out of a non-'pending' status raises ValueError.
Any attempt to enqueue twice for the same dossier_id raises (DB UNIQUE on
dossier_id enforces this at the storage layer too).
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.persistence.models import PendingSignal


_TERMINAL_STATUSES = frozenset({"promoted", "dismissed", "expired"})


async def enqueue(
    session: AsyncSession,
    dossier_id: UUID,
    mode: str,
) -> PendingSignal:
    """Add a notify/dry_run dossier to the pending queue.

    Idempotency: if a pending_signals row already exists for this dossier_id
    (unique index), DB raises IntegrityError. The router treats this as a
    programmer error — each dossier is queued at most once at decision time.
    """
    if mode not in ("notify", "dry_run"):
        raise ValueError(
            f"enqueue: mode must be 'notify' or 'dry_run', got {mode!r}; "
            "auto-mode decisions submit directly and do not queue"
        )
    row = PendingSignal(
        id=uuid4(),
        dossier_id=dossier_id,
        created_at=utcnow(),
        mode=mode,
        status="pending",
    )
    session.add(row)
    await session.flush()
    return row


async def _get_pending_or_raise(session: AsyncSession, signal_id: UUID) -> PendingSignal:
    row = await session.get(PendingSignal, signal_id)
    if row is None:
        raise ValueError(f"pending_signal {signal_id} not found")
    if row.status in _TERMINAL_STATUSES:
        raise ValueError(
            f"pending_signal {signal_id} already in terminal status "
            f"{row.status!r}; cannot re-resolve"
        )
    return row


async def promote(
    session: AsyncSession,
    signal_id: UUID,
    actor_id: str,
    resulting_client_order_id: UUID,
) -> PendingSignal:
    """User accepted the signal; record which order was actually submitted."""
    row = await _get_pending_or_raise(session, signal_id)
    row.status = "promoted"
    row.resolved_at = utcnow()
    row.resolved_by = actor_id
    row.resulting_client_order_id = resulting_client_order_id
    await session.flush()
    return row


async def dismiss(
    session: AsyncSession,
    signal_id: UUID,
    actor_id: str,
    reason: str | None = None,
) -> PendingSignal:
    """User rejected the signal."""
    row = await _get_pending_or_raise(session, signal_id)
    row.status = "dismissed"
    row.resolved_at = utcnow()
    row.resolved_by = actor_id
    row.resolution_reason = reason
    await session.flush()
    return row


async def expire(
    session: AsyncSession, signal_id: UUID, reason: str = "ttl"
) -> PendingSignal:
    """Auto-expire stale signals. Not invoked in v1; reserved for Stage 1+."""
    row = await _get_pending_or_raise(session, signal_id)
    row.status = "expired"
    row.resolved_at = utcnow()
    row.resolution_reason = reason
    await session.flush()
    return row


async def list_pending(session: AsyncSession, limit: int = 50) -> Sequence[PendingSignal]:
    """Read for the dashboard. Pending rows, newest first."""
    stmt = (
        select(PendingSignal)
        .where(PendingSignal.status == "pending")
        .order_by(PendingSignal.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()
