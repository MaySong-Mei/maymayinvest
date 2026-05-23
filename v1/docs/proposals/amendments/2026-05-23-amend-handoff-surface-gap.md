# Amendment A: Close HANDOFF.md surface gap in append-only mandate

**Type**: Mandate rule-6 amendment (per PHILOSOPHY.md "Append-only operator invariant" enforcement section)
**Date**: 2026-05-23
**Author**: claude-code-operator (post-compact session)
**Artifact target**: PHILOSOPHY.md enforcement section path list (commit `29cecbf`, lines 472-481)
**Cool-down**: N/A (this is a mandate scope amendment, not a pre-reg outcome amendment; the cool-down convention applies to outcome regret, not to closing self-flagged governance holes)
**Status**: Revised v2-final (per reviewer `a84df019be0ffb852` REQUEST-CHANGES on v1, then reviewer `a837fa393d7d7dad0` APPROVE-WITH-CAVEATS on v2 with caveats C1-C4 applied in this v2-final without a v3 round per the same reviewer's PART 5 P3 anti-reviewer-loop guidance); awaiting human approval per protocol clause 8.

---

## Amendment manifest (per protocol clause 4 — adapted for mandate-scope amendment)

The bin-3 amendment (`2026-05-23-amend-bin3-rule-defer-aggregator.md`) established the 6-field manifest format. This amendment satisfies all 6 fields, adapted to the mandate-scope context where "rule" = mandate path list, "observed outcome" = reviewer-surfaced gap rather than experimental result.

**Precedent-setting acknowledgment (per reviewer `a837fa393d7d7dad0` C2)**: PHILOSOPHY's amendment protocol clause 4 was authored for pre-reg outcome amendments. This is the first mandate-scope (rule-6) amendment and its adaptation of the 6-field format establishes a new precedent: future rule-6 amendments will inherit this shape unless explicitly overridden by a later amendment to PHILOSOPHY's protocol section itself.

### Field 1: Raw evidence (commit hashes + paths)

- **HANDOFF.md original commit**: `1a8ec63` "Add HANDOFF.md for cold-start continuity"
- **PHILOSOPHY.md enforcement section** (the path list being amended): commit `29cecbf` "Append-only operator invariant (mandate) + pre-commit hook", file path `v1/docs/PHILOSOPHY.md` lines 472-481
- **Reviewer ab312708ba406fe7b** (first to flag the gap, fresh-brain post-compact steer): full output captured in this session; no separate commit because reviewer outputs are conversation-scoped per project convention. The relevant quote is in this amendment field 5 below.
- **Reviewer a2c076ed832afc771** (second to flag, in context of operator's rejected errata-append): full output captured in this session. Relevant verdict quoted in field 3 below.
- **Reviewer a324347f0284774a6** (multi-problem triage that recommended this amendment): full output captured in this session.
- **Reviewer a84df019be0ffb852** (this amendment's v1 review, REQUEST-CHANGES verdict that drove this v2): output captured in this session.
- **The rejected errata-append attempt itself**: was made to working-tree HANDOFF.md, never committed, was `git checkout`-reverted after reviewer rejection. The errata-append text added a new section titled "Errata (append-only addenda by later operators)" at the end of HANDOFF.md with three subsections: (a) a correction noting the burned MidCap fixture, (b) a "burned fixture list" enumerating four fixtures, (c) a class-coverage tally and K=3-recommended-class hint. The full text is reconstructable from this session's conversation log but was never persisted to git; its non-persistence is itself the consequence of the reviewer rejection working as designed.

### Field 2: Original rule (verbatim, from commit `29cecbf`, PHILOSOPHY.md lines 472-481)

> Initial review-required surface (rules 1-6 list, may be expanded under rule 6):
>
> - `v1/docs/PHILOSOPHY.md` (existing clauses; new sections are append)
> - `v1/docs/V1_SCOPE.md` (existing items; new items are append)
> - `v1/docs/ARCHITECTURE.md` (existing sections; new sections are append)
> - `v1/docs/proposals/amendments/*.md` (any modification post-filing)
> - `v1/docs/evals/*-plan-*.md` (after lock — pre-reg plans)
> - `v1/docs/evals/**/README.md` (corpus discipline)
> - `v1/backend/app/intel/reviewer/prompt.py` PROMPTS dict (versioned prompts; new keys are append, existing keys are modification)
> - `v1/backend/app/intel/analyzer/prompt.py` PROMPTS dict (same)

`v1/docs/HANDOFF.md` is NOT in this list. By rule 1 default, it is therefore free-append for any operator.

### Field 3: Observed outcome (the gap surfacing, verbatim where possible)

The triggering observation is two independent fresh-brain reviewers identifying the same structural gap on different actions.

**Reviewer ab312708ba406fe7b** (forward-looking, in routine next-step audit):
> "PHILOSOPHY's 'Append-only operator invariant' enforcement section lists `v1/docs/evals/**/README.md` as review-required. HANDOFF.md is NOT on that list. Cold-start agents will treat HANDOFF as ground truth (HANDOFF says so explicitly: 'most recent ground-truth snapshot'). A ground-truth document that lives outside the review-required surface is a governance hole. Worth flagging — but NOT something to fix mid-task; file as a follow-up."

**Reviewer a2c076ed832afc771** (concrete, in audit of operator's rejected errata-append):
> "PART 1: REQUIRE-AMENDMENT-FIRST. [...] If the operator wants to ship something now without amendment, the lowest-friction path is to file a one-paragraph rule-6 amendment in `v1/docs/proposals/amendments/` that either (a) adds `v1/docs/HANDOFF.md` to the review-required surface and dispatches a reviewer for this errata, or (b) explicitly declares HANDOFF non-binding (with reasoning the user accepts) so future errata-appends are free."

**Reviewer a324347f0284774a6** (triage, recommending narrow sequential amendments):
> "file two sequential amendments, in this order: Amendment A (file first): Add `v1/docs/HANDOFF.md` to the review-required surface list (rule-6 modification). Smallest, cleanest, has the most established reviewer support [...]"

**Empirical evidence the gap is currently producing drift**: HANDOFF.md currently states "Currently at K=1 valid + 2 contaminated" (line 32) while the corpus directory contains 2-3 valid post-fix entries by `captured` timestamp ordering (DefenseTech, CloudSync, MidCap post-fix — exact count depends on how the duplicate "K=2" labeling on commits `3a37036` and `7776ea6` is reconciled, which is itself work deferred to Amendment B per reviewer `a837fa393d7d7dad0` C4). The HANDOFF artifact is already drifting from ground truth in a load-bearing way as a direct consequence of being off-surface — no review-gated update mechanism applies regardless of whether the correct count is 2 or 3.

### Field 4: Original disposition

Under the current rule, `v1/docs/HANDOFF.md` is rule-1 free-append. Any operator may add, edit, or restructure its contents in a single commit without reviewer dispatch. The file's self-description ("most recent ground-truth snapshot, self-contained") attempts to elevate it to binding status by content but the enforcement list does not recognize this.

### Field 5: Proposed revision

**Pick: Option 1 with agent-IDs carve-out** (operator's pick after reviewer `a84df019be0ffb852`'s analysis of option trade-offs).

Append two lines to PHILOSOPHY.md enforcement section path list:

```
- `v1/docs/HANDOFF.md` (existing sections; new sections are append-with-review; agent-IDs subsection at file end is rule-1 free-append exception)
```

Mechanical effect:

1. Any modification to existing HANDOFF.md text (including stale-fact corrections such as the "K=1 valid + 2 contaminated" line, recommended-next-move updates, errata that contradict-by-append per rule 4) becomes rule-2 reinterpretation → requires `Reviewer-Id:` trailer OR `Mentioned-Governance-Keyword:` declaration.
2. New top-level sections appended at the end of HANDOFF.md (e.g. session-N snapshot blocks, new invariant additions) are rule-2-shaped-as-rule-4 (append that adds new binding content) and require review.
3. Adding a new agent-ID line to HANDOFF's "Past key reviewer agent IDs" section (currently 17 entries, structurally a historical append-only log) is rule-1 free-append and does NOT require reviewer dispatch. This carve-out exists because that section is the highest-volume legitimate update path and is structurally similar to corpus entries (one-event-one-line append-only audit trail).

**Residual risk acknowledgment (per reviewer `a837fa393d7d7dad0` C3)**: the agent-IDs carve-out is structurally *similar* to corpus entries but not *identical* — corpus entries are individual files whose creation event is the appendage, while agent-IDs are line-additions inside a single file. This weaker append boundary means an operator could append a fabricated agent-ID line without mechanical prevention. The mitigation is cooperative, not mechanical: any claimed agent ID is verifiable post-hoc via git log + grep against the dispatched-agent record. Fabricated-ID detection is therefore bounded by post-hoc auditability, not by the carve-out itself. This is acceptable given the post-hoc check's cost is near-zero, but the operator notes the gap explicitly.

The carve-out is narrow and specific to one named section. It is not a slippery slope to "operator carves out whatever section they want next" because future carve-outs would themselves require rule-6 amendment (modifying the binding-artifact list rules).

### Field 6: Why this is not outcome-regret (LOAD-BEARING, expanded per reviewer a84df019be0ffb852 request)

**Primary counter-test** (the amendment's own):
> Would the operator file this amendment if BOTH reviewers had instead said "HANDOFF.md is fine off-surface, no action needed"?

**Answer: No.** The amendment fires only because two independent fresh-brain reviewers, dispatched on different operator actions in different conversation contexts, identified the same structural gap. The information being acted on is "the constraint space has a hole that fresh-brain reviewers detect," not "the operator dislikes an outcome."

**Secondary counter-test** (raised by reviewer a84df019be0ffb852, formerly missing):
> Would the operator file this amendment if reviewer a2c076ed832afc771 had APPROVED the operator's errata-append to HANDOFF.md?

**Answer: Also no, but this is the more dangerous version of the test and requires explicit handling.** If the errata-append had been approved, the operator would have learned that HANDOFF-as-free-append is currently the de facto rule, would have shipped the errata, and would not have filed an amendment. The gap would persist.

The risk this isolates: does Amendment A's Option 1 (or earlier draft Option 2) functionally legalize the rejected errata-append? Walking through:

- **Under Option 1 (selected)**: NO. The errata-append, if attempted under Option 1, would require `Reviewer-Id:` trailer. A reviewer dispatch on a near-identical errata-append text would likely re-produce the rule-4 reinterpretation-via-contradicting-append verdict. The rejection mechanism is preserved.
- **Under former Option 2** (now demoted to "considered and rejected"): YES, partially. Option 2 kept HANDOFF.md free-append with a disclaimer, which would have permitted future errata-appends of similar shape. This is precisely why reviewer a84df019be0ffb852 recommended Option 1 and why the operator now picks Option 1 over the operator's own previously-disclosed "weak preference for Option 2."

By picking Option 1 the amendment explicitly does NOT legalize the rejected action. The rejection stands as historical precedent and the new regime makes future similar appends reviewer-gated. **The secondary counter-test passes.**

**Tertiary check** — would picking Option 1 carry a hidden cost the operator hasn't surfaced?
The agent-IDs carve-out is the main concession to cadence. Without it, every routine reviewer dispatch generates a HANDOFF update commit that itself requires a reviewer dispatch — recursive overhead. The carve-out keeps that practical surface low. **Cost surfaced.**

---

## Per-file enumeration vs scope-rule formulation (per reviewer a84df019be0ffb852 PART 5a request)

The amendment as filed lists HANDOFF.md by name. An alternative formulation would be a scope-rule: "any file PHILOSOPHY/V1_SCOPE/HANDOFF/ARCHITECTURE references as load-bearing for operator behavior is implicitly review-required."

**Operator defends per-file enumeration on the following grounds**:

1. **Scope-rule lacks a concrete "load-bearing" test.** "Load-bearing for operator behavior" is itself an interpretive criterion that operators will dispute. The per-file list has no such ambiguity. Per-file enumeration trades expressiveness for unambiguity, which is what an enforcement layer needs.

2. **The current enforcement list IS per-file.** Adding HANDOFF.md keeps the surface internally consistent. Switching mid-stream to a scope-rule would require re-classifying every existing entry under the new rule, which is a much larger change and a much larger blast radius.

3. **Scope-rule would over-include.** PHILOSOPHY transitively references many files (V1_SCOPE references DoD items, ARCHITECTURE references code paths). A literal "transitively referenced = review-required" rule would balloon the surface to include implementation files, tests, even fixtures.

4. **The amendment's own falsifier #3** explicitly anticipates that if a THIRD off-surface load-bearing file emerges, the structural gap should be reconsidered as a scope-rule then. That is the right time for that conversation — when there is concrete evidence the per-file approach has scaled to a problem — not now on a sample of N=1 surfacing.

**Conclusion**: per-file is the correct grain for this amendment. Scope-rule remains a viable future amendment if falsifier #3 fires.

---

## What changes (procedurally, on approval)

1. **Single commit**: append the new line to PHILOSOPHY.md enforcement section path list. Commit message includes `Reviewer-Id: <amendment-reviewer-agent-id>:<diff-hash>` per existing mandate (since PHILOSOPHY.md itself is on the review-required surface). **The Reviewer-Id MUST be from the final-approving v-review** (reviewer `a837fa393d7d7dad0` on v2-final), not from earlier-version reviewers, per reviewer `a837fa393d7d7dad0` P4.

2. **Authorized follow-up scope, NOT pre-decided content (revised per reviewer `a837fa393d7d7dad0` C1)**: An immediate follow-up commit, reviewer-gated under the new regime, will address known stale facts in HANDOFF.md. The specific edits are the follow-up reviewer's call, not pre-decided here. The amendment authorizes the *channel* for those corrections; it does not prescribe their content. (v1 and v2 enumerated four specific edits as planned content; that enumeration is withdrawn because it pre-figured the follow-up review, which is the operator-deciding-ahead-of-reviewer shape the mandate exists to prevent.)

3. **Conditional on human approval** (per reviewer `a84df019be0ffb852` PART 5e + reviewer `a837fa393d7d7dad0` C5): human should condition approval on "next commit after this amendment lands is K=4 corpus capture or another DoD/data item, NOT another governance commit." Operator pre-commits to this. The follow-up HANDOFF stale-fact correction commit (item 2 above) is therefore deferred until after at least one K=4-or-DoD commit lands.

---

## Falsification

This amendment is wrong (and should be revised) if:

1. The chosen option produces ANOTHER fresh-brain reviewer "REQUIRE-AMENDMENT-FIRST" verdict on a HANDOFF-related action within 30 commits. That would indicate Option 1 doesn't actually close the gap (e.g. operators find a sub-pattern that escapes the rule).
2. The chosen option produces a measurable rate of HANDOFF-derived operator errors (>1 per 20 commits where operator acted on a stale HANDOFF fact without cross-checking). Indicates Option 1's friction made operators stop updating the file, leaving cold-start operators with increasingly stale snapshots.
3. A third class of artifact (not HANDOFF, not corpus) emerges with the same load-bearing-but-off-surface property. Indicates the gap is structural and a broader scope-rule is needed instead of per-file enumeration. This triggers a follow-up amendment using the scope-rule formulation described in the per-file-vs-scope-rule section above.

## Alternatives considered (rejected)

1. **Option 2 (HANDOFF stays free-append with disclaimer).** Rejected per reviewer `a84df019be0ffb852` PART 4: Option 2 reintroduces self-imposed discipline as the primary control on a file the operator has demonstrated they want to edit performatively. That is regression to the failure mode the mandate exists to prevent. Operator's earlier "weak preference for Option 2 on cadence grounds" was explicitly down-weighted as self-interested.

2. **Free-append errata to HANDOFF.md without an amendment.** Rejected: reviewer a2c076ed832afc771 already explicitly rejected this shape as rule-4 reinterpretation-via-contradicting-append. Repeating it is rule-5 disputed-precedent.

3. **Bundle this with a corpus-annotation-binding amendment (Amendment B).** Rejected on bundling-rule spirit per reviewer a324347f0284774a6: HANDOFF surface gap and corpus annotation binding are distinct invariant-list changes with different reasoning and different blast radii. File sequential narrow amendments rather than one bundled one.

4. **Wait for a concrete HANDOFF-related failure before amending.** Rejected: the failure mode already concretely fired this session (operator attempted errata, was correctly stopped). The "wait for more failures" stance would be the dd86446 self-classification pattern (operator declares "not load-bearing enough yet").

5. **Scope-rule formulation ("any load-bearing off-surface file is implicitly review-required").** Rejected at this amendment per the per-file-vs-scope-rule defense above. Remains viable for a future amendment if falsifier #3 fires.

6. **Add ALL load-bearing-but-currently-off-surface files (HANDOFF + corpus entries + annotations) to review-required in one amendment.** Rejected: too broad per bundling-rule spirit; corpus-annotation case has a specific live ambiguity (K-numbering convention) that needs to be resolved BEFORE the binding-vs-not decision is even meaningful. That work belongs in Amendment B.

## Reviewer judgment

### Pre-amendment dialogue reviewers (informational)

- Reviewer `ab312708ba406fe7b` (fresh-brain post-compact steer): identified the gap in PART 4 of its output. Confidence 0.72.
- Reviewer `a2c076ed832afc771` (audit of operator's errata-append attempt): REQUIRE-AMENDMENT-FIRST verdict. Confidence 0.78.
- Reviewer `a324347f0284774a6` (multi-problem triage that triggered this amendment): recommended path 2-prime (sequential narrow amendments, A then B). Confidence 0.78.

### Pre-reg amendment reviewer (per protocol clause 5) — v1 round

- Reviewer `a84df019be0ffb852`: REQUEST-CHANGES on v1 of this amendment. Recommended (a) populate the 6-field manifest with verbatim original-rule quote and commit hashes, (b) add the secondary counter-test for "Option 2 legalizes the rejected errata-append," (c) operator pick an option rather than pure delegation, recommended Option 1 with agent-IDs carve-out, (d) defend per-file vs scope-rule, (e) condition human approval on next commit being DoD/data not more governance. Confidence 0.74. All five revision requests are addressed in this v2.

### Pre-reg amendment reviewer (per protocol clause 5) — v2 round

**Reviewer ID**: `a837fa393d7d7dad0`
**Decision**: APPROVE-WITH-CAVEATS
**Reviewer confidence**: 0.78
**Caveats**:
- C1 (applied in v2-final): strike the planned-content enumeration in "What changes procedurally" item 2; replace with channel-authorization only. — DONE
- C2 (applied in v2-final): note that this amendment establishes the rule-6 mandate-amendment format precedent. — DONE (manifest preamble)
- C3 (applied in v2-final): acknowledge that the agent-IDs carve-out's fabricated-ID prevention is cooperative-not-mechanical, bounded by post-hoc git log auditability. — DONE (Field 5 residual risk paragraph)
- C4 (applied in v2-final): soften "3 valid post-fix entries" to "2-3 depending on Amendment B's K-numbering reconciliation." — DONE (Field 3 empirical evidence paragraph)
- C5 (for human, not operator): approval conditioned on next commit being DoD/data not governance. — recorded in Approval section.

**Reviewer's three process observations (P1-P3) noted but not blockers**:
- P1 (cool-down for mandate-scope amendments): suggested as future PHILOSOPHY clarification, not blocker for this amendment.
- P2 (mandate-amendment-cadence concern, "operator amends every time a reviewer flags a gap"): bounded by P1's recommended future cool-down + falsifier #3.
- P3 (don't loop into v3 unless residual disagreement is substantive): operator agrees, applying caveats in v2-final without a v3 review round.
- P4 (Reviewer-Id trailer mechanics): recorded in "What changes procedurally" item 1.

## Approval

(To be filled by user when merging or rejecting.)

**Approval condition (per reviewer `a837fa393d7d7dad0` C5 + reviewer `a84df019be0ffb852` PART 5e)**: human should condition approval on the next commit after this amendment lands being a K=4 corpus capture or another DoD/data item, NOT another governance commit. The HANDOFF stale-fact correction follow-up (this amendment's "What changes procedurally" item 2) is therefore deferred until after at least one K=4-or-DoD commit lands. Operator pre-commits to this condition.
