"""Repository functions for decisions / reviews / llm_calls.

Three responsibilities:
  1. Convert between domain models (app.domain.decision) and ORM rows.
  2. Enforce append-only at the application layer (no UPDATE/DELETE exposed).
  3. Enforce the reviewer outcome-blind invariant via build_reviewer_input —
     the ONLY function that constructs reviewer input strips by construction
     any field that could leak outcome information.

These functions are the sole write path for the three tables. Callers must
not import the ORM models directly to write — that bypasses invariants.

NOTE on outcome-blindness: the DecisionDossier domain model already doesn't
carry outcome fields (no realized_pnl, no fill_price, no subsequent_bars).
But a caller could construct a reviewer prompt that joins on fills/orders
by decision_id. build_reviewer_input is the architectural gate: pass it the
dossier id, get back ONLY the dossier's information-only fields, in a shape
the reviewer can consume.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.decision import (
    DecisionDossier,
    DecisionReview,
    LlmCall,
)
from app.persistence.models import Decision, LlmCallLog, Review


# ---------- write ----------


async def save_dossier(session: AsyncSession, dossier: DecisionDossier) -> Decision:
    """Persist a DecisionDossier. Append-only — caller must not modify after save.

    Returns the ORM row so callers can use .id for FK linking
    (e.g. when saving llm_calls that reference this decision).
    """
    row = Decision(
        id=dossier.id,
        created_at=dossier.created_at,
        actor_id=dossier.actor_id,
        actor_type=dossier.actor_type,
        event_id=dossier.event_id,
        event_kind=dossier.event_kind,
        event_summary=dossier.event_summary,
        available_info_snapshot=dossier.available_info_snapshot,
        reasoning_chain=dossier.reasoning_chain,
        alternatives_considered=[a.model_dump() for a in dossier.alternatives_considered],
        confidence=dossier.confidence,
        skills_invoked=[s.model_dump() for s in dossier.skills_invoked],
        proposed=dossier.proposed.model_dump(mode="json"),
        mode=dossier.mode,
        latency_ms=dossier.latency_ms,
    )
    session.add(row)
    await session.flush()
    return row


async def save_review(session: AsyncSession, review: DecisionReview) -> Review:
    """Persist a reviewer's judgment. Append-only.

    Verifies the referenced decision exists; raises if not. The reviewer
    must judge a real, persisted decision — orphan reviews are a bug.
    """
    exists = await session.get(Decision, review.decision_id)
    if exists is None:
        raise ValueError(
            f"save_review: decision_id {review.decision_id} does not exist; "
            "reviewer cannot judge a non-existent decision"
        )
    row = Review(
        id=review.id,
        decision_id=review.decision_id,
        created_at=review.created_at,
        reviewer_id=review.reviewer_id,
        reviewer_prompt_version=review.reviewer_prompt_version,
        verdict=review.verdict.value,
        reasoning=review.reasoning,
        flags=list(review.flags),
        confidence=review.confidence,
    )
    session.add(row)
    await session.flush()
    return row


async def save_llm_call(session: AsyncSession, call: LlmCall) -> LlmCallLog:
    """Persist a single LLM invocation trace.

    Must reference exactly one of decision_id / review_id. Floating LLM
    calls (referencing neither) are disallowed — every LLM call exists in
    service of either a decision or a review.
    """
    if (call.decision_id is None) == (call.review_id is None):
        raise ValueError(
            "save_llm_call: must reference exactly one of decision_id or review_id"
        )
    row = LlmCallLog(
        id=call.id,
        decision_id=call.decision_id,
        review_id=call.review_id,
        created_at=call.created_at,
        purpose=call.purpose,
        model=call.model,
        prompt=call.prompt,
        response=call.response,
        input_tokens=call.input_tokens,
        output_tokens=call.output_tokens,
        latency_ms=call.latency_ms,
        error=call.error,
    )
    session.add(row)
    await session.flush()
    return row


# ---------- outcome-blind reviewer input ----------


# Fields that MUST NOT leak into the reviewer's input.
# Listed explicitly here so an audit can grep for the keyword and find
# every potential outcome-leak vector. If a future field is added to
# the dossier that could carry outcome info, add it here too.
_OUTCOME_LEAK_FIELDS: frozenset[str] = frozenset({
    "broker_order_id",
    "fill_id",
    "filled_price",
    "fill_price",
    "realized_pnl",
    "unrealized_pnl",
    "pnl",
    "closed_at",
    "subsequent_bars",
    "subsequent_prices",
    "actual_outcome",
    "outcome",
    "final_equity",
    "exit_price",
})


def _strip_outcome_leaks(obj: Any) -> Any:
    """Recursively remove keys that could leak outcome information.

    Defensive deep walk: the snapshot dict is free-form, so a future
    contributor adding `recent_prices` could accidentally include a price
    timestamped AFTER the decision. This walk strips known outcome-y
    keys; it does NOT validate timestamps (that's a stricter check
    deferred until we have a stable snapshot schema).
    """
    if isinstance(obj, dict):
        return {
            k: _strip_outcome_leaks(v)
            for k, v in obj.items()
            if k not in _OUTCOME_LEAK_FIELDS
        }
    if isinstance(obj, list):
        return [_strip_outcome_leaks(item) for item in obj]
    return obj


async def build_reviewer_input(
    session: AsyncSession, decision_id: UUID
) -> dict[str, Any]:
    """Construct the reviewer's input from a stored decision.

    HARD INVARIANT: this is the ONLY supported way to build reviewer input.
    Callers that bypass this function and join fills/orders by decision_id
    are introducing outcome leakage. Code review must catch this.

    Returns a dict containing ONLY the dossier's information-only fields,
    with outcome-leak-prone keys stripped from the snapshot.
    """
    stmt = select(Decision).where(Decision.id == decision_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"build_reviewer_input: decision {decision_id} not found")

    return {
        "decision_id": str(row.id),
        "created_at": row.created_at.isoformat(),
        "event_kind": row.event_kind,
        "event_summary": row.event_summary,
        "available_info_snapshot": _strip_outcome_leaks(row.available_info_snapshot),
        "reasoning_chain": row.reasoning_chain,
        "alternatives_considered": row.alternatives_considered,
        "confidence": str(row.confidence),
        "skills_invoked": row.skills_invoked,
        "proposed": _strip_outcome_leaks(row.proposed),
        "mode": row.mode,
        # NOTE: latency_ms intentionally omitted — could carry timing-channel info
        # NOTE: actor_id intentionally omitted — reviewer shouldn't know who decided
    }
