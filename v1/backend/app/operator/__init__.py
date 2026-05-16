"""Operator surface — humans and agents share one capability set.

Use:

    @capability(
        category="act",
        max_calls_per_minute=20,
        max_notional_per_day=Decimal("10000"),
        requires_reasoning_for=("agent",),
        dry_run_default_for=("agent",),
    )
    async def submit_order(ctx, intent: OrderIntent, *, execute: bool = False) -> Order:
        ...

The decorator:
  1. Validates input via the function's Pydantic-typed signature.
  2. Enforces per-actor quotas (calls/min, notional/day).
  3. Requires non-empty reasoning when the actor type matches `requires_reasoning_for`.
  4. Routes through dry-run for matching actor types unless execute=True is passed.
  5. Writes an entry to `actions` audit log on every invocation (ok / dry_run / denied / error).
  6. Registers the function in both the FastAPI router and the agent tool spec.
"""
from app.operator.context import OperatorContext  # noqa: F401
from app.operator.registry import capability, registry  # noqa: F401
