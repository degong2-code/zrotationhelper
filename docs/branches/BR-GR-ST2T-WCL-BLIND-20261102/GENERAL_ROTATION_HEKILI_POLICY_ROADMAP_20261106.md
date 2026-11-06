# General Rotation + Dummy Trainer — Hekili-informed, Blizzard-compliant roadmap successor

**2026-11-06 / BRANCH ONLY / DRAFT FOR MAIN REVIEW.** The official product remains `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. This is a **roadmap successor**, not a rewrite of the product lock, MAIN-owned global roadmap, shared architecture contract, production manifest, current pointers or FROZEN historical evidence.

## 0. Decision and dependency rule

Borrow Hekili's architectural concepts — nested APL evaluation, state transitions, per-candidate reasons, spec-specific mechanics, reproducible snapshots — not its old live combat-state collection or in-game recommendation behavior. Keep **General Rotation research and practice evaluation entirely operational outside the WoW client**. The addon only obtains supported non-secret events/fields and displays bounded training information.

Reject the false choice "either rebuild Hekili as a live solver or do no useful training": a **verified post-session evaluator** can be valuable without prohibited live decision support. The educational objective does not erase policy/API constraints.

**Product sequence is still:** SimC-first hypothesis → WCL independent blind observation/candidate lock → source-state replay, Blizzard mechanic reconciliation, selective counterfactual and independent holdout → trusted ST/2T/AoE opener + conditional priority IR → opt-in target dummy practice comparison.

## 1. Current verified facts (do not overclaim)

- Source-pinned official SimC 4-case Native A/B, [Actions #42140591685](https://github.com/degong2-code/zrotationhelper/actions/runs/42140591685) **PASS**, four Native C++ scenarios Fury and Arcane ST/2T. The source selection collector/replay recorded **2,121 exact select_action sweeps**, 262 top-level source returned rows, 68 child-propagated returns and 1,774 null-exhausted returns; **many are control/list actions** rather than a spell cast.
- Prior source actor/mana PRE, [Actions #42136432768](https://github.com/degong2-code/zrotationhelper/actions/runs/42136432768) PASS: 4,682 root PRE; independently computed source IF ↔ Native **209 matches, 0 conflicts** with 46 Fury2T and 163 Arcane ST/2T; **not 209 damage/priority rules**.
- No source-exhaustive independent full positive READY closure; **0** proven; target-dummy error-feedback verdict **not authorized**. These are structural source observations, not performance/optimality claims.
- Existing `addons/research/ZRotDummyProbe` is a research-only, bounded opt-in candidate, **not real client tested**, and not production; do not silently promote it.
- Hekili legacy source and HekiLight user ZIP analyzed: architecture/design only, not current Retail permitted executable algorithms or an independent WCL truth source.

## 2. Short-term critical path — implement in highest user-value order

| Step | Precise next deliverable | Reuse Hekili concept | Proof / done gate | Why now |
|---|---|---|---|---|
| S1. Explain one original chosen action and its preceding candidates | **`SourceDecisionReasonLedgerV1`**: same C++ sweep, chosen source action row, prior rows, ordered negatives with typed `IF_FALSE`, `NATIVE_POST_FALSE_ONLY`, `BACKGROUND`, `CONTROL`, `WAIT`, `UNKNOWN`. Prevent cross-timestamp/sweep leakage. | `Core.lua` per-action reject diagnostics + `Hekili.lua` snapshot | Replay existing 2,121 sweeps/262 returned rows. Independently source-proven IF FALSE may label **that source gate**; Native false alone may NOT become independently proven NOT_READY. Add synthetic forged-method/cross-sweep negative test. | Direct route from current code to "why A was selected" rather than more PASS counter counts. |
| S2. Build explicit semantics and state inputs | Add `SpecAdapter` capability list for high-impact physical spell: requirement, replacement, resources, buff/proc, cooldown/charges, GCD, target, pooling/execute, readiness provenance. Typed `StateSnapshot` and immutable transition `real vs hypothetical`. | `Classes.lua` registration and `State.lua` virtual advancement | At least one real damage skill winner and earlier candidate independently fully assessed in 1T and 2T, with all missing gates declared UNKNOWN; no flat "full_READY=true" metadata without source walk. | Needed for actual conditional IF/ELSE and opener, not UI imitation. |
| S3. First user-facing General Rotation vertical slice | `GeneralRotationIR` for one current specialization/build covering opener and next 30s, ST and 2T transitions; typed human-readable reason codes and original spell identity/localization. | Nested APL, pack/list/condition decomposition | Deterministic replay of seeded build/context and 4-case source witnesses; `MATCH/CONFLICT/UNKNOWN` with full evidence; then second spec to prove generic layer. | Gives product functionality, not generic scaffolding. |
| S4. Independent WCL resolution | Fresh lawful WCL top-ranker collection, source identity, STRICT_PRE before action, numeric/structural candidate/threshold lock **without SimC/Hekili answer leak**. Post-lock SimC baseline and Blizzard fact reconciliation; independent holdout/target-count breaks. | None; Hekili is not an independent validation source | Candidate lock receipt fixed **before** holdout; thresholds frozen; missing readiness UNKNOWN; no boss-specific plan | Keeps precision and applicability to real user play. |

Avoid unnecessarily rebuilding full Native C++ on every doc/AST change; first cheap synthetic/deterministic replay of existing actual source receipts. Use C++ E2E only for newly instrumented high-impact operands or behavior-changing trace changes. Separate pipeline fault from hypothesis failure.

## 3. Medium/long-term product roadmap

| Stage | Deliverable | Dependency / acceptance |
|---|---|---|
| M1. Generalize model | ST, 2T, cleave, AoE, breakpoint, opener, talent/build alternatives, proc/buff/CD/charges, pooling, execute, fight-remains and sequence state | S1–S4 evidence; clear source patch/build/model version, negative/UNKNOWN and confidence |
| M2. Evidence-bounded Dummy Practice Evaluator | Compare own-cast action sequence with validated model at applicable PRE. Human-readable "actual → expected → state → why → corrective action"; explicit `UNKNOWN` when missing. | M1 versioned IR, per-cast source identity/readiness and independent WCL; no invented action-state |
| M3. Official Retail 12.1.5 API capability matrix and tiny recorder | Addon opt-in own cast/safe spell IDs, bounded session tracking, SavedVariables, user-controlled session start/stop, basic localization/icons | Real in-client target-dummy test + secret/forbidden per-field checks; mocked Lua CI does **not** count as real-client PASS. No player input/action manipulation |
| M4. External log/session import + feedback loop | WoW native `/combatlog` or permitted own-event export → offline parser → Strict PRE → practice receipt; lightweight in-game summary only if transport/UI permitted | Real dummy session source data and latency. No direct WoW Lua read of arbitrary file, no injected bridge |
| M5. User validation and patches | Test multiple specs/builds/target counts; error reason usefulness, localization, zero false-mistake assertions; patch/hotfix contract refresh | In-client user test, WCL/SimC independency, issue snapshots without protected/secret data |
| M6. Optional live cue | Restricted to **official, directly documented and client-verified safe fields**, no personalized combat decision automation | Only if materially better than post-session and compliant. **Not required** for success; can stay excluded |

## 4. Generic contracts to add after source proof, not before

1. **`CandidateEvaluation`**: list/ordinal/action/build/target count, each predicate/operand, source/observation confidence, source IF result, independently verified ready result, chosen/alternative paths, explicit reject reason.
2. **`StateSnapshot`**: time, actor, spell/talent/mechanics, buff/debuff/resource/cooldown/charge and provenance. Split `REAL_OBSERVATION` versus `SIMULATED_COUNTERFACTUAL`; do not mix simulated values with observed PRE.
3. **`DecisionExplanationReceipt`**: selected candidate, nearest feasible alternative, earlier exclusions and why, source/holdout confidence. The UI shows concise localized text and icons, source detailed receipts live outside the addon.
4. **`AddonCapabilityReceipt`**: current patch, API/event, own player/dummy context, observable fields and secret status, actual client proof, safe persistence, decision state `SUPPORTED / NOT_SUPPORTED / UNKNOWN`.
5. **`PracticeVerdict`**: `MATCH` / `CONFLICT` / `UNKNOWN`; only CONFLICT with source/readiness closure and baseline evidence becomes a candidate learning correction, never merely "Hekili would have suggested this".

## 5. Safety / compliance milestone gates

- Offline Hekili **model structure** is permitted as a design reference; never use an old `COMBAT_LOG_EVENT_UNFILTERED`-dependent Hekili addon as a current source of privileged combat observation.
- Strict split between Blizzard first-party Assisted Combat and **our offline independently validated priority**; HekiLight secondary icons are not a future temporal rotation.
- Never use HekiLight's secret-number exception side-channel or alternatives (UI/Frame visibility, timing, layout, error behavior). Unavailable = `UNKNOWN`.
- Real 12.1.5 addon tests only for opt-in, non-secret own spell recording and UI, with safety case and ability to disable capture; in combat never autonomously choose targets/spells, call protected action functions, inject hooks, read client memory or outside files.
- Historical mirror of Blizzard's old addon distribution policy is **not** a fresh official direct review; policy doc records this provenance. Current Blizzard policy direction is confirmed from official 2025-26 articles.
- Do not promote branch reference policies to shared MAIN/contracts/manifest without MAIN owner.

## 6. What will be deferred or consciously dropped

- Reimplementing Hekili’s entire Lua parser, 8,100-line game-state engine or 2,000+line per-spec live scripts. **Current Python typed APL source parser and native replay already exist.**
- Live 5-ability prediction queue on the user's game screen, raid encounter timing, NSRT exports and boss-specific plan.
- Broad in-game enemy counting/debuff inference; virtual state via secret values; policy-evasive error handling.
- Infinite "verify → block → verify" without producing a user-facing conditional rule or a stronger decision certificate.
- Automatic labeling of 262 observed source returns or 209 IF comparisons as 262 skill choices / 209 validated priority rules.

## 7. Milestone status and next exact action

| Contract | Status, 2026-11-06 |
|---|---|
| Hekili architectural source provenance and official policy research preserved | **DOCUMENTED / BRANCH_LOCAL** (not MAIN-promoted) |
| Fury/Arcane 1T/2T original source selected return | **ACTUAL_NATIVE_PASS** for bounded 2,121 selection sweeps; not independent full ready |
| Hekili-style `SourceDecisionReasonLedgerV1` implementation | **NOT IMPLEMENTED**, next engineering output |
| Complete independent positive READY + validated full opener/priority | **UNKNOWN / INCOMPLETE** |
| Current WCL blind candidate lock + independent holdout for this returned-source IR | **NOT RUN** |
| Retail client dummy addon observing, persisting and comparing actual practice | **NOT LIVE-TESTED / NO PRODUCT VERDICT** |

**Session Exact Next:** use existing actual Native selection-return and root PRE receipts to implement `SourceDecisionReasonLedgerV1` — chosen source action path and provenance-labeled prior candidate exclusion; keep underivable readiness UNKNOWN. Separately plan minimal current-API client proof using existing `ZRotDummyProbe` without elevating live combat judgment.

**Product Exact Next:** complete specialization+build General Rotation opener and conditional priority across ST/2T/AoE; validate with independent WCL; apply same evidence-bounded model to a player's target-dummy practice and explain mistakes only when verified.

**Future read order:** product scope lock → product scope prose → AGENTS + Engine-first Charter → branch LATEST_HANDOFF → current feature evidence index → `HEKILI_ARCHITECTURE_REFERENCE_20261106.md` → `RETAIL_ADDON_POLICY_CAPABILITY_GATE_20261106.md` → this roadmap → source/native evidence. This does not change the mandatory authoritative scope read order.
