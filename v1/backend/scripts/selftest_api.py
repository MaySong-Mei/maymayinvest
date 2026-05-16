"""End-to-end self-test of the operator surface via FastAPI TestClient.

Exercises:
  - /healthz
  - /metrics
  - /api/v1/op/get_portfolio          (user, immediate)
  - /api/v1/op/get_last_price         (user)
  - /api/v1/op/submit_order           (agent, no reasoning -> denied)
  - /api/v1/op/submit_order           (agent, with reasoning, default -> dry_run)
  - /api/v1/op/submit_order           (agent, X-Execute: true -> filled)
  - /api/v1/op/get_open_orders        (after exec — empty since market filled)
  - /api/v1/op/get_portfolio          (post-trade, position visible)
  - SQLite check: actions audit rows written
"""
import json
from decimal import Decimal
from pathlib import Path

# Make SQLite the DB before app import.
import os
os.environ["DATABASE_URL_ASYNC"] = "sqlite+aiosqlite:///./selftest.db"

from fastapi.testclient import TestClient

from app.engine.broker_registry import get_broker
from app.main import app


def dump(title, resp):
    print(f"\n=== {title}  [{resp.status_code}] ===")
    try:
        print(json.dumps(resp.json(), indent=2, default=str))
    except Exception:
        print(resp.text[:400])


def main():
    # Seed an account row so FK-bearing inserts don't fail later.
    # Phase 1: orders use FK to accounts.id; we don't write orders to DB yet
    # (paper broker is in-memory), so we don't actually need it. But the audit
    # log writes regardless and only references actor_id (no FK), so this is fine.

    broker = get_broker()
    broker.set_last_price("AAPL", Decimal("220.50"))

    with TestClient(app) as client:
        dump("healthz", client.get("/healthz"))
        m = client.get("/metrics")
        print(f"\n=== /metrics  [{m.status_code}] === (first 200 chars)")
        print(m.text[:200])

        dump("get_portfolio (user)", client.post("/api/v1/op/get_portfolio"))
        dump(
            "get_last_price AAPL (user)",
            client.post("/api/v1/op/get_last_price", json={"symbol": "AAPL"}),
        )

        order_body = {
            "symbol": "AAPL",
            "side": "buy",
            "qty": "5",
            "type": "market",
        }

        dump(
            "submit_order (agent, NO reasoning -> 403 denied)",
            client.post(
                "/api/v1/op/submit_order",
                json=order_body,
                headers={"X-Actor-Type": "agent", "X-Actor-Id": "claude"},
            ),
        )

        dump(
            "submit_order (agent, with reasoning, default -> dry_run)",
            client.post(
                "/api/v1/op/submit_order",
                json=order_body,
                headers={
                    "X-Actor-Type": "agent",
                    "X-Actor-Id": "claude",
                    "X-Reasoning": "ma_cross_confirmed long entry test",
                },
            ),
        )

        dump(
            "submit_order (agent, X-Execute: true -> filled)",
            client.post(
                "/api/v1/op/submit_order",
                json=order_body,
                headers={
                    "X-Actor-Type": "agent",
                    "X-Actor-Id": "claude",
                    "X-Reasoning": "ma_cross_confirmed long entry test",
                    "X-Execute": "true",
                },
            ),
        )

        dump("get_open_orders (post-trade)", client.post("/api/v1/op/get_open_orders"))
        dump("get_portfolio (post-trade)", client.post("/api/v1/op/get_portfolio"))

    # SQLite audit table inspection
    import sqlite3

    db = Path("selftest.db")
    if db.exists():
        con = sqlite3.connect(db)
        print("\n=== actions audit (latest 6) ===")
        rows = list(
            con.execute(
                "SELECT actor_id, actor_type, capability, outcome_status, "
                "       substr(coalesce(error,''), 1, 80), substr(coalesce(reasoning,''),1,40) "
                "FROM actions ORDER BY ts DESC LIMIT 6"
            )
        )
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()
