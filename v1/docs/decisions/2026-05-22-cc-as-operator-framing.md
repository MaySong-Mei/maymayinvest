# Decision Record: CC as Operator Framing

**Date**: 2026-05-22
**Status**: Adopted
**Supersedes**: Phase 1 framing in original `ARCHITECTURE.md` (2026-05-16)
**Related docs**: [`PHILOSOPHY.md`](../PHILOSOPHY.md), [`V1_SCOPE.md`](../V1_SCOPE.md), updated [`ARCHITECTURE.md`](../ARCHITECTURE.md)

---

## Why this record exists

This is the most important architectural decision of the project so far, and it was made through a conversation that **changed direction multiple times**. The chat itself contains the reasoning, the dead-ends explored, and the user's two key insights that pivoted the architecture. Future-self (and future-CC) should be able to reconstruct *why* the system looks the way it does without re-running the discussion.

This is also a hedge against memory loss: CC's memory between sessions is fragile; the user's memory of which arguments mattered is human; this file is the durable record.

---

## What was decided

The project pivots from "general-purpose personal investment platform" (the 2026-05-16 framing, ~5500 lines of scaffolding already shipped) to:

> **A self-evolving trading research system whose primary operator is Claude Code, optimizing for right-bet decision quality (process-based supervision) rather than right-gain (P&L outcome).**

Concretely:
- v1 vertical narrows to **US-equity event-driven right-side trading** (Crypto, A-shares, HK explicitly deferred)
- **CC is the operator agent** — not the SDK, not a traditional headless bot
- The system is structured as a **harness around CC**, with CC reading from perception, calling capabilities, and emitting decision dossiers
- A **separate reviewer subagent** judges each decision *on information-only basis* (outcome-blind) — verdict feeds CC's evolution loop
- **Skills** authored or proposed by CC require user approval before entering the active registry
- **P&L is tracked but is not the optimization target** — it's a long-run consistency check on the reviewer/framework
- Architecture must be **7×24-ready but Stage 0 starts local** (user's machine, user present)

## What was rejected (and why)

### Rejected: pure Agent SDK as primary path
- **Why considered**: faster, cheaper, productionizable, structured I/O, observability
- **Why rejected**: The set of tools CC might need is *part of the search*. SDK forces a pre-declared toolset that closes off the discovery process. Also: SDK agents can't author their own scaffolding; CC can.
- **Where SDK lives instead**: As one possible implementation of `EventAnalyzer` for Stage 2 cloud lift, when local CC runtime stops being sufficient. Same interface, swappable.

### Rejected: `claude` CLI as 7×24 backend daemon (the "WHY THIS IS WEIRD" path)
- **Why considered**: User initially asked for CC to *be* the runtime
- **Why rejected after explanation**: cold-start 3-10s × hundreds of events/day; subscription rate limits not designed for production workload; output parsing is hack-prone (`-p` markdown vs structured tool_use); no stateful multi-turn; deployment to unattended server requires Node + OAuth + login state maintenance
- **The user's correct counter-insight**: CC's value is the *built-in tool ecosystem* (Bash, WebFetch, Chrome MCP, Skills) and *self-modification capability* — these are real and not replicable in pure SDK. The conclusion: use CC, but accept it as a slow path inside a properly-designed harness, not pretend it's a low-latency service.

### Rejected: "fast SDK on hot path, CC only for maintenance"
- **Why considered (my own proposal)**: Clean separation of concerns, fast where it matters, CC where flexibility helps
- **Why rejected after the user's pushback**: This treats CC as a mechanic (修车工) when the user explicitly wants CC as the operator (操作员). Same words, different roles. The mechanic framing makes CC peripheral; the operator framing makes CC central. The user's vision is the latter.

### Rejected: "sub-second event response is necessary for event-driven trading"
- **Why I initially assumed it**: Event-driven sounds like "snipe the news"
- **Why rejected after the user's pushback**: Right-side trading **by construction** waits for trend confirmation. The whole point is *not* to be first; the point is to enter after the move has shown itself. Low latency causes more harm than good here — it amplifies hallucinations, miss retractions, and over-reactions. The trade-off is *information completeness vs speed*, and right-side strongly prefers completeness.

---

## The two user insights that pivoted the architecture

### Insight 1: CC's built-in toolbox is the differentiator
> "你拥有全套 internet access 工具，而 SDK 没有。"

This forced a reweighting of the CC-vs-SDK trade-off table. CC's `Bash`/`WebFetch`/`WebSearch`/`Chrome MCP`/Skills aren't trivially replicable — they would each be days of work to assemble in an SDK setup, and the Skill ecosystem in particular is not portable. This made "CC as operator" defensible despite its other costs.

### Insight 2: Right bet, not right gain
> "right bet 不一定是 right gain ... 类似 subagent review pr，aka 投资复盘 ... 指标分析是 pl 但是优化方向是做出正确的操作"

This single sentence collapsed a problem I (CC) had flagged as the *hardest unsolved part of the project* — reward signal for self-improvement — into a tractable design: process-based supervision via outcome-blind reviewer. This is the moment the system became coherent rather than aspirational.

---

## The discussion's shape (for posterity)

The conversation moved through these states (rough order):

1. **Status check** — repo is empty README locally; remote has 5500 lines of Phase 1 scaffolding (operator surface, paper broker, signals, Next.js dashboard). All tests green; selftest passes end-to-end against SQLite.
2. **Feasibility audit** — I (CC) gave a rather honest "what I can / can't deliver" breakdown. Conclusion: high feasibility for engineering, low feasibility for strategy alpha and live operations.
3. **Scope collapse** — user pivots: "do one thing — event-driven right-side trading." This was the most important *product* decision.
4. **Architecture pre-flight questions** — clarifications on timescale (event-driven), market (US first), modes (notify/dry-run/auto), intel scope (LLM event reading + technical confirm), risk gate.
5. **CC vs SDK debate (round 1)** — I argued strongly for API/SDK as production-grade. User pushed back: wants CC to be the operator.
6. **The "WHY THIS IS WEIRD" enumeration** — at user request, I laid out 10 reasons running CC as a backend daemon is unconventional/risky.
7. **User counter-insight (operator vs mechanic)** — user reframes: CC = full operator, SDK = paddle/tool that CC produces. This is not negotiable; it's the project's identity.
8. **My genuine update** — I realized I was translating the user's idea into "standard architecture" and missing the actual point. The conversation moved from technical debate to product framing.
9. **The right-bet insight** — user solves the reward-signal problem in one sentence: process-based supervision.
10. **Architecture redrawn** — three-stage pipeline (CC analysis → reviewer → mode routing), skill evolution loop, harness-tier invariants CC can't touch.
11. **Documentation pass** — `PHILOSOPHY.md` + `V1_SCOPE.md` + updated `ARCHITECTURE.md` + this decision record + memory updates.

---

## Open questions that survived this discussion

These are flagged for v1's empirical phase to answer:

1. **Can the reviewer reliably judge right-bet on information-only basis?** Without this assumption holding, the entire evolution loop becomes a noise generator. v1's first weeks should explicitly stress-test this.
2. **What's CC's actual rate-limit ceiling on the Claude Code subscription?** If events trigger faster than CC can be woken, queueing or degradation strategy is needed.
3. **How is skill bloat managed?** No good answer yet. Initial idea: decay metadata + periodic consolidation passes.
4. **How does the reviewer detect when CC is "writing convincing-sounding decisions" vs. making good decisions?** This is the specification-gaming risk on the reviewer itself.
5. **When does CC graduate to writing harness code, vs only writing skills?** v1 keeps a hard wall (CC can only propose; harness code is human-written). At some point this wall may move.

---

## Promises that this record locks in

The user has *not yet seen the implementation* of any of this — only the design discussion. The implementation that follows must:

- Define `EventAnalyzer` as an interface from day 1
- Make CC the first implementation, not the only one (no hard-coding of subprocess behavior into business logic)
- Capture decision dossiers richer than the existing `actions` audit (reasoning chain, alternatives, available info snapshot)
- Run the reviewer as a *separate* invocation with restricted context (not in-process with the operator agent)
- Provide UI for promote/dismiss + skill approval — these are the *only* paths for human-in-the-loop gates
- Preserve every invariant from the existing 2026-05-16 list, plus the new harness-tier invariants

If implementation drifts from these, the architecture is wrong, not the doc.
