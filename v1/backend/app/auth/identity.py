"""v1 dev auth — single hardcoded user + agent identity via HTTP header.

For laptop-only Phase 1. Replace before any non-laptop deploy.

The point of identifying actor_type cleanly here is that the operator
audit log and quotas key off it.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Identity:
    actor_id: str
    actor_type: Literal["user", "agent"]


DEFAULT_USER = Identity(actor_id="me", actor_type="user")


def identity_from_headers(headers) -> Identity:
    # X-Actor-Type: agent  + X-Actor-Id: <name> → agent identity
    actor_type = headers.get("x-actor-type", "user")
    actor_id = headers.get("x-actor-id", "me")
    if actor_type not in ("user", "agent"):
        actor_type = "user"
    return Identity(actor_id=actor_id, actor_type=actor_type)
