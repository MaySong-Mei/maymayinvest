"""Auto-mount every registered capability as a POST endpoint.

URL convention:  POST /api/v1/op/<capability_name>
Body:            the capability's primary Pydantic input model (omitted if none)
Headers:         X-Actor-Type, X-Actor-Id, X-Reasoning, X-Execute (for act capabilities)

This gives humans a REST surface and agents (via OpenAPI -> tool spec) the
exact same call surface, satisfying the AI-native invariant.
"""
from __future__ import annotations

import inspect

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_identity
from app.auth.identity import Identity
from app.operator.context import OperatorContext
from app.operator.registry import CapabilityDenied, registry

router = APIRouter(prefix="/api/v1/op", tags=["operator"])


def _build_handler(cap_name: str):
    spec = registry.get(cap_name)
    InputModel = spec.input_model

    if InputModel is None:

        async def handler(
            session: AsyncSession = Depends(db_session),
            identity: Identity = Depends(get_identity),
            x_reasoning: str | None = Header(default=None),
            x_execute: str | None = Header(default=None),
        ):
            ctx = OperatorContext(
                actor_id=identity.actor_id,
                actor_type=identity.actor_type,
                session=session,
                reasoning=x_reasoning,
            )
            try:
                # call decorated wrapper without explicit args
                kwargs = {}
                if x_execute is not None:
                    kwargs["execute"] = x_execute.lower() in ("1", "true", "yes")
                result = await spec.func(ctx, **kwargs)
            except CapabilityDenied as e:
                raise HTTPException(status_code=403, detail=e.reason) from e
            return _serialize(result)

        handler.__name__ = f"op_{cap_name}"
        return handler

    async def handler(  # type: ignore[no-redef,valid-type]
        payload: InputModel,  # type: ignore[valid-type]
        session: AsyncSession = Depends(db_session),
        identity: Identity = Depends(get_identity),
        x_reasoning: str | None = Header(default=None),
        x_execute: str | None = Header(default=None),
    ):
        ctx = OperatorContext(
            actor_id=identity.actor_id,
            actor_type=identity.actor_type,
            session=session,
            reasoning=x_reasoning,
        )
        kwargs = {}
        if x_execute is not None:
            kwargs["execute"] = x_execute.lower() in ("1", "true", "yes")
        try:
            result = await spec.func(ctx, payload, **kwargs)
        except CapabilityDenied as e:
            raise HTTPException(status_code=403, detail=e.reason) from e
        return _serialize(result)

    handler.__name__ = f"op_{cap_name}"
    return handler


def _serialize(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


def mount_capabilities() -> None:
    # Force import of capability modules so @capability decorators register.
    from app.operator import capabilities  # noqa: F401

    for name in registry.list_names():
        handler = _build_handler(name)
        router.add_api_route(
            path=f"/{name}",
            endpoint=handler,
            methods=["POST"],
            name=name,
            summary=f"operator capability: {name}",
        )


_ = inspect  # quiet unused
