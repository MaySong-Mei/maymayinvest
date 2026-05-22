# v1 Scope

Read after `PHILOSOPHY.md` and `ARCHITECTURE.md`. This doc states **what v1 will and will not include**, and the staged path from local-only to eventually 24/7.

## v1 vertical: US-equity event-driven right-side trading

Six original scope items have been deliberately collapsed into one vertical for v1:

- **In**: US equities (cash, long-only initially), event-driven entry (8-K / earnings / RSS news), right-side technical confirmation, manual + agent + auto trading modes
- **Out (deferred to Phase 2+)**: Crypto, A-shares, HK, long-term portfolio construction, asset allocation dashboard, intel sources beyond EDGAR + a small RSS set, Twitter/X
- **Out (likely never)**: Options, futures, HFT, sub-second strategies

This collapse is **a feature, not a constraint**. The previous "broad platform" scope was too wide to evolve a meaningful skill library inside. A narrow vertical gives CC a tighter feedback loop.

## What v1 must deliver (definition of done)

A working closed loop of:

1. **Event ingestion**: EDGAR 8-K poller + at least one RSS source (PR Newswire or SeekingAlpha) push events into the event bus
2. **CC-driven analysis**: An event triggers CC; CC produces a decision dossier (event signal + reasoning + alternatives + confidence)
3. **Technical confirmation**: Reuse existing `strategy/signals/trend.py` to gate the event signal on price action (breakout, MA cross, vol surge)
4. **Three execution modes selectable per signal**:
    - `notify`: dashboard surface + (optional) push, no order
    - `dry_run`: agent-produced OrderIntent, written to pending queue with full reasoning, no broker call
    - `auto`: subject to risk gate, submit to Alpaca paper (extended hours enabled)
5. **Decision reviewer subagent**: independently judges each decision on information-only basis, writes review row
6. **Audit + decision dossier**: every CC decision, every LLM call, every order intent, every review — fully captured
7. **Risk gate**: conservative defaults (single ≤ $500, daily notional ≤ $2000, max 3 open positions), UI-tunable
8. **Dashboard**: pending signals stream, decision dossier viewer (with reasoning + reviewer judgment), one-click promote/dismiss, audit log viewer, P&L tracker
9. **Skill registry (minimal)**: CC can propose new skill code; storage + version + human-approval flow; skills are invokable from CC's next analysis

## Staged delivery path

### Stage 0 — local arrival (target: 2-4 weeks)

**Mode of operation**: CC subprocess wakeup on events; user present; system runs while user's machine is on. No 24/7 expectation.

- Backend: FastAPI persistent on user's machine
- Event poll: APScheduler in-process, 30-60s cadence
- CC invocation: `claude -p` subprocess, JSON output parsed; rate-limited by Claude Code subscription
- Reviewer: separate `claude -p` subprocess with restricted prompt + outcome-blind input
- Broker: Alpaca paper, extended hours
- Storage: SQLite for dev simplicity, Postgres-compatible Alembic baseline kept (we've verified both work)
- Frontend: Next.js, runs on `localhost:3000`

**Stage 0 succeeds when**: one real EDGAR 8-K → CC dossier → reviewer judgment → dry-run intent visible in dashboard → user promotes → paper order fills in Alpaca → audit trail complete and inspectable.

### Stage 1 — local 24/7 (target: 1-2 months after Stage 0)

**Mode of operation**: same machine, no longer requires user present.

- FastAPI lifted to a Windows service (NSSM or task scheduler) or persistent terminal
- Power management tweaked so machine doesn't sleep
- CC subprocess still primary path; rate-limit usage monitored
- Hot paths that hit rate limits get **gracefully degraded** to direct `anthropic` SDK calls — same `EventAnalyzer` interface, swap implementation
- Push notifications (email or simple webhook) for user-required actions

### Stage 2 — cloud 24/7 (target: 3-6 months out, optional)

**Mode of operation**: VPS or container; user fully remote.

- **CC does not move to the cloud.** Cloud-side analyzer is a direct `anthropic` SDK implementation of `EventAnalyzer`, with a manually curated tool set
- CC remains on user's local machine in its **maintenance / evolution / Tier-2 role only**: handling incidents, reviewing audit trends, proposing new skills, doing PR reviews
- Skill registry syncs: skills authored in CC (local) flow to cloud analyzer (via PR + deploy)
- This stage is **optional and reconsidered when reached**; if Stage 1 is sufficient, don't build Stage 2

## What is deliberately not in v1

- **Crypto**: Phase 2 vertical, after US equity loop is stable
- **A-shares**: defer indefinitely; calendar, T+1, price limit, halt semantics are a separate research project
- **HK**: same as A-shares
- **Long-term portfolio + asset allocation**: separate vertical, not event-driven
- **Twitter / X firehose**: cost / access too unstable for v1
- **Sentiment scoring as a primary signal**: only as auxiliary input inside CC's reasoning, never as a standalone numeric signal driving orders
- **Real-money execution**: hard gate at the operator capability level; flipping to real requires explicit user action and is not in v1's automated path
- **Multi-account / multi-user**: single user, single account
- **Sophisticated backtest** beyond the existing event-driven runner: walk-forward, parameter sweep, regime conditioning are Phase 2

## Invariants reaffirmed for v1

These are non-negotiable. They are listed in detail in [`feedback_maymayinvest_invariants.md`](../../../.claude/...) memory and in `ARCHITECTURE.md`. Restating the v1-relevant subset here:

1. **Decimal money everywhere** — never float
2. **Fills are authoritative** — positions are derived from fills, not the other way around
3. **`tax_lots` tracked from day 1** — even though tax handling is a phase 2+ feature
4. **`client_order_id` (UUID) on every OrderIntent** — broker adapters must dedupe
5. **Agent dry-run default** — agent-initiated act capabilities default to dry-run; explicit `X-Execute: true` required
6. **Reasoning gate** — agent-initiated act capabilities require non-empty reasoning, denied otherwise (and **the denial is audited** — verified by regression test)
7. **Reviewer is outcome-blind** — given only what the operator saw at decision time
8. **Skill promotion requires human approval** — repeated right-bet judgments are necessary, never sufficient
9. **Risk gate caps are harness-level**, not strategy-level — CC cannot raise them by writing code; only user can, through UI
10. **Manual promote-to-live** — flipping the system from paper to real is a human-only action

## Non-goals for v1 (clarity for future-self)

- v1 does **not** need to make money
- v1 does **not** need to be "always right"
- v1 does **not** need to handle every possible event format
- v1 **does** need to produce: a working loop, a growing skill library, a decision history rich enough to learn from, and an architecture that doesn't have to be thrown away in Stage 1/2

## Success criteria for ending v1

v1 is "done enough" when **either** of:

- The closed loop has been running for 4+ weeks with at least 20 real CC decisions logged, reviewer judgments captured, at least 2 skills promoted to the registry, and no architectural rework needed for Stage 1 lift
- A clear architectural failure is identified (e.g. reviewer is too noisy, CC subprocess is too rate-limited, etc.) and a documented pivot to a Stage 1 / alternative analyzer plan is in place

Either outcome is acceptable. v1's job is to **answer questions about the framing**, not to *prove* it.
