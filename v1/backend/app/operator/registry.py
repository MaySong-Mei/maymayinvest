"""@capability decorator + registry — the AI-native operator core."""
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import insert

from app.core.logging import get_logger
from app.core.time import utcnow
from app.operator.context import ActorType, OperatorContext
from app.operator.quota import quota_store
from app.persistence.models import Action

log = get_logger("operator")

Category = Literal["read", "act", "meta"]


class CapabilityDenied(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class CapabilitySpec:
    """`func` is the protected wrapper (REST + agent dispatch).
    `raw` is the undecorated function, kept for direct unit-test access.
    """

    name: str
    category: Category
    func: Callable[..., Awaitable[Any]]
    raw: Callable[..., Awaitable[Any]]
    input_model: type[BaseModel] | None
    output_model: type | None
    max_calls_per_minute: int | None = None
    max_notional_per_day: Decimal | None = None
    requires_reasoning_for: tuple[ActorType, ...] = ()
    dry_run_default_for: tuple[ActorType, ...] = ()
    audits: bool = True


@dataclass
class Registry:
    capabilities: dict[str, CapabilitySpec] = field(default_factory=dict)

    def register(self, spec: CapabilitySpec) -> None:
        if spec.name in self.capabilities:
            raise ValueError(f"duplicate capability: {spec.name}")
        self.capabilities[spec.name] = spec

    def get(self, name: str) -> CapabilitySpec:
        return self.capabilities[name]

    def list_names(self) -> list[str]:
        return sorted(self.capabilities)


registry = Registry()


def _primary_input_model(func) -> type[BaseModel] | None:
    # `from __future__ import annotations` makes annotations strings; resolve.
    try:
        annotations = inspect.get_annotations(func, eval_str=True)
    except Exception:
        annotations = getattr(func, "__annotations__", {})
    sig = inspect.signature(func)
    for p in sig.parameters.values():
        if p.name in ("ctx", "execute"):
            continue
        ann = annotations.get(p.name, p.annotation)
        if inspect.isclass(ann) and issubclass(ann, BaseModel):
            return ann
    return None


def _intent_notional(intent: Any) -> Decimal:
    qty = getattr(intent, "qty", None)
    price = getattr(intent, "limit_price", None) or getattr(intent, "price", None)
    if qty is not None and price is not None:
        return Decimal(qty) * Decimal(price)
    return Decimal("0")


async def _audit(
    ctx: OperatorContext,
    spec: CapabilitySpec,
    intent_payload: dict,
    status: str,
    outcome: dict | None,
    error: str | None,
) -> None:
    if not spec.audits:
        return
    await ctx.session.execute(
        insert(Action).values(
            id=uuid4(),
            actor_id=ctx.actor_id,
            actor_type=ctx.actor_type,
            capability=spec.name,
            intent=intent_payload,
            reasoning=ctx.reasoning,
            outcome_status=status,
            outcome=outcome,
            error=error,
            ts=utcnow(),
        )
    )


def _to_jsonable(model: BaseModel | dict | None) -> dict:
    if model is None:
        return {}
    if isinstance(model, BaseModel):
        return model.model_dump(mode="json")
    return dict(model)


def capability(
    *,
    name: str | None = None,
    category: Category = "read",
    max_calls_per_minute: int | None = None,
    max_notional_per_day: Decimal | None = None,
    requires_reasoning_for: tuple[ActorType, ...] = (),
    dry_run_default_for: tuple[ActorType, ...] = (),
    audits: bool = True,
):
    """Register an async function as a capability. See app.operator docstring."""

    def deco(func: Callable[..., Awaitable[Any]]):
        ret = inspect.signature(func).return_annotation
        # spec is created first with a placeholder `func`; we patch it to the
        # wrapper at the end so the registry exposes the protected entrypoint.
        spec = CapabilitySpec(
            name=name or func.__name__,
            category=category,
            func=func,  # patched below
            raw=func,
            input_model=_primary_input_model(func),
            output_model=ret if ret is not inspect.Signature.empty else None,
            max_calls_per_minute=max_calls_per_minute,
            max_notional_per_day=max_notional_per_day,
            requires_reasoning_for=requires_reasoning_for,
            dry_run_default_for=dry_run_default_for,
            audits=audits,
        )
        registry.register(spec)

        async def wrapper(ctx: OperatorContext, *args, execute: bool | None = None, **kwargs):
            intent_payload: dict = {}
            if args and isinstance(args[0], BaseModel):
                intent_payload = _to_jsonable(args[0])
            elif kwargs:
                intent_payload = {
                    k: _to_jsonable(v) if isinstance(v, BaseModel) else v for k, v in kwargs.items()
                }

            if ctx.actor_type in spec.requires_reasoning_for and not (ctx.reasoning or "").strip():
                err = f"{spec.name} requires non-empty reasoning for actor_type={ctx.actor_type}"
                await _audit(ctx, spec, intent_payload, "denied", None, err)
                await ctx.session.commit()  # keep denial audit even though we raise
                raise CapabilityDenied(err)

            if spec.max_calls_per_minute is not None:
                count = quota_store().record_call(ctx.actor_id, spec.name)
                if count > spec.max_calls_per_minute:
                    err = (
                        f"{spec.name} exceeded {spec.max_calls_per_minute}/min "
                        f"for actor={ctx.actor_id}"
                    )
                    await _audit(ctx, spec, intent_payload, "denied", None, err)
                    await ctx.session.commit()  # keep denial audit even though we raise
                    raise CapabilityDenied(err)

            notional = _intent_notional(args[0]) if args else Decimal("0")
            if spec.max_notional_per_day is not None and notional > 0:
                total = quota_store().record_notional(ctx.actor_id, notional)
                if total > spec.max_notional_per_day:
                    err = (
                        f"{spec.name} would exceed daily notional cap "
                        f"({total} > {spec.max_notional_per_day}) for actor={ctx.actor_id}"
                    )
                    await _audit(ctx, spec, intent_payload, "denied", None, err)
                    await ctx.session.commit()  # keep denial audit even though we raise
                    raise CapabilityDenied(err)

            dry_run = ctx.actor_type in spec.dry_run_default_for and not execute
            if dry_run:
                log.info(
                    "capability.dry_run",
                    capability=spec.name,
                    actor_id=ctx.actor_id,
                    actor_type=ctx.actor_type,
                )
                outcome = {"dry_run": True, "intent": intent_payload}
                await _audit(ctx, spec, intent_payload, "dry_run", outcome, None)
                return {"dry_run": True, "intent": intent_payload}

            try:
                result = await func(ctx, *args, **kwargs)
            except Exception as e:  # noqa: BLE001
                await _audit(ctx, spec, intent_payload, "error", None, repr(e))
                raise
            outcome_payload = (
                _to_jsonable(result)
                if isinstance(result, BaseModel)
                else (result if isinstance(result, dict) else {"value": str(result)})
            )
            await _audit(ctx, spec, intent_payload, "ok", outcome_payload, None)
            log.info(
                "capability.ok",
                capability=spec.name,
                actor_id=ctx.actor_id,
                actor_type=ctx.actor_type,
            )
            return result

        wrapper.__capability_spec__ = spec  # type: ignore[attr-defined]
        wrapper.__name__ = spec.name
        spec.func = wrapper  # registry now exposes the protected wrapper
        return wrapper

    return deco
