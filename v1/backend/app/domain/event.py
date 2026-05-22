"""Event — what the analyzer receives.

Events are raw signals from the outside world: an EDGAR 8-K filing, an
RSS news item, a user-initiated "look at this ticker" request. The
analyzer reads an Event and produces a DecisionDossier.

Pure domain — no I/O.

Invariants:
  - Event.ts is tz-aware UTC (when the event occurred at the source,
    e.g. SEC filing accepted_datetime; NOT when our poller saw it)
  - Event.ingested_at is tz-aware UTC (when our poller saw it; can lag ts)
  - Event.external_id is the source's canonical id, used for dedupe
  - Event.payload is free-form JSON — the analyzer interprets it
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.time import ensure_utc, utcnow


class EventKind(StrEnum):
    """Closed set for v1. Add a value here when adding a new source.

    Naming convention: `{source}_{type}` lowercase, snake_case.
    """

    EDGAR_8K = "edgar_8k"
    EDGAR_10Q = "edgar_10q"
    EDGAR_10K = "edgar_10k"
    RSS_PR_NEWSWIRE = "rss_pr_newswire"
    RSS_BUSINESS_WIRE = "rss_business_wire"
    RSS_SEEKING_ALPHA = "rss_seeking_alpha"
    RSS_GENERIC = "rss_generic"
    USER_INITIATED = "user_initiated"
    TEST_SYNTHETIC = "test_synthetic"  # for fixtures and dev


class Event(BaseModel):
    """A trigger for analysis.

    Stored in the `events` table; referenced from DecisionDossier.event_id
    (the dossier's event_id holds the Event.external_id, not the row PK,
    because external_id is the human-readable / source-canonical handle).
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    kind: EventKind
    external_id: str  # source-canonical (e.g. "edgar:0000320193-26-000123")
    ts: datetime  # when the event occurred at the source
    ingested_at: datetime = Field(default_factory=utcnow)
    source: str  # short label: "sec_edgar", "pr_newswire", "user", "synthetic"
    symbols: list[str] = Field(default_factory=list)  # tickers mentioned/relevant
    headline: str
    payload: dict[str, Any] = Field(default_factory=dict)  # full source data

    @field_validator("ts", "ingested_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)
