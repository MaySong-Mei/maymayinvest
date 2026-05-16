"""Time helpers. Invariant: Bar.ts = bar CLOSE, UTC, tz-aware."""
from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime crossed a boundary; must be tz-aware UTC")
    return dt.astimezone(UTC)
