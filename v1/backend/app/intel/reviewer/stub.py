"""StubReviewer — deterministic no-LLM reviewer.

Purpose:
  - Wire the reviewer pipeline end-to-end without depending on a live LLM
  - Test downstream code (review storage, async firing, dashboard read)
  - Be the contract reference: any real reviewer must produce a
    DecisionReview with at least the same shape

Behavior:
  - Always returns verdict=ambiguous with confidence 0.5
  - reasoning is a fixed string acknowledging it's a stub
  - flags contains a single "stub-reviewer-no-real-judgment" marker so
    downstream consumers can filter stub reviews from real ones
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.decision import DecisionReview, DecisionVerdict
from app.intel.reviewer.base import DecisionReviewer, ReviewerContext


class StubReviewer(DecisionReviewer):
    """Always-ambiguous deterministic reviewer."""

    async def review(
        self,
        reviewer_input: dict[str, Any],
        ctx: ReviewerContext,
    ) -> DecisionReview:
        decision_id = UUID(reviewer_input["decision_id"])
        return DecisionReview(
            decision_id=decision_id,
            reviewer_id=ctx.actor_id,
            reviewer_prompt_version=ctx.prompt_version,
            verdict=DecisionVerdict.AMBIGUOUS,
            reasoning=(
                "[stub-reviewer] No real judgment formed. This reviewer is "
                "used for pipeline wiring and tests, not for actual decision "
                "quality evaluation."
            ),
            flags=["stub-reviewer-no-real-judgment"],
            confidence=Decimal("0.5"),
        )
