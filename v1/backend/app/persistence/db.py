from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


def _engine():
    return create_async_engine(get_settings().database_url_async, future=True, pool_pre_ping=True)


_engine_singleton = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = _engine()
    return _engine_singleton


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)
    return _sessionmaker


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
