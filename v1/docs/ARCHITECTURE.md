# maymayinvest — Architecture (v0)

Working architecture for the personal investment management system. Six scope items:
连接真实交易 API · 回测策略 · 情报追踪 · 长短期交易 · 资产配置 dashboard · 右侧交易（趋势确认追入）。

Markets supported via pluggable adapters: US stocks, A-shares, HK stocks, crypto.

---

## Recommended Stack

- **Backend:** Python 3.11+, FastAPI (async), Pydantic v2, SQLAlchemy 2.x, Alembic.
- **Frontend:** Next.js 14 (App Router), TypeScript, TanStack Query, TradingView Lightweight Charts + Recharts.
- **Data store:** PostgreSQL 16 + TimescaleDB (one DB; relational tables for orders/positions/users, hypertables for bars/ticks).
- **Backtest engine:** vectorbt as primary, wrapped behind an internal `Strategy` interface so the same code runs live.
- **Job runner:** APScheduler in-process for v0; upgradeable to Arq/Celery+Redis later.
- **Secrets:** `pydantic-settings` + `.env` locally; broker keys encrypted at rest, pluggable to OS keychain / Vault.

**Why:** the quant ecosystem (vectorbt, ccxt, akshare, tushare, ib_insync, alpaca-py) is Python. The dashboard needs a real FE framework — Streamlit/Dash can't carry auth + routing + rich charts at production quality.

---

## Module Map

| Module | Path | Responsibility |
|---|---|---|
| `core` | `backend/app/core` | Config, logging, time/calendar, money/FX, IDs. No business logic. |
| `domain` | `backend/app/domain` | Pure models: `Bar`, `Tick`, `Order`, `Fill`, `Position`, `Portfolio`, `Signal`, `Instrument`. No I/O. |
| `data.market` | `backend/app/data/market` | `MarketDataProvider` protocol + provider adapters (Alpaca, IBKR, ccxt, akshare, tushare). Historical loaders + realtime bus. |
| `data.reference` | `backend/app/data/reference` | Instrument master, trading calendars, corporate actions, FX. |
| `brokers` | `backend/app/brokers` | `BrokerAdapter` protocol + per-broker adapters (paper, alpaca, ibkr, binance, futu). |
| `strategy` | `backend/app/strategy` | `Strategy` ABC + `Context` protocol + signal library + registry. |
| `strategy/signals` | `backend/app/strategy/signals` | Composable signals — **this is where 右侧交易 lives** (breakout_confirmed, ma_cross_confirmed, pullback_resume, volume_surge). |
| `backtest` | `backend/app/backtest` | vectorbt-backed runner; consumes the same `Strategy` interface as live. |
| `engine` | `backend/app/engine` | Live event loop. Subscribes to data bus, ticks strategies, routes orders through risk to brokers. |
| `portfolio` | `backend/app/portfolio` | Multi-account/multi-currency rollup, target-vs-actual allocation, rebalancer. |
| `risk` | `backend/app/risk` | Pre-trade checks, limits, kill switch. |
| `intel` | `backend/app/intel` | News/info pipeline. v0: RSS + SEC EDGAR + 雪球. X/Twitter deferred. |
| `scheduler` | `backend/app/scheduler` | APScheduler jobs: historical refresh, signal scans, news polling, EoD snapshots. |
| `api` | `backend/app/api` | FastAPI routers + WebSocket. |
| `operator` | `backend/app/operator` | The unified operator surface. Each capability defined once as a Pydantic-validated function; auto-exposed as both a FastAPI endpoint and an agent tool (MCP server / tool registry). Writes to `actions` audit log. |
| `auth` | `backend/app/auth` | JWT + broker-credential vault. |
| `persistence` | `backend/app/persistence` | SQLAlchemy models, Alembic, repositories. |
| `frontend` | `frontend/` | Next.js dashboard. |

---

## Critical Design Decisions

### 0. AI-native: agents are first-class operators
The system exposes a **structured operator surface** — every meaningful action (read market, read portfolio, read news, propose order, submit order, cancel, allocate, kill switch) is both a FastAPI endpoint AND a registered agent tool, sharing the same Pydantic schema and the same validation path. A human clicking a UI button and an agent calling a tool go through the *same* code path, the *same* pre-trade risk checks, and the *same* append-only audit log (`actions` table: actor, intent, reasoning, outcome, timestamp).

`Strategy` (persistent code) is ONE kind of operator. An agent issuing ad-hoc orders is another. Both compose the same primitives. There is no separate "agent API" — the operator surface IS the API.

Manual promote-to-live: agents may propose live promotion of a strategy, but only a human UI click flips the bit. This is the human-in-the-loop gate.

### 1. Same strategy code in backtest AND live
Strategy never touches a broker or a dataframe directly. It receives a `Context` on each step and emits `Signal` / `OrderIntent`. Two runners implement `Context`:
- `BacktestContext` — vectorbt-driven.
- `LiveContext` — driven by the realtime bus, routes through risk to `BrokerAdapter`.

The `Strategy` class imports only `domain` and `signals` — never `backtest` or `engine`. Enforce with an import-linter rule in CI from day 1. This is the single most important invariant.

### 2. Multi-market reconciliation
- Every `Instrument` carries `(symbol, exchange, currency, calendar_id)`.
- Positions held in native currency; rollup to configured `base_currency` (default USD) at the `portfolio` layer.
- Trading calendars via `exchange_calendars`. Strategy `on_bar` only fires when its instrument's market is open.
- Storage + wire format: UTC ISO-8601. Conversion only at UI edge.

### 3. Long-term vs short-term
Tagged on strategies + sub-portfolios, NOT separate broker accounts. `Strategy` declares `horizon: Literal["intraday","swing","position","long_term"]` and a `sub_portfolio_id`. Same broker account can hold a long-term AAPL position and a short-term AAPL swing trade; dashboard rolls them up separately by tag.

### 4. 右侧交易 (right-side trading)
Not a module — a **signal style**. Lives in `strategy/signals/trend.py` as primitives (`breakout_confirmed`, `ma_cross_confirmed`, `pullback_to_ma`). Strategies compose them. See `strategy/examples/right_side_breakout.py`.

### 5. Persistence split
Single PostgreSQL + TimescaleDB. Relational: users, accounts, instruments, orders, fills, positions, strategies, backtests, news_items. Hypertables: `bars_1m`, `bars_1d`, `ticks` (off by default). Parquet+DuckDB rejected — extra moving part, no live append.

### 6. Monorepo
`backend/` + `frontend/` siblings. Shared types via FastAPI OpenAPI → `openapi-typescript` → `frontend/src/api/types.ts`.

### 7. Secrets
Broker API keys encrypted at rest in `broker_credentials` table, key from OS keychain (or `.env`-supplied master key in v0). Never returned by the API in plaintext. Accessed via `auth.vault.get_broker_credentials(account_id)`.

---

## Directory Skeleton

See the tree created in this repo. Top level: `backend/`, `frontend/`, `infra/`, `docs/`.

---

## Phased Roadmap

### Phase 1 — paper-trade one US stock end-to-end, agent-operable (2–3 weekends)
- docker-compose: Postgres + Timescale. Alembic baseline.
- `domain` models + `BrokerAdapter` + `MarketDataProvider` protocols.
- One market data provider: **Alpaca** (free, US stocks, historical + live).
- One broker adapter: Alpaca paper + in-process `paper` broker.
- `Strategy` ABC + `Context` protocol + `BacktestContext` + `LiveContext`.
- One example strategy: `dual_ma_trend` (right-side, MA-cross confirmation).
- **`operator` module**: `@capability` decorator + registry. Phase-1 capabilities — `get_portfolio`, `get_positions`, `get_quote`, `get_bars`, `submit_order`, `cancel_order`, `kill_switch`. Each auto-exposed as FastAPI endpoint + agent tool spec.
- `actions` audit table — every act-capability writes (actor, intent, reasoning, outcome).
- Backtest runner + `/backtests` endpoint returning equity curve JSON.
- Next.js skeleton: Dashboard, Backtests, Orders pages — all calling the operator endpoints.
- Auth: single hardcoded user with JWT; agent identities issued same JWT shape with `actor_type=agent`.

**Done when:** (a) backtest `dual_ma_trend` on AAPL 2020–2024 and view equity curve in browser; (b) start live engine against Alpaca paper, watch orders submit, positions update in dashboard; (c) Claude (or any agent) can call the same `submit_order`/`get_portfolio` capabilities and the action shows up in the audit log with `actor_type=agent`.

### Phase 2 — strategy framework hardening + right-side library
- Full `signals/` library: breakout_confirmed, ma_cross_confirmed, pullback_to_ma, volume_surge, regime/liquidity filters.
- Strategy registry + UI enable/disable + sub-portfolio assignment.
- Risk module with pre-trade checks + UI kill switch.
- Sub-portfolios (long-term vs short-term tagging in DB + rollup in UI).
- Parameter sweep / walk-forward in backtest runner.
- Second broker.

### Phase 3 — intel pipeline
- `intel.sources`: RSS, SEC EDGAR, 雪球.
- Ticker extraction + linking, news feed page, per-instrument news drawer.
- Polling jobs in scheduler.
- X/Twitter + earnings transcripts deferred.

### Phase 4 — multi-market + portfolio rollup
- ccxt (Binance) and/or akshare (A-shares) provider+broker pair.
- FX rates pipeline, base-currency rollup.
- Calendar-aware engine.
- Cross-market allocation targets + rebalance proposer.

---

## Invariants (locked 2026-05-16, see feedback memory for full list)

Every PR is gated by these. Cheap to enforce now, expensive to retrofit.

### Money & accounting
- All monetary fields = `Decimal`, Postgres `Numeric(20,8)`. Floats only inside vectorbt kernel.
- `fills` is authoritative. `positions` is a materialized view.
- `tax_lots` table exists from day 1, FIFO default, configurable per `sub_portfolio`.
- Bars stored unadjusted; `corporate_actions` separate; adjust on read for backtests only.

### Time correctness
- `Bar.ts` = bar close, UTC. Provider adapters normalize at boundary.
- `Context.history()` only returns rows with `ts < ctx.now`. `BacktestContext` asserts. Tested.
- Storage + wire = UTC ISO-8601. Conversion at UI edge only.

### Strategy framework
- `universe` = `Callable[[datetime], list[str]]`, never a static list.
- `Strategy` imports only `domain` + `strategy.signals`. Enforced by import-linter in CI.

### Backtest fidelity
- `BacktestContext` takes pluggable `FillModel`. Default = `RealisticEquityFillModel` (next-bar open + 5bps slippage + commission field).
- Strategy source + param dict stored content-addressed alongside each backtest run.

### Order lifecycle
- `OrderIntent.client_order_id: UUID` (UUIDv7). All adapters pass through.
- States: `pending_local → submitted → ack → filled | canceled`. Persist before broker call.
- Engine startup: reconcile via `list_orders` by client_order_id before resuming.

### Agent safety (operator surface)
- `@capability` decorator: `max_calls_per_minute`, `max_notional_per_day`, `requires_reasoning_for=("agent",)`, `dry_run_default_for=("agent",)`.
- **Agents default to dry-run on `act` capabilities.** Must pass `execute=True`. Read capabilities run immediately.
- Global circuit breaker on `submit_order` trips kill switch automatically (in decorator).
- No "trust the human" bypass on risk checks.

### Observability
- `structlog` JSON + `/metrics` Prometheus endpoint from day 1.
- Counters: `orders_submitted_total{actor_type}`, `capability_call_rate{actor_type,capability}`, `realized_pnl_5m`.
- Default alert: agent >N orders/min → kill switch. `actions` table is audit, NOT monitoring.

### Secrets
- `auth.vault.get_broker_credentials(account_id)` only. v0 = `EnvVault`. Pluggable.
- Paper and live = separate account_ids with separate keys.
- Live promotion in UI re-prompts for passphrase (live key never in env).
- Pydantic field marker auto-redacts credentials in logs and `actions` payloads.

### External-data realities
- Alpaca free tier = IEX-only (not SIP). Paper-feed prices differ from real SIP feeds by design.
- 雪球 has no public API; RSS scraping aggressively = blocked.
- SEC EDGAR = 10 req/s + user-agent email header.
- Rate limits encoded in each provider's constructor, not scattered `asyncio.sleep`.

---

## Confirmed Decisions (2026-05-16)

1. First broker: **Alpaca paper** (US stocks, free).
2. Postgres + TimescaleDB via Docker locally. ✓
3. Hosting: laptop now, Mac mini as always-on daemon later (Phase 2+).
4. No live trading accounts currently — Phase 4 (multi-market) stays Phase 4. Phase 2 second broker deferred.
5. **AI-native operator surface** — agents and humans share one tool/endpoint set. Strategy stays code-first; YAML/no-code not needed because agents replace it.
6. Paper → live: manual UI button (`promote to live`). Agents may propose; humans confirm.
