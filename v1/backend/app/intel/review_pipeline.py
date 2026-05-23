"""Review pipeline — bridges a persisted DecisionDossier to a stored Review.

Reviewer is deliberately NOT in the hot path (see
app/intel/reviewer/base.py docstring). The router does NOT call this
module. Callers (selftest, scheduled background job, dashboard
"review now" button) invoke review_decision() against decisions that
are already persisted.

This module is thin: it composes the outcome-blind input builder, the
reviewer protocol, and the review repository. Each is already tested
in isolation; this glue does no decision-making of its own.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.decision import DecisionReview
from app.intel.reviewer.base import DecisionReviewer, ReviewerContext
from app.persistence.repositories.decisions import (
    build_reviewer_input,
    save_review,
)


async def review_decision(
    session: AsyncSession,
    reviewer: DecisionReviewer,
    decision_id: UUID,
    ctx: ReviewerContext,
) -> DecisionReview:
    """Run a single review pass over a persisted decision.

    Steps:
      1. build outcome-blind reviewer input from the dossier
         (this is where the outcome-blindness invariant is enforced;
         see build_reviewer_input docstring)
      2. invoke reviewer (subprocess / API / stub)
      3. persist the resulting DecisionReview

    Returns the persisted DecisionReview. Caller can re-invoke with a
    different reviewer (different actor_id / prompt_version) to get
    multiple judgments on the same decision; reviews table allows
    multiple rows per decision_id by design.

    Raises whatever the reviewer raises on failure (ReviewerError, etc).
    The caller decides retry vs incident; we do NOT swallow.
    """
    reviewer_input = await build_reviewer_input(session, decision_id)
    review = await reviewer.review(reviewer_input, ctx)
    await save_review(session, review)
    return review
