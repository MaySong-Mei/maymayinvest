"""Production wiring of router Protocols to operator capabilities.

The router (app.intel.router) depends on an OrderSubmitter Protocol — a
narrow interface of "submit(intent, reasoning) -> Order". Production
wiring needs that to go through the operator capability surface so it
inherits the capability decorator's behaviors (audit, quota, dry-run
default for agents, reasoning gate).

The import direction is intel -> operator (not the other way), preserving
the layering where intel knows about operator but operator does not know
about intel.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.order import Order, OrderIntent
from app.intel.router import OrderSubmitter
from app.operator.capabilities import submit_order
from app.operator.context import ActorType, OperatorContext


@dataclass
class OperatorOrderSubmitter(OrderSubmitter):
    """Implements router's OrderSubmitter Protocol by calling the operator
    capability `submit_order` with execute=True.

    Each submission constructs an OperatorContext from the values provided
    at construction time + the reasoning passed in by the router. This is
    deliberately not stateful w.r.t. reasoning — the router supplies
    reasoning per-call so each dossier gets its own audit row.

    Note on `execute=True`: this is the path the router uses ONLY for
    auto-mode dispatches. notify and dry_run NEVER call submit() at all
    (they enqueue pending_signals instead). So bypassing the agent's
    default dry-run is correct here: auto-mode is precisely the "user
    has pre-authorized execution" mode.
    """

    session: AsyncSession
    actor_id: str
    actor_type: ActorType = "agent"
    request_id: str | None = None

    async def submit(self, intent: OrderIntent, reasoning: str) -> Order:
        ctx = OperatorContext(
            actor_id=self.actor_id,
            actor_type=self.actor_type,
            session=self.session,
            reasoning=reasoning,
            request_id=self.request_id,
        )
        # Route through the protected capability wrapper so audit / quota /
        # reasoning-gate all run. execute=True opts out of dry-run-default
        # for agents — auto-mode is the only path that does this.
        result = await submit_order(ctx, intent, execute=True)
        return cast(Order, result)
