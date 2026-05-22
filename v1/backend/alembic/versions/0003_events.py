"""Events table — perception layer for the analyzer.

One row per source-canonical event (EDGAR filing, RSS item, etc).
Dedupe via unique external_id; idempotent re-poll friendly.

Revision ID: 0003_events
Revises: 0002_decision_dossier
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_events"
down_revision: Union[str, None] = "0002_decision_dossier"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False, unique=True),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("symbols", sa.JSON, nullable=False),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
    )
    op.create_index("ix_events_kind_ingested", "events", ["kind", "ingested_at"])
    op.create_index("ix_events_ts", "events", ["ts"])


def downgrade() -> None:
    op.drop_index("ix_events_ts", table_name="events")
    op.drop_index("ix_events_kind_ingested", table_name="events")
    op.drop_table("events")
