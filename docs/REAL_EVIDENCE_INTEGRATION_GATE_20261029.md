# Research core — real evidence integration gate (2026-10-29)

**Type:** branch-local integration audit; historical source evidence, no canonical MAIN promotion.

## What was discovered after source-backtracking

A partial recreation of the research evaluator in the GitHub bootstrap branch was at risk of duplicating work already completed in MAIN research sequences 617–623.

- Seq617–618: generic state/condition/action evaluator and ordered IF/ELSE synthetic research.
- Seq619–620: **785 real SimC-source decision samples** processed by the same generic evaluator across Enhancement/Fury (442+343); independent review was reported in the historical MAIN handoff.
- Seq621–623: research on printed source-state lifetime and decision-relative timestamps. A directly inspected Seq623 reconciliation CSV contains **785 rows**, with a pinned raw SHA256 `5ed9e9efa4b6d4a9d0dba5f542ba7aafaecdcfb51ac275f79e8a3c4c1e1655e9`:
  - Enhancement **442**: `WITHIN_PRINTED_DURATION_WINDOW=237`, `AMBIGUOUS_LAST_REFRESH=68`, `INVALIDATED_BY_LATER_SOURCE_CHANGE=137`;
  - Fury **343**: `WITHIN_PRINTED_DURATION_WINDOW=343`;
  - **all 785 readiness=UNKNOWN**; claim labels all `SIMC_SOURCE_EQUIVALENCE_RESEARCH_ONLY`.
- Real pinned profile files from the MAIN handoff:
  - Enhancement Seq616 baseline `probe.simc`: SHA256 `3ce833659dd301921371844364e92f36dd698017f42f34a5bece3fb8f4937297`, 113 APL action lines;
  - Fury Seq619 source `source_profile.simc`: SHA256 `5b51405a71ac74ec7200a312b971a3cc812cdfc3e8637617fcf205f23cec0c4c`, 121 APL action lines.
- Historical Seq634 result: `NO_ELIGIBLE_TARGET_COHORT__MAIN_REGISTRY_UNVERIFIED`, eligible targeted cohorts **0**.
- Seq635 source intake: `PASS_PINNED_SOURCE_CONTENT_CAPTURE_ONLY`, `current_main_authority_certified=false`, `live_wcl_validated=false`.
- Seq636 scoped behavioral audit: source projection is **not** a behavioral evaluator. Seq637 package is an offline source-intake tool; its actual user-PC output/approval is **UNKNOWN**.

**Interpretation:** Existing SimC decisions and source-state alignment are real research assets, but are **not** real WCL independent cohort/behavioral replay, full action readiness, or validated gameplay recommendations. They must not be counted as those things.

## Concrete omissions in the current public GitHub research prototype

- `simc_apl_condition_research.py` evaluates limited **explicitly bound** numeric guards with strict-PRE controls; it does not execute `variable` assignments, `value_else`/operation state updates, full nested `call_action_list`/`run_action_list`, `target_if`, spell readiness, or cooldown/charge semantics.
- `post_lock_simc_wcl_guard_replay.py` aligns guards for one mapped observed numeric action. `GUARD_FALSE_DISCREPANCY_CANDIDATE` **does not** prove the SimC APL would recommend another action, nor that a WCL choice was wrong. Its local synthetic lock schema proves only file integrity/shape, **not independent blind discovery**.
- `BehavioralEvaluator` evaluates already-supplied rules and readiness; it does not independently reconstruct them or certify readiness from log events.
- None of these files is currently a MAIN-approved production General Rotation provider.

## Acceptance gates for the next *real* integration step

1. **Current MAIN identity.** Obtain current approved `LATEST_HANDOFF`, `CURRENT_STATE`, and active source/IR manifest; verify exact source hashes and whether the sequence-617–623 evaluator has a newer approved successor. Without these, mark `MAIN_ACTIVE_SOURCE=UNKNOWN` and do not replace it.
2. **Real source cohorts.** Identify at least one **authorized, build-matched** WCL cohort with report/fight/actor/spec/build/source-timestamp identity and eligibility checks. Keep raw/private data outside the public GitHub repo. Without qualifying cohorts, `REAL_WCL_REPLAY=BLOCKED_NO_ELIGIBLE_COHORT`.
3. **Blind lock isolation.** Independently discover/lock numeric/structural WCL candidate state/action identities, record SHA and provenance **before** semantic reconciliation. A JSON flag declaring “LOCKED” is insufficient scientific proof.
4. **PRE/readiness.** Build state strictly from valid events with timestamps preceding each cast; retain feature provenance/expiry and `UNKNOWN` for missing readiness or unsupported SimC operands.
5. **Actual replay.** Use the approved APL/profile (profile hash + spec/build/version), verified name→numeric-ID bindings, independently locked WCL candidate set, and source-derived PRE observations. Report `match/conflict/missing/unknown` **only where the compared object is identifiable**. Do not equate guard concordance with actionable predicted-action concordance.
6. **Claims and holdout.** Treat data alignment as research-only until independent holdout/confounder review; use selective SimC counterfactual for user-facing priority ambiguity.

## Efficiency decision

**Do not** rerun the existing 785 source-side SimC decisions, rewrite Seq617–623 from scratch, repeat synthetic CI without a new behavior, or upload historical private logs or Windows-local paths. The next meaningful code change should reuse the **latest MAIN-owned verified actual evaluator/source provider** and an **eligible WCL fixture**, once identified. The present branch remains an isolated research tooling pilot.

No live WCL or SimC execution, MAIN promotion, Seq637 status change, Seq578 reopening, or FROZEN mutation is claimed.
