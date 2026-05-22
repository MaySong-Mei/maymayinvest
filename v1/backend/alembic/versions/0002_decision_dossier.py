"""Decision dossier schema: decisions, reviews, llm_calls.

Three append-only tables introduced to support the CC-as-operator
framing (see v1/docs/PHILOSOPHY.md and v1/docs/ARCHITECTURE.md "v1 —
CC-centric harness" section):

- decisions: every CC analysis run; the central data artifact
- reviews: outcome-blind reviewer subagent judgments, linked to decisions
- llm_calls: per-invocation trace for both decisions and reviews

All append-only at the application layer (no UPDATE/DELETE through repos).

Revision ID: 0002_decision_dossier
Revises: 0001_baseline
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_decision_dossier"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY = sa.Numeric(20, 8)


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=True),
        sa.Column("event_kind", sa.String(32), nullable=False),
        sa.Column("event_summary", sa.Text, nullable=False),
        sa.Column("available_info_snapshot", sa.JSON, nullable=False),
        sa.Column("reasoning_chain", sa.Text, nullable=False),
        sa.Column("alternatives_considered", sa.JSON, nullable=False),
        sa.Column("confidence", MONEY, nullable=False),
        sa.Column("skills_invoked", sa.JSON, nullable=False),
        sa.Column("proposed", sa.JSON, nullable=False),
        sa.Column("mode", sa.String(16), nullable=False, server_default="dry_run"),
        sa.Column("latency_ms", sa.BigInteger, nullable=False, server_default="0"),
    )
    op.create_index("ix_decisions_event_ts", "decisions", ["event_kind", "created_at"])
    op.create_index("ix_decisions_actor_ts", "decisions", ["actor_id", "created_at"])

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decisions.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("reviewer_id", sa.String(64), nullable=False),
        sa.Column("reviewer_prompt_version", sa.String(32), nullable=False),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("flags", sa.JSON, nullable=False),
        sa.Column("confidence", MONEY, nullable=False),
    )
    op.create_index("ix_reviews_decision", "reviews", ["decision_id"])
    op.create_index("ix_reviews_verdict_ts", "reviews", ["verdict", "created_at"])

    op.create_table(
        "llm_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decisions.id"),
            nullable=True,
        ),
        sa.Column(
            "review_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reviews.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_llm_calls_decision", "llm_calls", ["decision_id"])
    op.create_index("ix_llm_calls_review", "llm_calls", ["review_id"])
    op.create_index("ix_llm_calls_purpose_ts", "llm_calls", ["purpose", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_purpose_ts", table_name="llm_calls")
    op.drop_index("ix_llm_calls_review", table_name="llm_calls")
    op.drop_index("ix_llm_calls_decision", table_name="llm_calls")
    op.drop_table("llm_calls")
    op.drop_index("ix_reviews_verdict_ts", table_name="reviews")
    op.drop_index("ix_reviews_decision", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("ix_decisions_actor_ts", table_name="decisions")
    op.drop_index("ix_decisions_event_ts", table_name="decisions")
    op.drop_table("decisions")
