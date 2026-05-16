from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.time import ensure_utc


class Bar(BaseModel):
    """OHLCV bar. `ts` = bar CLOSE, tz-aware UTC. Provider adapters normalize."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    freq: str  # "1m" | "5m" | "1h" | "1d"
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(default=Decimal("0"))

    @field_validator("ts")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)
