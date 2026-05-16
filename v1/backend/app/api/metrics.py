"""Prometheus counters required by invariants.

Wired here once and read by the operator wrapper / api layer.
"""
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

ORDERS_SUBMITTED = Counter(
    "orders_submitted_total",
    "Orders submitted",
    ["actor_type"],
)

CAPABILITY_CALLS = Counter(
    "capability_call_total",
    "Operator capability invocations",
    ["actor_type", "capability", "status"],
)

CAPABILITY_LATENCY = Histogram(
    "capability_latency_seconds",
    "Latency of operator capability invocations",
    ["capability"],
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
