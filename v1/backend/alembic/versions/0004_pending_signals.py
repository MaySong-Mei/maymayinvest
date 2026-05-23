"""pending_signals: notify/dry_run dossiers awaiting human action.

User-facing queue. dashboard displays rows where status='pending';
promote/dismiss/expire transitions update status + resolved_*.

Revision ID: 0004_pending_signals
Revises: 0003_events
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_pending_signals"
down_revision: Union[str, None] = "0003_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dossier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decisions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(64), nullable=True),
        sa.Column("resolution_reason", sa.Text, nullable=True),
        sa.Column(
            "resulting_client_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.client_order_id"),
            nullable=True,
        ),
    )
    op.create_index("ix_pending_status_created", "pending_signals", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_status_created", table_name="pending_signals")
    op.drop_table("pending_signals")
