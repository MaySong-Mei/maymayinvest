# Project Philosophy

This doc explains **what this project is and is not**. Read it before reading `ARCHITECTURE.md`. Architecture follows from philosophy; if you disagree with this doc, the architecture won't make sense.

---

## What this project is

**A self-evolving trading research system whose primary operator is Claude Code.**

Three claims packed in:

1. **Self-evolving** — the system is expected to accumulate trading skills, tools, and shortcuts over time. The skill library is a first-class artifact, on par with the order book and the audit log.
2. **Trading research** — not a trading product. The goal is to *discover and validate* trading approaches, not to ship a fixed strategy. Profit is a long-run consistency check, not the optimization target.
3. **Claude Code as primary operator** — CC is the decision-maker, the learner, and the one in the driver's seat. SDK-based agents and deterministic Python paths are shortcuts CC produces or invokes, not replacements for CC.

## What this project is not

- **Not** a productized trading platform aimed at scale, multi-user, or B2B
- **Not** a "trading bot" in the conventional sense (fire-and-forget strategy code)
- **Not** an "LLM-augmented system" where LLMs are components inside a traditional architecture
- **Not** a project whose success is measured by P&L in the short to medium run

If you came here expecting any of those, the architecture will look over-engineered or weirdly off-target. It is intentional.

---

## The CC-as-operator framing

The defining decision: **Claude Code is the body, SDK is a paddle.**

> *User's words (2026-05-22):* "我希望是做一个 CC 的外围 harness，能够自己演化出来对的交易 skill/tool/shortcut。本体是 CC 驱动的，而 SDK 只是手段。Coding agent 本体是操作员，不是修车工。SDK 更像是一种 tool 或 paddle 让 CC 更快反应。"

### What this means concretely

**CC is in the driver's seat.**
- Events wake CC up
- CC perceives (reads event, fetches context, looks at prices)
- CC decides (composes signals, evaluates risk, proposes orders)
- CC reasons (writes its rationale into the decision dossier)
- CC learns (reflects on past decisions, proposes new skills)

**SDK / deterministic code is what CC writes when it wants to be faster.**
- A reusable signal primitive becomes a Python function in `strategy/signals/`
- A recurring data-fetch pattern becomes a tool or a cached endpoint
- A well-validated strategy becomes a `Strategy` subclass that CC can invoke instead of re-deriving from scratch
- These are **products of CC's evolution**, not parallel systems competing with CC

**The harness is the unchangeable scaffolding around CC.**
- Perception (event sources, market data) — CC reads from it but doesn't own the polling
- Memory (decision dossiers, audit log, skill registry) — CC writes to it through capabilities, can't bypass it
- Actuators (broker adapters, order submission) — CC goes through `operator` capabilities with risk gate, audit, dry-run default
- Invariants (risk caps, reviewer outcome-blindness, skill approval gate) — CC can read these but **cannot modify them**, by design

### Why not just use the Agent SDK

A reasonable engineering instinct is: define tools, hand them to an Agent SDK loop, run it as a long-lived backend service.

We rejected this **as the primary path** for two reasons.

1. **The set of useful tools is unknown.** A traditional Agent SDK setup assumes you know the tools the agent needs and writes them up front. Here, *discovering which tools matter* is part of the work. CC's full toolbox (Bash, WebFetch, WebSearch, Chrome MCP, Skills, file I/O, ad-hoc code execution) is the search space. Constraining to a pre-declared tool set prematurely closes that search.
2. **CC can evolve its own scaffolding.** When CC needs a new capability — a new data source, a new parsing routine, a new signal — it can write the code and register it. An Agent SDK agent cannot rewrite its own tool list at runtime; a human developer must intervene. CC can.

The Agent SDK still has a role: it is **one possible implementation** of the `EventAnalyzer` interface (see ARCHITECTURE.md), the form CC takes when latency or scale forces a more constrained execution path. But it is downstream of CC, not parallel to it.

---

## The evaluation framing: right bet, not right gain

The single most important idea in this doc.

> *User's words (2026-05-22):* "pl 肯定为主，不过你要意识到这个本身是一个自我迭代的系统，长期肯定是 pl。但是就像德州，right bet 不一定是 right gain。我需要的是 right bet（评估正确的行动，类似 subagent review pr，aka 投资复盘）而不是 right gain。虽然有种 supervised training 的意思但是核心就是指标分析是 pl 但是优化方向是做出正确的操作。"

### The poker analogy

In poker, a skilled player who goes all-in with AA pre-flop has made the right bet — even if they lose to a runner-runner flush. A bad player who goes all-in with 7-2 offsuit has made the wrong bet — even if they hit two pair and win.

**Outcome is `decision × luck`. Luck is noise. Evaluating decisions by outcome is statistically broken at any sample size CC can plausibly accumulate.**

### Process-based supervision

This is a known idea in AI safety literature: **process-based evaluation** (judge the reasoning chain) vs **outcome-based evaluation** (judge by results). Process-based is safer because it resists specification gaming — an outcome-rewarded agent will eventually find ways to game the metric without actually getting better at the task.

We adopt process-based as the **optimization target**, and keep P&L as the **long-run consistency check**.

### How it works in this system

1. **Every CC decision is captured as a decision dossier.** Not just "what was done" — the full reasoning, alternatives considered, available information snapshot, confidence estimate.
2. **A separate reviewer subagent independently re-evaluates each decision.** Critically, the reviewer **only sees what CC saw at decision time**. No outcome leak. The reviewer judges: given this information, was this the right bet?
3. **The reviewer's judgment, paired with CC's decision, becomes a supervised sample** for CC's evolution. Patterns that produce repeatedly-judged-right bets become skill candidates.
4. **Skills are promoted to the registry only after human (your) approval.** Even repeated "right bet" judgments are necessary, not sufficient.
5. **P&L is tracked but not used as a learning signal in the short term.** Over months/years, persistent positive P&L should emerge if the right-bet machinery is working. If P&L diverges from reviewer judgments (e.g. reviewer says 90% right but the book is bleeding), something in the reviewer or the framework is systematically wrong — investigate, don't follow P&L.

### The reviewer must be outcome-blind

This is a hard invariant. The moment the reviewer can peek at how the trade actually went, it stops being process-based — hindsight bias contaminates every judgment ("you lost so it was wrong"). The reviewer is given only the information CC had at decision time. Subsequent prices, fill quality, final P&L — all withheld.

---

## What this implies for the system

| Aspect | Conventional trading system | This project |
|---|---|---|
| **Success metric** | Sharpe, P&L, drawdown | Right-bet rate, skill library depth, decision quality trajectory |
| **Failure mode** | Drawdown beyond limit | Reviewer flags decisions as poorly reasoned; or P&L diverges from reviewer scores |
| **Iteration unit** | Backtest run + manual code change | A decision dossier + reviewer judgment + (maybe) a skill proposal |
| **Optimization target** | Code-level: pick parameters, pick strategies | Process-level: improve CC's reasoning quality and information aggregation |
| **Role of human** | Strategy designer, parameter tuner, code maintainer | Skill approver, reviewer-of-reviewer (occasionally), system invariant defender |
| **Role of CC** | (Not present) | Operator, learner, skill author |
| **Role of code** | Implements the strategy | Implements the harness; CC operates from within it |
| **What can be deleted** | Bad strategies | Bad skills (with audit trail of why) |
| **Long-run product** | A trading algorithm | A library of right-bet patterns + a CC-shaped operator that knows how to use them |

---

## The hardest unsolved problem (read before getting excited)

This framing is internally consistent, but it depends on **one assumption that has to hold for the whole project to work**:

> The reviewer subagent must be able to judge "right bet" reliably from information-only basis, without ground truth outcomes.

If this assumption holds, the system can bootstrap. If it doesn't — if the reviewer is too noisy, too biased, or too easily gamed by CC's writing style — the whole loop becomes a generator of plausible-sounding garbage.

We don't know yet whether this assumption holds. Stage 0 of the build is partly an experiment to find out. **Be prepared to find that it doesn't, and have a fallback plan** (e.g. human review of every decision for the first N months, slower evolution).

Related concerns we're choosing to accept the risk of:
- **Specification gaming on the reviewer.** CC may learn to write decisions that *sound* right rather than *are* right. Mitigation: occasionally human-review the reviewer's own judgments — see "Goal evolution" section below for the structured form of this.
- **Skill bloat.** Without strong pruning, the skill library accumulates marginal-value entries. Mitigation: skills decay if not used in N days; periodic CC-led skill consolidation.
- **Distributional shift.** A skill learned in a calm market may misfire in a regime change. Mitigation: skills carry regime metadata; reviewer considers regime fit explicitly.

---

## Goal evolution as a process-based decision

The framing above pins **how we evaluate decisions** (right-bet, outcome-blind, reviewer-mediated). It does not pin **what counts as a right bet**. That definition lives in:

- the reviewer prompt (currently `v1-2026-05-22`)
- the flag taxonomy the reviewer applies
- the implicit standards the human applies when approving skills / promoting signals
- the metrics we use to track whether the system is "working"

**All of these will need to change.** We can't see far enough ahead at v1 to define them once. But the *mechanism* by which they change is itself a process-based decision, and it deserves the same supervision as the trading decisions the system makes.

### The invariant

> Goals, metrics, reviewer prompts, and evaluation criteria MAY evolve, but only through a structured proposal-and-review process with cool-down, versioning, and explicit human approval. No silent in-place updates. No "I'll just tweak this and re-run".

### Why this matters (the failure mode it prevents)

The most plausible way this project rots is **gradual goal drift**:

1. Reviewer keeps judging things `wrong_bet`
2. Operator (me, future-me, or a future CC instance) finds the reviewer annoying
3. Operator notices the reviewer prompt could be "tuned" — and writes a polished justification for relaxing it
4. Prompt gets updated; reviewer becomes more lenient
5. Right-bet rate goes up. The metric "looks healthier"
6. Nothing was learned. Specification gaming has eaten the supervision layer.

The operator at step 3 won't *know* it's gaming the metric. The rationalization will sound legitimate. This is the same dynamic that causes researchers to gradually weaken the criteria a study has to meet — Goodhart in slow motion.

### How we resist it

Five concrete mechanisms, listed in order of how seriously they should be applied:

1. **Versioning is mandatory, never in-place edit.** The reviewer prompt today is `v1-2026-05-22`. If we want to change it, the next version is `v2-<date>-<slug>`. The old version stays in the registry. Historical reviews retain their prompt-version stamp so we can always interpret them in their original context.

2. **Cool-down after change.** After a goal/metric/prompt update, **no further changes to that artifact for N days** (default 14). This prevents tuning-loop pathology where each unsatisfying run triggers another tweak.

3. **Proposal documents change in writing first.** A change is a markdown file in `v1/docs/proposals/<date>-<artifact>-<change>.md` containing: what changes, why, what metric is expected to move and in what direction, what would falsify the proposal. The proposal goes to git BEFORE the code change. A change without a proposal is suspect.

4. **Cool-headed reviewer (potentially the same subagent pattern this project uses for trading decisions).** A `goal_change_reviewer` subagent reads the proposal + git history of past changes to the same artifact + the system's current performance trajectory, and judges: is this change a right bet? Or is this tuning under frustration? Outcome-blind to whether the change "would have worked" — judges only whether the reasoning for changing is sound given pre-change information.

5. **Human-only final approval gate.** Even after reviewer judgment, the change requires explicit human merge of the proposal PR. This is non-negotiable. The system **cannot self-modify its own goals**, full stop. This sits at the same architectural tier as "manual promote-to-live" — a human action that cannot be exposed as a capability.

### What this enables

Paradoxically, *more* flexibility, not less. Because the change mechanism is trustworthy, we can lower the cost of admitting "the current goal is wrong":

- If reviewer prompt v1 is genuinely too strict, that's a legitimate finding — propose v2 with reasoning, cool down, get approved, ship
- If a metric we initially thought mattered turns out to be a distraction, propose dropping it from the dashboard
- If we discover a whole new way to characterize "right bet" (e.g. add a "regime fit" axis), propose adding it as a new dimension

**The point of process is not to prevent change; it is to make change observable.** A bad change with a paper trail is a learnable failure. A bad change that snuck in via a tactical commit is a poisoned data well.

### How the human side scales (or doesn't)

This whole structure depends on the human (you) actually reviewing the proposals. The user's view (2026-05-22): "review 可以大幅度解决 [specification gaming]". I (the current operator) agree directionally but want the dependency surface visible:

Effective supervision = `review coverage × review independence × review quality`

- **Coverage**: what % of proposals do you actually read? 100% is ideal; realistically declines under load
- **Independence**: do you read with fresh eyes, or rubber-stamp because you trust the operator?
- **Quality**: do you actively look for failure modes, or skim for plausibility?

The biggest risk is **time decay**. Today you'd read every proposal carefully. Three months in, after the operator has produced 30 reasonable-looking changes, you may start trusting and skimming. **That moment is when specification gaming actually enters the system.** Nothing in the harness prevents this; it must be a deliberate practice on your side.

Mitigations the operator can offer:

- Each proposal carries the operator's own `confidence` and an explicit `what I'm uncertain about` section — lets the user know which to scrutinize
- Periodic `audit cadence` reminders that force a meta-review of recent changes (e.g. every 10 commits, do a from-scratch read of the diff vs the project's stated goals)
- Old proposals stay in `v1/docs/proposals/` so you can see the shape of past reasoning and notice if it's drifted

None of this guarantees the human doesn't drift. But it makes drift visible after the fact.

---

## Goal state machine

The "Goal evolution" section above pins **the mechanism by which goals can change**. This section pins **the runtime state machine of a goal in flight** — how attempts, failures, and accumulated evidence move a goal toward "completed" or "needs revision."

This is a refinement, not a replacement. Both are needed: the mechanism (proposals, cool-down, human approval) describes governance; the state machine describes operations.

### The state machine

```
                  ┌──────────────────┐
                  │   goal active    │
                  └────────┬─────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  attempt N   │
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
         ┌────────────┐        ┌──────────────┐
         │ completed  │        │ not completed│
         └─────┬──────┘        └──────┬───────┘
               │                      │
               ▼                      ▼
        proposal: update         under thresholds?
        goal forward             (OR logic)
        (versioned)              ┌────────┴────────┐
                                 ▼                 ▼
                              under           thresholds hit:
                              attempts        REQUIRED dialogue
                              and cost        with reviewer
                                 │                 │
                                 ▼                 ▼
                              retry          ┌───────┴───────┐
                              (same goal)    ▼               ▼
                                          keep goal      propose goal
                                          (just unlucky) change
                                                         (via proposals/)
```

### The thresholds (OR logic — both apply)

Operator MAY retry the same goal silently *only while both* conditions hold:

- **Attempts on this exact goal < 3**
- **Cumulative cost for this goal < a budget cap**
  (default in v1: ~$2 of subscription credit equivalent, or ~15 minutes wall time, whichever is the relevant resource)

Once **either** is breached, retry without reviewer dialogue is prohibited. The operator may not "decide" to extend the threshold mid-attempt — that's exactly the spec-gaming entry point the rest of this doc tries to close.

### The two reviewer roles (architecturally separate)

The reviewer that judges trading decisions (or any single dossier) and the reviewer that participates in goal-change dialogues are **different subagents**, even if both are powered by the same underlying LLM.

| | Verdict reviewer | Dialogue reviewer |
|---|---|---|
| Input | one DecisionDossier | conversation thread + attempt history + operator's hypothesis about why goal might be wrong |
| Mode | single-shot, no follow-up | multi-turn (capped at N rounds, default 3) |
| Knowledge of outcomes | NO (architectural invariant; build_reviewer_input strips outcome fields) | YES — the dialogue reviewer needs to see what happened across attempts to weigh "goal is bad" vs "operator was unlucky" |
| Output | structured verdict | proposal recommendation: keep-goal / propose-change / escalate-to-human |
| Persistence | one row in `reviews` table | full transcript in `goal_dialogues` table (TBD) |
| Replaceability | swap-in different verdict reviewers for cross-check is fine | the dialogue reviewer is conceptually a different role; should not be substituted by verdict reviewer |

**Critical**: the dialogue reviewer is NOT outcome-blind. By design — it must see the attempt history to do its job. This is why it is architecturally separate. **A verdict reviewer that has ever been used as a dialogue reviewer is contaminated and must not be used as a verdict reviewer again**, because it now has outcome priors. Future implementation: separate subagent identities, separate prompts, separate spawn paths.

### Risks of multi-turn dialogue (and mitigations)

Multi-turn opens an attack surface that single-shot doesn't have. Operator gets more chances to "convince" the reviewer of its position. Mitigations:

1. **Cap rounds at 3.** Hard limit. If no resolution in 3, escalate to human.
2. **Full transcript persisted.** Audit later for "operator was clearly arguing into the reviewer's bias" patterns.
3. **Reviewer's verdict is non-final**: even after dialogue, any actual goal change goes through `proposals/` flow with cool-down + human approval. The dialogue reviewer recommends; the human approves.
4. **Operator must declare confidence in its own goal-change hypothesis up front**, before reading reviewer's first response. Prevents anchoring to whatever the reviewer says.

### Worked example: case 3 from the reviewer eval

The first time this state machine matters is now. From the eval addendum just above:

- **Goal under test**: the fixture's `expected_verdict="ambiguous"` for case 3
- **Attempt**: ran ClaudeCodeReviewer once
- **Outcome**: reviewer disagreed (`right_bet`), with a substantive argument that the fixture itself partially conceded
- **Attempt count**: 1
- **Cost incurred**: ~$0.10 (one claude -p call)

By the state machine, the operator MAY NOT yet treat this as "goal is wrong, change it." Both thresholds are well under:

- attempts < 3 ✓
- cost < cap ✓

The operator's options:
- Run the same fixture 1-2 more times, see if reviewer is consistent (if it consistently judges right_bet, the signal is stronger)
- Inspect the reviewer's argument more carefully — maybe the operator's `ambiguous` label was using the wrong category (situation-ambiguous vs decision-ambiguous, as the reviewer pointed out)
- Try with slightly perturbed fixtures to see what changes the verdict

Only if the reviewer's disagreement persists across multiple attempts AND the operator can't reconcile it does the operator have grounds to:
- Open a dialogue with a `goal_change_reviewer` subagent
- File a proposal in `proposals/` if the dialogue points toward a fixture or label change

This is the right read of "one disagreement is not yet evidence that the goal is wrong." It might be evidence. It might be noise. Wait for a stable pattern.

### Why "completed → update goal" matters too

Goals don't just need revision when they fail. Successful goals should explicitly **complete and be replaced with the next goal** rather than silently moving the bar.

Example: if the right-bet rate on hand-labeled fixtures stabilizes at >80% after several rounds of eval, the goal "demonstrate reviewer viability on hand-labeled cases" is **completed**. The next goal might be "demonstrate reviewer viability on dossiers produced by a real (non-stub) analyzer." This is a separate, harder, well-defined next thing — and it deserves a versioned goal of its own, not a silent extension of "viability" to a moving target.

Closing a goal triggers the same proposals/ workflow as changing one. Both are change events at the framing level.

### Quote that prompted this section (2026-05-23)

> "在 goal 的哲学上我想继续说一个类似的状态机：goal 未完成：再次尝试或者多次尝试积累了语义之后可以调整 goal（因为 goal 可能不合理）（最好有 reviewer 对话讨论）。goal 完成则更新 goal。"

The user's framing: goals are not just things to achieve; they are things to **operate** — including the explicit possibility that the goal itself is wrong and discovering that is part of the work.

---

## Anchoring quotes (from 2026-05-22 conversation)

These are kept because they are the ground truth of *why* this project is shaped this way. If a future implementation decision contradicts these, the implementation is wrong, not the quotes.

> "我希望是做一个 CC 的外围 harness，能够自己演化出来对的交易 skill/tool/shortcut。本体是 CC 驱动的，而 SDK 只是手段。"

> "Coding agent 本体是操作员，不是只当修车工。而 SDK 更像是一种 tool 或 paddle 让 CC 更快反应。"

> "right bet 不一定是 right gain。我需要的是 right bet ... 类似 subagent review pr，aka 投资复盘 ... 指标分析是 pl 但是优化方向是做出正确的操作。"

> "一步一步到 7×24" — meaning: architecture must permit eventual 24/7 operation, but v1 starts on local machine, present when user is.

> "得定指标然后这个指标或者 metric 是可以换的但是需要 review 的慎重更新, ... goal 可以 progressive 地变更但是要 right bet 和 flexibility 并存" — source of the "Goal evolution as a process-based decision" section. Goals are not pinned at v1; they evolve through the same supervised process that the system uses for trading decisions.

> "claude 确实有作弊率高的问题，但是 review 我认为可以大幅度解决" — acknowledgement of specification gaming as a real risk, and a belief that structured review can contain it. The "Goal evolution" section frames this as `review coverage × independence × quality`, with explicit note that time decay is the failure mode.

> "在 goal 的哲学上我想继续说一个类似的状态机：goal 未完成：再次尝试或者多次尝试积累了语义之后可以调整 goal（因为 goal 可能不合理）（最好有 reviewer 对话讨论）。goal 完成则更新 goal" — source of the "Goal state machine" section. Goals are operated, not just achieved — the possibility that the goal itself is wrong is a first-class operational state.

> "我觉得还有一个核心思路就是实验，你可以使用 subagent 进行实验，来证明证伪你的假设来推进" — source of the subagent-as-prober pattern (commit b49c50a). Subagent dispatch serves two distinct purposes: reviewing decisions (process supervision) and probing hypotheses (epistemic supervision). Both are clean-context tools that bypass the operator's accumulated bias.
