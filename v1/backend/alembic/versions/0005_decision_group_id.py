"""Add decision_group_id to decisions for N-of-1 trial grouping.

Authorized by proposal:
  v1/docs/proposals/2026-05-23-aggregator-design-resolver-pattern.md
  (commit 6311ec1).

Backward-compatible nullable column. Pre-existing single-trial dossiers
remain ungrouped (decision_group_id IS NULL), which is the correct
historical state — no backfill is required. New captures from the capture
script will populate this with a single UUID shared across the N trials
of one event.

Indexed because the derived consensus function and dashboard surface will
query "all decisions with this group_id" frequently.

Revision ID: 0005_decision_group_id
Revises: 0004_pending_signals
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_decision_group_id"
down_revision: Union[str, None] = "0004_pending_signals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "decisions",
        sa.Column(
            "decision_group_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_decisions_group_id",
        "decisions",
        ["decision_group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_decisions_group_id", table_name="decisions")
    op.drop_column("decisions", "decision_group_id")
