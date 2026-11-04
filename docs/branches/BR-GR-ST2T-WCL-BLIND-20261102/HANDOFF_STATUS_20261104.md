# Current verified project checkpoint — 2026-11-04
**Product policy:** ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1 (unchanged).
**Branch:** work/gr-simc-st-2t-wcl-blind-20261102. **Baseline HEAD before handoff docs:** 502e2e9c8364034d7b485c86aa5d49bcc0d8476b; **MAIN observed:** 4790f77f76a75f26ff0558d1d18c16cd9d630c4b. Any subsequent handoff commit changes branch HEAD; the next chat MUST query it directly.
**Detailed historical log:** CURRENT_STATUS_20261102.md (preserved). **Feature reuse/receipts:** FEATURE_EVIDENCE_REUSE_INDEX_20261104.md. **Engine completion gate:** SIMC_APL_MODEL_COMPLETION_CONTRACT_20261103.md.

## Purpose and roadmap
Long-term reusable Engine: official patch source + SimC-first opener and conditional priority hypothesis → independent locked WCL discovery/Strict PRE → post-lock comparisons and mechanics reconciliation → evidenced ST/2-target/cleave/AoE General Rotation IF/ELSE → lightweight target-dummy feedback (real-time only if legal/observable, else post-session). Never resume encounter-specific raid/NSRT plans.

**Active short-term priority, explicitly selected by user:** finish **accurate SimC APL → runnable General Rotation model** before additional WCL comparisons or addon work.

## Honest state by proof type
- **Source parsing**: Fury 121/121 and Enhancement 114/114 native-profile source AST lines PASS (CI 41563832907). Only *syntax coverage* generalized to Enhancement, not full behavior.
- **Effective model identity**: Fury official Native SimC effective APL 121/121 source rows match (CI 41563013349). Source model including precombat, CALL/RUN, Slayer/Thane route generated (CI 41565944271), still a hypothesis.
- **Actual Native chosen APL rows**: 214 foreground scans ST 118 / two target 96, 190 selected rows ST 100 / two target 90; Native source-pointer structural replay conditional on Native ready() bits passed (CI 41580466416). This is NOT independent source readiness.
- **Native IF evaluation boundary**: 2,572 ready() attempts; 477 actual IF evaluations (255 ST / 222 2T), 142 true/335 false, 2,095 IF not observed (CI 41582637785). IF not observed is NOT equivalent to FALSE.
- **Independent bounded AST proof**: From native PRE Rage and active_enemies facts, 3 fully-known numeric + 63 logical partial = **66/477** matched native IF; remaining **411 UNKNOWN**. True Native result used for post-calculation comparison, not as a value/operand. Full native sequence nonperturbation passed ST and 2T (CI 41584822737).
- **Fast reuse**: frozen 477-row evidence rechecked in offline CI 41585210821, same Python evaluator; not second independent oracle, no Native recompilation.
- **Previously obtained WCL**: Discovery 54 casts + separate-report holdout 51 casts, actual WCL evidence obtained (CI 41463589665 / 41473060401); currently paused. Old handoff flag NOT_COLLECTED obsolete and MUST NOT be inherited.
- **Training**: ZRotDummyProbe research-only mock client, real in-game not tested. Product feedback and player wrong-cast evaluator NOT validated.
- **No completed playable model**: full opener, post-opener IF/ELSE, buffs/procs/cost/CD/charge/GCD, variable effects, exact hero/build, second-spec Native decision parity, live dummy validation are all incomplete. Never infer READY or mark player errors from missing observations.

## Distinguish deficiency types
- **Evidence missing**: 411/477 IF evaluations need bounded, trustworthy source operands (first native buff.recklessness.up, hero talents, variable.*). Full skill-ready operands/alternates are not captured.
- **Implementation/semantic gap**: complete variable mutation, native per-decision if-expression and readiness reasons, persistent list transitions, opener sequencing & end conditions, target switching, independent source AST parity for major cases.
- **Product linkage missing**: conditional source hypothesis cannot yet become validated user-facing General Rotation; no causal WCL priority claim, no in-game target-dummy evaluation.
- **External data constraint**: time-limited GitHub artifacts around 2026-11-10; missing archive on later chat is not an engine bug.

## Next steps
**Product Exact Next:** finish generic SimC APL execution / opener and condition model, validate against Native execution across ST/2T/AoE/builds; then locked WCL replay + Blizzard mechanics + selective holdout/counterfactual; then trainer.
**Session Exact Next (only AFTER user's explicit '진행'):** inspect existing SimC operand/resource/variable source producers and pinned ledger; implement minimum generic provenance-gated pre-IF operand provider for buff.recklessness.up, hero-talent state and variable.* where official source permits; replay the existing 477 rows offline first, run actual Native once only for new observational facts; compare decisions without Native truth leakage, preserving UNKNOWN. Batch independent changes and reuse same acceptance matrix.
**First new-chat reply:** READ-ONLY verify actual GitHub branch HEAD/policy/parent handoff/CI and report restoration, blockers and short/long roadmap; STOP. No coding, pushes, tests, simulations, API calls, Actions dispatch, commits or promotion until '진행'.
