# Amendment: Bin-3 disposition update — corpus accumulated, aggregator scope is resolver pattern

**Type**: Pre-reg amendment (per PHILOSOPHY.md "Pre-reg amendment protocol")
**Date**: 2026-05-23
**Author**: claude-code-operator
**Artifact target**: bin-3 disposition as revised by amendment `2026-05-23-amend-bin3-rule-defer-aggregator.md` (commit `c6393e5`, approved)
**Cool-down expires**: 2026-06-06 (14 days from filing per protocol clause 7)
**Status**: Revised v1-final (per reviewer `a5e691e99a086e259` REQUEST-CHANGES with C1-C3 applied inline per anti-reviewer-loop pattern, no v2 round); awaiting human approval per protocol clause 8.

---

## Amendment manifest (per protocol clause 4)

### Field 1: Raw evidence

- Original pre-reg plan: `v1/docs/evals/analyzer-determinism-eval-plan-2026-05-23.md` (commit `90e4db1`)
- First bin-3 amendment (the one this amendment further amends): `v1/docs/proposals/amendments/2026-05-23-amend-bin3-rule-defer-aggregator.md` (commit `c6393e5`)
- Corpus completed: K=10 of 10 valid post-fix entries under `v1/docs/evals/analyzer-determinism-corpus/`
- K=10 corpus entries by commit:
  - K=1 DefenseTech (`dd86446` inner, post-fix)
  - K=2 CloudSync (`3a37036`)
  - K=3 MidCap post-fix (`7776ea6` + annotation `a58e284`)
  - K=4 Heartland (`aa6d566`)
  - K=5 Coastal (`a61ead9`)
  - K=6 Cascade (`5d54bee`)
  - K=7 Meridian (`3b124ee`)
  - K=8 Northwind (`e1ffa75`)
  - K=9 Beacon (`105d3a6`)
  - K=10 Crestmark (`6e78910`), with HARKing correction (`ddd21b3`)
- Picking-criterion-v2: `v1/docs/evals/analyzer-determinism-corpus-picking-criterion-v2.md` (commit `e573d44`)
- K=10 aggregator analysis: reviewer `ab623c696b74f9c12` (output captured in session conversation; not yet committed to repo). Key findings used as evidence: 5/10 decision-disagreement rate (30-70% bucket), 0 parse/subprocess errors across 30 trials, stereotyped 2:1 split shape in 4 of 5 disagreement events.
- K=10 HARKing correction reviewer: `a5d1aad491c5e813d`

### Field 2: Original rule (verbatim, from prior bin-3 amendment commit `c6393e5`)

> "Revise bin-3 disposition to: **'File an amendment proposal that EITHER specifies the aggregator design OR specifies a corpus-observation-first strategy as an intermediate step before aggregator design. If the corpus-observation-first path is chosen, K=10 corpus entries (each event analyzed N=3 times with operator manual pick recorded) must be accumulated before any aggregator code is written. The B-and-C deferral stays in effect during corpus accumulation.'"

### Field 3: Observed outcome (verbatim from K=10 aggregator reviewer ab623c696b74f9c12 PART 1)

> "**Decision-disagreement rate = 5/10 = 50%.** [...] **50% decision-disagreement rate → squarely in the 30-70% bucket.** Per the amendment's pre-committed rule: 'aggregation is the right project; reviewer-mediated or human-in-the-loop strategies become preferred; design proposal follows the corpus evidence.'"

Also: "Across all 10 entries × 3 trials = **30 trial observations, 0 parse errors, 0 subprocess errors, 0 trials missing or replaced.**"

Also: "in 4 of 5 split events (all except K=3), the split is 2:1 between `notify+null` and `dry_run+small_sized_intent`. The split is never about *direction*. It is never about *which event class*. It is always about **whether to queue a token-sized probe-in-dry_run alongside the 'wait for confirmation' reasoning.**"

### Field 4: Original disposition

Bin-3 amendment's locked disposition required EITHER aggregator design proposal OR corpus-observation-first with K=10 threshold. Corpus-observation-first path was chosen and K=10 was reached. Per the amendment's "Metric expected to move and direction" section, the 30-70% bucket result mandates: "aggregation is the right project; reviewer-mediated or human-in-the-loop strategies become preferred; design proposal follows the corpus evidence."

The original disposition does NOT specify the aggregator design itself — only that one must be proposed following the corpus evidence pattern. The proposal is the next step, not in-scope for this amendment.

### Field 5: Proposed revision

Lift the B-and-C deferral upon landing of the aggregator design proposal (Action 2 below). The B-and-C deferral remains in force until aggregator design proposal is filed (separately, in its own commit, with its own reviewer dispatch).

The aggregator design proposal MUST address two constraints carried forward from prior reviews; **all other design decisions (including routing logic, schema specifics, implementation timeline) are explicitly NOT pre-figured here and remain the design proposal author's job under separate reviewer scrutiny.**

1. **No synthesized fabricated dossier** (per reviewer `ad49a25df845c280f` authorship-invariant objection, still load-bearing from prior bin-3 amendment). The resolver may NOT produce a Decision row whose `actor_id` is a fabricated aggregator identity claiming authorship of reasoning_chain content the analyzer did not produce.

2. **Separation between picking-criterion and resolver** (per K=10 aggregator reviewer `ab623c696b74f9c12` PART 2). Picking-criterion-v2 is research/calibration only; resolver is production routing. These are orthogonal — conflating them was a v1-epoch category error.

**What this amendment does NOT pre-figure** (per reviewer `a5e691e99a086e259` C1, applying the same Amendment-A C1 discipline):
- Routing logic for unanimous / mode-split / fully-split cases — the design proposal authors this under its own reviewer pass; this amendment authorizes the channel only
- Schema specifics (e.g. `decision_group_id` UUID column shape) — implementation detail
- Live-router-vs-dashboard-surfaces tradeoff — design proposal decides based on evidence
- Whether per-class routing is needed — design proposal decides

The K=10 evidence (stereotyped 2:1 split shape in 4 of 5 disagreements, 0 parse errors, 50% disagreement rate) is **available to** the design proposal author as input but is **not used to lock** design decisions by this amendment. Reviewer `a5e691e99a086e259` PART 7 specifically flagged that pre-figuring routing branches off the 2:1 shape would be the same HARKing-adjacent pattern that the K=10 entry's `ddd21b3` correction just struck.

### Field 6: Why this is not outcome-regret (LOAD-BEARING)

**Primary counter-test**: would the operator file this amendment if the K=10 result had been different?

- If K=10 had been < 30% disagreement: the amendment would still fire, but with a different aggregator scope ("simple first-of-3 or vote rule").
- If K=10 had been > 70% disagreement: the amendment would still fire, but with a different downstream ("prompt v2 or model-temperature investigation, aggregation is wrong framing").

In all three cases the amendment **fires because the corpus-observation-first deferral ran to completion**, not because the operator dislikes any specific result. The 30-70% bucket result is being taken at face value. The amendment lifts a deferral that was always pre-committed to lift upon corpus completion.

**Secondary counter-test** (for the resolver design specifically): would the operator file this resolver design if the corpus split pattern had been 1:1:1 (three distinct patterns) instead of stereotyped 2:1?

If the corpus had shown 1:1:1 splits, the resolver design would need to handle three-way disagreement, not the binary `notify+null` vs `dry_run+small_sized_intent` shape. The resolver primitive (mechanical agreement classification) would still apply, but the routing logic would have more cases. **The amendment IS sensitive to the observed split shape** — this is not outcome-regret because the observed shape directly informs the design, but it does mean the design is contingent on observed evidence and a future operator/reviewer could legitimately re-litigate the resolver design if K=11+ evidence overturns the 2:1 shape pattern.

**Tertiary check** — what does the amendment NOT smuggle:
- Does NOT lift the picking-criterion-v2 from research-only to production. v2 is for selecting research-data picks; resolver is for production routing.
- Does NOT commit to any specific aggregator implementation timeline. Design proposal is the next artifact, not implementation.
- Does NOT settle the continuum-vs-binary hypothesis question. K=10 entry's HARKing correction (`ddd21b3`) explicitly demoted the continuum to speculative hypothesis. Aggregator design does not depend on resolving this — it routes on observed agreement, not predicted suppression strength.

---

## What changes (procedurally, on approval)

1. **Bin-3 disposition is satisfied** by the K=10 corpus accumulation and the aggregator design proposal that follows. No further deferral is authorized under bin-3.

2. **B-and-C deferral remains** until aggregator design proposal lands (separate commit, separate reviewer dispatch).

3. **Picking-criterion-v2 stays in force** for any K=11+ corpus capture (if it happens — corpus may pause now that bin-3 milestone is reached), with the note that v2's Dim 4 weight should be clarified before next v2-epoch split (per K=10 aggregator reviewer PART 6 sub-flag #1 about Dim 4 silent expansion).

4. **The K=10 entry's HARKing correction (`ddd21b3`) establishes precedent** for rule-5 review of corpus-entry post-result framings going forward. Not a new mandate, but a precedent: corpus entries that introduce post-result hypotheses as "findings" can be flagged for correction.

5. **No PHILOSOPHY changes** authored by this amendment. (Distinct from Amendment A which proposes PHILOSOPHY changes pending approval).

---

## Falsification

This amendment is wrong (and should be revised) if:

1. The aggregator design proposal that follows is not actually fileable within 30 days of this amendment landing. That would indicate the amendment lifted the deferral prematurely.
2. The "30-70% bucket → aggregator-is-right-project" mapping turns out to be wrong on closer inspection — e.g. if 4 of 5 disagreements share a common structural feature that a simpler intervention (prompt v2) could eliminate, the aggregator framing is wrong. The K=10 aggregator reviewer flagged the stereotyped 2:1 shape; this could be probed by attempting prompt v2 first.
3. The picking-criterion-v2 framework turns out to be load-bearing on the resolver (currently held as orthogonal). If during aggregator design proposal authorship the orthogonality breaks, the amendment's "research-only" framing of v2 needs revisiting.

## Alternatives considered (rejected)

1. **Skip this amendment, ship aggregator design directly.** Rejected on minimum-action analysis (per reviewer `a5e691e99a086e259` C2): the prior bin-3 amendment's Field 5 specified "EITHER aggregator design OR corpus-observation-first." The corpus path was taken and K=10 reached, and the prior amendment's "Metric expected to move" section did pre-commit that "30-70% → design proposal follows the corpus evidence." A defensible reading is that this auto-fires the design-proposal channel without needing a fresh amendment. Why this amendment fires anyway: (a) the prior amendment's disposition language was "File an amendment proposal that EITHER specifies the aggregator design OR..." — this phrasing puts "amendment proposal" as the artifact, not "design proposal," so the literal text requires this amendment to lift the B-and-C deferral cleanly; (b) the corpus-completion event itself deserves its own reviewable disposition-update step, separable from the design proposal's content; (c) the picking-criterion-v2 introduction during corpus accumulation was not anticipated by the prior amendment and needs disposition acknowledgment. **Honest concession**: argument (a) is the strongest of the three; arguments (b) and (c) could plausibly be folded into the design proposal preamble and skipping this amendment would only weakly violate the prior pre-reg's letter. The amendment is filed on the conservative reading; if a future operator chooses the bundled-with-design-proposal path on a similar future trigger, that is also defensible and this filing does not establish a precedent against it.

2. **Bundle this amendment with the aggregator design proposal in one commit.** Rejected per bundling-rule spirit and per reviewer `a5d1aad491c5e813d` PART 3 (don't bundle review-required artifacts with different review framings).

3. **Defer aggregator further — extend corpus to K=20 first.** Rejected: K=10 was the pre-committed threshold; extending it without an amendment changing K would be moving goalposts post-data. If K=11+ are valuable, file a separate proposal stating why; do not amortize them into the bin-3 deferral.

4. **Treat picking-criterion-v2 as the resolver.** Rejected per K=10 aggregator reviewer PART 2: v2 is for "judging which trial reasoned best" (research/calibration); resolver is for "what action to take when trials disagree" (production routing). These are orthogonal — conflating them was a v1-epoch category error that v2 already inherited; the resolver design must not perpetuate it.

5. **Build the live router immediately.** Rejected per reviewer PART 2 simplest-implementation: dashboard surfaces group + operator routes by hand for ~20 more events first. Live router is premature until resolver-derived classifications are validated against operator intuition at scale.

## Reviewer judgment

### Pre-amendment dialogue reviewers (informational)

- Reviewer `ab623c696b74f9c12` (K=10 aggregator analysis): produced the 50% disagreement-rate finding + 30-70% bucket conclusion + concrete resolver design (PART 2). Confidence 0.72.
- Reviewer `a5d1aad491c5e813d` (K=10 HARKing correction review): produced bundling-rule guidance ("own commit, do NOT bundle with bin-3 amendment"). Confidence 0.82.

### Pre-reg amendment reviewer (per protocol clause 5)

**Reviewer ID**: (TO BE FILLED — fresh-brain reviewer dispatched at amendment-file time)
**Decision**: (TO BE FILLED)
**Reviewer confidence**: (TO BE FILLED)

## Approval

(To be filled by user when merging or rejecting.)

**Approval condition (per reviewer `a5e691e99a086e259` C3, analogous to Amendment A C5)**: human should condition approval on at least one non-governance commit (K=11+ corpus capture, a DoD item, or actual code) landing between this amendment's approval and the aggregator design proposal — OR explicit reviewer scrutiny on the design proposal of whether this amendment's Field 5 over-specified its content. Without this condition the post-K=10 sequence is three consecutive governance commits (HARKing correction `ddd21b3` → this amendment → aggregator design proposal), which is the cadence concern in `feedback_maymayinvest_no_reviewer_chain_governance_creep.md`. Operator pre-commits to honor whichever path the human chooses.

## Reviewer judgment (continued — v1-final reviewer block)

### Pre-reg amendment reviewer (per protocol clause 5) — v1 round

**Reviewer ID**: `a5e691e99a086e259`
**Decision**: REQUEST-CHANGES
**Confidence**: 0.74
**Changes requested**:
- C1 (applied in v1-final): strike Field 5 constraint 2 (routing branches pre-figured design proposal content). **DONE** — Field 5 revised to authorize-channel-only with explicit "what this amendment does NOT pre-figure" list.
- C2 (applied in v1-final): add minimum-action defense in Alternatives Considered #1. **DONE** — alternative #1 expanded with honest 3-part argument and concession.
- C3 (applied in v1-final): approval condition on next non-governance commit. **DONE** — approval section now carries the condition.

Other PART findings noted but not blockers:
- PART 2 Form-A reproduction risk on uncommitted reviewer `ab623c696b74f9c12` output — accepted as project-convention risk per Amendment A pattern; not blocker.
- PART 6 Interlock 1 weakness — partially addressed by C2's honest concession; structural critique recorded for future similar amendments.
- PART 7 HARKing-adjacent 2:1 shape pre-figuring — directly addressed by C1 strike.

v1-final applies all three caveats inline per anti-reviewer-loop pattern (Amendment A precedent). No v2 round.
