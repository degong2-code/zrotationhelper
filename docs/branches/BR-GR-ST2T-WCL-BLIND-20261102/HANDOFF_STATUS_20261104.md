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

## 2026-11-04 session successor — source-clock operand

**Current bounded independent Native IF proof: 68/477 matched, 409 UNKNOWN.** Earlier 66/477 (411 UNKNOWN) is the immutable baseline and remains valid for its earlier operand set. Two additional IFs became decidable with a source-backed time operand; all prior 66 still matched.

Source: tools/research/simc_native_if_source_clock_successor_v1.py (Git blob 2bc7fc9d8ea8a8e05ee6aaf248e8eae915024273; tested file SHA256 41e23ede7e0aa5fb7c3ef5b56f5472ca3a7aff96967b0e95cefb2c2860967abd). Native official SimC source commit b522cded8c26b97dac03fdf56e57a03ec7e8faa6, engine/sim/sim.cpp blob ae5c258953787196e0aecad58814ff14d4cd2bed, direct time-to-event_mgr.current_time binding. Existing 477-row ledger SHA256 ebf8a902bff1c1167306217535ac5fc10466bc3a1d4512adc175a2449e7fbd13.

[Actions #41753660425](https://github.com/degong2-code/zrotationhelper/actions/runs/41753660425) SUCCESS: Python 3.12 and 3.14 compile/synthetic plus pinned 477 ledger replay. New receipt SHA256 310eb9f369e537eac5916ebbcb23ea34bc6de558ca34f43b3e359bc76c57d85d. Temporary artifact ID 13286884187 expires 2026-11-11T01:23:24Z. No Native SimC rerun, WCL API, addon or second independent AST implementation. Native truth is used only after independent AST calculation; Native ready is never an operand. Same-time clock observation at IF evaluation is not a WCL Strict PRE state transition.

Repeated unknown symbol incidences (overlapping): talent.slayers_dominance=103; buff.recklessness.up=77; movement.distance=71; buff.whirlwind.stack=39; talent.improved_whirlwind=39; buff.enrage.remains=29; gcd=29. These counts do not add up to independent recoverable cases.

**Next Session Exact Next:** Inspect official player_t::create_expression talent meaning and existing Native reporters, then source-drive passive pre-IF talent-value capture using a generic APL-derived symbol inventory (prioritize talent.slayers_dominance), validate pristine-vs-instrumented ST/2T nonperturbation and independent AST replay. Then consider buff.recklessness.up and variable values; never use selected Native action as a substitute for talent facts.

G2, G4, G5, G6 and G7 complete gates remain NOT ESTABLISHED. General Rotation and target-dummy feedback incomplete, WCL comparison paused. MAIN, FROZEN and global handoff unchanged; Seq578 FAILED_QUARANTINED, Seq637 UNKNOWN.

## 2026-11-04 actual Native talent PRE operand successor

**Latest verified bounded Native IF proof: 210/477 independently AST matched; 267 UNKNOWN.** Previous 68/477 (409 UNKNOWN) remains a valid historical source-clock baseline. This successor adds 142 genuinely decisive IF cases using new passive talent values; all 68 previous cases remain matched.

Actual Native Fury ST and 2-target verification: [Actions #41757998253](https://github.com/degong2-code/zrotationhelper/actions/runs/41757998253) SUCCESS, run HEAD f609bcc81135a92b16a913c32a6c0685a6294474. Python 3.12/3.14 compile and synthetic PASS; official pristine vs instrumented SimC precombat/combat action sequences EXACT match in both scenarios. Previous 214 Native foreground roots, 190 selected source rows and 2,572 action_ready attempts remained structurally reproducible, but those structural proofs still consume Native readiness truth.

Pinned SimC commit b522cded8c26b97dac03fdf56e57a03ec7e8faa6, official Fury APL blob 3225992ed5b754ad5d61e8b785d9d859f1eed1be; official player.cpp blob 88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8 implements actor talent expressions via spec/hero/class lookup and enabled/disabled/rank constant. Source-derived generic IF-only inventory contains FIVE symbols: talent.deep_wounds, talent.improved_whirlwind, talent.lightning_strikes, talent.slayers_dominance, talent.wrath_and_fury. Seven symbols in the profile overall are NOT seven IF symbols.

New producer: tools/research/simc_native_if_talent_pre_instrument_v1.py SHA256 535fbae496684ca57bc75fe1316dfd82b173adc6cc3b5324ed90ca99ae02d4e9.
New independent Python AST reporter: tools/research/simc_native_if_talent_pre_replay_v1.py SHA256 ed7328bef214196257a915e895dea7005e51b7a638475a6cf03d627b7da61125.
Actual receipt SHA256 8fd2df01ebdba7096a3c9c10c9718e168205005f064edbbc4647b8e1f28f6948. Artifact #13288848180 expires 2026-11-11T02:03:07Z. Native IF truth was ONLY postcomputed comparator; Native readiness was never an AST operand; no WCL API calls, no addon validation, no independent second AST implementation.

Historical failures preserved: #41757715589 FAIL due synthetic test exception-class mismatch; #41757774893 FAIL due CI erroneously expecting seven profile-wide talents instead of five IF-only talents. These are not Native semantic failures. Successor #41757998253 supersedes implementation defects, without altering prior receipts.

**Session Exact Next:** inspect unknown operand incidence in the retained 210/477 receipt first; then add the highest-value official Native source-backed mutable buff/conditional operand (potentially buff.recklessness.up), with generic source-derived symbol inventory and nonperturbation ST/2T gate. Replay 477 real IFs via existing Python AST, never infer readiness, and avoid WCL or addon expansion. General Rotation remains incomplete. G2/G4/G5/G6/G7 final gates NOT proven; MAIN/FROZEN/global handoff untouched; Seq578 FAILED_QUARANTINED, Seq637 UNKNOWN.
