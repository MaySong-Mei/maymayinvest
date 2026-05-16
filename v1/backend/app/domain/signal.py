from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Signal(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    ts: datetime
    kind: Literal["entry", "exit", "scale_in", "scale_out"]
    confidence: float = 1.0  # 0..1
    reason: str | None = None
