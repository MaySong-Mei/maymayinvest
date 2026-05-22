# maymayinvest — Architecture

> **Read first:** [`PHILOSOPHY.md`](./PHILOSOPHY.md) and [`V1_SCOPE.md`](./V1_SCOPE.md). The architecture below makes sense only if you've internalized that this project is a **self-evolving trading research system with Claude Code as the primary operator**, optimizing for **right bet (process)** not right gain (outcome). If you haven't read those, the layering below will look over-engineered.

---

## Two documents in one

This file contains two layers of design:

1. **v0 platform skeleton (Sections "Recommended Stack" → "Critical Design Decisions" → "Phased Roadmap" → "Invariants")** — the original 2026-05-16 design for a general-purpose personal investment platform. Already partially implemented (the v1/ tree). Still load-bearing: stack, module map, adapter contracts, and invariants all remain authoritative.
2. **v1 evolution framework (Section "v1 — CC-centric harness")** — the 2026-05-22 reframing. Same underlying skeleton, but the system is now organized around **CC as the operating agent** with a decision-quality reviewer and a skill evolution loop. This supersedes Phase 1's framing (single-strategy paper-trade) and the Phase 3 "intel pipeline" framing — both are absorbed into the v1 harness.

When the two layers conflict, **v1 wins for the active scope** (US-equity event-driven). The v0 skeleton is preserved for what it gets right (clean modules, invariants, adapter design) and to give future verticals (crypto, A-shares) a known starting point.

---

## v1 — CC-centric harness

### The big picture

```
┌─ Harness (Python / FastAPI / Next.js, NOT modifiable by CC) ──────┐
│                                                                    │
│  Perception                                                        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ EDGAR poller │ RSS poller │ market data │ portfolio state   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          ↓ event bus                               │
│                                                                    │
│  Operator Agent  (this is CC — the body)                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ - Reads event from event bus                                │  │
│  │ - Uses CC-native tools: Read / Bash / WebFetch / WebSearch /│  │
│  │   Chrome MCP / Skills / file I/O                            │  │
│  │ - Uses CC-evolved tools: registered Skills, signal          │  │
│  │   primitives, deterministic scoring functions               │  │
│  │ - Calls `operator` capabilities for portfolio / orders      │  │
│  │ - Emits decision dossier: event, info gathered, alternatives│  │
│  │   considered, reasoning chain, confidence, OrderIntent      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          ↓                                         │
│                                                                    │
│  Decision Quality Reviewer  (separate subagent — outcome-blind)    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Input  = decision dossier ONLY (no subsequent prices, no    │  │
│  │          fill quality, no realized P&L, no future events)  │  │
│  │ Output = right-bet judgment + reasoning + flags             │  │
│  │ Writes → reviews table                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          ↓                                         │
│                                                                    │
│  Mode routing (existing operator surface)                          │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ notify  → dashboard + (optional) push                       │  │
│  │ dry_run → OrderIntent persisted, no broker call             │  │
│  │ auto    → risk gate → broker.submit_order                   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          ↓                                         │
│                                                                    │
│  Broker (Alpaca paper, extended hours)                             │
│  Audit log (existing actions table + new dossier/review/llm_call) │
│                                                                    │
│  Skill Evolution Loop  (CC, run on cadence, NOT on hot path)       │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ - CC reads its own decision + review history                │  │
│  │ - Identifies repeated right-bet patterns                    │  │
│  │ - Proposes new Skill code or signal primitive               │  │
│  │ - User approves via UI → skill registry → next decision     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

Invariant tier (CC cannot reach):
- Risk gate ceilings (config file CC has read-only on)
- Reviewer outcome-blindness (reviewer process runs with restricted env)
- Audit log append-only (DB-level constraint + capability decorator)
- Skill approval gate (UI action only, not a capability)
- Manual promote-to-live (UI action only, not a capability)
```

### EventAnalyzer interface — the swap point

CC is the v1 implementation of the operator agent. To keep Stage 1/2 evolution open (see V1_SCOPE.md), the system depends on an interface, not on CC directly:

```python
# app/intel/analyzer/base.py
class EventAnalyzer(Protocol):
    async def analyze(
        self,
        event: Event,
        context: AnalyzerContext,
    ) -> DecisionDossier:
        ...
```

Two implementations are planned, only the first is built in Stage 0:

- `ClaudeCodeAnalyzer` (Stage 0/1) — wakes a `claude -p` subprocess with a structured prompt, parses JSON output. Slow (5-30s) but has full CC toolbox. Primary path.
- `ClaudeAPIAnalyzer` (Stage 2, deferred) — direct `anthropic` SDK calls with a manually-curated tool set (web fetch, price fetch, etc.). Faster, cloud-deployable, narrower toolbox. Built when local 24/7 hits its limits.

Everything downstream of `EventAnalyzer.analyze()` is implementation-agnostic. Reviewer, mode routing, persistence, dashboard — all see only the `DecisionDossier`. This is the most important contract in v1.

### Why slower-but-richer beats faster-but-naive (for right-side)

Right-side entry **waits for trend confirmation by construction**. It is the opposite of "snipe the first second after the news." The hot-path latency budget is therefore **tens of seconds**, not sub-second.

This is good news for the CC-driven path: a 5-30s analysis is well inside the budget, and the extra time buys:

- Wider information aggregation (multi-source pull beyond the raw event)
- Hallucination resistance (CC can cross-check claims against price action and news)
- Retraction / amendment handling (PR Newswire and similar occasionally publish corrected versions; a slower path sees the correction)
- Avoidance of duplicate-event firing (same 8-K via SEC + Bloomberg + PR Newswire arrives at slightly different times; CC dedupes)

The **deterministic** mode-routing → risk-gate → broker step **must remain sub-second**. That stays in plain Python.

### The decision dossier (data structure)

Every CC analysis produces a `DecisionDossier`. This is the **central artifact** of the system — richer than `actions` audit, intended to be read by both the reviewer and (later) by CC itself during skill evolution.

Fields (final list TBD when implementing):

- `event_id`, `event_payload` — what triggered the analysis
- `available_info_snapshot` — everything CC could see at decision time: prices, portfolio, news fetched, regime indicators
- `reasoning_chain` — CC's narrative reasoning (markdown text + structured spans)
- `alternatives_considered` — explicit list, e.g. ["hold", "buy small", "buy full"] with why each was rejected
- `decision` — the OrderIntent (or "no action" with reason)
- `confidence` — CC's self-assessed confidence
- `skills_invoked` — which Skills / signal primitives CC called during analysis
- `llm_calls` — references to `llm_calls` table rows (every prompt/response captured)
- `latency_ms` — end-to-end analysis duration
- `created_at`

### The reviewer (decision quality)

A separate `claude -p` subprocess (or, in Stage 2, a separate API call), with a strict prompt:

> You are reviewing a trading decision made by another agent. **You are given only what the decision-making agent saw at decision time. You do not have access to subsequent prices, fill quality, or realized P&L.** Your job is to judge whether the bet was right *given the information available* — not whether it worked out.

Output (structured):
- `verdict`: `right_bet` / `wrong_bet` / `ambiguous`
- `reasoning`: why
- `flags`: list of concerns (e.g. "considered too few alternatives", "missed obvious downside catalyst", "reasoning chain doesn't justify confidence level")

Reviewer judgments are stored in a `reviews` table linked to the `DecisionDossier`. They never enter the dossier directly (avoid feedback loop to CC's own reasoning at decision time).

**Invariants on the reviewer:**

- Outcome-blind (architectural — reviewer process has no access to fills, prices after `event.ts`, or P&L)
- Persistent prompt — same prompt version for all reviews in a window, versioned in the registry
- Not a quorum — single reviewer is acceptable in v1; multi-reviewer ensembling is Phase 2

### Skill registry (minimal v1)

CC's evolved skills live in `app/intel/skills_registry/` (or a similar location). Each skill is:

- A Python module with a known interface (`analyze_event`, `score_signal`, `derive_indicator`, etc.)
- Versioned (semver or hash)
- Tagged with regime metadata, confidence prior, expected use case
- Has approval status: `proposed` / `approved` / `deprecated`

CC may **propose** skills (writes the file, opens a PR, leaves an entry in a `skill_proposals` table). Skills **only become invokable after user approval** through the UI. This is the human-in-the-loop gate for the evolution dimension.

Skill discovery is part of CC's analysis flow: at the start of each `analyze()` call, CC sees the list of `approved` skills relevant to the event type and may invoke any of them.

### What goes in the audit log vs. the dossier

| Thing | `actions` (existing) | `decisions` (new) | `reviews` (new) | `llm_calls` (new) |
|---|---|---|---|---|
| Order intent submitted | ✓ | (referenced) | — | — |
| Capability denial (e.g. agent without reasoning) | ✓ | — | — | — |
| CC's analysis of an event | — | ✓ | — | — |
| CC's reasoning chain for that analysis | — | ✓ | — | — |
| Reviewer's judgment | — | (referenced) | ✓ | — |
| Each individual LLM call (prompt + response + latency + tokens) | — | (referenced) | (referenced) | ✓ |

All four tables are **append-only** at the application level. `actions` already has this property (verified in regression tests).

### Where the harness invariants live

Five invariants are CC-untouchable. The mechanism enforcing each:

| Invariant | Enforced by |
|---|---|
| Risk gate ceilings | Config file in a read-only directory (CC has no write perms); enforced in `operator.submit_order` |
| Reviewer outcome-blindness | Reviewer subprocess invoked with restricted prompt + filtered context; reviewer Python module imports nothing that could leak future state |
| Audit append-only | `actions`, `decisions`, `reviews`, `llm_calls` writes go through capability functions, no direct DB session exposure to CC |
| Skill approval gate | Approval is a user-only UI action; not exposed as a `@capability` |
| Manual promote-to-live | Real-money broker keys only loaded when user explicitly promotes; promotion is a user-only UI action |

CC operating from inside its own runtime **could in principle bypass any of these by editing source code** — that's the cost of "CC as operator". The defense is:

- **Code review by user before promotion of any skill that touches harness layer** (skill registry approval flow)
- **Sandbox CC's file write permissions** in Stage 1+: CC can write to `skills_registry/proposed/` but not to `app/operator/` or config files
- **Audit log of CC's own file modifications** — tail `git diff` on each CC wake-up

This is acceptable for a single-user research system. It would not be acceptable for multi-user / production.

---

## v0 platform skeleton

Below is the original 2026-05-16 design. **Still authoritative for**: stack choice, module map, adapter contracts, invariants list, and as the starting point for future verticals (crypto, A-shares) outside v1's scope.

**No longer authoritative for**: phase ordering. The "Phased Roadmap" below is superseded by [`V1_SCOPE.md`](./V1_SCOPE.md). Phases 2-4 below describe *future verticals*, not v1's next steps.

### Recommended Stack

- **Backend:** Python 3.11+, FastAPI (async), Pydantic v2, SQLAlchemy 2.x, Alembic.
- **Frontend:** Next.js 14 (App Router), TypeScript, TanStack Query, TradingView Lightweight Charts + Recharts.
- **Data store:** PostgreSQL 16 + TimescaleDB (one DB; relational tables for orders/positions/users, hypertables for bars/ticks).
- **Backtest engine:** vectorbt as primary, wrapped behind an internal `Strategy` interface so the same code runs live.
- **Job runner:** APScheduler in-process for v0; upgradeable to Arq/Celery+Redis later.
- **Secrets:** `pydantic-settings` + `.env` locally; broker keys encrypted at rest, pluggable to OS keychain / Vault.

**Why:** the quant ecosystem (vectorbt, ccxt, akshare, tushare, ib_insync, alpaca-py) is Python. The dashboard needs a real FE framework — Streamlit/Dash can't carry auth + routing + rich charts at production quality.

---

### Module Map

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

### Critical Design Decisions

#### 0. AI-native: agents are first-class operators
The system exposes a **structured operator surface** — every meaningful action (read market, read portfolio, read news, propose order, submit order, cancel, allocate, kill switch) is both a FastAPI endpoint AND a registered agent tool, sharing the same Pydantic schema and the same validation path. A human clicking a UI button and an agent calling a tool go through the *same* code path, the *same* pre-trade risk checks, and the *same* append-only audit log (`actions` table: actor, intent, reasoning, outcome, timestamp).

`Strategy` (persistent code) is ONE kind of operator. An agent issuing ad-hoc orders is another. Both compose the same primitives. There is no separate "agent API" — the operator surface IS the API.

Manual promote-to-live: agents may propose live promotion of a strategy, but only a human UI click flips the bit. This is the human-in-the-loop gate.

#### 1. Same strategy code in backtest AND live
Strategy never touches a broker or a dataframe directly. It receives a `Context` on each step and emits `Signal` / `OrderIntent`. Two runners implement `Context`:
- `BacktestContext` — vectorbt-driven.
- `LiveContext` — driven by the realtime bus, routes through risk to `BrokerAdapter`.

The `Strategy` class imports only `domain` and `signals` — never `backtest` or `engine`. Enforce with an import-linter rule in CI from day 1. This is the single most important invariant.

#### 2. Multi-market reconciliation
- Every `Instrument` carries `(symbol, exchange, currency, calendar_id)`.
- Positions held in native currency; rollup to configured `base_currency` (default USD) at the `portfolio` layer.
- Trading calendars via `exchange_calendars`. Strategy `on_bar` only fires when its instrument's market is open.
- Storage + wire format: UTC ISO-8601. Conversion only at UI edge.

#### 3. Long-term vs short-term
Tagged on strategies + sub-portfolios, NOT separate broker accounts. `Strategy` declares `horizon: Literal["intraday","swing","position","long_term"]` and a `sub_portfolio_id`. Same broker account can hold a long-term AAPL position and a short-term AAPL swing trade; dashboard rolls them up separately by tag.

#### 4. 右侧交易 (right-side trading)
Not a module — a **signal style**. Lives in `strategy/signals/trend.py` as primitives (`breakout_confirmed`, `ma_cross_confirmed`, `pullback_to_ma`). Strategies compose them. See `strategy/examples/right_side_breakout.py`.

#### 5. Persistence split
Single PostgreSQL + TimescaleDB. Relational: users, accounts, instruments, orders, fills, positions, strategies, backtests, news_items. Hypertables: `bars_1m`, `bars_1d`, `ticks` (off by default). Parquet+DuckDB rejected — extra moving part, no live append.

#### 6. Monorepo
`backend/` + `frontend/` siblings. Shared types via FastAPI OpenAPI → `openapi-typescript` → `frontend/src/api/types.ts`.

#### 7. Secrets
Broker API keys encrypted at rest in `broker_credentials` table, key from OS keychain (or `.env`-supplied master key in v0). Never returned by the API in plaintext. Accessed via `auth.vault.get_broker_credentials(account_id)`.

---

### Directory Skeleton

See the tree created in this repo. Top level: `backend/`, `frontend/`, `infra/`, `docs/`.

---

### Phased Roadmap (v0 era — superseded for v1 active work)

> **For v1 active work, use [`V1_SCOPE.md`](./V1_SCOPE.md) staging instead.** The phases below describe future verticals (crypto, A-shares, multi-market) that v1 deliberately does not pursue.


#### Phase 1 — paper-trade one US stock end-to-end, agent-operable (2–3 weekends)
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

#### Phase 2 — strategy framework hardening + right-side library
- Full `signals/` library: breakout_confirmed, ma_cross_confirmed, pullback_to_ma, volume_surge, regime/liquidity filters.
- Strategy registry + UI enable/disable + sub-portfolio assignment.
- Risk module with pre-trade checks + UI kill switch.
- Sub-portfolios (long-term vs short-term tagging in DB + rollup in UI).
- Parameter sweep / walk-forward in backtest runner.
- Second broker.

#### Phase 3 — intel pipeline
- `intel.sources`: RSS, SEC EDGAR, 雪球.
- Ticker extraction + linking, news feed page, per-instrument news drawer.
- Polling jobs in scheduler.
- X/Twitter + earnings transcripts deferred.

#### Phase 4 — multi-market + portfolio rollup
- ccxt (Binance) and/or akshare (A-shares) provider+broker pair.
- FX rates pipeline, base-currency rollup.
- Calendar-aware engine.
- Cross-market allocation targets + rebalance proposer.

---

### Invariants (locked 2026-05-16, see feedback memory for full list)

> **For v1, add the invariants in the "v1 — CC-centric harness" section above** (reviewer outcome-blindness, skill approval gate, harness-tier write protection). The list below is the original platform-level invariants and remains in force.


Every PR is gated by these. Cheap to enforce now, expensive to retrofit.

#### Money & accounting
- All monetary fields = `Decimal`, Postgres `Numeric(20,8)`. Floats only inside vectorbt kernel.
- `fills` is authoritative. `positions` is a materialized view.
- `tax_lots` table exists from day 1, FIFO default, configurable per `sub_portfolio`.
- Bars stored unadjusted; `corporate_actions` separate; adjust on read for backtests only.

#### Time correctness
- `Bar.ts` = bar close, UTC. Provider adapters normalize at boundary.
- `Context.history()` only returns rows with `ts < ctx.now`. `BacktestContext` asserts. Tested.
- Storage + wire = UTC ISO-8601. Conversion at UI edge only.

#### Strategy framework
- `universe` = `Callable[[datetime], list[str]]`, never a static list.
- `Strategy` imports only `domain` + `strategy.signals`. Enforced by import-linter in CI.

#### Backtest fidelity
- `BacktestContext` takes pluggable `FillModel`. Default = `RealisticEquityFillModel` (next-bar open + 5bps slippage + commission field).
- Strategy source + param dict stored content-addressed alongside each backtest run.

#### Order lifecycle
- `OrderIntent.client_order_id: UUID` (UUIDv7). All adapters pass through.
- States: `pending_local → submitted → ack → filled | canceled`. Persist before broker call.
- Engine startup: reconcile via `list_orders` by client_order_id before resuming.

#### Agent safety (operator surface)
- `@capability` decorator: `max_calls_per_minute`, `max_notional_per_day`, `requires_reasoning_for=("agent",)`, `dry_run_default_for=("agent",)`.
- **Agents default to dry-run on `act` capabilities.** Must pass `execute=True`. Read capabilities run immediately.
- Global circuit breaker on `submit_order` trips kill switch automatically (in decorator).
- No "trust the human" bypass on risk checks.

#### Observability
- `structlog` JSON + `/metrics` Prometheus endpoint from day 1.
- Counters: `orders_submitted_total{actor_type}`, `capability_call_rate{actor_type,capability}`, `realized_pnl_5m`.
- Default alert: agent >N orders/min → kill switch. `actions` table is audit, NOT monitoring.

#### Secrets
- `auth.vault.get_broker_credentials(account_id)` only. v0 = `EnvVault`. Pluggable.
- Paper and live = separate account_ids with separate keys.
- Live promotion in UI re-prompts for passphrase (live key never in env).
- Pydantic field marker auto-redacts credentials in logs and `actions` payloads.

#### External-data realities
- Alpaca free tier = IEX-only (not SIP). Paper-feed prices differ from real SIP feeds by design.
- 雪球 has no public API; RSS scraping aggressively = blocked.
- SEC EDGAR = 10 req/s + user-agent email header.
- Rate limits encoded in each provider's constructor, not scattered `asyncio.sleep`.

---

### Confirmed Decisions (2026-05-16)

1. First broker: **Alpaca paper** (US stocks, free).
2. Postgres + TimescaleDB via Docker locally. ✓
3. Hosting: laptop now, Mac mini as always-on daemon later (Phase 2+).
4. No live trading accounts currently — Phase 4 (multi-market) stays Phase 4. Phase 2 second broker deferred.
5. **AI-native operator surface** — agents and humans share one tool/endpoint set. Strategy stays code-first; YAML/no-code not needed because agents replace it.
6. Paper → live: manual UI button (`promote to live`). Agents may propose; humans confirm.
