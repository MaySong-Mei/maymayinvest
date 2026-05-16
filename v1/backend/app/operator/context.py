from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

ActorType = Literal["user", "agent"]


@dataclass(slots=True)
class OperatorContext:
    actor_id: str
    actor_type: ActorType
    session: AsyncSession
    reasoning: str | None = None
    request_id: str | None = None
