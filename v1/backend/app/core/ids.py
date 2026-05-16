"""IDs used at module boundaries.

`new_client_order_id` returns a UUID. UUIDv4 for v1; switch to UUIDv7 when a
maintained Python wheel lands. Time-sortability is nice-to-have, not required —
the persistence layer indexes by `created_at` separately.
"""
from uuid import UUID, uuid4


def new_client_order_id() -> UUID:
    return uuid4()
