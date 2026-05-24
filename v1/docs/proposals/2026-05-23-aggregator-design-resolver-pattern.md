# Proposal: Aggregator design — decision_group + mechanical resolver, no synthesized dossier

**Type**: Implementation proposal authorized by bin-3 disposition (commit `c6393e5` Field 5: "design proposal follows the corpus evidence" upon 30-70% disagreement bucket)
**Date**: 2026-05-23
**Author**: claude-code-operator

---

## Authority

The original bin-3 amendment (`v1/docs/proposals/amendments/2026-05-23-amend-bin3-rule-defer-aggregator.md`, commit `c6393e5`) pre-committed: "If decision-disagreement rate is 30-70%: aggregation is the right project; reviewer-mediated or human-in-the-loop strategies become preferred; **design proposal follows the corpus evidence.**" K=10 corpus accumulation completed at commit `6e78910`; K=10 aggregator analysis reviewer `ab623c696b74f9c12` confirmed 5/10 = 50% disagreement rate, placing it in the 30-70% bucket. This proposal is the "design proposal follows the corpus evidence" artifact the original disposition required.

A second amendment (`3caf887`) was filed before this proposal attempting to lift the B-and-C deferral. Per user steer 2026-05-23: that amendment was unnecessary because the original bin-3 disposition already authorized this proposal channel; it stands as historical record per append-only invariant but does not gate this proposal. This proposal cites the original disposition (`c6393e5`) directly as its authority. The collapse of "disposition amendment + design proposal" into "design proposal alone" is itself the Interlock-1-minimum-action interpretation that should have been applied initially.

---

## Evidence inputs

The K=10 aggregator analysis (reviewer `ab623c696b74f9c12`) is the load-bearing evidence packet. Key findings used here:

1. **Decision-disagreement rate**: 5 of 10 events (50%). Per-event detail in K=1..K=10 corpus entries under `v1/docs/evals/analyzer-determinism-corpus/`.
2. **Error rate**: 0 parse errors, 0 subprocess errors across 30 trial observations.
3. **Stereotyped split shape**: 4 of 5 disagreement events show 2:1 between `notify+null` and `dry_run+small_sized_intent`. K=3 is the exception (mode split but intent unanimous null). No 1:1:1 split ever observed. No split on direction.
4. **Operator pick bias**: v1-epoch (K=1/2/3/6) picked notify 4/4 times when alternative existed; v2-epoch (K=10) picked dry_run 1/1 time. Bias is real but is in the picking-criterion layer, not the analyzer layer.

The K=10 entry's "continuum-of-counter-pointing-concern-strength" hypothesis was demoted to speculative post-result hypothesis by commit `ddd21b3`. This design does NOT depend on whether the continuum holds; it routes on observed agreement, not predicted suppression strength.

---

## Design

### What this proposal SPECIFIES

**Carried forward as hard constraints from prior reviews**:

1. **No synthesized fabricated dossier.** The resolver may NOT produce a `DecisionDossier` row whose `actor_id` is a fabricated aggregator identity claiming authorship of `reasoning_chain` content the analyzer did not produce. Per reviewer `ad49a25df845c280f` authorship-invariant objection, still load-bearing.

2. **Picking-criterion / resolver separation.** Picking-criterion-v2 is research/calibration only. Resolver is production routing. The resolver does NOT consume operator picks at decision time. Per K=10 aggregator reviewer `ab623c696b74f9c12` PART 2.

**Design specification** (proposed by this proposal, subject to revision in implementation if evidence emerges against any element):

3. **`decision_group_id` (UUID) added to `DecisionDossier`.** Populated at capture time, shared across the N=3 trials for one event. Migration adds the column nullable; backfill is a no-op (pre-existing dossiers are single-trial and remain ungrouped, which is the correct historical state). New captures populate group_id from the capture script.

4. **Derived view `decision_group_consensus(group_id)`** returning one of:
   - `unanimous` — all N trials agree on `(mode, intent_is_null)` tuple
   - `mode_split_intent_unanimous` — `mode` varies but `intent_is_null` is unanimous across trials (matches K=3 corpus shape; effectively-unanimous-no-action)
   - `mode_and_intent_split` — both `mode` and `intent_is_null` vary across trials (matches K=1/K=2/K=6/K=10 corpus shape)
   - `multi_pattern` — three distinct `(mode, intent_is_null)` patterns (NEVER observed in 10 events; reserved for future)

5. **Routing logic for the resolver** (initial version, scoped to current evidence):
   - `unanimous` → advance the unanimous decision (still `dry_run` or `notify` by analyzer choice; no auto-execute on first deployment regardless)
   - `mode_split_intent_unanimous` → advance as `notify` (intent is unanimously null; mode differences are framing-only at the no-action boundary)
   - `mode_and_intent_split` → **do not advance.** Surface the full group to operator; if operator is the agent, dispatch a reviewer pass before any further routing
   - `multi_pattern` → same as mode_and_intent_split (surface, do not advance)

   **Note on routing-branch evidence basis**: The four-branch logic above maps directly to the four consensus categories the corpus has actually exhibited (with `multi_pattern` reserved as never-observed). A future K=11+ event that produces an unobserved shape (e.g., direction disagreement, which has not occurred in K=1..K=10) would require routing revision. The routing logic is **explicitly contingent on the observed split shape staying stereotyped**; if K=11+ shows direction disagreement or 1:1:1 patterns, this routing needs amendment.

6. **No live router in v0.** The `decision_group_id` schema addition + the derived consensus view + dashboard surface of the group is sufficient initial scope. The operator routes by hand based on the consensus classification until ~10 more events validate that the resolver's classification matches operator intuition on routing. A live router lands in v0.5 if validation holds; otherwise the resolver design revisits.

### What this proposal does NOT specify

- Dashboard UI specifics for surfacing the group (separate implementation concern, scoped under DoD #8).
- Reviewer-pass automation for the `mode_and_intent_split` case (separate concern; operator dispatches by hand initially).
- Auto-execute thresholds for `unanimous` advancements (separate concern; v0 keeps `auto` mode behind manual promotion gate per V1_SCOPE Stage 0 #4).
- Picking-criterion-v2 promotion or demotion (orthogonal; v2 stays as research/calibration only).
- Whether per-event-class routing is needed (corpus evidence does NOT support class-based routing — disagreement is not class-correlated per K=10 aggregator reviewer PART 2).

---

## Why this design at this evidence level

**Simplest plausible thing that matches the corpus pattern**:

- The corpus disagreement is stereotyped (2:1 between two specific action shapes, never direction disagreement). This makes the routing problem much smaller than generic noisy-classifier ensembling. A mechanical-agreement classifier on `(mode, intent_is_null)` captures the structure without inventing new representations.

- Authorship invariant rules out any fabricated-aggregator-dossier approach. This removes a large design space and forces the resolver into the "preserve and route" pattern rather than "synthesize and replace."

- The 0% error rate (30/30 trials clean) means error-handling is not a load-bearing concern at this scale. A v0 resolver does not need fallback logic for missing trials. (If error rate emerges at higher scale, revisit.)

- The 50% disagreement rate puts the load on routing logic (handle disagreement) rather than on prevention (e.g. prompt v2 to reduce disagreement). Prompt v2 remains a valid alternative explored at design-revision time, but the current proposal honors the corpus-observation-first commitment by acting on the observed disagreement rather than treating it as a defect to suppress.

**Why NOT a vote-based aggregator** (rejected design): the minority trial in 4 of 5 splits is the structurally-distinct trial (the `dry_run+sized` shape vs `notify+null`). Vote would silently discard it. The minority is sometimes the right pick (K=10 operator picked the minority `dry_run+sized` under v2 criterion). Vote design would conflict with picking-criterion-v2 outcomes asymmetrically.

**Why NOT confidence-weighted aggregation** (rejected design): trial confidence varies 0.55-0.78 across the corpus with no clear correlation to which trial the operator picks. Weighting by stated confidence would amplify operator-pick bias because high-confidence trials may be high-confidence-in-procedural-discipline (notify) rather than high-confidence-in-substance.

---

## What changes (implementation roadmap)

1. **Schema migration**: add `decision_group_id UUID NULL` to `decisions` table. Alembic migration. ~5 lines schema + 1 migration file.

2. **DecisionDossier domain model**: add `decision_group_id: UUID | None` field. ~3 lines + type updates downstream.

3. **Capture script** (`capture_event_to_corpus.py`): generate a single `decision_group_id` UUID per capture invocation and pass it to all N=3 analyzer calls. ~10 lines.

4. **Derived consensus function**: `decision_group_consensus(group_id: UUID) -> ConsensusCategory` in `app/intel/router.py` or a new `app/intel/resolver.py`. ~40 lines + tests.

5. **Dashboard surface**: read group when displaying any single dossier; show consensus classification + sibling trials. Scope under DoD #8 (dashboard signals page), not in this proposal's mandatory scope.

Total v0 surface: ~60 lines + 1 migration + tests. Two commits suggested: (a) schema + domain + migration as one commit; (b) capture script + derived function as second commit. Each is reviewer-gated only if it touches binding artifacts (the migration touches schema, which is binding; the resolver function touches `app/intel/router.py` which is on the implementation-but-not-binding side).

---

## Falsification

This design is wrong (and should be revised or replaced) if:

1. **Within first 10 production-deployed events**, the `decision_group_consensus` classification disagrees with operator intuition on routing in >30% of cases. That would indicate the mechanical agreement classifier is missing structure the operator picks up on, and the resolver needs more inputs (e.g. confidence, reasoning-chain features).

2. **A K=11+ event produces a previously-unobserved split shape** (direction disagreement, 1:1:1, parse error). The routing logic explicitly assumes the corpus's stereotyped 2:1 shape; new shapes require routing revision.

3. **The picking-criterion / resolver separation breaks in practice** — e.g. operator finds themselves consistently reaching for picking-criterion-v2's outputs when deciding how to route a `mode_and_intent_split` group. That would indicate the orthogonality assumption is wrong and the design needs to consolidate the two layers.

4. **Synthesized-dossier becomes structurally necessary** for any downstream consumer (e.g. dashboard cannot render N=3 dossiers without one canonical view). Would force re-litigation of the authorship invariant — separate proposal.

---

## Alternatives considered (rejected)

1. **Vote-based aggregator**: rejected per "why not vote" above; minority trial is sometimes structurally-correct pick.

2. **Confidence-weighted aggregator**: rejected per "why not confidence-weighted" above; confidence does not track operator pick or substantive quality cleanly.

3. **Synthesized canonical dossier authored by aggregator**: rejected per authorship invariant (`ad49a25df845c280f`).

4. **Picking-criterion-v2 as production resolver**: rejected per separation principle (`ab623c696b74f9c12` PART 2); v2 judges trial quality, resolver judges trial agreement.

5. **Per-class routing** (different aggregator per event class): rejected per K=10 aggregator reviewer PART 2 — class is empirically not the right axis; disagreement is not class-correlated.

6. **Prompt v2 to suppress disagreement at source** rather than aggregate it: not rejected, but deferred. The 50% disagreement rate places this in the aggregation-is-right-project bucket per the pre-committed bin-3 disposition. Prompt v2 remains a parallel candidate if K=11+ evidence emerges that disagreement has a single removable cause.

7. **Skip the proposal — file an amendment first** (the path commit `3caf887` took): not rejected per se since `3caf887` is historical record, but per user steer 2026-05-23 the minimum-action interpretation is direct proposal filing citing original disposition. The `3caf887` amendment is preserved as audit context for how the operator got here; the proposal does not require it as authority.

---

## Reviewer judgment

**Not dispatched for this proposal.** Per user steer 2026-05-23: "Reviewer dispatch should drop noticeably for next 3 commits. Aim for ratio < 0.5 per commit. Substantive K=10 finding deserves bandwidth." This proposal is being filed direct-to-human without a fresh-brain reviewer round.

The design rests on three already-reviewed evidence packets:
- K=10 aggregator analysis (reviewer `ab623c696b74f9c12`, conf 0.72)
- Authorship invariant prior objection (reviewer `ad49a25df845c280f`, prior bin-3 amendment)
- HARKing correction precedent (reviewer `a5d1aad491c5e813d`, conf 0.82, applied to K=10 entry at `ddd21b3`)

If the human wants reviewer dispatch on this proposal before approving, that is a defensible request and not a violation of the bandwidth steer (one reviewer for one substantive proposal is within the < 0.5 ratio if subsequent commits are reviewer-less DoD work).

---

## Approval

(To be filled by user when merging or rejecting.)

Operator note: this proposal authorizes implementation. Implementation commits (schema migration, capture script update, resolver function) follow as separate commits under DoD work; per user steer they should NOT each carry reviewer dispatch — code review on the migration is the natural gate, not amendment-style reviewer rounds.
