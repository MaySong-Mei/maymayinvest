from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssetClass = Literal["equity", "etf", "crypto", "future", "option", "fx"]


class Instrument(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1, max_length=32)
    exchange: str = Field(min_length=1, max_length=16)  # e.g. "NASDAQ", "NYSE", "SSE", "BINANCE"
    asset_class: AssetClass
    currency: str = Field(min_length=3, max_length=3)   # ISO 4217, e.g. "USD"
    calendar_id: str = Field(default="XNYS")            # exchange_calendars id
