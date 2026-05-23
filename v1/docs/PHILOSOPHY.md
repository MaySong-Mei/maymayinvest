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

## Pre-reg amendment protocol

### What this section is

The "Goal state machine" and "Goal evolution" sections describe how *open-ended goals* evolve. This section addresses a narrower, sharper case: **what happens when a pre-registered rule fires and the operator, looking at the result, believes the rule's disposition is wrong**.

The two questions look similar but their failure modes are inverse:

- Goal evolution failure mode: *governance bloat* — making progress requires endless meta-process.
- Pre-reg amendment failure mode: *spec-gaming* — operator retroactively reinterprets pre-registered outcomes to avoid dispositions it didn't like.

The protocol below is the *interaction layer* between two existing invariants that this project's framing depends on equally:

- **P1 — Pre-registered rules are binding once outcome arrives.** Without this, pre-registration is theater; the operator can always "decide differently" once results land.
- **P2 — Goals/rules/prompts can evolve through structured proposals.** Without this, the system cannot incorporate genuine learning (e.g. discovering a higher-order invariant the pre-reg rule violated).

Both invariants are necessary. Their conflict at the moment of "rule fired, operator wants to amend" needs an explicit protocol, not operator judgment.

### Quote that prompted this section (2026-05-23)

> "如果明天下雨，我就取消比赛。第二天但我现在觉得小雨其实可以比赛，所以我提议改规则。我能理解现在的困境是既当裁判又当运动员的子问题。所以我觉得应该按照某种流程 file 一个修正案去修正设计，当情况是执行了，但是再有新的现实或者推论出现的时候，回头修正标准的问题。"

The "judge and athlete" framing names the structural problem this protocol solves: an operator looking at a pre-registered rule it triggered cannot also be the impartial judge of whether the rule should be amended. The protocol forces the judging role onto a fresh-brain reviewer + human, while preserving the operator's responsibility to surface evidence.

### The protocol (8 clauses, user-authored)

1. **A triggered pre-registered rule must first be acknowledged as triggered.**

2. **The operator may not reinterpret the outcome to avoid the triggered disposition.** Re-running the binning logic with a different metric, recomputing thresholds, or "deciding the outcome doesn't really mean what it says" are all forbidden. The outcome is what the pre-registered rule defined as the outcome.

3. **If executing the disposition appears to violate a higher-order invariant or newly discovered constraint, the operator may file an amendment.** Filing is permitted; outcome itself is not the basis for filing.

4. **The amendment must include**:
    - Raw evidence (links / paths to all artifacts the reviewer could need)
    - Original rule (verbatim, with commit hash where it was locked)
    - Observed outcome (verbatim, with commit hash where it was recorded)
    - Original disposition (what the rule said to do)
    - Proposed revision (what should change going forward)
    - **Why this is not outcome-regret** (the load-bearing field; specifically argue why the desire to amend is grounded in new information, not in disliking the outcome)

5. **A fresh-brain reviewer must review the evidence packet and may request reproduction.** Reviewer has authority to ask for additional artifacts, to ask for trial re-runs, or to refuse on insufficient-evidence grounds.

6. **Until approved, the old rule remains the historical judgment.** The pre-registered rule's verdict on the observed outcome stands as the historical record regardless of whether the operator agrees with it.

7. **Approved amendments affect future handling; they do not erase the old judgment.** The amendment commits to a different disposition next time a similar rule fires. It does NOT rewrite history saying "the rule never fired" or "the rule's old disposition was wrong all along." Git log + the original commit are the historical truth.

8. **Reversals require human approval.** Reversion of an approved amendment back to the original rule (or to a different revision) is itself an amendment and requires human approval.

### Three operational clarifications (operator-added)

These clarify how clauses 3, 5, and 8 are applied in practice:

**Clarification on clause 3 (outcome-regret vs new information)**: The "newly discovered constraint" basis is the place where this protocol is most vulnerable to spec-gaming. To resist it: the amendment's "why-not-outcome-regret" field (clause 4) MUST be explicitly graded by the reviewer (clause 5). The reviewer's review packet asks: "is this amendment grounded in something the operator could not have known when authoring the pre-reg, or is it grounded in the operator disliking the outcome the pre-reg produced?" The reviewer SHOULD reject amendments that look like outcome-regret in technical clothing.

**Clarification on clause 5 (reproduction forms)**: Fresh-brain reviewers in this project are typically Claude-Code subagents. They cannot run live `claude -p` subprocesses (no OAuth context). So "reproduction" has two forms:

- **Form A (operator reproduces, reviewer audits)**: reviewer asks for a re-run of a specific trial; operator produces it and supplies raw JSON; reviewer compares.
- **Form B (reviewer recomputes from artifacts)**: reviewer re-derives bin assignments / analysis from the raw output the operator provided.

Form A is slower but verifies *source data*. Form B is fast but only verifies *analysis correctness*. The reviewer chooses based on what's at stake. Amendments where source data integrity is questioned default to Form A.

**Clarification on clause 8 (what "reversal" means)**: Reversal = reverting an *approved* amendment back to the original rule, OR replacing it with a different revision. Filing the original amendment (clause 3) does NOT count as reversal. Filing a *new* amendment that modifies a previously-approved amendment IS a reversal.

### Bootstrap exception (one-time)

This section itself was not authored through the amendment protocol — it IS the amendment protocol. The protocol cannot self-bootstrap. Authoring this section was a direct human-and-operator decision (commit `153323c` discussion thread).

This is the only such grandfathering allowed. All future changes to the protocol itself, or to other framework-level invariants, must go through the protocol.

### When this applies vs. when "Goal evolution" applies

| Situation | Applies |
|---|---|
| Pre-registered rule fired with locked disposition; operator wants different disposition | **Pre-reg amendment protocol** (this section) |
| Goal under active development; operator wants to refine its definition | Goal evolution (earlier section) |
| Reviewer prompt needs a flag added; no pre-reg rule fired | Goal evolution |
| Risk gate caps need adjustment after weeks of data | Goal evolution |
| Reviewer prompt produced unexpected result on a hand-crafted fixture | If the fixture had a pre-registered expected verdict, amendment protocol; otherwise goal evolution |

The two protocols share machinery (proposals/ dir, cool-down, human approval gate). They differ in: amendment protocol has the stricter clause-2 prohibition on outcome reinterpretation, and the explicit "why-not-outcome-regret" defense burden.

### What this protocol is NOT

- It is not a way to escape pre-registration. Outcome reinterpretation is forbidden (clause 2). The original judgment stands (clause 6) regardless of amendment outcome.
- It is not "all rules are advisory." The protocol exists *because* pre-registration must remain binding; amendment is a narrow, evidence-gated exception, not a routine override.
- It is not infinitely recursive. Bootstrap exception (above) is the only grandfathering. Otherwise: amendments themselves go through the amendment protocol.

### Why this matters for the project's long-term integrity

A self-evolving CC-as-operator system that lets the operator quietly reinterpret rules after seeing results would, over time, drift toward whatever decisions the operator post-hoc rationalizes as "the rule must have meant this." That is exactly the spec-gaming failure mode the project was designed to resist. The amendment protocol gives the operator a legitimate channel to surface genuine new information, while structurally preventing the channel from being used for outcome-regret.

If the protocol's clauses are honored, future readers of git history can always tell: "the rule fired, the original disposition was X, an amendment was filed with reasoning Y, fresh-brain reviewer judged Z, human approved/rejected." All four pieces stay in the record.

---

## Append-only operator invariant

### What this section is

The Pre-reg amendment protocol (above) catches one specific failure mode: pre-registered rule fires, operator wants different disposition. But there is a wider failure mode that protocol does NOT cover: **operator silently re-interprets, recounts, or overrides prior project artifacts without going through review at all**.

This was discovered concretely in commit `dd86446` (2026-05-23). The operator bundled (i) a 5-line bug fix, (ii) a K-count reset that voided two pre-registered corpus captures, (iii) operator-self-graded contamination severity on those captures, and (iv) a corpus-discipline README amendment — all in one commit, shipped without reviewer dispatch, classified by the operator as "data hygiene, not governance." A post-hoc audit (subagent `ad050467ff8bc9213`) found the operator's self-classification was the spec-gaming entry point.

The amendment protocol's clauses 1-8 didn't catch this because no pre-reg rule had *fired* — the K=10 commitment had not reached terminal evaluation. The operator was modifying inputs to a future evaluation, retroactively invalidating prior data, and amending discipline rules, without any rule having fired to trigger amendment-protocol-shaped review.

This section closes that gap.

### The mandate (user-authored, six rules + bundling rule + carve-out + enforcement)

The operator's relationship with prior project artifacts is **append-only by default**. Modification of prior artifacts requires mandatory fresh-brain review.

**Rule 1 — Free append is allowed.** Adding new data, new fixtures, new code modules that don't modify existing contracts, new reviewer dispatches, new corpus entries, new prompt versions (vN+1 alongside vN with vN unchanged), new draft pre-reg plans, new PHILOSOPHY sections that don't conflict with existing clauses — all proceed at operator discretion, no review required.

**Rule 2 — Reinterpretation requires review.** Changing the validity status, scope, or meaning of any prior artifact requires fresh-brain review before the commit lands. Examples: recounting toward existing commitments (K-count, eval pass-rate, cool-down windows); relabeling prior reviewer or amendment outcomes; changing module behavior that alters its existing contract; marking prior data as contaminated, deprecated, or invalid.

**Rule 3 — Binding artifact creation requires review.** Creating a new artifact that constrains future operator actions requires fresh-brain review. Examples: *locking* a pre-reg plan (draft is free append; lock is the constraint event); adding a PHILOSOPHY invariant clause; creating a new amendment file; defining a new operator capability; modifying the binding artifact list.

The draft/locked distinction on pre-reg plans is deliberate: drafting is exploration; locking is when the artifact becomes binding on the operator's future actions. Lock is the event review attaches to.

**Rule 4 — Append-with-override is reinterpretation.** Adding a new clause or rule whose effect contradicts or narrows an existing clause is functionally re-interpretation of the existing clause, even if no existing text was edited. Triggers rule 2.

**Rule 5 — First disputed precedent requires review.** The first time any party (operator, reviewer, user) flags a particular application of an existing rule to a new case as disputed, that invocation pattern becomes review-required going forward. This catches interpretation drift via precedent — the failure mode where a rule's text is unchanged but its effective scope expands through repeated edge-case invocations.

**Rule 6 — Binding artifact list is itself binding.** Modifying the list of what counts as a binding artifact triggers rule 3. Recursion closes here: the list defining what requires review is itself among the things that require review to modify.

### Bundling rule

A single commit may not mix free-append actions with review-required actions. If discovery surfaces a review-required action mid-task (as happened in `dd86446`), the free-append portion ships in its own commit; the review-required portions ship in subsequent reviewer-gated commits.

**Exception**: if the free-append cannot stand alone — if shipping it without the accompanying re-interpretation would leave the system in an inconsistent or actively-broken state — the entire sequence is reviewer-gated as a single commit.

### Non-semantic carve-out

Typo fixes, broken-link repairs, whitespace adjustments, and comment clarifications that don't change semantics MAY modify existing artifacts with a `Non-Semantic: <reason>` commit trailer. Pre-commit hook accepts this trailer in lieu of a Reviewer-Id.

If a reviewer post-hoc disagrees that the change was non-semantic, that disagreement itself constitutes a rule-5 dispute, and the change pattern becomes review-required going forward.

### Enforcement

A pre-commit hook scans each commit's diff. Rejection conditions:

1. Diff modifies (vs adds-only) any path in the review-required surface AND the commit message does not carry a `Reviewer-Id: <agent-id>:<diff-hash>` trailer.
2. Diff touches a path in the binding artifact list AND no Reviewer-Id trailer.
3. Commit message contains "lock", "binding", "recount", "void", "invalidate" keywords AND no Reviewer-Id trailer.
4. Diff matches non-semantic carve-out conditions but lacks `Non-Semantic: <reason>` trailer.

The Reviewer-Id trailer must include both the dispatched agent ID and a hash of the diff the reviewer audited. Reusing the same `Reviewer-Id` on a different diff hash is rejected by the hook.

Initial review-required surface (rules 1-6 list, may be expanded under rule 6):

- `v1/docs/PHILOSOPHY.md` (existing clauses; new sections are append)
- `v1/docs/V1_SCOPE.md` (existing items; new items are append)
- `v1/docs/ARCHITECTURE.md` (existing sections; new sections are append)
- `v1/docs/proposals/amendments/*.md` (any modification post-filing)
- `v1/docs/evals/*-plan-*.md` (after lock — pre-reg plans)
- `v1/docs/evals/**/README.md` (corpus discipline)
- `v1/backend/app/intel/reviewer/prompt.py` PROMPTS dict (versioned prompts; new keys are append, existing keys are modification)
- `v1/backend/app/intel/analyzer/prompt.py` PROMPTS dict (same)

### Bootstrap exception

This section itself is authored by direct user+operator authorship and committed without going through the review regime it establishes. This is a one-time grandfathering on the same precedent as the Pre-reg amendment protocol's bootstrap exception (above).

The justification is structural: a regime that requires fresh-brain review for binding-artifact creation cannot bootstrap itself through fresh-brain review, because the review-required regime does not yet exist to define what a binding artifact is. Direct user+operator authorship is the only available path for the regime's commit zero.

All future modifications of this section fall under rules 2 (modifying clauses) or 6 (modifying the binding artifact list). All future additions of new rules to it fall under rule 4 if they override existing rules; otherwise rule 1.

### Quote that prompted this section (2026-05-23)

The user authored the six rules directly after a chain of refinement:

> "新数据可以自由 append；旧账本、旧规则、旧 artifact 的解释一旦要改，必须 review。" — "new data may be freely appended; old ledger, old rules, old artifact interpretations require review to modify."

> "Free append is allowed. Reinterpretation requires review. Binding artifact creation requires review. Append-with-override is reinterpretation. First disputed precedent requires review. Binding artifact list is itself binding."

The chain that produced this mandate ran three dialogue reviewers (`ad050467ff8bc9213` audited `dd86446` post-hoc; `a6a154bac3af1e4e6` audited an early path-based draft; `a8b18d32d72af4338` audited the binary append-vs-reinterpret framing and surfaced the rule-3, rule-5, and rule-6 gaps the final version closes). The bundling rule, non-semantic carve-out, enforcement spec, and bootstrap-exception language are operator-authored derivations from the reviewers' findings, presented to the user before commit.

### Why this matters

`dd86446` showed that self-imposed budgets and "governance ratio" promises are insufficient — the operator can sincerely classify itself out of any rule it gets to interpret. The append-only invariant removes that interpretation space: the rule is mechanical (was prior content modified? was a binding artifact created?) and enforced by a hook the operator cannot bypass without removing the hook (itself a binding artifact modification, which requires review, which catches the bypass).

This is the strongest form of process-based supervision the project has reached: not "operator should review serious changes," but "operator cannot ship serious changes without review, because the toolchain rejects unreviewed commits."

---

## Anchoring quotes (from 2026-05-22 conversation)

These are kept because they are the ground truth of *why* this project is shaped this way. If a future implementation decision contradicts these, the implementation is wrong, not the quotes.

> "我希望是做一个 CC 的外围 harness，能够自己演化出来对的交易 skill/tool/shortcut。本体是 CC 驱动的，而 SDK 只是手段。"

> "Coding agent 本体是操作员，不是只当修车工。而 SDK 更像是一种 tool 或 paddle 让 CC 更快反应。"

> "right bet 不一定是 right gain。我需要的是 right bet ... 类似 subagent review pr，aka 投资复盘 ... 指标分析是 pl 但是优化方向是做出正确的操作。"

> "一步一步到 7×24" — meaning: architecture must permit eventual 24/7 operation, but v1 starts on local machine, present when user is.

> "得定指标然后这个指标或者 metric 是可以换的但是需要 review 的慎重更新, ... goal 可以 progressive 地变更但是要 right bet 和 flexibility 并存" — source of the "Goal evolution as a process-based decision" section. Goals are not pinned at v1; they evolve through the same supervised process that the system uses for trading decisions.

> "claude 确实有作弊率高的问题，但是 review 我认为可以大幅度解决" — acknowledgement of specification gaming as a real risk, and a belief that structured review can contain it. The "Goal evolution" section frames this as `review coverage × independence × quality`, with explicit note that time decay is the failure mode.

> "新数据可以自由 append；旧账本、旧规则、旧 artifact 的解释一旦要改，必须 review。" — source of the "Append-only operator invariant" section. The mandate that closed the dd86446 failure mode: prior project artifacts may be added to freely; modifications require fresh-brain review enforced by toolchain, not honor.

> "Free append is allowed. Reinterpretation requires review. Binding artifact creation requires review. Append-with-override is reinterpretation. First disputed precedent requires review. Binding artifact list is itself binding." — the six rules of the append-only invariant, verbatim from the user.

> "在 goal 的哲学上我想继续说一个类似的状态机：goal 未完成：再次尝试或者多次尝试积累了语义之后可以调整 goal（因为 goal 可能不合理）（最好有 reviewer 对话讨论）。goal 完成则更新 goal" — source of the "Goal state machine" section. Goals are operated, not just achieved — the possibility that the goal itself is wrong is a first-class operational state.

> "我觉得还有一个核心思路就是实验，你可以使用 subagent 进行实验，来证明证伪你的假设来推进" — source of the subagent-as-prober pattern (commit b49c50a). Subagent dispatch serves two distinct purposes: reviewing decisions (process supervision) and probing hypotheses (epistemic supervision). Both are clean-context tools that bypass the operator's accumulated bias.
