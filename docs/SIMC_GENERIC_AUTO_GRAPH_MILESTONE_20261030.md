# zRotationHelper — Generic SimC Automatic Decision Graph Milestone (2026-10-30)

Status: **BRANCH VALIDATED FOR SOURCE STRUCTURE ONLY; NOT MAIN APPROVED**.

## Product criterion — mandatory self-audit

Build one generic research engine that **knows how to automatically derive conditional rotation hypotheses from any input SimC APL/profile**. Producing one Enhancement Shaman rotation or hand-coding any of 27 specs is not the deliverable. Encounter-specific semantics must not be hardcoded into the generic layer. Each follow-up must ask whether a feature increases cross-spec engine capabilities, improves validated IF/ELSE accuracy, or merely patches one fixture.

Research architecture: SimC-first semantic/conditional hypothesis bootstrap **in parallel with independently blind WCL discovery**. Do not inject SimC answers into the independent WCL cohort before candidate lock. Replay/compare only afterward, then evaluate Blizzard truth, selective counterfactual and independent holdout. Retain strict PRE (`timestamp < decision_time`), UNKNOWN readiness, lifecycle, Seq637 UNKNOWN, Seq578 and all FROZEN baselines untouched. MAIN alone promotes.

## Implementation delivered (research branch only)

- `tools/research/simc_apl_decision_graph.py` compiles the existing `ZrotGenericSimcConditionalPriorityStructuralIRV1` **without reparsing source** into `ZrotSimcGenericSymbolicDecisionGraphV1`.
- Per-row IF/ELSE arcs distinguish guard true/false/UNKNOWN; action READY/NOT_READY/UNKNOWN/UNOBSERVABLE; nested call continuation vs run-list no-fallthrough; unsupported variable/control semantics and non-guard action modifiers fail closed. Every original source row maps once, with source-APl SHA and source line preserved; precombat is separated.
- Automatically emits required readiness tokens and operand namespaces. Operand namespaces are **grammar only**, not trusted Blizzard mechanics, measured PRE transitions, or readiness evidence.
- Ingestor now supports upstream actor directives `deathknight` and `demonhunter` in addition to legacy underscored spellings.
- SimC `opts::parse` delegates to `util::string_split(..., ",")` where `skip_empty_entries=true` by default (source `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`, `engine/sim/option.cpp` and `engine/util/util.hpp`). Research syntax parser now mirrors that behavior for APL options and **records** the count of ignored empty modifiers; the source/model/IR/graph keep normalization provenance. This unblocked official Havoc APL line 57 `actions+=/immolation_aura,,if=...`, without silently inventing an option.

## Pinned public source regression and held-out generalization

Fixed upstream source SHA: `710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.

GitHub Actions run https://github.com/degong2-code/zrotationhelper/actions/runs/41007507492 — **SUCCESS**.
GitHub Actions https://github.com/degong2-code/zrotationhelper/actions/runs/41007507583 — **Python 3.12/3.14 offline CI SUCCESS**.

| Pinned public source profile | Spec | APL rows preserved | Action candidate rows | Nature |
| --- | --- | ---: | ---: | --- |
| `MID2_Shaman_Enhancement.simc` | enhancement | 114 | 99 | Existing structural comparison |
| `MID2_Warrior_Fury.simc` | fury | 121 | 94 | Existing structural comparison |
| `MID2_Death_Knight_Unholy.simc` | unholy | 63 | 39 | New held-out source |
| `MID2_Demon_Hunter_Havoc.simc` | havoc | 46 | 35 | New held-out source; exposes valid empty option slots |

All are `SOURCE_DERIVED_HYPOTHESIS_ONLY`: same generic generator, no spec-specific generated rules or hardcoded action names. The initial four-spec holdout failed on Havoc's upstream option syntax, exposed a **pipeline coverage deficiency**, and passed only after a generic parser correction; the original failure is retained in run `41007296325`.

**Proof boundary:** This is 4/4 sampled source profiles for structural parsing and symbolic graph construction, **not** 4/27 validated specialization rotations, not SimC native action parity, not proven runtime IF/ELSE recommendations, and not WCL discovery. The historical 785 cases are regression data, not an engine.

## Required follow-up — no duplicate interpreter

1. **Connect the generated graph to the existing** `simc_apl_priority_trace.py` evaluator or derive the same core evaluation primitive; do not develop a second competing APL runtime with duplicated semantics. Compare generated IF/ELSE decisions across independently supplied valid state/readiness fixtures, fail-closed on missing features. Make the execution path accept an arbitrary new spec/profile without coding its abilities.
2. Cover actual SimC expression/control semantics incrementally according to observed **cross-profile blockers**, not individual boss or spell names: variables over scans, nested lists, target_if, target selection, use_item options, pooling, cooldown/charges, timing.
3. Once the generic runtime produces state-conditioned recommendations, compare with **certified** native SimC foreground decisions and valid Strict PRE; do not treat JSON2 equal-time samples as PRE. Only then compare to independently locked WCL candidates and Blizzard truth.
4. Future generalization checks should include input profiles not used to author fixes and measure **semantic** coverage, not just row counts. High-impact UNKNOWN states stay UNKNOWN.
5. The research branch may offer a MAIN merge handoff, but cannot modify MAIN `CURRENT_STATE`, global `LATEST_HANDOFF`, active manifest, FROZEN, Seq578, or Seq637.

MAIN local authoritative state, Work OS Runtime and actual current active Manifest remain **UNKNOWN** in this chat. No MAIN promotion, no WCL live call, and no user-private profile capture in this milestone.
