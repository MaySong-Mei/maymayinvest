from collections.abc import AsyncIterator

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.identity import Identity, identity_from_headers
from app.operator.context import OperatorContext
from app.persistence.db import session_scope


async def db_session() -> AsyncIterator[AsyncSession]:
    async with session_scope() as s:
        yield s


def get_identity(
    x_actor_type: str | None = Header(default="user"),
    x_actor_id: str | None = Header(default="me"),
    x_reasoning: str | None = Header(default=None),
) -> Identity:
    headers = {
        "x-actor-type": x_actor_type or "user",
        "x-actor-id": x_actor_id or "me",
    }
    ident = identity_from_headers(headers)
    return ident


async def operator_context(
    session: AsyncSession,
    identity: Identity,
    x_reasoning: str | None = Header(default=None),
) -> OperatorContext:
    return OperatorContext(
        actor_id=identity.actor_id,
        actor_type=identity.actor_type,
        session=session,
        reasoning=x_reasoning,
    )
